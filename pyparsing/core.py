#
# core.py
#
import string
import copy
import sys
import warnings
import re
import sre_constants
from collections.abc import Iterable
import traceback
import types
from operator import itemgetter
from functools import wraps
from threading import RLock

from .util import (
    _FifoCache,
    _UnboundedCache,
    __config_flags,
    _collapseAndEscapeRegexRangeChars,
    _escapeRegexRangeChars,
    _bslash,
    _flatten,
)
from pyparsing.exceptions import *
from pyparsing.actions import *
from pyparsing.results import ParseResults, _ParseResultsWithOffset

_MAX_INT = sys.maxsize
str_type = (str, bytes)

#
# Copyright (c) 2003-2019  Paul T. McGuire
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

__version__ = "3.0.0a1"
__versionTime__ = "24 Feb 2020 02:17 UTC"
__author__ = "Paul McGuire <ptmcg@users.sourceforge.net>"


class __compat__(__config_flags):
    """
    A cross-version compatibility configuration for pyparsing features that will be
    released in a future version. By setting values in this configuration to True,
    those features can be enabled in prior versions for compatibility development
    and testing.

     - collect_all_And_tokens - flag to enable fix for Issue #63 that fixes erroneous grouping
       of results names when an And expression is nested within an Or or MatchFirst;
       maintained for compatibility, but setting to False no longer restores pre-2.3.1
       behavior
    """

    _type_desc = "compatibility"

    collect_all_And_tokens = True

    _all_names = [__ for __ in locals() if not __.startswith("_")]
    _fixed_names = """
        collect_all_And_tokens
        """.split()


class __diag__(__config_flags):
    """
    Diagnostic configuration (all default to False)
     - warn_multiple_tokens_in_named_alternation - flag to enable warnings when a results
       name is defined on a MatchFirst or Or expression with one or more And subexpressions
     - warn_ungrouped_named_tokens_in_collection - flag to enable warnings when a results
       name is defined on a containing expression with ungrouped subexpressions that also
       have results names
     - warn_name_set_on_empty_Forward - flag to enable warnings whan a Forward is defined
       with a results name, but has no contents defined
     - warn_on_multiple_string_args_to_oneof - flag to enable warnings whan oneOf is
       incorrectly called with multiple str arguments
     - enable_debug_on_named_expressions - flag to auto-enable debug on all subsequent
       calls to ParserElement.setName()
    """

    _type_desc = "diagnostic"

    warn_multiple_tokens_in_named_alternation = False
    warn_ungrouped_named_tokens_in_collection = False
    warn_name_set_on_empty_Forward = False
    warn_on_multiple_string_args_to_oneof = False
    warn_on_match_first_with_lshift_operator = False
    enable_debug_on_named_expressions = False

    _all_names = [__ for __ in locals() if not __.startswith("_")]
    _warning_names = [name for name in _all_names if name.startswith("warn")]
    _debug_names = [name for name in _all_names if name.startswith("enable_debug")]

    @classmethod
    def enable_all_warnings(cls):
        for name in cls._warning_names:
            cls.enable(name)


# hide abstract class
del __config_flags

# build list of single arg builtins, that can be used as parse actions
singleArgBuiltins = [sum, len, sorted, reversed, list, tuple, set, any, all, min, max]

_generatorType = types.GeneratorType

alphas = string.ascii_uppercase + string.ascii_lowercase
nums = "0123456789"
hexnums = nums + "ABCDEFabcdef"
alphanums = alphas + nums
printables = "".join(c for c in string.printable if c not in string.whitespace)


def _trim_arity(func, maxargs=2):
    "decorator to trim function calls to match the arity of the target"

    if func in singleArgBuiltins:
        return lambda s, l, t: func(t)

    limit = 0
    found_arity = False

    def extract_tb(tb, limit=0):
        frames = traceback.extract_tb(tb, limit=limit)
        frame_summary = frames[-1]
        return [frame_summary[:2]]

    # synthesize what would be returned by traceback.extract_stack at the call to
    # user's parse action 'func', so that we don't incur call penalty at parse time

    LINE_DIFF = 7
    # IF ANY CODE CHANGES, EVEN JUST COMMENTS OR BLANK LINES, BETWEEN THE NEXT LINE AND
    # THE CALL TO FUNC INSIDE WRAPPER, LINE_DIFF MUST BE MODIFIED!!!!
    this_line = traceback.extract_stack(limit=2)[-1]
    pa_call_line_synth = (this_line[0], this_line[1] + LINE_DIFF)

    def wrapper(*args):
        nonlocal found_arity, limit
        while 1:
            try:
                ret = func(*args[limit:])
                found_arity = True
                return ret
            except TypeError:
                # re-raise TypeErrors if they did not come from our arity testing
                if found_arity:
                    raise
                else:
                    try:
                        tb = sys.exc_info()[-1]
                        if not extract_tb(tb, limit=2)[-1][:2] == pa_call_line_synth:
                            raise
                    finally:
                        try:
                            del tb
                        except NameError:
                            pass

                if limit <= maxargs:
                    limit += 1
                    continue
                raise

    # copy func name to wrapper for sensible debug output
    func_name = "<parse action>"
    try:
        func_name = getattr(func, "__name__", getattr(func, "__class__").__name__)
    except Exception:
        func_name = str(func)
    wrapper.__name__ = func_name

    return wrapper


def conditionAsParseAction(fn, message=None, fatal=False):
    """
    Function to convert a simple predicate function that returns True or False
    into a parse action. Can be used in places when a parse action is required
    and ParserElement.addCondition cannot be used (such as when adding a condition
    to an operator level in infixNotation).

    Optional keyword arguments:

    - message = define a custom message to be used in the raised exception
    - fatal = if True, will raise ParseFatalException to stop parsing immediately; otherwise will raise ParseException

    """
    msg = message if message is not None else "failed user-defined condition"
    exc_type = ParseFatalException if fatal else ParseException
    fn = _trim_arity(fn)

    @wraps(fn)
    def pa(s, l, t):
        if not bool(fn(s, l, t)):
            raise exc_type(s, l, msg)

    return pa


def _defaultStartDebugAction(instring, loc, expr):
    print(
        (
            "Match "
            + str(expr)
            + " at loc "
            + str(loc)
            + "(%d,%d)" % (lineno(loc, instring), col(loc, instring))
        )
    )


def _defaultSuccessDebugAction(instring, startloc, endloc, expr, toks):
    print("Matched " + str(expr) + " -> " + str(toks.asList()))


def _defaultExceptionDebugAction(instring, loc, expr, exc):
    print("Exception raised:" + str(exc))


def nullDebugAction(*args):
    """'Do-nothing' debug action, to suppress debugging output during parsing."""
    pass


class ParserElement:
    """Abstract base level parser element class."""

    DEFAULT_WHITE_CHARS = " \n\t\r"
    verbose_stacktrace = False

    @classmethod
    def _trim_traceback(cls, tb):
        while tb.tb_next:
            tb = tb.tb_next
        return tb

    @staticmethod
    def setDefaultWhitespaceChars(chars):
        r"""
        Overrides the default whitespace chars

        Example::

            # default whitespace chars are space, <TAB> and newline
            OneOrMore(Word(alphas)).parseString("abc def\nghi jkl")  # -> ['abc', 'def', 'ghi', 'jkl']

            # change to just treat newline as significant
            ParserElement.setDefaultWhitespaceChars(" \t")
            OneOrMore(Word(alphas)).parseString("abc def\nghi jkl")  # -> ['abc', 'def']
        """
        ParserElement.DEFAULT_WHITE_CHARS = chars

        # update whitespace all parse expressions defined in this module
        for expr in _builtin_exprs:
            if expr.copyDefaultWhiteChars:
                expr.whiteChars = chars

    @staticmethod
    def inlineLiteralsUsing(cls):
        """
        Set class to be used for inclusion of string literals into a parser.

        Example::

            # default literal class used is Literal
            integer = Word(nums)
            date_str = integer("year") + '/' + integer("month") + '/' + integer("day")

            date_str.parseString("1999/12/31")  # -> ['1999', '/', '12', '/', '31']


            # change to Suppress
            ParserElement.inlineLiteralsUsing(Suppress)
            date_str = integer("year") + '/' + integer("month") + '/' + integer("day")

            date_str.parseString("1999/12/31")  # -> ['1999', '12', '31']
        """
        ParserElement._literalStringClass = cls

    def __init__(self, savelist=False):
        self.parseAction = list()
        self.failAction = None
        # ~ self.name = "<unknown>"  # don't define self.name, let subclasses try/except upcall
        self.strRepr = None
        self.resultsName = None
        self.saveAsList = savelist
        self.skipWhitespace = True
        self.whiteChars = set(ParserElement.DEFAULT_WHITE_CHARS)
        self.copyDefaultWhiteChars = True
        self.mayReturnEmpty = False  # used when checking for left-recursion
        self.keepTabs = False
        self.ignoreExprs = list()
        self.debug = False
        self.streamlined = False
        self.mayIndexError = True  # used to optimize exception handling for subclasses that don't advance parse index
        self.errmsg = ""
        self.modalResults = True  # used to mark results names as modal (report only last) or cumulative (list all)
        self.debugActions = (None, None, None)  # custom debug actions
        self.re = None
        self.callPreparse = True  # used to avoid redundant calls to preParse
        self.callDuringTry = False

    def copy(self):
        """
        Make a copy of this :class:`ParserElement`.  Useful for defining
        different parse actions for the same parsing pattern, using copies of
        the original parse element.

        Example::

            integer = Word(nums).setParseAction(lambda toks: int(toks[0]))
            integerK = integer.copy().addParseAction(lambda toks: toks[0] * 1024) + Suppress("K")
            integerM = integer.copy().addParseAction(lambda toks: toks[0] * 1024 * 1024) + Suppress("M")

            print(OneOrMore(integerK | integerM | integer).parseString("5K 100 640K 256M"))

        prints::

            [5120, 100, 655360, 268435456]

        Equivalent form of ``expr.copy()`` is just ``expr()``::

            integerM = integer().addParseAction(lambda toks: toks[0] * 1024 * 1024) + Suppress("M")
        """
        cpy = copy.copy(self)
        cpy.parseAction = self.parseAction[:]
        cpy.ignoreExprs = self.ignoreExprs[:]
        if self.copyDefaultWhiteChars:
            cpy.whiteChars = ParserElement.DEFAULT_WHITE_CHARS
        return cpy

    def setName(self, name):
        """
        Define name for this expression, makes debugging and exception messages clearer.

        Example::

            Word(nums).parseString("ABC")  # -> Exception: Expected W:(0123...) (at char 0), (line:1, col:1)
            Word(nums).setName("integer").parseString("ABC")  # -> Exception: Expected integer (at char 0), (line:1, col:1)
        """
        self.name = name
        self.errmsg = "Expected " + self.name
        if __diag__.enable_debug_on_named_expressions:
            self.setDebug()
        return self

    def setResultsName(self, name, listAllMatches=False):
        """
        Define name for referencing matching tokens as a nested attribute
        of the returned parse results.
        NOTE: this returns a *copy* of the original :class:`ParserElement` object;
        this is so that the client can define a basic element, such as an
        integer, and reference it in multiple places with different names.

        You can also set results names using the abbreviated syntax,
        ``expr("name")`` in place of ``expr.setResultsName("name")``
        - see :class:`__call__`.

        Example::

            date_str = (integer.setResultsName("year") + '/'
                        + integer.setResultsName("month") + '/'
                        + integer.setResultsName("day"))

            # equivalent form:
            date_str = integer("year") + '/' + integer("month") + '/' + integer("day")
        """
        return self._setResultsName(name, listAllMatches)

    def _setResultsName(self, name, listAllMatches=False):
        newself = self.copy()
        if name.endswith("*"):
            name = name[:-1]
            listAllMatches = True
        newself.resultsName = name
        newself.modalResults = not listAllMatches
        return newself

    def setBreak(self, breakFlag=True):
        """Method to invoke the Python pdb debugger when this element is
           about to be parsed. Set ``breakFlag`` to True to enable, False to
           disable.
        """
        if breakFlag:
            _parseMethod = self._parse

            def breaker(instring, loc, doActions=True, callPreParse=True):
                import pdb

                # this call to pdb.set_trace() is intentional, not a checkin error
                pdb.set_trace()
                return _parseMethod(instring, loc, doActions, callPreParse)

            breaker._originalParseMethod = _parseMethod
            self._parse = breaker
        else:
            if hasattr(self._parse, "_originalParseMethod"):
                self._parse = self._parse._originalParseMethod
        return self

    def setParseAction(self, *fns, **kwargs):
        """
        Define one or more actions to perform when successfully matching parse element definition.
        Parse action fn is a callable method with 0-3 arguments, called as ``fn(s, loc, toks)`` ,
        ``fn(loc, toks)`` , ``fn(toks)`` , or just ``fn()`` , where:

        - s   = the original string being parsed (see note below)
        - loc = the location of the matching substring
        - toks = a list of the matched tokens, packaged as a :class:`ParseResults` object

        If the functions in fns modify the tokens, they can return them as the return
        value from fn, and the modified list of tokens will replace the original.
        Otherwise, fn does not need to return any value.

        If None is passed as the parse action, all previously added parse actions for this
        expression are cleared.

        Optional keyword arguments:

        - callDuringTry = (default= ``False``) indicate if parse action should be run during lookaheads and alternate testing

        Note: the default parsing behavior is to expand tabs in the input string
        before starting the parsing process.  See :class:`parseString` for more
        information on parsing strings containing ``<TAB>``\ s, and suggested
        methods to maintain a consistent view of the parsed string, the parse
        location, and line and column positions within the parsed string.

        Example::

            integer = Word(nums)
            date_str = integer + '/' + integer + '/' + integer

            date_str.parseString("1999/12/31")  # -> ['1999', '/', '12', '/', '31']

            # use parse action to convert to ints at parse time
            integer = Word(nums).setParseAction(lambda toks: int(toks[0]))
            date_str = integer + '/' + integer + '/' + integer

            # note that integer fields are now ints, not strings
            date_str.parseString("1999/12/31")  # -> [1999, '/', 12, '/', 31]
        """
        if list(fns) == [
            None,
        ]:
            self.parseAction = []
        else:
            if not all(callable(fn) for fn in fns):
                raise TypeError("parse actions must be callable")
            self.parseAction = list(map(_trim_arity, list(fns)))
            self.callDuringTry = kwargs.get("callDuringTry", False)
        return self

    def addParseAction(self, *fns, **kwargs):
        """
        Add one or more parse actions to expression's list of parse actions. See :class:`setParseAction`.

        See examples in :class:`copy`.
        """
        self.parseAction += list(map(_trim_arity, list(fns)))
        self.callDuringTry = self.callDuringTry or kwargs.get("callDuringTry", False)
        return self

    def addCondition(self, *fns, **kwargs):
        """Add a boolean predicate function to expression's list of parse actions. See
        :class:`setParseAction` for function call signatures. Unlike ``setParseAction``,
        functions passed to ``addCondition`` need to return boolean success/fail of the condition.

        Optional keyword arguments:

        - message = define a custom message to be used in the raised exception
        - fatal = if True, will raise ParseFatalException to stop parsing immediately; otherwise will raise
          ParseException
        - callDuringTry = boolean to indicate if this method should be called during internal tryParse calls,
          default=False

        Example::

            integer = Word(nums).setParseAction(lambda toks: int(toks[0]))
            year_int = integer.copy()
            year_int.addCondition(lambda toks: toks[0] >= 2000, message="Only support years 2000 and later")
            date_str = year_int + '/' + integer + '/' + integer

            result = date_str.parseString("1999/12/31")  # -> Exception: Only support years 2000 and later (at char 0),
                                                                         (line:1, col:1)
        """
        for fn in fns:
            self.parseAction.append(
                conditionAsParseAction(
                    fn, message=kwargs.get("message"), fatal=kwargs.get("fatal", False)
                )
            )

        self.callDuringTry = self.callDuringTry or kwargs.get("callDuringTry", False)
        return self

    def setFailAction(self, fn):
        """Define action to perform if parsing fails at this expression.
           Fail acton fn is a callable function that takes the arguments
           ``fn(s, loc, expr, err)`` where:

           - s = string being parsed
           - loc = location where expression match was attempted and failed
           - expr = the parse expression that failed
           - err = the exception thrown

           The function returns no value.  It may throw :class:`ParseFatalException`
           if it is desired to stop parsing immediately."""
        self.failAction = fn
        return self

    def _skipIgnorables(self, instring, loc):
        exprsFound = True
        while exprsFound:
            exprsFound = False
            for e in self.ignoreExprs:
                try:
                    while 1:
                        loc, dummy = e._parse(instring, loc)
                        exprsFound = True
                except ParseException:
                    pass
        return loc

    def preParse(self, instring, loc):
        if self.ignoreExprs:
            loc = self._skipIgnorables(instring, loc)

        if self.skipWhitespace:
            wt = self.whiteChars
            instrlen = len(instring)
            while loc < instrlen and instring[loc] in wt:
                loc += 1

        return loc

    def parseImpl(self, instring, loc, doActions=True):
        return loc, []

    def postParse(self, instring, loc, tokenlist):
        return tokenlist

    # ~ @profile
    def _parseNoCache(self, instring, loc, doActions=True, callPreParse=True):
        TRY, MATCH, FAIL = 0, 1, 2
        debugging = self.debug  # and doActions)

        if debugging or self.failAction:
            # ~ print("Match", self, "at loc", loc, "(%d, %d)" % (lineno(loc, instring), col(loc, instring)))
            if self.debugActions[TRY]:
                self.debugActions[TRY](instring, loc, self)
            try:
                if callPreParse and self.callPreparse:
                    preloc = self.preParse(instring, loc)
                else:
                    preloc = loc
                tokensStart = preloc
                if self.mayIndexError or preloc >= len(instring):
                    try:
                        loc, tokens = self.parseImpl(instring, preloc, doActions)
                    except IndexError:
                        raise ParseException(instring, len(instring), self.errmsg, self)
                else:
                    loc, tokens = self.parseImpl(instring, preloc, doActions)
            except Exception as err:
                # ~ print("Exception raised:", err)
                if self.debugActions[FAIL]:
                    self.debugActions[FAIL](instring, tokensStart, self, err)
                if self.failAction:
                    self.failAction(instring, tokensStart, self, err)
                raise
        else:
            if callPreParse and self.callPreparse:
                preloc = self.preParse(instring, loc)
            else:
                preloc = loc
            tokensStart = preloc
            if self.mayIndexError or preloc >= len(instring):
                try:
                    loc, tokens = self.parseImpl(instring, preloc, doActions)
                except IndexError:
                    raise ParseException(instring, len(instring), self.errmsg, self)
            else:
                loc, tokens = self.parseImpl(instring, preloc, doActions)

        tokens = self.postParse(instring, loc, tokens)

        retTokens = ParseResults(
            tokens, self.resultsName, asList=self.saveAsList, modal=self.modalResults
        )
        if self.parseAction and (doActions or self.callDuringTry):
            if debugging:
                try:
                    for fn in self.parseAction:
                        try:
                            tokens = fn(instring, tokensStart, retTokens)
                        except IndexError as parse_action_exc:
                            exc = ParseException("exception raised in parse action")
                            exc.__cause__ = parse_action_exc
                            raise exc

                        if tokens is not None and tokens is not retTokens:
                            retTokens = ParseResults(
                                tokens,
                                self.resultsName,
                                asList=self.saveAsList
                                and isinstance(tokens, (ParseResults, list)),
                                modal=self.modalResults,
                            )
                except Exception as err:
                    # ~ print "Exception raised in user parse action:", err
                    if self.debugActions[FAIL]:
                        self.debugActions[FAIL](instring, tokensStart, self, err)
                    raise
            else:
                for fn in self.parseAction:
                    try:
                        tokens = fn(instring, tokensStart, retTokens)
                    except IndexError as parse_action_exc:
                        exc = ParseException("exception raised in parse action")
                        exc.__cause__ = parse_action_exc
                        raise exc

                    if tokens is not None and tokens is not retTokens:
                        retTokens = ParseResults(
                            tokens,
                            self.resultsName,
                            asList=self.saveAsList
                            and isinstance(tokens, (ParseResults, list)),
                            modal=self.modalResults,
                        )
        if debugging:
            # ~ print("Matched", self, "->", retTokens.asList())
            if self.debugActions[MATCH]:
                self.debugActions[MATCH](instring, tokensStart, loc, self, retTokens)

        return loc, retTokens

    def tryParse(self, instring, loc, raise_fatal=False):
        try:
            return self._parse(instring, loc, doActions=False)[0]
        except ParseFatalException:
            if raise_fatal:
                raise
            raise ParseException(instring, loc, self.errmsg, self)

    def canParseNext(self, instring, loc):
        try:
            self.tryParse(instring, loc)
        except (ParseException, IndexError):
            return False
        else:
            return True

    # argument cache for optimizing repeated calls when backtracking through recursive expressions
    packrat_cache = (
        {}
    )  # this is set later by enabledPackrat(); this is here so that resetCache() doesn't fail
    packrat_cache_lock = RLock()
    packrat_cache_stats = [0, 0]

    # this method gets repeatedly called during backtracking with the same arguments -
    # we can cache these arguments and save ourselves the trouble of re-parsing the contained expression
    def _parseCache(self, instring, loc, doActions=True, callPreParse=True):
        HIT, MISS = 0, 1
        lookup = (self, instring, loc, callPreParse, doActions)
        with ParserElement.packrat_cache_lock:
            cache = ParserElement.packrat_cache
            value = cache.get(lookup)
            if value is cache.not_in_cache:
                ParserElement.packrat_cache_stats[MISS] += 1
                try:
                    value = self._parseNoCache(instring, loc, doActions, callPreParse)
                except ParseBaseException as pe:
                    # cache a copy of the exception, without the traceback
                    cache.set(lookup, pe.__class__(*pe.args))
                    raise
                else:
                    cache.set(lookup, (value[0], value[1].copy()))
                    return value
            else:
                ParserElement.packrat_cache_stats[HIT] += 1
                if isinstance(value, Exception):
                    raise value
                return value[0], value[1].copy()

    _parse = _parseNoCache

    @staticmethod
    def resetCache():
        ParserElement.packrat_cache.clear()
        ParserElement.packrat_cache_stats[:] = [0] * len(
            ParserElement.packrat_cache_stats
        )

    _packratEnabled = False

    @staticmethod
    def enablePackrat(cache_size_limit=128):
        """Enables "packrat" parsing, which adds memoizing to the parsing logic.
           Repeated parse attempts at the same string location (which happens
           often in many complex grammars) can immediately return a cached value,
           instead of re-executing parsing/validating code.  Memoizing is done of
           both valid results and parsing exceptions.

           Parameters:

           - cache_size_limit - (default= ``128``) - if an integer value is provided
             will limit the size of the packrat cache; if None is passed, then
             the cache size will be unbounded; if 0 is passed, the cache will
             be effectively disabled.

           This speedup may break existing programs that use parse actions that
           have side-effects.  For this reason, packrat parsing is disabled when
           you first import pyparsing.  To activate the packrat feature, your
           program must call the class method :class:`ParserElement.enablePackrat`.
           For best results, call ``enablePackrat()`` immediately after
           importing pyparsing.

           Example::

               import pyparsing
               pyparsing.ParserElement.enablePackrat()
        """
        if not ParserElement._packratEnabled:
            ParserElement._packratEnabled = True
            if cache_size_limit is None:
                ParserElement.packrat_cache = _UnboundedCache()
            else:
                ParserElement.packrat_cache = _FifoCache(cache_size_limit)
            ParserElement._parse = ParserElement._parseCache

    def parseString(self, instring, parseAll=False):
        """
        Parse a string with respect to the parser definition. This function is intended as the primary interface to the
        client code.

        :param instring: The input string to be parsed.
        :param parseAll: If set, the entire input string must match the grammar.
        :raises ParseException: Raised if ``parseAll`` is set and the input string does not match the whole grammar.
        :returns: the parsed data as a :class:`ParseResults` object, which may be accessed as a `list`, a `dict`, or
          an object with attributes if the given parser includes results names.

        If the input string is required to match the entire grammar, ``parseAll`` flag must be set to ``True``. This
        is also equivalent to ending the grammar with ``StringEnd()``.

        To report proper column numbers, ``parseString`` operates on a copy of the input string where all tabs are
        converted to spaces (8 spaces per tab, as per the default in ``string.expandtabs``). If the input string
        contains tabs and the grammar uses parse actions that use the ``loc`` argument to index into the string
        being parsed, one can ensure a consistent view of the input string by doing one of the following:

        - calling ``parseWithTabs`` on your grammar before calling ``parseString`` (see :class:`parseWithTabs`),
        - define your parse action using the full ``(s,loc,toks)`` signature, and reference the input string using the
          parse action's ``s`` argument, or
        - explicitly expand the tabs in your input string before calling ``parseString``.

        Examples:

        By default, partial matches are OK.

        >>> res = Word('a').parseString('aaaaabaaa')
        >>> print(res)
        ['aaaaa']

        The parsing behavior varies by the inheriting class of this abstract class. Please refer to the children
        directly to see more examples.

        It raises an exception if parseAll flag is set and instring does not match the whole grammar.

        >>> res = Word('a').parseString('aaaaabaaa', parseAll=True)
        Traceback (most recent call last):
        ...
        pyparsing.ParseException: Expected end of text, found 'b'  (at char 5), (line:1, col:6)
        """

        ParserElement.resetCache()
        if not self.streamlined:
            self.streamline()
            # ~ self.saveAsList = True
        for e in self.ignoreExprs:
            e.streamline()
        if not self.keepTabs:
            instring = instring.expandtabs()
        try:
            loc, tokens = self._parse(instring, 0)
            if parseAll:
                loc = self.preParse(instring, loc)
                se = Empty() + StringEnd()
                se._parse(instring, loc)
        except ParseBaseException as exc:
            if ParserElement.verbose_stacktrace:
                raise
            else:
                # catch and re-raise exception from here, clearing out pyparsing internal stack trace
                exc.__traceback__ = self._trim_traceback(exc.__traceback__)
                raise exc
        else:
            return tokens

    def scanString(self, instring, maxMatches=_MAX_INT, overlap=False):
        """
        Scan the input string for expression matches.  Each match will return the
        matching tokens, start location, and end location.  May be called with optional
        ``maxMatches`` argument, to clip scanning after 'n' matches are found.  If
        ``overlap`` is specified, then overlapping matches will be reported.

        Note that the start and end locations are reported relative to the string
        being parsed.  See :class:`parseString` for more information on parsing
        strings with embedded tabs.

        Example::

            source = "sldjf123lsdjjkf345sldkjf879lkjsfd987"
            print(source)
            for tokens, start, end in Word(alphas).scanString(source):
                print(' '*start + '^'*(end-start))
                print(' '*start + tokens[0])

        prints::

            sldjf123lsdjjkf345sldkjf879lkjsfd987
            ^^^^^
            sldjf
                    ^^^^^^^
                    lsdjjkf
                              ^^^^^^
                              sldkjf
                                       ^^^^^^
                                       lkjsfd
        """
        if not self.streamlined:
            self.streamline()
        for e in self.ignoreExprs:
            e.streamline()

        if not self.keepTabs:
            instring = str(instring).expandtabs()
        instrlen = len(instring)
        loc = 0
        preparseFn = self.preParse
        parseFn = self._parse
        ParserElement.resetCache()
        matches = 0
        try:
            while loc <= instrlen and matches < maxMatches:
                try:
                    preloc = preparseFn(instring, loc)
                    nextLoc, tokens = parseFn(instring, preloc, callPreParse=False)
                except ParseException:
                    loc = preloc + 1
                else:
                    if nextLoc > loc:
                        matches += 1
                        yield tokens, preloc, nextLoc
                        if overlap:
                            nextloc = preparseFn(instring, loc)
                            if nextloc > loc:
                                loc = nextLoc
                            else:
                                loc += 1
                        else:
                            loc = nextLoc
                    else:
                        loc = preloc + 1
        except ParseBaseException as exc:
            if ParserElement.verbose_stacktrace:
                raise
            else:
                # catch and re-raise exception from here, clears out pyparsing internal stack trace
                exc.__traceback__ = self._trim_traceback(exc.__traceback__)
                raise exc

    def transformString(self, instring):
        """
        Extension to :class:`scanString`, to modify matching text with modified tokens that may
        be returned from a parse action.  To use ``transformString``, define a grammar and
        attach a parse action to it that modifies the returned token list.
        Invoking ``transformString()`` on a target string will then scan for matches,
        and replace the matched text patterns according to the logic in the parse
        action.  ``transformString()`` returns the resulting transformed string.

        Example::

            wd = Word(alphas)
            wd.setParseAction(lambda toks: toks[0].title())

            print(wd.transformString("now is the winter of our discontent made glorious summer by this sun of york."))

        prints::

            Now Is The Winter Of Our Discontent Made Glorious Summer By This Sun Of York.
        """
        out = []
        lastE = 0
        # force preservation of <TAB>s, to minimize unwanted transformation of string, and to
        # keep string locs straight between transformString and scanString
        self.keepTabs = True
        try:
            for t, s, e in self.scanString(instring):
                out.append(instring[lastE:s])
                if t:
                    if isinstance(t, ParseResults):
                        out += t.asList()
                    elif isinstance(t, list):
                        out += t
                    else:
                        out.append(t)
                lastE = e
            out.append(instring[lastE:])
            out = [o for o in out if o]
            return "".join(map(str, _flatten(out)))
        except ParseBaseException as exc:
            if ParserElement.verbose_stacktrace:
                raise
            else:
                # catch and re-raise exception from here, clears out pyparsing internal stack trace
                exc.__traceback__ = self._trim_traceback(exc.__traceback__)
                raise exc

    def searchString(self, instring, maxMatches=_MAX_INT):
        """
        Another extension to :class:`scanString`, simplifying the access to the tokens found
        to match the given parse expression.  May be called with optional
        ``maxMatches`` argument, to clip searching after 'n' matches are found.

        Example::

            # a capitalized word starts with an uppercase letter, followed by zero or more lowercase letters
            cap_word = Word(alphas.upper(), alphas.lower())

            print(cap_word.searchString("More than Iron, more than Lead, more than Gold I need Electricity"))

            # the sum() builtin can be used to merge results into a single ParseResults object
            print(sum(cap_word.searchString("More than Iron, more than Lead, more than Gold I need Electricity")))

        prints::

            [['More'], ['Iron'], ['Lead'], ['Gold'], ['I'], ['Electricity']]
            ['More', 'Iron', 'Lead', 'Gold', 'I', 'Electricity']
        """
        try:
            return ParseResults(
                [t for t, s, e in self.scanString(instring, maxMatches)]
            )
        except ParseBaseException as exc:
            if ParserElement.verbose_stacktrace:
                raise
            else:
                # catch and re-raise exception from here, clears out pyparsing internal stack trace
                exc.__traceback__ = self._trim_traceback(exc.__traceback__)
                raise exc

    def split(self, instring, maxsplit=_MAX_INT, includeSeparators=False):
        """
        Generator method to split a string using the given expression as a separator.
        May be called with optional ``maxsplit`` argument, to limit the number of splits;
        and the optional ``includeSeparators`` argument (default= ``False``), if the separating
        matching text should be included in the split results.

        Example::

            punc = oneOf(list(".,;:/-!?"))
            print(list(punc.split("This, this?, this sentence, is badly punctuated!")))

        prints::

            ['This', ' this', '', ' this sentence', ' is badly punctuated', '']
        """
        splits = 0
        last = 0
        for t, s, e in self.scanString(instring, maxMatches=maxsplit):
            yield instring[last:s]
            if includeSeparators:
                yield t[0]
            last = e
        yield instring[last:]

    def __add__(self, other):
        """
        Implementation of + operator - returns :class:`And`. Adding strings to a ParserElement
        converts them to :class:`Literal`s by default.

        Example::

            greet = Word(alphas) + "," + Word(alphas) + "!"
            hello = "Hello, World!"
            print(hello, "->", greet.parseString(hello))

        prints::

            Hello, World! -> ['Hello', ',', 'World', '!']

        ``...`` may be used as a parse expression as a short form of :class:`SkipTo`.

            Literal('start') + ... + Literal('end')

        is equivalent to:

            Literal('start') + SkipTo('end')("_skipped*") + Literal('end')

        Note that the skipped text is returned with '_skipped' as a results name,
        and to support having multiple skips in the same parser, the value returned is
        a list of all skipped text.
        """
        if other is Ellipsis:
            return _PendingSkip(self)

        if isinstance(other, str_type):
            other = self._literalStringClass(other)
        if not isinstance(other, ParserElement):
            warnings.warn(
                "Cannot combine element of type {} with ParserElement".format(
                    type(other).__name__
                ),
                SyntaxWarning,
                stacklevel=2,
            )
            return None
        return And([self, other])

    def __radd__(self, other):
        """
        Implementation of + operator when left operand is not a :class:`ParserElement`
        """
        if other is Ellipsis:
            return SkipTo(self)("_skipped*") + self

        if isinstance(other, str_type):
            other = self._literalStringClass(other)
        if not isinstance(other, ParserElement):
            warnings.warn(
                "Cannot combine element of type %s with ParserElement" % type(other),
                SyntaxWarning,
                stacklevel=2,
            )
            return None
        return other + self

    def __sub__(self, other):
        """
        Implementation of - operator, returns :class:`And` with error stop
        """
        if isinstance(other, str_type):
            other = self._literalStringClass(other)
        if not isinstance(other, ParserElement):
            warnings.warn(
                "Cannot combine element of type %s with ParserElement" % type(other),
                SyntaxWarning,
                stacklevel=2,
            )
            return None
        return self + And._ErrorStop() + other

    def __rsub__(self, other):
        """
        Implementation of - operator when left operand is not a :class:`ParserElement`
        """
        if isinstance(other, str_type):
            other = self._literalStringClass(other)
        if not isinstance(other, ParserElement):
            warnings.warn(
                "Cannot combine element of type %s with ParserElement" % type(other),
                SyntaxWarning,
                stacklevel=2,
            )
            return None
        return other - self

    def __mul__(self, other):
        """
        Implementation of * operator, allows use of ``expr * 3`` in place of
        ``expr + expr + expr``.  Expressions may also be multiplied by a 2-integer
        tuple, similar to ``{min, max}`` multipliers in regular expressions.  Tuples
        may also include ``None`` as in:
         - ``expr*(n, None)`` or ``expr*(n, )`` is equivalent
              to ``expr*n + ZeroOrMore(expr)``
              (read as "at least n instances of ``expr``")
         - ``expr*(None, n)`` is equivalent to ``expr*(0, n)``
              (read as "0 to n instances of ``expr``")
         - ``expr*(None, None)`` is equivalent to ``ZeroOrMore(expr)``
         - ``expr*(1, None)`` is equivalent to ``OneOrMore(expr)``

        Note that ``expr*(None, n)`` does not raise an exception if
        more than n exprs exist in the input stream; that is,
        ``expr*(None, n)`` does not enforce a maximum number of expr
        occurrences.  If this behavior is desired, then write
        ``expr*(None, n) + ~expr``
        """
        if other is Ellipsis:
            other = (0, None)
        elif isinstance(other, tuple) and other[:1] == (Ellipsis,):
            other = ((0,) + other[1:] + (None,))[:2]

        if isinstance(other, int):
            minElements, optElements = other, 0
        elif isinstance(other, tuple):
            other = tuple(o if o is not Ellipsis else None for o in other)
            other = (other + (None, None))[:2]
            if other[0] is None:
                other = (0, other[1])
            if isinstance(other[0], int) and other[1] is None:
                if other[0] == 0:
                    return ZeroOrMore(self)
                if other[0] == 1:
                    return OneOrMore(self)
                else:
                    return self * other[0] + ZeroOrMore(self)
            elif isinstance(other[0], int) and isinstance(other[1], int):
                minElements, optElements = other
                optElements -= minElements
            else:
                raise TypeError(
                    "cannot multiply 'ParserElement' and ('%s', '%s') objects",
                    type(other[0]),
                    type(other[1]),
                )
        else:
            raise TypeError(
                "cannot multiply 'ParserElement' and '%s' objects", type(other)
            )

        if minElements < 0:
            raise ValueError("cannot multiply ParserElement by negative value")
        if optElements < 0:
            raise ValueError(
                "second tuple value must be greater or equal to first tuple value"
            )
        if minElements == optElements == 0:
            raise ValueError("cannot multiply ParserElement by 0 or (0, 0)")

        if optElements:

            def makeOptionalList(n):
                if n > 1:
                    return Optional(self + makeOptionalList(n - 1))
                else:
                    return Optional(self)

            if minElements:
                if minElements == 1:
                    ret = self + makeOptionalList(optElements)
                else:
                    ret = And([self] * minElements) + makeOptionalList(optElements)
            else:
                ret = makeOptionalList(optElements)
        else:
            if minElements == 1:
                ret = self
            else:
                ret = And([self] * minElements)
        return ret

    def __rmul__(self, other):
        return self.__mul__(other)

    def __or__(self, other):
        """
        Implementation of | operator - returns :class:`MatchFirst`
        """
        if other is Ellipsis:
            return _PendingSkip(self, must_skip=True)

        if isinstance(other, str_type):
            other = self._literalStringClass(other)
        if not isinstance(other, ParserElement):
            warnings.warn(
                "Cannot combine element of type %s with ParserElement" % type(other),
                SyntaxWarning,
                stacklevel=2,
            )
            return None
        return MatchFirst([self, other])

    def __ror__(self, other):
        """
        Implementation of | operator when left operand is not a :class:`ParserElement`
        """
        if isinstance(other, str_type):
            other = self._literalStringClass(other)
        if not isinstance(other, ParserElement):
            warnings.warn(
                "Cannot combine element of type %s with ParserElement" % type(other),
                SyntaxWarning,
                stacklevel=2,
            )
            return None
        return other | self

    def __xor__(self, other):
        """
        Implementation of ^ operator - returns :class:`Or`
        """
        if isinstance(other, str_type):
            other = self._literalStringClass(other)
        if not isinstance(other, ParserElement):
            warnings.warn(
                "Cannot combine element of type %s with ParserElement" % type(other),
                SyntaxWarning,
                stacklevel=2,
            )
            return None
        return Or([self, other])

    def __rxor__(self, other):
        """
        Implementation of ^ operator when left operand is not a :class:`ParserElement`
        """
        if isinstance(other, str_type):
            other = self._literalStringClass(other)
        if not isinstance(other, ParserElement):
            warnings.warn(
                "Cannot combine element of type %s with ParserElement" % type(other),
                SyntaxWarning,
                stacklevel=2,
            )
            return None
        return other ^ self

    def __and__(self, other):
        """
        Implementation of & operator - returns :class:`Each`
        """
        if isinstance(other, str_type):
            other = self._literalStringClass(other)
        if not isinstance(other, ParserElement):
            warnings.warn(
                "Cannot combine element of type %s with ParserElement" % type(other),
                SyntaxWarning,
                stacklevel=2,
            )
            return None
        return Each([self, other])

    def __rand__(self, other):
        """
        Implementation of & operator when left operand is not a :class:`ParserElement`
        """
        if isinstance(other, str_type):
            other = self._literalStringClass(other)
        if not isinstance(other, ParserElement):
            warnings.warn(
                "Cannot combine element of type %s with ParserElement" % type(other),
                SyntaxWarning,
                stacklevel=2,
            )
            return None
        return other & self

    def __invert__(self):
        """
        Implementation of ~ operator - returns :class:`NotAny`
        """
        return NotAny(self)

    def __iter__(self):
        # must implement __iter__ to override legacy use of sequential access to __getitem__ to
        # iterate over a sequence
        raise TypeError("%r object is not iterable" % self.__class__.__name__)

    def __getitem__(self, key):
        """
        use ``[]`` indexing notation as a short form for expression repetition:
         - ``expr[n]`` is equivalent to ``expr*n``
         - ``expr[m, n]`` is equivalent to ``expr*(m, n)``
         - ``expr[n, ...]`` or ``expr[n,]`` is equivalent
              to ``expr*n + ZeroOrMore(expr)``
              (read as "at least n instances of ``expr``")
         - ``expr[..., n]`` is equivalent to ``expr*(0, n)``
              (read as "0 to n instances of ``expr``")
         - ``expr[...]`` and ``expr[0, ...]`` are equivalent to ``ZeroOrMore(expr)``
         - ``expr[1, ...]`` is equivalent to ``OneOrMore(expr)``
         ``None`` may be used in place of ``...``.

        Note that ``expr[..., n]`` and ``expr[m, n]``do not raise an exception
        if more than ``n`` ``expr``s exist in the input stream.  If this behavior is
        desired, then write ``expr[..., n] + ~expr``.
       """

        # convert single arg keys to tuples
        try:
            if isinstance(key, str_type):
                key = (key,)
            iter(key)
        except TypeError:
            key = (key, key)

        if len(key) > 2:
            warnings.warn(
                "only 1 or 2 index arguments supported ({}{})".format(
                    key[:5], "... [{}]".format(len(key)) if len(key) > 5 else ""
                )
            )

        # clip to 2 elements
        ret = self * tuple(key[:2])
        return ret

    def __call__(self, name=None):
        """
        Shortcut for :class:`setResultsName`, with ``listAllMatches=False``.

        If ``name`` is given with a trailing ``'*'`` character, then ``listAllMatches`` will be
        passed as ``True``.

        If ``name` is omitted, same as calling :class:`copy`.

        Example::

            # these are equivalent
            userdata = Word(alphas).setResultsName("name") + Word(nums + "-").setResultsName("socsecno")
            userdata = Word(alphas)("name") + Word(nums + "-")("socsecno")
        """
        if name is not None:
            return self._setResultsName(name)
        else:
            return self.copy()

    def suppress(self):
        """
        Suppresses the output of this :class:`ParserElement`; useful to keep punctuation from
        cluttering up returned output.
        """
        return Suppress(self)

    def leaveWhitespace(self):
        """
        Disables the skipping of whitespace before matching the characters in the
        :class:`ParserElement`'s defined pattern.  This is normally only used internally by
        the pyparsing module, but may be needed in some whitespace-sensitive grammars.
        """
        self.skipWhitespace = False
        return self

    def setWhitespaceChars(self, chars, copy_defaults=False):
        """
        Overrides the default whitespace chars
        """
        self.skipWhitespace = True
        self.whiteChars = chars
        self.copyDefaultWhiteChars = copy_defaults
        return self

    def parseWithTabs(self):
        """
        Overrides default behavior to expand ``<TAB>``\ s to spaces before parsing the input string.
        Must be called before ``parseString`` when the input grammar contains elements that
        match ``<TAB>`` characters.
        """
        self.keepTabs = True
        return self

    def ignore(self, other):
        """
        Define expression to be ignored (e.g., comments) while doing pattern
        matching; may be called repeatedly, to define multiple comment or other
        ignorable patterns.

        Example::

            patt = OneOrMore(Word(alphas))
            patt.parseString('ablaj /* comment */ lskjd')
            # -> ['ablaj']

            patt.ignore(cStyleComment)
            patt.parseString('ablaj /* comment */ lskjd')
            # -> ['ablaj', 'lskjd']
        """
        if isinstance(other, str_type):
            other = Suppress(other)

        if isinstance(other, Suppress):
            if other not in self.ignoreExprs:
                self.ignoreExprs.append(other)
        else:
            self.ignoreExprs.append(Suppress(other.copy()))
        return self

    def setDebugActions(self, startAction, successAction, exceptionAction):
        """
        Enable display of debugging messages while doing pattern matching.
        """
        self.debugActions = (
            startAction or _defaultStartDebugAction,
            successAction or _defaultSuccessDebugAction,
            exceptionAction or _defaultExceptionDebugAction,
        )
        self.debug = True
        return self

    def setDebug(self, flag=True):
        """
        Enable display of debugging messages while doing pattern matching.
        Set ``flag`` to True to enable, False to disable.

        Example::

            wd = Word(alphas).setName("alphaword")
            integer = Word(nums).setName("numword")
            term = wd | integer

            # turn on debugging for wd
            wd.setDebug()

            OneOrMore(term).parseString("abc 123 xyz 890")

        prints::

            Match alphaword at loc 0(1,1)
            Matched alphaword -> ['abc']
            Match alphaword at loc 3(1,4)
            Exception raised:Expected alphaword (at char 4), (line:1, col:5)
            Match alphaword at loc 7(1,8)
            Matched alphaword -> ['xyz']
            Match alphaword at loc 11(1,12)
            Exception raised:Expected alphaword (at char 12), (line:1, col:13)
            Match alphaword at loc 15(1,16)
            Exception raised:Expected alphaword (at char 15), (line:1, col:16)

        The output shown is that produced by the default debug actions - custom debug actions can be
        specified using :class:`setDebugActions`. Prior to attempting
        to match the ``wd`` expression, the debugging message ``"Match <exprname> at loc <n>(<line>,<col>)"``
        is shown. Then if the parse succeeds, a ``"Matched"`` message is shown, or an ``"Exception raised"``
        message is shown. Also note the use of :class:`setName` to assign a human-readable name to the expression,
        which makes debugging and exception messages easier to understand - for instance, the default
        name created for the :class:`Word` expression without calling ``setName`` is ``"W:(ABCD...)"``.
        """
        if flag:
            self.setDebugActions(
                _defaultStartDebugAction,
                _defaultSuccessDebugAction,
                _defaultExceptionDebugAction,
            )
        else:
            self.debug = False
        return self

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)

    def streamline(self):
        self.streamlined = True
        self.strRepr = None
        return self

    def checkRecursion(self, parseElementList):
        pass

    def validate(self, validateTrace=None):
        """
        Check defined expressions for valid structure, check for infinite recursive definitions.
        """
        self.checkRecursion([])

    def parseFile(self, file_or_filename, parseAll=False):
        """
        Execute the parse expression on the given file or filename.
        If a filename is specified (instead of a file object),
        the entire file is opened, read, and closed before parsing.
        """
        try:
            file_contents = file_or_filename.read()
        except AttributeError:
            with open(file_or_filename, "r") as f:
                file_contents = f.read()
        try:
            return self.parseString(file_contents, parseAll)
        except ParseBaseException as exc:
            if ParserElement.verbose_stacktrace:
                raise
            else:
                # catch and re-raise exception from here, clears out pyparsing internal stack trace
                exc.__traceback__ = self._trim_traceback(exc.__traceback__)
                raise exc

    def __eq__(self, other):
        if self is other:
            return True
        elif isinstance(other, str_type):
            return self.matches(other)
        elif isinstance(other, ParserElement):
            return vars(self) == vars(other)
        return False

    def __hash__(self):
        return id(self)

    def __req__(self, other):
        return self == other

    def __rne__(self, other):
        return not (self == other)

    def matches(self, testString, parseAll=True):
        """
        Method for quick testing of a parser against a test string. Good for simple
        inline microtests of sub expressions while building up larger parser.

        Parameters:
         - testString - to test against this expression for a match
         - parseAll - (default= ``True``) - flag to pass to :class:`parseString` when running tests

        Example::

            expr = Word(nums)
            assert expr.matches("100")
        """
        try:
            self.parseString(str(testString), parseAll=parseAll)
            return True
        except ParseBaseException:
            return False

    def runTests(
        self,
        tests,
        parseAll=True,
        comment="#",
        fullDump=True,
        printResults=True,
        failureTests=False,
        postParse=None,
        file=None,
    ):
        """
        Execute the parse expression on a series of test strings, showing each
        test, the parsed results or where the parse failed. Quick and easy way to
        run a parse expression against a list of sample strings.

        Parameters:
         - tests - a list of separate test strings, or a multiline string of test strings
         - parseAll - (default= ``True``) - flag to pass to :class:`parseString` when running tests
         - comment - (default= ``'#'``) - expression for indicating embedded comments in the test
           string; pass None to disable comment filtering
         - fullDump - (default= ``True``) - dump results as list followed by results names in nested outline;
           if False, only dump nested list
         - printResults - (default= ``True``) prints test output to stdout
         - failureTests - (default= ``False``) indicates if these tests are expected to fail parsing
         - postParse - (default= ``None``) optional callback for successful parse results; called as
           `fn(test_string, parse_results)` and returns a string to be added to the test output
         - file - (default= ``None``) optional file-like object to which test output will be written;
           if None, will default to ``sys.stdout``

        Returns: a (success, results) tuple, where success indicates that all tests succeeded
        (or failed if ``failureTests`` is True), and the results contain a list of lines of each
        test's output

        Example::

            number_expr = pyparsing_common.number.copy()

            result = number_expr.runTests('''
                # unsigned integer
                100
                # negative integer
                -100
                # float with scientific notation
                6.02e23
                # integer with scientific notation
                1e-12
                ''')
            print("Success" if result[0] else "Failed!")

            result = number_expr.runTests('''
                # stray character
                100Z
                # missing leading digit before '.'
                -.100
                # too many '.'
                3.14.159
                ''', failureTests=True)
            print("Success" if result[0] else "Failed!")

        prints::

            # unsigned integer
            100
            [100]

            # negative integer
            -100
            [-100]

            # float with scientific notation
            6.02e23
            [6.02e+23]

            # integer with scientific notation
            1e-12
            [1e-12]

            Success

            # stray character
            100Z
               ^
            FAIL: Expected end of text (at char 3), (line:1, col:4)

            # missing leading digit before '.'
            -.100
            ^
            FAIL: Expected {real number with scientific notation | real number | signed integer} (at char 0), (line:1, col:1)

            # too many '.'
            3.14.159
                ^
            FAIL: Expected end of text (at char 4), (line:1, col:5)

            Success

        Each test string must be on a single line. If you want to test a string that spans multiple
        lines, create a test like this::

            expr.runTest(r"this is a test\\n of strings that spans \\n 3 lines")

        (Note that this is a raw string literal, you must include the leading ``'r'``.)
        """
        if isinstance(tests, str_type):
            tests = list(map(type(tests).strip, tests.rstrip().splitlines()))
        if isinstance(comment, str_type):
            comment = Literal(comment)
        if file is None:
            file = sys.stdout
        print_ = file.write

        allResults = []
        comments = []
        success = True
        NL = Literal(r"\n").addParseAction(replaceWith("\n")).ignore(quotedString)
        BOM = "\ufeff"
        for t in tests:
            if comment is not None and comment.matches(t, False) or comments and not t:
                comments.append(t)
                continue
            if not t:
                continue
            out = ["\n".join(comments), t]
            comments = []
            try:
                # convert newline marks to actual newlines, and strip leading BOM if present
                t = NL.transformString(t.lstrip(BOM))
                result = self.parseString(t, parseAll=parseAll)
            except ParseBaseException as pe:
                fatal = "(FATAL)" if isinstance(pe, ParseFatalException) else ""
                if "\n" in t:
                    out.append(line(pe.loc, t))
                    out.append(" " * (col(pe.loc, t) - 1) + "^" + fatal)
                else:
                    out.append(" " * pe.loc + "^" + fatal)
                out.append("FAIL: " + str(pe))
                success = success and failureTests
                result = pe
            except Exception as exc:
                out.append("FAIL-EXCEPTION: " + str(exc))
                success = success and failureTests
                result = exc
            else:
                success = success and not failureTests
                if postParse is not None:
                    try:
                        pp_value = postParse(t, result)
                        if pp_value is not None:
                            if isinstance(pp_value, ParseResults):
                                out.append(pp_value.dump())
                            else:
                                out.append(str(pp_value))
                        else:
                            out.append(result.dump())
                    except Exception as e:
                        out.append(result.dump(full=fullDump))
                        out.append(
                            "{} failed: {}: {}".format(
                                postParse.__name__, type(e).__name__, e
                            )
                        )
                else:
                    out.append(result.dump(full=fullDump))
                out.append("")

            if printResults:
                print_("\n".join(out))

            allResults.append((t, result))

        return success, allResults


class _PendingSkip(ParserElement):
    # internal placeholder class to hold a place were '...' is added to a parser element,
    # once another ParserElement is added, this placeholder will be replaced with a SkipTo
    def __init__(self, expr, must_skip=False):
        super().__init__()
        self.strRepr = str(expr + Empty()).replace("Empty", "...")
        self.name = self.strRepr
        self.anchor = expr
        self.must_skip = must_skip

    def __add__(self, other):
        skipper = SkipTo(other).setName("...")("_skipped*")
        if self.must_skip:

            def must_skip(t):
                if not t._skipped or t._skipped.asList() == [""]:
                    del t[0]
                    t.pop("_skipped", None)

            def show_skip(t):
                if t._skipped.asList()[-1:] == [""]:
                    skipped = t.pop("_skipped")
                    t["_skipped"] = "missing <" + repr(self.anchor) + ">"

            return (
                self.anchor + skipper().addParseAction(must_skip)
                | skipper().addParseAction(show_skip)
            ) + other

        return self.anchor + skipper + other

    def __repr__(self):
        return self.strRepr

    def parseImpl(self, *args):
        raise Exception(
            "use of `...` expression without following SkipTo target expression"
        )


class Token(ParserElement):
    """Abstract :class:`ParserElement` subclass, for defining atomic
    matching patterns.
    """

    def __init__(self):
        super().__init__(savelist=False)


class Empty(Token):
    """An empty token, will always match.
    """

    def __init__(self):
        super().__init__()
        self.name = "Empty"
        self.mayReturnEmpty = True
        self.mayIndexError = False


class NoMatch(Token):
    """A token that will never match.
    """

    def __init__(self):
        super().__init__()
        self.name = "NoMatch"
        self.mayReturnEmpty = True
        self.mayIndexError = False
        self.errmsg = "Unmatchable token"

    def parseImpl(self, instring, loc, doActions=True):
        raise ParseException(instring, loc, self.errmsg, self)


class Literal(Token):
    """Token to exactly match a specified string.

    Example::

        Literal('blah').parseString('blah')  # -> ['blah']
        Literal('blah').parseString('blahfooblah')  # -> ['blah']
        Literal('blah').parseString('bla')  # -> Exception: Expected "blah"

    For case-insensitive matching, use :class:`CaselessLiteral`.

    For keyword matching (force word break before and after the matched string),
    use :class:`Keyword` or :class:`CaselessKeyword`.
    """

    def __init__(self, matchString):
        super().__init__()
        self.match = matchString
        self.matchLen = len(matchString)
        try:
            self.firstMatchChar = matchString[0]
        except IndexError:
            warnings.warn(
                "null string passed to Literal; use Empty() instead",
                SyntaxWarning,
                stacklevel=2,
            )
            self.__class__ = Empty
        self.name = '"%s"' % str(self.match)
        self.errmsg = "Expected " + self.name
        self.mayReturnEmpty = False
        self.mayIndexError = False

        # Performance tuning: modify __class__ to select
        # a parseImpl optimized for single-character check
        if self.matchLen == 1 and type(self) is Literal:
            self.__class__ = _SingleCharLiteral

    def parseImpl(self, instring, loc, doActions=True):
        if instring[loc] == self.firstMatchChar and instring.startswith(
            self.match, loc
        ):
            return loc + self.matchLen, self.match
        raise ParseException(instring, loc, self.errmsg, self)


class _SingleCharLiteral(Literal):
    def parseImpl(self, instring, loc, doActions=True):
        if instring[loc] == self.firstMatchChar:
            return loc + 1, self.match
        raise ParseException(instring, loc, self.errmsg, self)


ParserElement._literalStringClass = Literal


class Keyword(Token):
    """Token to exactly match a specified string as a keyword, that is,
    it must be immediately followed by a non-keyword character.  Compare
    with :class:`Literal`:

     - ``Literal("if")`` will match the leading ``'if'`` in
       ``'ifAndOnlyIf'``.
     - ``Keyword("if")`` will not; it will only match the leading
       ``'if'`` in ``'if x=1'``, or ``'if(y==2)'``

    Accepts two optional constructor arguments in addition to the
    keyword string:

     - ``identChars`` is a string of characters that would be valid
       identifier characters, defaulting to all alphanumerics + "_" and
       "$"
     - ``caseless`` allows case-insensitive matching, default is ``False``.

    Example::

        Keyword("start").parseString("start")  # -> ['start']
        Keyword("start").parseString("starting")  # -> Exception

    For case-insensitive matching, use :class:`CaselessKeyword`.
    """

    DEFAULT_KEYWORD_CHARS = alphanums + "_$"

    def __init__(self, matchString, identChars=None, caseless=False):
        super().__init__()
        if identChars is None:
            identChars = Keyword.DEFAULT_KEYWORD_CHARS
        self.match = matchString
        self.matchLen = len(matchString)
        try:
            self.firstMatchChar = matchString[0]
        except IndexError:
            warnings.warn(
                "null string passed to Keyword; use Empty() instead",
                SyntaxWarning,
                stacklevel=2,
            )
        self.name = '"%s"' % self.match
        self.errmsg = "Expected " + self.name
        self.mayReturnEmpty = False
        self.mayIndexError = False
        self.caseless = caseless
        if caseless:
            self.caselessmatch = matchString.upper()
            identChars = identChars.upper()
        self.identChars = set(identChars)

    def parseImpl(self, instring, loc, doActions=True):
        if self.caseless:
            if (
                (instring[loc : loc + self.matchLen].upper() == self.caselessmatch)
                and (
                    loc >= len(instring) - self.matchLen
                    or instring[loc + self.matchLen].upper() not in self.identChars
                )
                and (loc == 0 or instring[loc - 1].upper() not in self.identChars)
            ):
                return loc + self.matchLen, self.match

        else:
            if instring[loc] == self.firstMatchChar:
                if (
                    (self.matchLen == 1 or instring.startswith(self.match, loc))
                    and (
                        loc >= len(instring) - self.matchLen
                        or instring[loc + self.matchLen] not in self.identChars
                    )
                    and (loc == 0 or instring[loc - 1] not in self.identChars)
                ):
                    return loc + self.matchLen, self.match

        raise ParseException(instring, loc, self.errmsg, self)

    def copy(self):
        c = super().copy()
        c.identChars = Keyword.DEFAULT_KEYWORD_CHARS
        return c

    @staticmethod
    def setDefaultKeywordChars(chars):
        """Overrides the default Keyword chars
        """
        Keyword.DEFAULT_KEYWORD_CHARS = chars


class CaselessLiteral(Literal):
    """Token to match a specified string, ignoring case of letters.
    Note: the matched results will always be in the case of the given
    match string, NOT the case of the input text.

    Example::

        OneOrMore(CaselessLiteral("CMD")).parseString("cmd CMD Cmd10")
        # -> ['CMD', 'CMD', 'CMD']

    (Contrast with example for :class:`CaselessKeyword`.)
    """

    def __init__(self, matchString):
        super().__init__(matchString.upper())
        # Preserve the defining literal.
        self.returnString = matchString
        self.name = "'%s'" % self.returnString
        self.errmsg = "Expected " + self.name

    def parseImpl(self, instring, loc, doActions=True):
        if instring[loc : loc + self.matchLen].upper() == self.match:
            return loc + self.matchLen, self.returnString
        raise ParseException(instring, loc, self.errmsg, self)


class CaselessKeyword(Keyword):
    """
    Caseless version of :class:`Keyword`.

    Example::

        OneOrMore(CaselessKeyword("CMD")).parseString("cmd CMD Cmd10")
        # -> ['CMD', 'CMD']

    (Contrast with example for :class:`CaselessLiteral`.)
    """

    def __init__(self, matchString, identChars=None):
        super().__init__(matchString, identChars, caseless=True)


class CloseMatch(Token):
    """A variation on :class:`Literal` which matches "close" matches,
    that is, strings with at most 'n' mismatching characters.
    :class:`CloseMatch` takes parameters:

     - ``match_string`` - string to be matched
     - ``maxMismatches`` - (``default=1``) maximum number of
       mismatches allowed to count as a match

    The results from a successful parse will contain the matched text
    from the input string and the following named results:

     - ``mismatches`` - a list of the positions within the
       match_string where mismatches were found
     - ``original`` - the original match_string used to compare
       against the input string

    If ``mismatches`` is an empty list, then the match was an exact
    match.

    Example::

        patt = CloseMatch("ATCATCGAATGGA")
        patt.parseString("ATCATCGAAXGGA") # -> (['ATCATCGAAXGGA'], {'mismatches': [[9]], 'original': ['ATCATCGAATGGA']})
        patt.parseString("ATCAXCGAAXGGA") # -> Exception: Expected 'ATCATCGAATGGA' (with up to 1 mismatches) (at char 0), (line:1, col:1)

        # exact match
        patt.parseString("ATCATCGAATGGA") # -> (['ATCATCGAATGGA'], {'mismatches': [[]], 'original': ['ATCATCGAATGGA']})

        # close match allowing up to 2 mismatches
        patt = CloseMatch("ATCATCGAATGGA", maxMismatches=2)
        patt.parseString("ATCAXCGAAXGGA") # -> (['ATCAXCGAAXGGA'], {'mismatches': [[4, 9]], 'original': ['ATCATCGAATGGA']})
    """

    def __init__(self, match_string, maxMismatches=1):
        super().__init__()
        self.name = match_string
        self.match_string = match_string
        self.maxMismatches = maxMismatches
        self.errmsg = "Expected %r (with up to %d mismatches)" % (
            self.match_string,
            self.maxMismatches,
        )
        self.mayIndexError = False
        self.mayReturnEmpty = False

    def parseImpl(self, instring, loc, doActions=True):
        start = loc
        instrlen = len(instring)
        maxloc = start + len(self.match_string)

        if maxloc <= instrlen:
            match_string = self.match_string
            match_stringloc = 0
            mismatches = []
            maxMismatches = self.maxMismatches

            for match_stringloc, s_m in enumerate(
                zip(instring[loc:maxloc], match_string)
            ):
                src, mat = s_m
                if src != mat:
                    mismatches.append(match_stringloc)
                    if len(mismatches) > maxMismatches:
                        break
            else:
                loc = start + match_stringloc + 1
                results = ParseResults([instring[start:loc]])
                results["original"] = match_string
                results["mismatches"] = mismatches
                return loc, results

        raise ParseException(instring, loc, self.errmsg, self)


class Word(Token):
    """Token for matching words composed of allowed character sets.
    Defined with string containing all allowed initial characters, an
    optional string containing allowed body characters (if omitted,
    defaults to the initial character set), and an optional minimum,
    maximum, and/or exact length.  The default value for ``min`` is
    1 (a minimum value < 1 is not valid); the default values for
    ``max`` and ``exact`` are 0, meaning no maximum or exact
    length restriction. An optional ``excludeChars`` parameter can
    list characters that might be found in the input ``bodyChars``
    string; useful to define a word of all printables except for one or
    two characters, for instance.

    :class:`srange` is useful for defining custom character set strings
    for defining :class:`Word` expressions, using range notation from
    regular expression character sets.

    A common mistake is to use :class:`Word` to match a specific literal
    string, as in ``Word("Address")``. Remember that :class:`Word`
    uses the string argument to define *sets* of matchable characters.
    This expression would match "Add", "AAA", "dAred", or any other word
    made up of the characters 'A', 'd', 'r', 'e', and 's'. To match an
    exact literal string, use :class:`Literal` or :class:`Keyword`.

    pyparsing includes helper strings for building Words:

     - :class:`alphas`
     - :class:`nums`
     - :class:`alphanums`
     - :class:`hexnums`
     - :class:`alphas8bit` (alphabetic characters in ASCII range 128-255
       - accented, tilded, umlauted, etc.)
     - :class:`punc8bit` (non-alphabetic characters in ASCII range
       128-255 - currency, symbols, superscripts, diacriticals, etc.)
     - :class:`printables` (any non-whitespace character)

    Example::

        # a word composed of digits
        integer = Word(nums) # equivalent to Word("0123456789") or Word(srange("0-9"))

        # a word with a leading capital, and zero or more lowercase
        capital_word = Word(alphas.upper(), alphas.lower())

        # hostnames are alphanumeric, with leading alpha, and '-'
        hostname = Word(alphas, alphanums + '-')

        # roman numeral (not a strict parser, accepts invalid mix of characters)
        roman = Word("IVXLCDM")

        # any string of non-whitespace characters, except for ','
        csv_value = Word(printables, excludeChars=",")
    """

    def __init__(
        self,
        initChars,
        bodyChars=None,
        min=1,
        max=0,
        exact=0,
        asKeyword=False,
        excludeChars=None,
    ):
        super().__init__()
        if excludeChars:
            excludeChars = set(excludeChars)
            initChars = "".join(c for c in initChars if c not in excludeChars)
            if bodyChars:
                bodyChars = "".join(c for c in bodyChars if c not in excludeChars)
        self.initCharsOrig = initChars
        self.initChars = set(initChars)
        if bodyChars:
            self.bodyCharsOrig = bodyChars
            self.bodyChars = set(bodyChars)
        else:
            self.bodyCharsOrig = initChars
            self.bodyChars = set(initChars)

        self.maxSpecified = max > 0

        if min < 1:
            raise ValueError(
                "cannot specify a minimum length < 1; use Optional(Word()) if zero-length word is permitted"
            )

        self.minLen = min

        if max > 0:
            self.maxLen = max
        else:
            self.maxLen = _MAX_INT

        if exact > 0:
            self.maxLen = exact
            self.minLen = exact

        self.name = str(self)
        self.errmsg = "Expected " + self.name
        self.mayIndexError = False
        self.asKeyword = asKeyword

        if " " not in self.initCharsOrig + self.bodyCharsOrig and (
            min == 1 and max == 0 and exact == 0
        ):
            if self.bodyCharsOrig == self.initCharsOrig:
                self.reString = "[%s]+" % _collapseAndEscapeRegexRangeChars(
                    self.initCharsOrig
                )
            elif len(self.initCharsOrig) == 1:
                self.reString = "%s[%s]*" % (
                    re.escape(self.initCharsOrig),
                    _collapseAndEscapeRegexRangeChars(self.bodyCharsOrig),
                )
            else:
                self.reString = "[%s][%s]*" % (
                    _collapseAndEscapeRegexRangeChars(self.initCharsOrig),
                    _collapseAndEscapeRegexRangeChars(self.bodyCharsOrig),
                )
            if self.asKeyword:
                self.reString = r"\b" + self.reString + r"\b"

            try:
                self.re = re.compile(self.reString)
            except sre_constants.error:
                self.re = None
            else:
                self.re_match = self.re.match
                self.__class__ = _WordRegex

    def parseImpl(self, instring, loc, doActions=True):
        if instring[loc] not in self.initChars:
            raise ParseException(instring, loc, self.errmsg, self)

        start = loc
        loc += 1
        instrlen = len(instring)
        bodychars = self.bodyChars
        maxloc = start + self.maxLen
        maxloc = min(maxloc, instrlen)
        while loc < maxloc and instring[loc] in bodychars:
            loc += 1

        throwException = False
        if loc - start < self.minLen:
            throwException = True
        elif self.maxSpecified and loc < instrlen and instring[loc] in bodychars:
            throwException = True
        elif self.asKeyword:
            if (
                start > 0
                and instring[start - 1] in bodychars
                or loc < instrlen
                and instring[loc] in bodychars
            ):
                throwException = True

        if throwException:
            raise ParseException(instring, loc, self.errmsg, self)

        return loc, instring[start:loc]

    def __str__(self):
        try:
            return super().__str__()
        except Exception:
            pass

        if self.strRepr is None:

            def charsAsStr(s):
                if len(s) > 4:
                    return s[:4] + "..."
                else:
                    return s

            if self.initCharsOrig != self.bodyCharsOrig:
                self.strRepr = "W:(%s, %s)" % (
                    charsAsStr(self.initCharsOrig),
                    charsAsStr(self.bodyCharsOrig),
                )
            else:
                self.strRepr = "W:(%s)" % charsAsStr(self.initCharsOrig)

        return self.strRepr


class _WordRegex(Word):
    def parseImpl(self, instring, loc, doActions=True):
        result = self.re_match(instring, loc)
        if not result:
            raise ParseException(instring, loc, self.errmsg, self)

        loc = result.end()
        return loc, result.group()


class Char(_WordRegex):
    """A short-cut class for defining ``Word(characters, exact=1)``,
    when defining a match of any single character in a string of
    characters.
    """

    def __init__(self, charset, asKeyword=False, excludeChars=None):
        super().__init__(
            charset, exact=1, asKeyword=asKeyword, excludeChars=excludeChars
        )
        self.reString = "[{}]".format(_collapseAndEscapeRegexRangeChars(self.initChars))
        if asKeyword:
            self.reString = r"\b{}\b".format(self.reString)
        self.re = re.compile(self.reString)
        self.re_match = self.re.match


class Regex(Token):
    r"""Token for matching strings that match a given regular
    expression. Defined with string specifying the regular expression in
    a form recognized by the stdlib Python  `re module <https://docs.python.org/3/library/re.html>`_.
    If the given regex contains named groups (defined using ``(?P<name>...)``),
    these will be preserved as named :class:`ParseResults`.

    If instead of the Python stdlib re module you wish to use a different RE module
    (such as the `regex` module), you can replace it by either building your
    Regex object with a compiled RE that was compiled using regex, or by replacing
    the imported `re` module in pyparsing with the `regex` module:


    Example::

        realnum = Regex(r"[+-]?\d+\.\d*")
        date = Regex(r'(?P<year>\d{4})-(?P<month>\d\d?)-(?P<day>\d\d?)')
        # ref: https://stackoverflow.com/questions/267399/how-do-you-match-only-valid-roman-numerals-with-a-regular-expression
        roman = Regex(r"M{0,4}(CM|CD|D?{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})")

        import regex
        parser = pp.Regex(regex.compile(r'[0-9]'))

        # or

        import pyparsing
        pyparsing.re = regex

        # both of these will use the regex module to compile their internal re's
        parser = pp.Regex(r'[0-9]')
        parser = pp.Word(pp.nums)

    """

    def __init__(self, pattern, flags=0, asGroupList=False, asMatch=False):
        """The parameters ``pattern`` and ``flags`` are passed
        to the ``re.compile()`` function as-is. See the Python
        `re module <https://docs.python.org/3/library/re.html>`_ module for an
        explanation of the acceptable patterns and flags.
        """
        super().__init__()

        if isinstance(pattern, str_type):
            if not pattern:
                warnings.warn(
                    "null string passed to Regex; use Empty() instead",
                    SyntaxWarning,
                    stacklevel=2,
                )

            self.pattern = pattern
            self.flags = flags

            try:
                self.re = re.compile(self.pattern, self.flags)
                self.reString = self.pattern
            except sre_constants.error:
                warnings.warn(
                    "invalid pattern (%s) passed to Regex" % pattern,
                    SyntaxWarning,
                    stacklevel=2,
                )
                raise

        elif hasattr(pattern, "pattern") and hasattr(pattern, "match"):
            self.re = pattern
            self.pattern = self.reString = pattern.pattern
            self.flags = flags

        else:
            raise TypeError(
                "Regex may only be constructed with a string or a compiled RE object"
            )

        self.re_match = self.re.match

        self.name = str(self)
        self.errmsg = "Expected " + self.name
        self.mayIndexError = False
        self.mayReturnEmpty = self.re_match("") is not None
        self.asGroupList = asGroupList
        self.asMatch = asMatch
        if self.asGroupList:
            self.parseImpl = self.parseImplAsGroupList
        if self.asMatch:
            self.parseImpl = self.parseImplAsMatch

    def parseImpl(self, instring, loc, doActions=True):
        result = self.re_match(instring, loc)
        if not result:
            raise ParseException(instring, loc, self.errmsg, self)

        loc = result.end()
        ret = ParseResults(result.group())
        d = result.groupdict()
        if d:
            for k, v in d.items():
                ret[k] = v
        return loc, ret

    def parseImplAsGroupList(self, instring, loc, doActions=True):
        result = self.re_match(instring, loc)
        if not result:
            raise ParseException(instring, loc, self.errmsg, self)

        loc = result.end()
        ret = result.groups()
        return loc, ret

    def parseImplAsMatch(self, instring, loc, doActions=True):
        result = self.re_match(instring, loc)
        if not result:
            raise ParseException(instring, loc, self.errmsg, self)

        loc = result.end()
        ret = result
        return loc, ret

    def __str__(self):
        try:
            return super().__str__()
        except Exception:
            pass

        if self.strRepr is None:
            self.strRepr = "Re:(%s)" % repr(self.pattern)

        return self.strRepr

    def sub(self, repl):
        r"""
        Return :class:`Regex` with an attached parse action to transform the parsed
        result as if called using `re.sub(expr, repl, string) <https://docs.python.org/3/library/re.html#re.sub>`_.

        Example::

            make_html = Regex(r"(\w+):(.*?):").sub(r"<\1>\2</\1>")
            print(make_html.transformString("h1:main title:"))
            # prints "<h1>main title</h1>"
        """
        if self.asGroupList:
            warnings.warn(
                "cannot use sub() with Regex(asGroupList=True)",
                SyntaxWarning,
                stacklevel=2,
            )
            raise SyntaxError()

        if self.asMatch and callable(repl):
            warnings.warn(
                "cannot use sub() with a callable with Regex(asMatch=True)",
                SyntaxWarning,
                stacklevel=2,
            )
            raise SyntaxError()

        if self.asMatch:

            def pa(tokens):
                return tokens[0].expand(repl)

        else:

            def pa(tokens):
                return self.re.sub(repl, tokens[0])

        return self.addParseAction(pa)


class QuotedString(Token):
    r"""
    Token for matching strings that are delimited by quoting characters.

    Defined with the following parameters:

        - quoteChar - string of one or more characters defining the
          quote delimiting string
        - escChar - character to escape quotes, typically backslash
          (default= ``None``)
        - escQuote - special quote sequence to escape an embedded quote
          string (such as SQL's ``""`` to escape an embedded ``"``)
          (default= ``None``)
        - multiline - boolean indicating whether quotes can span
          multiple lines (default= ``False``)
        - unquoteResults - boolean indicating whether the matched text
          should be unquoted (default= ``True``)
        - endQuoteChar - string of one or more characters defining the
          end of the quote delimited string (default= ``None``  => same as
          quoteChar)
        - convertWhitespaceEscapes - convert escaped whitespace
          (``'\t'``, ``'\n'``, etc.) to actual whitespace
          (default= ``True``)

    Example::

        qs = QuotedString('"')
        print(qs.searchString('lsjdf "This is the quote" sldjf'))
        complex_qs = QuotedString('{{', endQuoteChar='}}')
        print(complex_qs.searchString('lsjdf {{This is the "quote"}} sldjf'))
        sql_qs = QuotedString('"', escQuote='""')
        print(sql_qs.searchString('lsjdf "This is the quote with ""embedded"" quotes" sldjf'))

    prints::

        [['This is the quote']]
        [['This is the "quote"']]
        [['This is the quote with "embedded" quotes']]
    """

    def __init__(
        self,
        quoteChar,
        escChar=None,
        escQuote=None,
        multiline=False,
        unquoteResults=True,
        endQuoteChar=None,
        convertWhitespaceEscapes=True,
    ):
        super().__init__()

        # remove white space from quote chars - wont work anyway
        quoteChar = quoteChar.strip()
        if not quoteChar:
            warnings.warn(
                "quoteChar cannot be the empty string", SyntaxWarning, stacklevel=2
            )
            raise SyntaxError()

        if endQuoteChar is None:
            endQuoteChar = quoteChar
        else:
            endQuoteChar = endQuoteChar.strip()
            if not endQuoteChar:
                warnings.warn(
                    "endQuoteChar cannot be the empty string",
                    SyntaxWarning,
                    stacklevel=2,
                )
                raise SyntaxError()

        self.quoteChar = quoteChar
        self.quoteCharLen = len(quoteChar)
        self.firstQuoteChar = quoteChar[0]
        self.endQuoteChar = endQuoteChar
        self.endQuoteCharLen = len(endQuoteChar)
        self.escChar = escChar
        self.escQuote = escQuote
        self.unquoteResults = unquoteResults
        self.convertWhitespaceEscapes = convertWhitespaceEscapes

        if multiline:
            self.flags = re.MULTILINE | re.DOTALL
            self.pattern = r"%s(?:[^%s%s]" % (
                re.escape(self.quoteChar),
                _escapeRegexRangeChars(self.endQuoteChar[0]),
                (escChar is not None and _escapeRegexRangeChars(escChar) or ""),
            )
        else:
            self.flags = 0
            self.pattern = r"%s(?:[^%s\n\r%s]" % (
                re.escape(self.quoteChar),
                _escapeRegexRangeChars(self.endQuoteChar[0]),
                (escChar is not None and _escapeRegexRangeChars(escChar) or ""),
            )
        if len(self.endQuoteChar) > 1:
            self.pattern += (
                "|(?:"
                + ")|(?:".join(
                    "%s[^%s]"
                    % (
                        re.escape(self.endQuoteChar[:i]),
                        _escapeRegexRangeChars(self.endQuoteChar[i]),
                    )
                    for i in range(len(self.endQuoteChar) - 1, 0, -1)
                )
                + ")"
            )

        if escQuote:
            self.pattern += r"|(?:%s)" % re.escape(escQuote)
        if escChar:
            self.pattern += r"|(?:%s.)" % re.escape(escChar)
            self.escCharReplacePattern = re.escape(self.escChar) + "(.)"
        self.pattern += r")*%s" % re.escape(self.endQuoteChar)

        try:
            self.re = re.compile(self.pattern, self.flags)
            self.reString = self.pattern
            self.re_match = self.re.match
        except sre_constants.error:
            warnings.warn(
                "invalid pattern (%s) passed to Regex" % self.pattern,
                SyntaxWarning,
                stacklevel=2,
            )
            raise

        self.name = str(self)
        self.errmsg = "Expected " + self.name
        self.mayIndexError = False
        self.mayReturnEmpty = True

    def parseImpl(self, instring, loc, doActions=True):
        result = (
            instring[loc] == self.firstQuoteChar
            and self.re_match(instring, loc)
            or None
        )
        if not result:
            raise ParseException(instring, loc, self.errmsg, self)

        loc = result.end()
        ret = result.group()

        if self.unquoteResults:

            # strip off quotes
            ret = ret[self.quoteCharLen : -self.endQuoteCharLen]

            if isinstance(ret, str_type):
                # replace escaped whitespace
                if "\\" in ret and self.convertWhitespaceEscapes:
                    ws_map = {
                        r"\t": "\t",
                        r"\n": "\n",
                        r"\f": "\f",
                        r"\r": "\r",
                    }
                    for wslit, wschar in ws_map.items():
                        ret = ret.replace(wslit, wschar)

                # replace escaped characters
                if self.escChar:
                    ret = re.sub(self.escCharReplacePattern, r"\g<1>", ret)

                # replace escaped quotes
                if self.escQuote:
                    ret = ret.replace(self.escQuote, self.endQuoteChar)

        return loc, ret

    def __str__(self):
        try:
            return super().__str__()
        except Exception:
            pass

        if self.strRepr is None:
            self.strRepr = "quoted string, starting with %s ending with %s" % (
                self.quoteChar,
                self.endQuoteChar,
            )

        return self.strRepr


class CharsNotIn(Token):
    """Token for matching words composed of characters *not* in a given
    set (will include whitespace in matched characters if not listed in
    the provided exclusion set - see example). Defined with string
    containing all disallowed characters, and an optional minimum,
    maximum, and/or exact length.  The default value for ``min`` is
    1 (a minimum value < 1 is not valid); the default values for
    ``max`` and ``exact`` are 0, meaning no maximum or exact
    length restriction.

    Example::

        # define a comma-separated-value as anything that is not a ','
        csv_value = CharsNotIn(',')
        print(delimitedList(csv_value).parseString("dkls,lsdkjf,s12 34,@!#,213"))

    prints::

        ['dkls', 'lsdkjf', 's12 34', '@!#', '213']
    """

    def __init__(self, notChars, min=1, max=0, exact=0):
        super().__init__()
        self.skipWhitespace = False
        self.notChars = notChars

        if min < 1:
            raise ValueError(
                "cannot specify a minimum length < 1; use "
                "Optional(CharsNotIn()) if zero-length char group is permitted"
            )

        self.minLen = min

        if max > 0:
            self.maxLen = max
        else:
            self.maxLen = _MAX_INT

        if exact > 0:
            self.maxLen = exact
            self.minLen = exact

        self.name = str(self)
        self.errmsg = "Expected " + self.name
        self.mayReturnEmpty = self.minLen == 0
        self.mayIndexError = False

    def parseImpl(self, instring, loc, doActions=True):
        if instring[loc] in self.notChars:
            raise ParseException(instring, loc, self.errmsg, self)

        start = loc
        loc += 1
        notchars = self.notChars
        maxlen = min(start + self.maxLen, len(instring))
        while loc < maxlen and instring[loc] not in notchars:
            loc += 1

        if loc - start < self.minLen:
            raise ParseException(instring, loc, self.errmsg, self)

        return loc, instring[start:loc]

    def __str__(self):
        try:
            return super().__str__()
        except Exception:
            pass

        if self.strRepr is None:
            if len(self.notChars) > 4:
                self.strRepr = "!W:(%s...)" % self.notChars[:4]
            else:
                self.strRepr = "!W:(%s)" % self.notChars

        return self.strRepr


class White(Token):
    """Special matching class for matching whitespace.  Normally,
    whitespace is ignored by pyparsing grammars.  This class is included
    when some whitespace structures are significant.  Define with
    a string containing the whitespace characters to be matched; default
    is ``" \\t\\r\\n"``.  Also takes optional ``min``,
    ``max``, and ``exact`` arguments, as defined for the
    :class:`Word` class.
    """

    whiteStrs = {
        " ": "<SP>",
        "\t": "<TAB>",
        "\n": "<LF>",
        "\r": "<CR>",
        "\f": "<FF>",
        "\u00A0": "<NBSP>",
        "\u1680": "<OGHAM_SPACE_MARK>",
        "\u180E": "<MONGOLIAN_VOWEL_SEPARATOR>",
        "\u2000": "<EN_QUAD>",
        "\u2001": "<EM_QUAD>",
        "\u2002": "<EN_SPACE>",
        "\u2003": "<EM_SPACE>",
        "\u2004": "<THREE-PER-EM_SPACE>",
        "\u2005": "<FOUR-PER-EM_SPACE>",
        "\u2006": "<SIX-PER-EM_SPACE>",
        "\u2007": "<FIGURE_SPACE>",
        "\u2008": "<PUNCTUATION_SPACE>",
        "\u2009": "<THIN_SPACE>",
        "\u200A": "<HAIR_SPACE>",
        "\u200B": "<ZERO_WIDTH_SPACE>",
        "\u202F": "<NNBSP>",
        "\u205F": "<MMSP>",
        "\u3000": "<IDEOGRAPHIC_SPACE>",
    }

    def __init__(self, ws=" \t\r\n", min=1, max=0, exact=0):
        super().__init__()
        self.matchWhite = ws
        self.setWhitespaceChars(
            "".join(c for c in self.whiteChars if c not in self.matchWhite),
            copy_defaults=True,
        )
        # ~ self.leaveWhitespace()
        self.name = "".join(White.whiteStrs[c] for c in self.matchWhite)
        self.mayReturnEmpty = True
        self.errmsg = "Expected " + self.name

        self.minLen = min

        if max > 0:
            self.maxLen = max
        else:
            self.maxLen = _MAX_INT

        if exact > 0:
            self.maxLen = exact
            self.minLen = exact

    def parseImpl(self, instring, loc, doActions=True):
        if instring[loc] not in self.matchWhite:
            raise ParseException(instring, loc, self.errmsg, self)
        start = loc
        loc += 1
        maxloc = start + self.maxLen
        maxloc = min(maxloc, len(instring))
        while loc < maxloc and instring[loc] in self.matchWhite:
            loc += 1

        if loc - start < self.minLen:
            raise ParseException(instring, loc, self.errmsg, self)

        return loc, instring[start:loc]


class _PositionToken(Token):
    def __init__(self):
        super().__init__()
        self.name = self.__class__.__name__
        self.mayReturnEmpty = True
        self.mayIndexError = False


class GoToColumn(_PositionToken):
    """Token to advance to a specific column of input text; useful for
    tabular report scraping.
    """

    def __init__(self, colno):
        super().__init__()
        self.col = colno

    def preParse(self, instring, loc):
        if col(loc, instring) != self.col:
            instrlen = len(instring)
            if self.ignoreExprs:
                loc = self._skipIgnorables(instring, loc)
            while (
                loc < instrlen
                and instring[loc].isspace()
                and col(loc, instring) != self.col
            ):
                loc += 1
        return loc

    def parseImpl(self, instring, loc, doActions=True):
        thiscol = col(loc, instring)
        if thiscol > self.col:
            raise ParseException(instring, loc, "Text not in expected column", self)
        newloc = loc + self.col - thiscol
        ret = instring[loc:newloc]
        return newloc, ret


class LineStart(_PositionToken):
    r"""Matches if current position is at the beginning of a line within
    the parse string

    Example::

        test = '''\
        AAA this line
        AAA and this line
          AAA but not this one
        B AAA and definitely not this one
        '''

        for t in (LineStart() + 'AAA' + restOfLine).searchString(test):
            print(t)

    prints::

        ['AAA', ' this line']
        ['AAA', ' and this line']

    """

    def __init__(self):
        super().__init__()
        self.errmsg = "Expected start of line"

    def parseImpl(self, instring, loc, doActions=True):
        if col(loc, instring) == 1:
            return loc, []
        raise ParseException(instring, loc, self.errmsg, self)


class LineEnd(_PositionToken):
    """Matches if current position is at the end of a line within the
    parse string
    """

    def __init__(self):
        super().__init__()
        self.setWhitespaceChars(
            ParserElement.DEFAULT_WHITE_CHARS.replace("\n", ""), copy_defaults=False
        )
        self.errmsg = "Expected end of line"

    def parseImpl(self, instring, loc, doActions=True):
        if loc < len(instring):
            if instring[loc] == "\n":
                return loc + 1, "\n"
            else:
                raise ParseException(instring, loc, self.errmsg, self)
        elif loc == len(instring):
            return loc + 1, []
        else:
            raise ParseException(instring, loc, self.errmsg, self)


class StringStart(_PositionToken):
    """Matches if current position is at the beginning of the parse
    string
    """

    def __init__(self):
        super().__init__()
        self.errmsg = "Expected start of text"

    def parseImpl(self, instring, loc, doActions=True):
        if loc != 0:
            # see if entire string up to here is just whitespace and ignoreables
            if loc != self.preParse(instring, 0):
                raise ParseException(instring, loc, self.errmsg, self)
        return loc, []


class StringEnd(_PositionToken):
    """Matches if current position is at the end of the parse string
    """

    def __init__(self):
        super().__init__()
        self.errmsg = "Expected end of text"

    def parseImpl(self, instring, loc, doActions=True):
        if loc < len(instring):
            raise ParseException(instring, loc, self.errmsg, self)
        elif loc == len(instring):
            return loc + 1, []
        elif loc > len(instring):
            return loc, []
        else:
            raise ParseException(instring, loc, self.errmsg, self)


class WordStart(_PositionToken):
    """Matches if the current position is at the beginning of a
    :class:`Word`, and is not preceded by any character in a given
    set of ``wordChars`` (default= ``printables``). To emulate the
    ``\b`` behavior of regular expressions, use
    ``WordStart(alphanums)``. ``WordStart`` will also match at
    the beginning of the string being parsed, or at the beginning of
    a line.
    """

    def __init__(self, wordChars=printables):
        super().__init__()
        self.wordChars = set(wordChars)
        self.errmsg = "Not at the start of a word"

    def parseImpl(self, instring, loc, doActions=True):
        if loc != 0:
            if (
                instring[loc - 1] in self.wordChars
                or instring[loc] not in self.wordChars
            ):
                raise ParseException(instring, loc, self.errmsg, self)
        return loc, []


class WordEnd(_PositionToken):
    """Matches if the current position is at the end of a :class:`Word`,
    and is not followed by any character in a given set of ``wordChars``
    (default= ``printables``). To emulate the ``\b`` behavior of
    regular expressions, use ``WordEnd(alphanums)``. ``WordEnd``
    will also match at the end of the string being parsed, or at the end
    of a line.
    """

    def __init__(self, wordChars=printables):
        super().__init__()
        self.wordChars = set(wordChars)
        self.skipWhitespace = False
        self.errmsg = "Not at the end of a word"

    def parseImpl(self, instring, loc, doActions=True):
        instrlen = len(instring)
        if instrlen > 0 and loc < instrlen:
            if (
                instring[loc] in self.wordChars
                or instring[loc - 1] not in self.wordChars
            ):
                raise ParseException(instring, loc, self.errmsg, self)
        return loc, []


class ParseExpression(ParserElement):
    """Abstract subclass of ParserElement, for combining and
    post-processing parsed tokens.
    """

    def __init__(self, exprs, savelist=False):
        super().__init__(savelist)
        if isinstance(exprs, _generatorType):
            exprs = list(exprs)

        if isinstance(exprs, str_type):
            self.exprs = [self._literalStringClass(exprs)]
        elif isinstance(exprs, ParserElement):
            self.exprs = [exprs]
        elif isinstance(exprs, Iterable):
            exprs = list(exprs)
            # if sequence of strings provided, wrap with Literal
            if any(isinstance(expr, str_type) for expr in exprs):
                exprs = (
                    self._literalStringClass(e) if isinstance(e, str_type) else e
                    for e in exprs
                )
            self.exprs = list(exprs)
        else:
            try:
                self.exprs = list(exprs)
            except TypeError:
                self.exprs = [exprs]
        self.callPreparse = False

    def append(self, other):
        self.exprs.append(other)
        self.strRepr = None
        return self

    def leaveWhitespace(self):
        """Extends ``leaveWhitespace`` defined in base class, and also invokes ``leaveWhitespace`` on
           all contained expressions."""
        self.skipWhitespace = False
        self.exprs = [e.copy() for e in self.exprs]
        for e in self.exprs:
            e.leaveWhitespace()
        return self

    def ignore(self, other):
        if isinstance(other, Suppress):
            if other not in self.ignoreExprs:
                super().ignore(other)
                for e in self.exprs:
                    e.ignore(self.ignoreExprs[-1])
        else:
            super().ignore(other)
            for e in self.exprs:
                e.ignore(self.ignoreExprs[-1])
        return self

    def __str__(self):
        try:
            return super().__str__()
        except Exception:
            pass

        if self.strRepr is None:
            self.strRepr = "%s:(%s)" % (self.__class__.__name__, str(self.exprs))
        return self.strRepr

    def streamline(self):
        super().streamline()

        for e in self.exprs:
            e.streamline()

        # collapse nested And's of the form And(And(And(a, b), c), d) to And(a, b, c, d)
        # but only if there are no parse actions or resultsNames on the nested And's
        # (likewise for Or's and MatchFirst's)
        if len(self.exprs) == 2:
            other = self.exprs[0]
            if (
                isinstance(other, self.__class__)
                and not other.parseAction
                and other.resultsName is None
                and not other.debug
            ):
                self.exprs = other.exprs[:] + [self.exprs[1]]
                self.strRepr = None
                self.mayReturnEmpty |= other.mayReturnEmpty
                self.mayIndexError |= other.mayIndexError

            other = self.exprs[-1]
            if (
                isinstance(other, self.__class__)
                and not other.parseAction
                and other.resultsName is None
                and not other.debug
            ):
                self.exprs = self.exprs[:-1] + other.exprs[:]
                self.strRepr = None
                self.mayReturnEmpty |= other.mayReturnEmpty
                self.mayIndexError |= other.mayIndexError

        self.errmsg = "Expected " + str(self)

        return self

    def validate(self, validateTrace=None):
        tmp = (validateTrace if validateTrace is not None else [])[:] + [self]
        for e in self.exprs:
            e.validate(tmp)
        self.checkRecursion([])

    def copy(self):
        ret = super().copy()
        ret.exprs = [e.copy() for e in self.exprs]
        return ret

    def _setResultsName(self, name, listAllMatches=False):
        if __diag__.warn_ungrouped_named_tokens_in_collection:
            for e in self.exprs:
                if isinstance(e, ParserElement) and e.resultsName:
                    warnings.warn(
                        "{}: setting results name {!r} on {} expression "
                        "collides with {!r} on contained expression".format(
                            "warn_ungrouped_named_tokens_in_collection",
                            name,
                            type(self).__name__,
                            e.resultsName,
                        ),
                        stacklevel=3,
                    )

        return super()._setResultsName(name, listAllMatches)


class And(ParseExpression):
    """
    Requires all given :class:`ParseExpression`\ s to be found in the given order.
    Expressions may be separated by whitespace.
    May be constructed using the ``'+'`` operator.
    May also be constructed using the ``'-'`` operator, which will
    suppress backtracking.

    Example::

        integer = Word(nums)
        name_expr = OneOrMore(Word(alphas))

        expr = And([integer("id"), name_expr("name"), integer("age")])
        # more easily written as:
        expr = integer("id") + name_expr("name") + integer("age")
    """

    class _ErrorStop(Empty):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.name = "-"
            self.leaveWhitespace()

    def __init__(self, exprs, savelist=True):
        exprs = list(exprs)
        if exprs and Ellipsis in exprs:
            tmp = []
            for i, expr in enumerate(exprs):
                if expr is Ellipsis:
                    if i < len(exprs) - 1:
                        skipto_arg = (Empty() + exprs[i + 1]).exprs[-1]
                        tmp.append(SkipTo(skipto_arg)("_skipped*"))
                    else:
                        raise Exception(
                            "cannot construct And with sequence ending in ..."
                        )
                else:
                    tmp.append(expr)
            exprs[:] = tmp
        super().__init__(exprs, savelist)
        self.mayReturnEmpty = all(e.mayReturnEmpty for e in self.exprs)
        self.setWhitespaceChars(
            self.exprs[0].whiteChars, copy_defaults=self.exprs[0].copyDefaultWhiteChars
        )
        self.skipWhitespace = self.exprs[0].skipWhitespace
        self.callPreparse = True

    def streamline(self):
        # collapse any _PendingSkip's
        if self.exprs:
            if any(
                isinstance(e, ParseExpression)
                and e.exprs
                and isinstance(e.exprs[-1], _PendingSkip)
                for e in self.exprs[:-1]
            ):
                for i, e in enumerate(self.exprs[:-1]):
                    if e is None:
                        continue
                    if (
                        isinstance(e, ParseExpression)
                        and e.exprs
                        and isinstance(e.exprs[-1], _PendingSkip)
                    ):
                        e.exprs[-1] = e.exprs[-1] + self.exprs[i + 1]
                        self.exprs[i + 1] = None
                self.exprs = [e for e in self.exprs if e is not None]

        super().streamline()
        self.mayReturnEmpty = all(e.mayReturnEmpty for e in self.exprs)
        return self

    def parseImpl(self, instring, loc, doActions=True):
        # pass False as last arg to _parse for first element, since we already
        # pre-parsed the string as part of our And pre-parsing
        loc, resultlist = self.exprs[0]._parse(
            instring, loc, doActions, callPreParse=False
        )
        errorStop = False
        for e in self.exprs[1:]:
            if isinstance(e, And._ErrorStop):
                errorStop = True
                continue
            if errorStop:
                try:
                    loc, exprtokens = e._parse(instring, loc, doActions)
                except ParseSyntaxException:
                    raise
                except ParseBaseException as pe:
                    pe.__traceback__ = None
                    raise ParseSyntaxException._from_exception(pe)
                except IndexError:
                    raise ParseSyntaxException(
                        instring, len(instring), self.errmsg, self
                    )
            else:
                loc, exprtokens = e._parse(instring, loc, doActions)
            if exprtokens or exprtokens.haskeys():
                resultlist += exprtokens
        return loc, resultlist

    def __iadd__(self, other):
        if isinstance(other, str_type):
            other = self._literalStringClass(other)
        return self.append(other)  # And([self, other])

    def checkRecursion(self, parseElementList):
        subRecCheckList = parseElementList[:] + [self]
        for e in self.exprs:
            e.checkRecursion(subRecCheckList)
            if not e.mayReturnEmpty:
                break

    def __str__(self):
        if hasattr(self, "name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + " ".join(str(e) for e in self.exprs) + "}"

        return self.strRepr


class Or(ParseExpression):
    """Requires that at least one :class:`ParseExpression` is found. If
    two expressions match, the expression that matches the longest
    string will be used. May be constructed using the ``'^'``
    operator.

    Example::

        # construct Or using '^' operator

        number = Word(nums) ^ Combine(Word(nums) + '.' + Word(nums))
        print(number.searchString("123 3.1416 789"))

    prints::

        [['123'], ['3.1416'], ['789']]
    """

    def __init__(self, exprs, savelist=False):
        super().__init__(exprs, savelist)
        if self.exprs:
            self.mayReturnEmpty = any(e.mayReturnEmpty for e in self.exprs)
        else:
            self.mayReturnEmpty = True

    def streamline(self):
        super().streamline()
        self.saveAsList = any(e.saveAsList for e in self.exprs)
        return self

    def parseImpl(self, instring, loc, doActions=True):
        maxExcLoc = -1
        maxException = None
        matches = []
        fatals = []
        for e in self.exprs:
            try:
                loc2 = e.tryParse(instring, loc, raise_fatal=True)
            except ParseFatalException as pfe:
                pfe.__traceback__ = None
                pfe.parserElement = e
                fatals.append(pfe)
                maxException = None
                maxExcLoc = -1
            except ParseException as err:
                if not fatals:
                    err.__traceback__ = None
                    if err.loc > maxExcLoc:
                        maxException = err
                        maxExcLoc = err.loc
            except IndexError:
                if len(instring) > maxExcLoc:
                    maxException = ParseException(
                        instring, len(instring), e.errmsg, self
                    )
                    maxExcLoc = len(instring)
            else:
                # save match among all matches, to retry longest to shortest
                matches.append((loc2, e))

        if matches:
            # re-evaluate all matches in descending order of length of match, in case attached actions
            # might change whether or how much they match of the input.
            matches.sort(key=itemgetter(0), reverse=True)

            if not doActions:
                # no further conditions or parse actions to change the selection of
                # alternative, so the first match will be the best match
                best_expr = matches[0][1]
                return best_expr._parse(instring, loc, doActions)

            longest = -1, None
            for loc1, expr1 in matches:
                if loc1 <= longest[0]:
                    # already have a longer match than this one will deliver, we are done
                    return longest

                try:
                    loc2, toks = expr1._parse(instring, loc, doActions)
                except ParseException as err:
                    err.__traceback__ = None
                    if err.loc > maxExcLoc:
                        maxException = err
                        maxExcLoc = err.loc
                else:
                    if loc2 >= loc1:
                        return loc2, toks
                    # didn't match as much as before
                    elif loc2 > longest[0]:
                        longest = loc2, toks

            if longest != (-1, None):
                return longest

        if fatals:
            if len(fatals) > 1:
                fatals.sort(key=lambda e: -e.loc)
                if fatals[0].loc == fatals[1].loc:
                    fatals.sort(key=lambda e: (-e.loc, -len(str(e.parserElement))))
            max_fatal = fatals[0]
            raise max_fatal

        if maxException is not None:
            maxException.msg = self.errmsg
            raise maxException
        else:
            raise ParseException(
                instring, loc, "no defined alternatives to match", self
            )

    def __ixor__(self, other):
        if isinstance(other, str_type):
            other = self._literalStringClass(other)
        return self.append(other)  # Or([self, other])

    def __str__(self):
        if hasattr(self, "name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + " ^ ".join(str(e) for e in self.exprs) + "}"

        return self.strRepr

    def checkRecursion(self, parseElementList):
        subRecCheckList = parseElementList[:] + [self]
        for e in self.exprs:
            e.checkRecursion(subRecCheckList)

    def _setResultsName(self, name, listAllMatches=False):
        if __diag__.warn_multiple_tokens_in_named_alternation:
            if any(isinstance(e, And) for e in self.exprs):
                warnings.warn(
                    "{}: setting results name {!r} on {} expression "
                    "will return a list of all parsed tokens in an And alternative, "
                    "in prior versions only the first token was returned".format(
                        "warn_multiple_tokens_in_named_alternation",
                        name,
                        type(self).__name__,
                    ),
                    stacklevel=3,
                )

        return super()._setResultsName(name, listAllMatches)


class MatchFirst(ParseExpression):
    """Requires that at least one :class:`ParseExpression` is found. If
    two expressions match, the first one listed is the one that will
    match. May be constructed using the ``'|'`` operator.

    Example::

        # construct MatchFirst using '|' operator

        # watch the order of expressions to match
        number = Word(nums) | Combine(Word(nums) + '.' + Word(nums))
        print(number.searchString("123 3.1416 789")) #  Fail! -> [['123'], ['3'], ['1416'], ['789']]

        # put more selective expression first
        number = Combine(Word(nums) + '.' + Word(nums)) | Word(nums)
        print(number.searchString("123 3.1416 789")) #  Better -> [['123'], ['3.1416'], ['789']]
    """

    def __init__(self, exprs, savelist=False):
        super().__init__(exprs, savelist)
        if self.exprs:
            self.mayReturnEmpty = any(e.mayReturnEmpty for e in self.exprs)
        else:
            self.mayReturnEmpty = True

    def streamline(self):
        super().streamline()
        self.saveAsList = any(e.saveAsList for e in self.exprs)
        return self

    def parseImpl(self, instring, loc, doActions=True):
        maxExcLoc = -1
        maxException = None
        fatals = []
        for e in self.exprs:
            try:
                ret = e._parse(instring, loc, doActions)
                return ret
            except ParseFatalException as pfe:
                pfe.__traceback__ = None
                pfe.parserElement = e
                fatals.append(pfe)
                maxException = None
            except ParseException as err:
                if not fatals and err.loc > maxExcLoc:
                    maxException = err
                    maxExcLoc = err.loc
            except IndexError:
                if len(instring) > maxExcLoc:
                    maxException = ParseException(
                        instring, len(instring), e.errmsg, self
                    )
                    maxExcLoc = len(instring)

        # only got here if no expression matched, raise exception for match that made it the furthest
        if fatals:
            if len(fatals) > 1:
                fatals.sort(key=lambda e: -e.loc)
                if fatals[0].loc == fatals[1].loc:
                    fatals.sort(key=lambda e: (-e.loc, -len(str(e.parserElement))))
            max_fatal = fatals[0]
            raise max_fatal

        if maxException is not None:
            maxException.msg = self.errmsg
            raise maxException
        else:
            raise ParseException(
                instring, loc, "no defined alternatives to match", self
            )

    def __ior__(self, other):
        if isinstance(other, str_type):
            other = self._literalStringClass(other)
        return self.append(other)  # MatchFirst([self, other])

    def __str__(self):
        if hasattr(self, "name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + " | ".join(str(e) for e in self.exprs) + "}"

        return self.strRepr

    def checkRecursion(self, parseElementList):
        subRecCheckList = parseElementList[:] + [self]
        for e in self.exprs:
            e.checkRecursion(subRecCheckList)

    def _setResultsName(self, name, listAllMatches=False):
        if __diag__.warn_multiple_tokens_in_named_alternation:
            if any(isinstance(e, And) for e in self.exprs):
                warnings.warn(
                    "{}: setting results name {!r} on {} expression "
                    "may only return a single token for an And alternative, "
                    "in future will return the full list of tokens".format(
                        "warn_multiple_tokens_in_named_alternation",
                        name,
                        type(self).__name__,
                    ),
                    stacklevel=3,
                )

        return super()._setResultsName(name, listAllMatches)


class Each(ParseExpression):
    """Requires all given :class:`ParseExpression`\ s to be found, but in
    any order. Expressions may be separated by whitespace.

    May be constructed using the ``'&'`` operator.

    Example::

        color = oneOf("RED ORANGE YELLOW GREEN BLUE PURPLE BLACK WHITE BROWN")
        shape_type = oneOf("SQUARE CIRCLE TRIANGLE STAR HEXAGON OCTAGON")
        integer = Word(nums)
        shape_attr = "shape:" + shape_type("shape")
        posn_attr = "posn:" + Group(integer("x") + ',' + integer("y"))("posn")
        color_attr = "color:" + color("color")
        size_attr = "size:" + integer("size")

        # use Each (using operator '&') to accept attributes in any order
        # (shape and posn are required, color and size are optional)
        shape_spec = shape_attr & posn_attr & Optional(color_attr) & Optional(size_attr)

        shape_spec.runTests('''
            shape: SQUARE color: BLACK posn: 100, 120
            shape: CIRCLE size: 50 color: BLUE posn: 50,80
            color:GREEN size:20 shape:TRIANGLE posn:20,40
            '''
            )

    prints::

        shape: SQUARE color: BLACK posn: 100, 120
        ['shape:', 'SQUARE', 'color:', 'BLACK', 'posn:', ['100', ',', '120']]
        - color: BLACK
        - posn: ['100', ',', '120']
          - x: 100
          - y: 120
        - shape: SQUARE


        shape: CIRCLE size: 50 color: BLUE posn: 50,80
        ['shape:', 'CIRCLE', 'size:', '50', 'color:', 'BLUE', 'posn:', ['50', ',', '80']]
        - color: BLUE
        - posn: ['50', ',', '80']
          - x: 50
          - y: 80
        - shape: CIRCLE
        - size: 50


        color: GREEN size: 20 shape: TRIANGLE posn: 20,40
        ['color:', 'GREEN', 'size:', '20', 'shape:', 'TRIANGLE', 'posn:', ['20', ',', '40']]
        - color: GREEN
        - posn: ['20', ',', '40']
          - x: 20
          - y: 40
        - shape: TRIANGLE
        - size: 20
    """

    def __init__(self, exprs, savelist=True):
        super().__init__(exprs, savelist)
        self.mayReturnEmpty = all(e.mayReturnEmpty for e in self.exprs)
        self.skipWhitespace = True
        self.initExprGroups = True
        self.saveAsList = True

    def streamline(self):
        super().streamline()
        self.mayReturnEmpty = all(e.mayReturnEmpty for e in self.exprs)
        return self

    def parseImpl(self, instring, loc, doActions=True):
        if self.initExprGroups:
            self.opt1map = dict(
                (id(e.expr), e) for e in self.exprs if isinstance(e, Optional)
            )
            opt1 = [e.expr for e in self.exprs if isinstance(e, Optional)]
            opt2 = [
                e
                for e in self.exprs
                if e.mayReturnEmpty and not isinstance(e, (Optional, Regex))
            ]
            self.optionals = opt1 + opt2
            self.multioptionals = [
                e.expr for e in self.exprs if isinstance(e, ZeroOrMore)
            ]
            self.multirequired = [
                e.expr for e in self.exprs if isinstance(e, OneOrMore)
            ]
            self.required = [
                e
                for e in self.exprs
                if not isinstance(e, (Optional, ZeroOrMore, OneOrMore))
            ]
            self.required += self.multirequired
            self.initExprGroups = False
        tmpLoc = loc
        tmpReqd = self.required[:]
        tmpOpt = self.optionals[:]
        matchOrder = []

        keepMatching = True
        failed = []
        fatals = []
        while keepMatching:
            tmpExprs = tmpReqd + tmpOpt + self.multioptionals + self.multirequired
            failed.clear()
            fatals.clear()
            for e in tmpExprs:
                try:
                    tmpLoc = e.tryParse(instring, tmpLoc, raise_fatal=True)
                except ParseFatalException as pfe:
                    pfe.__traceback__ = None
                    pfe.parserElement = e
                    fatals.append(pfe)
                    failed.append(e)
                except ParseException:
                    failed.append(e)
                else:
                    matchOrder.append(self.opt1map.get(id(e), e))
                    if e in tmpReqd:
                        tmpReqd.remove(e)
                    elif e in tmpOpt:
                        tmpOpt.remove(e)
            if len(failed) == len(tmpExprs):
                keepMatching = False

        # look for any ParseFatalExceptions
        if fatals:
            if len(fatals) > 1:
                fatals.sort(key=lambda e: -e.loc)
                if fatals[0].loc == fatals[1].loc:
                    fatals.sort(key=lambda e: (-e.loc, -len(str(e.parserElement))))
            max_fatal = fatals[0]
            raise max_fatal

        if tmpReqd:
            missing = ", ".join(str(e) for e in tmpReqd)
            raise ParseException(
                instring, loc, "Missing one or more required elements (%s)" % missing
            )

        # add any unmatched Optionals, in case they have default values defined
        matchOrder += [
            e for e in self.exprs if isinstance(e, Optional) and e.expr in tmpOpt
        ]

        resultlist = []
        for e in matchOrder:
            loc, results = e._parse(instring, loc, doActions)
            resultlist.append(results)

        finalResults = sum(resultlist, ParseResults([]))
        return loc, finalResults

    def __str__(self):
        if hasattr(self, "name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + " & ".join(str(e) for e in self.exprs) + "}"

        return self.strRepr

    def checkRecursion(self, parseElementList):
        subRecCheckList = parseElementList[:] + [self]
        for e in self.exprs:
            e.checkRecursion(subRecCheckList)


class ParseElementEnhance(ParserElement):
    """Abstract subclass of :class:`ParserElement`, for combining and
    post-processing parsed tokens.
    """

    def __init__(self, expr, savelist=False):
        super().__init__(savelist)
        if isinstance(expr, str_type):
            if issubclass(self._literalStringClass, Token):
                expr = self._literalStringClass(expr)
            elif issubclass(type(self), self._literalStringClass):
                expr = Literal(expr)
            else:
                expr = self._literalStringClass(Literal(expr))
        self.expr = expr
        self.strRepr = None
        if expr is not None:
            self.mayIndexError = expr.mayIndexError
            self.mayReturnEmpty = expr.mayReturnEmpty
            self.setWhitespaceChars(
                expr.whiteChars, copy_defaults=expr.copyDefaultWhiteChars
            )
            self.skipWhitespace = expr.skipWhitespace
            self.saveAsList = expr.saveAsList
            self.callPreparse = expr.callPreparse
            self.ignoreExprs.extend(expr.ignoreExprs)

    def parseImpl(self, instring, loc, doActions=True):
        if self.expr is not None:
            return self.expr._parse(instring, loc, doActions, callPreParse=False)
        else:
            raise ParseException("", loc, self.errmsg, self)

    def leaveWhitespace(self):
        self.skipWhitespace = False
        self.expr = self.expr.copy()
        if self.expr is not None:
            self.expr.leaveWhitespace()
        return self

    def ignore(self, other):
        if isinstance(other, Suppress):
            if other not in self.ignoreExprs:
                super().ignore(other)
                if self.expr is not None:
                    self.expr.ignore(self.ignoreExprs[-1])
        else:
            super().ignore(other)
            if self.expr is not None:
                self.expr.ignore(self.ignoreExprs[-1])
        return self

    def streamline(self):
        super().streamline()
        if self.expr is not None:
            self.expr.streamline()
        return self

    def checkRecursion(self, parseElementList):
        if self in parseElementList:
            raise RecursiveGrammarException(parseElementList + [self])
        subRecCheckList = parseElementList[:] + [self]
        if self.expr is not None:
            self.expr.checkRecursion(subRecCheckList)

    def validate(self, validateTrace=None):
        if validateTrace is None:
            validateTrace = []
        tmp = validateTrace[:] + [self]
        if self.expr is not None:
            self.expr.validate(tmp)
        self.checkRecursion([])

    def __str__(self):
        try:
            return super().__str__()
        except Exception:
            pass

        if self.strRepr is None and self.expr is not None:
            self.strRepr = "%s:(%s)" % (self.__class__.__name__, str(self.expr))
        return self.strRepr


class FollowedBy(ParseElementEnhance):
    """Lookahead matching of the given parse expression.
    ``FollowedBy`` does *not* advance the parsing position within
    the input string, it only verifies that the specified parse
    expression matches at the current position.  ``FollowedBy``
    always returns a null token list. If any results names are defined
    in the lookahead expression, those *will* be returned for access by
    name.

    Example::

        # use FollowedBy to match a label only if it is followed by a ':'
        data_word = Word(alphas)
        label = data_word + FollowedBy(':')
        attr_expr = Group(label + Suppress(':') + OneOrMore(data_word, stopOn=label).setParseAction(' '.join))

        OneOrMore(attr_expr).parseString("shape: SQUARE color: BLACK posn: upper left").pprint()

    prints::

        [['shape', 'SQUARE'], ['color', 'BLACK'], ['posn', 'upper left']]
    """

    def __init__(self, expr):
        super().__init__(expr)
        self.mayReturnEmpty = True

    def parseImpl(self, instring, loc, doActions=True):
        # by using self._expr.parse and deleting the contents of the returned ParseResults list
        # we keep any named results that were defined in the FollowedBy expression
        _, ret = self.expr._parse(instring, loc, doActions=doActions)
        del ret[:]

        return loc, ret


class PrecededBy(ParseElementEnhance):
    """Lookbehind matching of the given parse expression.
    ``PrecededBy`` does not advance the parsing position within the
    input string, it only verifies that the specified parse expression
    matches prior to the current position.  ``PrecededBy`` always
    returns a null token list, but if a results name is defined on the
    given expression, it is returned.

    Parameters:

     - expr - expression that must match prior to the current parse
       location
     - retreat - (default= ``None``) - (int) maximum number of characters
       to lookbehind prior to the current parse location

    If the lookbehind expression is a string, :class:`Literal`,
    :class:`Keyword`, or a :class:`Word` or :class:`CharsNotIn`
    with a specified exact or maximum length, then the retreat
    parameter is not required. Otherwise, retreat must be specified to
    give a maximum number of characters to look back from
    the current parse position for a lookbehind match.

    Example::

        # VB-style variable names with type prefixes
        int_var = PrecededBy("#") + pyparsing_common.identifier
        str_var = PrecededBy("$") + pyparsing_common.identifier

    """

    def __init__(self, expr, retreat=None):
        super().__init__(expr)
        self.expr = self.expr().leaveWhitespace()
        self.mayReturnEmpty = True
        self.mayIndexError = False
        self.exact = False
        if isinstance(expr, str_type):
            retreat = len(expr)
            self.exact = True
        elif isinstance(expr, (Literal, Keyword)):
            retreat = expr.matchLen
            self.exact = True
        elif isinstance(expr, (Word, CharsNotIn)) and expr.maxLen != _MAX_INT:
            retreat = expr.maxLen
            self.exact = True
        elif isinstance(expr, _PositionToken):
            retreat = 0
            self.exact = True
        self.retreat = retreat
        self.errmsg = "not preceded by " + str(expr)
        self.skipWhitespace = False
        self.parseAction.append(lambda s, l, t: t.__delitem__(slice(None, None)))

    def parseImpl(self, instring, loc=0, doActions=True):
        if self.exact:
            if loc < self.retreat:
                raise ParseException(instring, loc, self.errmsg)
            start = loc - self.retreat
            _, ret = self.expr._parse(instring, start)
        else:
            # retreat specified a maximum lookbehind window, iterate
            test_expr = self.expr + StringEnd()
            instring_slice = instring[max(0, loc - self.retreat) : loc]
            last_expr = ParseException(instring, loc, self.errmsg)
            for offset in range(1, min(loc, self.retreat + 1) + 1):
                try:
                    # print('trying', offset, instring_slice, repr(instring_slice[loc - offset:]))
                    _, ret = test_expr._parse(
                        instring_slice, len(instring_slice) - offset
                    )
                except ParseBaseException as pbe:
                    last_expr = pbe
                else:
                    break
            else:
                raise last_expr
        return loc, ret


class NotAny(ParseElementEnhance):
    """Lookahead to disallow matching with the given parse expression.
    ``NotAny`` does *not* advance the parsing position within the
    input string, it only verifies that the specified parse expression
    does *not* match at the current position.  Also, ``NotAny`` does
    *not* skip over leading whitespace. ``NotAny`` always returns
    a null token list.  May be constructed using the ``'~'`` operator.

    Example::

        AND, OR, NOT = map(CaselessKeyword, "AND OR NOT".split())

        # take care not to mistake keywords for identifiers
        ident = ~(AND | OR | NOT) + Word(alphas)
        boolean_term = Optional(NOT) + ident

        # very crude boolean expression - to support parenthesis groups and
        # operation hierarchy, use infixNotation
        boolean_expr = boolean_term + ZeroOrMore((AND | OR) + boolean_term)

        # integers that are followed by "." are actually floats
        integer = Word(nums) + ~Char(".")
    """

    def __init__(self, expr):
        super().__init__(expr)
        # ~ self.leaveWhitespace()
        self.skipWhitespace = (
            False  # do NOT use self.leaveWhitespace(), don't want to propagate to exprs
        )
        self.mayReturnEmpty = True
        self.errmsg = "Found unwanted token, " + str(self.expr)

    def parseImpl(self, instring, loc, doActions=True):
        if self.expr.canParseNext(instring, loc):
            raise ParseException(instring, loc, self.errmsg, self)
        return loc, []

    def __str__(self):
        if hasattr(self, "name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "~{" + str(self.expr) + "}"

        return self.strRepr


class _MultipleMatch(ParseElementEnhance):
    def __init__(self, expr, stopOn=None):
        super().__init__(expr)
        self.saveAsList = True
        ender = stopOn
        if isinstance(ender, str_type):
            ender = self._literalStringClass(ender)
        self.stopOn(ender)

    def stopOn(self, ender):
        if isinstance(ender, str_type):
            ender = self._literalStringClass(ender)
        self.not_ender = ~ender if ender is not None else None
        return self

    def parseImpl(self, instring, loc, doActions=True):
        self_expr_parse = self.expr._parse
        self_skip_ignorables = self._skipIgnorables
        check_ender = self.not_ender is not None
        if check_ender:
            try_not_ender = self.not_ender.tryParse

        # must be at least one (but first see if we are the stopOn sentinel;
        # if so, fail)
        if check_ender:
            try_not_ender(instring, loc)
        loc, tokens = self_expr_parse(instring, loc, doActions, callPreParse=False)
        try:
            hasIgnoreExprs = not not self.ignoreExprs
            while 1:
                if check_ender:
                    try_not_ender(instring, loc)
                if hasIgnoreExprs:
                    preloc = self_skip_ignorables(instring, loc)
                else:
                    preloc = loc
                loc, tmptokens = self_expr_parse(instring, preloc, doActions)
                if tmptokens or tmptokens.haskeys():
                    tokens += tmptokens
        except (ParseException, IndexError):
            pass

        return loc, tokens

    def _setResultsName(self, name, listAllMatches=False):
        if __diag__.warn_ungrouped_named_tokens_in_collection:
            for e in [self.expr] + getattr(self.expr, "exprs", []):
                if isinstance(e, ParserElement) and e.resultsName:
                    warnings.warn(
                        "{}: setting results name {!r} on {} expression "
                        "collides with {!r} on contained expression".format(
                            "warn_ungrouped_named_tokens_in_collection",
                            name,
                            type(self).__name__,
                            e.resultsName,
                        ),
                        stacklevel=3,
                    )

        return super()._setResultsName(name, listAllMatches)


class OneOrMore(_MultipleMatch):
    """Repetition of one or more of the given expression.

    Parameters:
     - expr - expression that must match one or more times
     - stopOn - (default= ``None``) - expression for a terminating sentinel
          (only required if the sentinel would ordinarily match the repetition
          expression)

    Example::

        data_word = Word(alphas)
        label = data_word + FollowedBy(':')
        attr_expr = Group(label + Suppress(':') + OneOrMore(data_word).setParseAction(' '.join))

        text = "shape: SQUARE posn: upper left color: BLACK"
        OneOrMore(attr_expr).parseString(text).pprint()  # Fail! read 'color' as data instead of next label -> [['shape', 'SQUARE color']]

        # use stopOn attribute for OneOrMore to avoid reading label string as part of the data
        attr_expr = Group(label + Suppress(':') + OneOrMore(data_word, stopOn=label).setParseAction(' '.join))
        OneOrMore(attr_expr).parseString(text).pprint() # Better -> [['shape', 'SQUARE'], ['posn', 'upper left'], ['color', 'BLACK']]

        # could also be written as
        (attr_expr * (1,)).parseString(text).pprint()
    """

    def __str__(self):
        if hasattr(self, "name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + str(self.expr) + "}..."

        return self.strRepr


class ZeroOrMore(_MultipleMatch):
    """Optional repetition of zero or more of the given expression.

    Parameters:
     - expr - expression that must match zero or more times
     - stopOn - (default= ``None``) - expression for a terminating sentinel
       (only required if the sentinel would ordinarily match the repetition
       expression)

    Example: similar to :class:`OneOrMore`
    """

    def __init__(self, expr, stopOn=None):
        super().__init__(expr, stopOn=stopOn)
        self.mayReturnEmpty = True

    def parseImpl(self, instring, loc, doActions=True):
        try:
            return super().parseImpl(instring, loc, doActions)
        except (ParseException, IndexError):
            return loc, ParseResults([], name=self.resultsName)

    def __str__(self):
        if hasattr(self, "name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "[" + str(self.expr) + "]..."

        return self.strRepr


class _NullToken:
    def __bool__(self):
        return False

    def __str__(self):
        return ""


class Optional(ParseElementEnhance):
    """Optional matching of the given expression.

    Parameters:
     - expr - expression that must match zero or more times
     - default (optional) - value to be returned if the optional expression is not found.

    Example::

        # US postal code can be a 5-digit zip, plus optional 4-digit qualifier
        zip = Combine(Word(nums, exact=5) + Optional('-' + Word(nums, exact=4)))
        zip.runTests('''
            # traditional ZIP code
            12345

            # ZIP+4 form
            12101-0001

            # invalid ZIP
            98765-
            ''')

    prints::

        # traditional ZIP code
        12345
        ['12345']

        # ZIP+4 form
        12101-0001
        ['12101-0001']

        # invalid ZIP
        98765-
             ^
        FAIL: Expected end of text (at char 5), (line:1, col:6)
    """

    __optionalNotMatched = _NullToken()

    def __init__(self, expr, default=__optionalNotMatched):
        super().__init__(expr, savelist=False)
        self.saveAsList = self.expr.saveAsList
        self.defaultValue = default
        self.mayReturnEmpty = True

    def parseImpl(self, instring, loc, doActions=True):
        try:
            loc, tokens = self.expr._parse(instring, loc, doActions, callPreParse=False)
        except (ParseException, IndexError):
            if self.defaultValue is not self.__optionalNotMatched:
                if self.expr.resultsName:
                    tokens = ParseResults([self.defaultValue])
                    tokens[self.expr.resultsName] = self.defaultValue
                else:
                    tokens = [self.defaultValue]
            else:
                tokens = []
        return loc, tokens

    def __str__(self):
        if hasattr(self, "name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "[" + str(self.expr) + "]"

        return self.strRepr


class SkipTo(ParseElementEnhance):
    """Token for skipping over all undefined text until the matched
    expression is found.

    Parameters:
     - expr - target expression marking the end of the data to be skipped
     - include - (default= ``False``) if True, the target expression is also parsed
       (the skipped text and target expression are returned as a 2-element list).
     - ignore - (default= ``None``) used to define grammars (typically quoted strings and
       comments) that might contain false matches to the target expression
     - failOn - (default= ``None``) define expressions that are not allowed to be
       included in the skipped test; if found before the target expression is found,
       the SkipTo is not a match

    Example::

        report = '''
            Outstanding Issues Report - 1 Jan 2000

               # | Severity | Description                               |  Days Open
            -----+----------+-------------------------------------------+-----------
             101 | Critical | Intermittent system crash                 |          6
              94 | Cosmetic | Spelling error on Login ('log|n')         |         14
              79 | Minor    | System slow when running too many reports |         47
            '''
        integer = Word(nums)
        SEP = Suppress('|')
        # use SkipTo to simply match everything up until the next SEP
        # - ignore quoted strings, so that a '|' character inside a quoted string does not match
        # - parse action will call token.strip() for each matched token, i.e., the description body
        string_data = SkipTo(SEP, ignore=quotedString)
        string_data.setParseAction(tokenMap(str.strip))
        ticket_expr = (integer("issue_num") + SEP
                      + string_data("sev") + SEP
                      + string_data("desc") + SEP
                      + integer("days_open"))

        for tkt in ticket_expr.searchString(report):
            print tkt.dump()

    prints::

        ['101', 'Critical', 'Intermittent system crash', '6']
        - days_open: 6
        - desc: Intermittent system crash
        - issue_num: 101
        - sev: Critical
        ['94', 'Cosmetic', "Spelling error on Login ('log|n')", '14']
        - days_open: 14
        - desc: Spelling error on Login ('log|n')
        - issue_num: 94
        - sev: Cosmetic
        ['79', 'Minor', 'System slow when running too many reports', '47']
        - days_open: 47
        - desc: System slow when running too many reports
        - issue_num: 79
        - sev: Minor
    """

    def __init__(self, other, include=False, ignore=None, failOn=None):
        super().__init__(other)
        self.ignoreExpr = ignore
        self.mayReturnEmpty = True
        self.mayIndexError = False
        self.includeMatch = include
        self.saveAsList = False
        if isinstance(failOn, str_type):
            self.failOn = self._literalStringClass(failOn)
        else:
            self.failOn = failOn
        self.errmsg = "No match found for " + str(self.expr)

    def parseImpl(self, instring, loc, doActions=True):
        startloc = loc
        instrlen = len(instring)
        expr = self.expr
        expr_parse = self.expr._parse
        self_failOn_canParseNext = (
            self.failOn.canParseNext if self.failOn is not None else None
        )
        self_ignoreExpr_tryParse = (
            self.ignoreExpr.tryParse if self.ignoreExpr is not None else None
        )

        tmploc = loc
        while tmploc <= instrlen:
            if self_failOn_canParseNext is not None:
                # break if failOn expression matches
                if self_failOn_canParseNext(instring, tmploc):
                    break

            if self_ignoreExpr_tryParse is not None:
                # advance past ignore expressions
                while 1:
                    try:
                        tmploc = self_ignoreExpr_tryParse(instring, tmploc)
                    except ParseBaseException:
                        break

            try:
                expr_parse(instring, tmploc, doActions=False, callPreParse=False)
            except (ParseException, IndexError):
                # no match, advance loc in string
                tmploc += 1
            else:
                # matched skipto expr, done
                break

        else:
            # ran off the end of the input string without matching skipto expr, fail
            raise ParseException(instring, loc, self.errmsg, self)

        # build up return values
        loc = tmploc
        skiptext = instring[startloc:loc]
        skipresult = ParseResults(skiptext)

        if self.includeMatch:
            loc, mat = expr_parse(instring, loc, doActions, callPreParse=False)
            skipresult += mat

        return loc, skipresult


class Forward(ParseElementEnhance):
    """Forward declaration of an expression to be defined later -
    used for recursive grammars, such as algebraic infix notation.
    When the expression is known, it is assigned to the ``Forward``
    variable using the ``'<<'`` operator.

    Note: take care when assigning to ``Forward`` not to overlook
    precedence of operators.

    Specifically, ``'|'`` has a lower precedence than ``'<<'``, so that::

        fwdExpr << a | b | c

    will actually be evaluated as::

        (fwdExpr << a) | b | c

    thereby leaving b and c out as parseable alternatives.  It is recommended that you
    explicitly group the values inserted into the ``Forward``::

        fwdExpr << (a | b | c)

    Converting to use the ``'<<='`` operator instead will avoid this problem.

    See :class:`ParseResults.pprint` for an example of a recursive
    parser created using ``Forward``.
    """

    def __init__(self, other=None):
        super().__init__(other, savelist=False)
        self.lshift_line = None

    def __lshift__(self, other):
        if isinstance(other, str_type):
            other = self._literalStringClass(other)
        self.expr = other
        self.strRepr = None
        self.mayIndexError = self.expr.mayIndexError
        self.mayReturnEmpty = self.expr.mayReturnEmpty
        self.setWhitespaceChars(
            self.expr.whiteChars, copy_defaults=self.expr.copyDefaultWhiteChars
        )
        self.skipWhitespace = self.expr.skipWhitespace
        self.saveAsList = self.expr.saveAsList
        self.ignoreExprs.extend(self.expr.ignoreExprs)
        self.lshift_line = traceback.extract_stack(limit=2)[-2]
        return self

    def __ilshift__(self, other):
        return self << other

    def __or__(self, other):
        caller_line = traceback.extract_stack(limit=2)[-2]
        if (
            __diag__.warn_on_match_first_with_lshift_operator
            and caller_line == self.lshift_line
        ):
            warnings.warn(
                "using '<<' operator with '|' is probably error, use '<<='",
                SyntaxWarning,
                stacklevel=3,
            )
        ret = super().__or__(other)
        return ret

    def leaveWhitespace(self):
        self.skipWhitespace = False
        return self

    def streamline(self):
        if not self.streamlined:
            self.streamlined = True
            if self.expr is not None:
                self.expr.streamline()
        return self

    def validate(self, validateTrace=None):
        if validateTrace is None:
            validateTrace = []

        if self not in validateTrace:
            tmp = validateTrace[:] + [self]
            if self.expr is not None:
                self.expr.validate(tmp)
        self.checkRecursion([])

    def __str__(self):
        if hasattr(self, "name"):
            return self.name
        if self.strRepr is not None:
            return self.strRepr

        # Avoid infinite recursion by setting a temporary strRepr
        self.strRepr = ": ..."

        # Use the string representation of main expression.
        retString = "..."
        try:
            if self.expr is not None:
                retString = str(self.expr)[:1000]
            else:
                retString = "None"
        finally:
            self.strRepr = self.__class__.__name__ + ": " + retString
        return self.strRepr

    def copy(self):
        if self.expr is not None:
            return super().copy()
        else:
            ret = Forward()
            ret <<= self
            return ret

    def _setResultsName(self, name, listAllMatches=False):
        if __diag__.warn_name_set_on_empty_Forward:
            if self.expr is None:
                warnings.warn(
                    "{}: setting results name {!r} on {} expression "
                    "that has no contained expression".format(
                        "warn_name_set_on_empty_Forward", name, type(self).__name__
                    ),
                    stacklevel=3,
                )

        return super()._setResultsName(name, listAllMatches)


class TokenConverter(ParseElementEnhance):
    """
    Abstract subclass of :class:`ParseExpression`, for converting parsed results.
    """

    def __init__(self, expr, savelist=False):
        super().__init__(expr)  # , savelist)
        self.saveAsList = False


class Combine(TokenConverter):
    """Converter to concatenate all matching tokens to a single string.
    By default, the matching patterns must also be contiguous in the
    input string; this can be disabled by specifying
    ``'adjacent=False'`` in the constructor.

    Example::

        real = Word(nums) + '.' + Word(nums)
        print(real.parseString('3.1416')) # -> ['3', '.', '1416']
        # will also erroneously match the following
        print(real.parseString('3. 1416')) # -> ['3', '.', '1416']

        real = Combine(Word(nums) + '.' + Word(nums))
        print(real.parseString('3.1416')) # -> ['3.1416']
        # no match when there are internal spaces
        print(real.parseString('3. 1416')) # -> Exception: Expected W:(0123...)
    """

    def __init__(self, expr, joinString="", adjacent=True):
        super().__init__(expr)
        # suppress whitespace-stripping in contained parse expressions, but re-enable it on the Combine itself
        if adjacent:
            self.leaveWhitespace()
        self.adjacent = adjacent
        self.skipWhitespace = True
        self.joinString = joinString
        self.callPreparse = True

    def ignore(self, other):
        if self.adjacent:
            ParserElement.ignore(self, other)
        else:
            super().ignore(other)
        return self

    def postParse(self, instring, loc, tokenlist):
        retToks = tokenlist.copy()
        del retToks[:]
        retToks += ParseResults(
            ["".join(tokenlist._asStringList(self.joinString))], modal=self.modalResults
        )

        if self.resultsName and retToks.haskeys():
            return [retToks]
        else:
            return retToks


class Group(TokenConverter):
    """Converter to return the matched tokens as a list - useful for
    returning tokens of :class:`ZeroOrMore` and :class:`OneOrMore` expressions.

    Example::

        ident = Word(alphas)
        num = Word(nums)
        term = ident | num
        func = ident + Optional(delimitedList(term))
        print(func.parseString("fn a, b, 100"))
        # -> ['fn', 'a', 'b', '100']

        func = ident + Group(Optional(delimitedList(term)))
        print(func.parseString("fn a, b, 100"))
        # -> ['fn', ['a', 'b', '100']]
    """

    def __init__(self, expr):
        super().__init__(expr)
        self.saveAsList = True

    def postParse(self, instring, loc, tokenlist):
        return [tokenlist]


class Dict(TokenConverter):
    """Converter to return a repetitive expression as a list, but also
    as a dictionary. Each element can also be referenced using the first
    token in the expression as its key. Useful for tabular report
    scraping when the first column can be used as a item key.

    Example::

        data_word = Word(alphas)
        label = data_word + FollowedBy(':')
        attr_expr = Group(label + Suppress(':') + OneOrMore(data_word).setParseAction(' '.join))

        text = "shape: SQUARE posn: upper left color: light blue texture: burlap"
        attr_expr = (label + Suppress(':') + OneOrMore(data_word, stopOn=label).setParseAction(' '.join))

        # print attributes as plain groups
        print(OneOrMore(attr_expr).parseString(text).dump())

        # instead of OneOrMore(expr), parse using Dict(OneOrMore(Group(expr))) - Dict will auto-assign names
        result = Dict(OneOrMore(Group(attr_expr))).parseString(text)
        print(result.dump())

        # access named fields as dict entries, or output as dict
        print(result['shape'])
        print(result.asDict())

    prints::

        ['shape', 'SQUARE', 'posn', 'upper left', 'color', 'light blue', 'texture', 'burlap']
        [['shape', 'SQUARE'], ['posn', 'upper left'], ['color', 'light blue'], ['texture', 'burlap']]
        - color: light blue
        - posn: upper left
        - shape: SQUARE
        - texture: burlap
        SQUARE
        {'color': 'light blue', 'posn': 'upper left', 'texture': 'burlap', 'shape': 'SQUARE'}

    See more examples at :class:`ParseResults` of accessing fields by results name.
    """

    def __init__(self, expr):
        super().__init__(expr)
        self.saveAsList = True

    def postParse(self, instring, loc, tokenlist):
        for i, tok in enumerate(tokenlist):
            if len(tok) == 0:
                continue
            ikey = tok[0]
            if isinstance(ikey, int):
                ikey = str(tok[0]).strip()
            if len(tok) == 1:
                tokenlist[ikey] = _ParseResultsWithOffset("", i)
            elif len(tok) == 2 and not isinstance(tok[1], ParseResults):
                tokenlist[ikey] = _ParseResultsWithOffset(tok[1], i)
            else:
                dictvalue = tok.copy()  # ParseResults(i)
                del dictvalue[0]
                if len(dictvalue) != 1 or (
                    isinstance(dictvalue, ParseResults) and dictvalue.haskeys()
                ):
                    tokenlist[ikey] = _ParseResultsWithOffset(dictvalue, i)
                else:
                    tokenlist[ikey] = _ParseResultsWithOffset(dictvalue[0], i)

        if self.resultsName:
            return [tokenlist]
        else:
            return tokenlist


class Suppress(TokenConverter):
    """Converter for ignoring the results of a parsed expression.

    Example::

        source = "a, b, c,d"
        wd = Word(alphas)
        wd_list1 = wd + ZeroOrMore(',' + wd)
        print(wd_list1.parseString(source))

        # often, delimiters that are useful during parsing are just in the
        # way afterward - use Suppress to keep them out of the parsed output
        wd_list2 = wd + ZeroOrMore(Suppress(',') + wd)
        print(wd_list2.parseString(source))

    prints::

        ['a', ',', 'b', ',', 'c', ',', 'd']
        ['a', 'b', 'c', 'd']

    (See also :class:`delimitedList`.)
    """

    def postParse(self, instring, loc, tokenlist):
        return []

    def suppress(self):
        return self


class OnlyOnce:
    """Wrapper for parse actions, to ensure they are only called once.
    """

    def __init__(self, methodCall):
        self.callable = _trim_arity(methodCall)
        self.called = False

    def __call__(self, s, l, t):
        if not self.called:
            results = self.callable(s, l, t)
            self.called = True
            return results
        raise ParseException(s, l, "")

    def reset(self):
        self.called = False


def traceParseAction(f):
    """Decorator for debugging parse actions.

    When the parse action is called, this decorator will print
    ``">> entering method-name(line:<current_source_line>, <parse_location>, <matched_tokens>)"``.
    When the parse action completes, the decorator will print
    ``"<<"`` followed by the returned value, or any exception that the parse action raised.

    Example::

        wd = Word(alphas)

        @traceParseAction
        def remove_duplicate_chars(tokens):
            return ''.join(sorted(set(''.join(tokens))))

        wds = OneOrMore(wd).setParseAction(remove_duplicate_chars)
        print(wds.parseString("slkdjs sld sldd sdlf sdljf"))

    prints::

        >>entering remove_duplicate_chars(line: 'slkdjs sld sldd sdlf sdljf', 0, (['slkdjs', 'sld', 'sldd', 'sdlf', 'sdljf'], {}))
        <<leaving remove_duplicate_chars (ret: 'dfjkls')
        ['dfjkls']
    """
    f = _trim_arity(f)

    def z(*paArgs):
        thisFunc = f.__name__
        s, l, t = paArgs[-3:]
        if len(paArgs) > 3:
            thisFunc = paArgs[0].__class__.__name__ + "." + thisFunc
        sys.stderr.write(
            ">>entering %s(line: '%s', %d, %r)\n" % (thisFunc, line(l, s), l, t)
        )
        try:
            ret = f(*paArgs)
        except Exception as exc:
            sys.stderr.write("<<leaving %s (exception: %s)\n" % (thisFunc, exc))
            raise
        sys.stderr.write("<<leaving %s (ret: %r)\n" % (thisFunc, ret))
        return ret

    try:
        z.__name__ = f.__name__
    except AttributeError:
        pass
    return z


# convenience constants for positional expressions
empty = Empty().setName("empty")
lineStart = LineStart().setName("lineStart")
lineEnd = LineEnd().setName("lineEnd")
stringStart = StringStart().setName("stringStart")
stringEnd = StringEnd().setName("stringEnd")

_escapedPunc = Word(_bslash, r"\[]-*.$+^?()~ ", exact=2).setParseAction(
    lambda s, l, t: t[0][1]
)
_escapedHexChar = Regex(r"\\0?[xX][0-9a-fA-F]+").setParseAction(
    lambda s, l, t: chr(int(t[0].lstrip(r"\0x"), 16))
)
_escapedOctChar = Regex(r"\\0[0-7]+").setParseAction(
    lambda s, l, t: chr(int(t[0][1:], 8))
)
_singleChar = (
    _escapedPunc | _escapedHexChar | _escapedOctChar | CharsNotIn(r"\]", exact=1)
)
_charRange = Group(_singleChar + Suppress("-") + _singleChar)
_reBracketExpr = (
    Literal("[")
    + Optional("^").setResultsName("negate")
    + Group(OneOrMore(_charRange | _singleChar)).setResultsName("body")
    + "]"
)


def srange(s):
    r"""Helper to easily define string ranges for use in :class:`Word`
    construction. Borrows syntax from regexp '[]' string range
    definitions::

        srange("[0-9]")   -> "0123456789"
        srange("[a-z]")   -> "abcdefghijklmnopqrstuvwxyz"
        srange("[a-z$_]") -> "abcdefghijklmnopqrstuvwxyz$_"

    The input string must be enclosed in []'s, and the returned string
    is the expanded character set joined into a single string. The
    values enclosed in the []'s may be:

     - a single character
     - an escaped character with a leading backslash (such as ``\-``
       or ``\]``)
     - an escaped hex character with a leading ``'\x'``
       (``\x21``, which is a ``'!'`` character) (``\0x##``
       is also supported for backwards compatibility)
     - an escaped octal character with a leading ``'\0'``
       (``\041``, which is a ``'!'`` character)
     - a range of any of the above, separated by a dash (``'a-z'``,
       etc.)
     - any combination of the above (``'aeiouy'``,
       ``'a-zA-Z0-9_$'``, etc.)
    """
    _expanded = (
        lambda p: p
        if not isinstance(p, ParseResults)
        else "".join(chr(c) for c in range(ord(p[0]), ord(p[1]) + 1))
    )
    try:
        return "".join(_expanded(part) for part in _reBracketExpr.parseString(s).body)
    except Exception:
        return ""


def tokenMap(func, *args):
    """Helper to define a parse action by mapping a function to all
    elements of a ParseResults list. If any additional args are passed,
    they are forwarded to the given function as additional arguments
    after the token, as in
    ``hex_integer = Word(hexnums).setParseAction(tokenMap(int, 16))``,
    which will convert the parsed data to an integer using base 16.

    Example (compare the last to example in :class:`ParserElement.transformString`::

        hex_ints = OneOrMore(Word(hexnums)).setParseAction(tokenMap(int, 16))
        hex_ints.runTests('''
            00 11 22 aa FF 0a 0d 1a
            ''')

        upperword = Word(alphas).setParseAction(tokenMap(str.upper))
        OneOrMore(upperword).runTests('''
            my kingdom for a horse
            ''')

        wd = Word(alphas).setParseAction(tokenMap(str.title))
        OneOrMore(wd).setParseAction(' '.join).runTests('''
            now is the winter of our discontent made glorious summer by this sun of york
            ''')

    prints::

        00 11 22 aa FF 0a 0d 1a
        [0, 17, 34, 170, 255, 10, 13, 26]

        my kingdom for a horse
        ['MY', 'KINGDOM', 'FOR', 'A', 'HORSE']

        now is the winter of our discontent made glorious summer by this sun of york
        ['Now Is The Winter Of Our Discontent Made Glorious Summer By This Sun Of York']
    """

    def pa(s, l, t):
        return [func(tokn, *args) for tokn in t]

    try:
        func_name = getattr(func, "__name__", getattr(func, "__class__").__name__)
    except Exception:
        func_name = str(func)
    pa.__name__ = func_name

    return pa


dblQuotedString = Combine(
    Regex(r'"(?:[^"\n\r\\]|(?:"")|(?:\\(?:[^x]|x[0-9a-fA-F]+)))*') + '"'
).setName("string enclosed in double quotes")

sglQuotedString = Combine(
    Regex(r"'(?:[^'\n\r\\]|(?:'')|(?:\\(?:[^x]|x[0-9a-fA-F]+)))*") + "'"
).setName("string enclosed in single quotes")

quotedString = Combine(
    Regex(r'"(?:[^"\n\r\\]|(?:"")|(?:\\(?:[^x]|x[0-9a-fA-F]+)))*') + '"'
    | Regex(r"'(?:[^'\n\r\\]|(?:'')|(?:\\(?:[^x]|x[0-9a-fA-F]+)))*") + "'"
).setName("quotedString using single or double quotes")

unicodeString = Combine("u" + quotedString.copy()).setName("unicode string literal")


alphas8bit = srange(r"[\0xc0-\0xd6\0xd8-\0xf6\0xf8-\0xff]")
punc8bit = srange(r"[\0xa1-\0xbf\0xd7\0xf7]")

# build list of built-in expressions, for future reference if a global default value
# gets updated
_builtin_exprs = [v for v in vars().values() if isinstance(v, ParserElement)]
