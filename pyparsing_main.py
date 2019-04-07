#-*- coding: utf-8 -*-
# module pyparsing.py
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

__doc__ = \
"""
pyparsing module - Classes and methods to define and execute parsing grammars
=============================================================================

The pyparsing module is an alternative approach to creating and
executing simple grammars, vs. the traditional lex/yacc approach, or the
use of regular expressions.  With pyparsing, you don't need to learn
a new syntax for defining grammars or matching expressions - the parsing
module provides a library of classes that you use to construct the
grammar directly in Python.

Here is a program to parse "Hello, World!" (or any greeting of the form
``"<salutation>, <addressee>!"``), built up using :class:`Word`,
:class:`Literal`, and :class:`And` elements
(the :class:`'+'<ParserElement.__add__>` operators create :class:`And` expressions,
and the strings are auto-converted to :class:`Literal` expressions)::

    from pyparsing import Word, alphas

    # define grammar of a greeting
    greet = Word(alphas) + "," + Word(alphas) + "!"

    hello = "Hello, World!"
    print (hello, "->", greet.parseString(hello))

The program outputs the following::

    Hello, World! -> ['Hello', ',', 'World', '!']

The Python representation of the grammar is quite readable, owing to the
self-explanatory class names, and the use of '+', '|' and '^' operators.

The :class:`ParseResults` object returned from
:class:`ParserElement.parseString` can be
accessed as a nested list, a dictionary, or an object with named
attributes.

The pyparsing module handles some of the problems that are typically
vexing when writing text parsers:

  - extra or missing whitespace (the above program will also handle
    "Hello,World!", "Hello  ,  World  !", etc.)
  - quoted strings
  - embedded comments


Getting Started -
-----------------
Visit the classes :class:`ParserElement` and :class:`ParseResults` to
see the base classes that most other pyparsing
classes inherit from. Use the docstrings for examples of how to:

 - construct literal match expressions from :class:`Literal` and
   :class:`CaselessLiteral` classes
 - construct character word-group expressions using the :class:`Word`
   class
 - see how to create repetitive expressions using :class:`ZeroOrMore`
   and :class:`OneOrMore` classes
 - use :class:`'+'<And>`, :class:`'|'<MatchFirst>`, :class:`'^'<Or>`,
   and :class:`'&'<Each>` operators to combine simple expressions into
   more complex ones
 - associate names with your parsed results using
   :class:`ParserElement.setResultsName`
 - find some helpful expression short-cuts like :class:`delimitedList`
   and :class:`oneOf`
 - find more useful common expressions in the :class:`pyparsing_common`
   namespace class
"""

__version__ = "2.4.0"
__versionTime__ = "07 Apr 2019 12:40 UTC"
__author__ = "Paul McGuire <ptmcg@users.sourceforge.net>"

import string
from weakref import ref as wkref
import copy
import sys
import warnings
import re
import sre_constants
import collections
import pprint
import traceback
import types
from datetime import datetime

try:
    # Python 3
    from itertools import filterfalse
except ImportError:
    from itertools import ifilterfalse as filterfalse

try:
    from _thread import RLock
except ImportError:
    from threading import RLock

try:
    # Python 3
    from collections.abc import Iterable
    from collections.abc import MutableMapping
except ImportError:
    # Python 2.7
    from collections import Iterable
    from collections import MutableMapping

try:
    from collections import OrderedDict as _OrderedDict
except ImportError:
    try:
        from ordereddict import OrderedDict as _OrderedDict
    except ImportError:
        _OrderedDict = None

try:
    from types import SimpleNamespace
except ImportError:
    class SimpleNamespace: pass




#~ sys.stderr.write( "testing pyparsing module, version %s, %s\n" % (__version__,__versionTime__ ) )

# __all__ = [ '__version__', '__versionTime__', '__author__', '__compat__',
# 'And', 'CaselessKeyword', 'CaselessLiteral', 'CharsNotIn', 'Combine', 'Dict', 'Each', 'Empty',
# 'FollowedBy', 'Forward', 'GoToColumn', 'Group', 'Keyword', 'LineEnd', 'LineStart', 'Literal',
# 'PrecededBy', 'MatchFirst', 'NoMatch', 'NotAny', 'OneOrMore', 'OnlyOnce', 'Optional', 'Or',
# 'ParseBaseException', 'ParseElementEnhance', 'ParseException', 'ParseExpression', 'ParseFatalException',
# 'ParseResults', 'ParseSyntaxException', 'ParserElement', 'QuotedString', 'RecursiveGrammarException',
# 'Regex', 'SkipTo', 'StringEnd', 'StringStart', 'Suppress', 'Token', 'TokenConverter',
# 'White', 'Word', 'WordEnd', 'WordStart', 'ZeroOrMore', 'Char',
# 'alphanums', 'alphas', 'alphas8bit', 'anyCloseTag', 'anyOpenTag', 'cStyleComment', 'col',
# 'commaSeparatedList', 'commonHTMLEntity', 'countedArray', 'cppStyleComment', 'dblQuotedString',
# 'dblSlashComment', 'delimitedList', 'dictOf', 'downcaseTokens', 'empty', 'hexnums',
# 'htmlComment', 'javaStyleComment', 'line', 'lineEnd', 'lineStart', 'lineno',
# 'makeHTMLTags', 'makeXMLTags', 'matchOnlyAtCol', 'matchPreviousExpr', 'matchPreviousLiteral',
# 'nestedExpr', 'nullDebugAction', 'nums', 'oneOf', 'opAssoc', 'operatorPrecedence', 'printables',
# 'punc8bit', 'pythonStyleComment', 'quotedString', 'removeQuotes', 'replaceHTMLEntity',
# 'replaceWith', 'restOfLine', 'sglQuotedString', 'srange', 'stringEnd',
# 'stringStart', 'traceParseAction', 'unicodeString', 'upcaseTokens', 'withAttribute',
# 'indentedBlock', 'originalTextFor', 'ungroup', 'infixNotation','locatedExpr', 'withClass',
# 'CloseMatch', 'tokenMap', 'pyparsing_common', 'pyparsing_unicode', 'unicode_set',
# ]

system_version = tuple(sys.version_info)[:3]
PY_3 = system_version[0] == 3
if PY_3:
    _MAX_INT = sys.maxsize
    basestring = str
    unichr = chr
    unicode = str
    _ustr = str

    # build list of single arg builtins, that can be used as parse actions
    singleArgBuiltins = [sum, len, sorted, reversed, list, tuple, set, any, all, min, max]

else:
    _MAX_INT = sys.maxint
    range = xrange

    def _ustr(obj):
        """Drop-in replacement for str(obj) that tries to be Unicode
        friendly. It first tries str(obj). If that fails with
        a UnicodeEncodeError, then it tries unicode(obj). It then
        < returns the unicode object | encodes it with the default
        encoding | ... >.
        """
        if isinstance(obj,unicode):
            return obj

        try:
            # If this works, then _ustr(obj) has the same behaviour as str(obj), so
            # it won't break any existing code.
            return str(obj)

        except UnicodeEncodeError:
            # Else encode it
            ret = unicode(obj).encode(sys.getdefaultencoding(), 'xmlcharrefreplace')
            xmlcharref = Regex(r'&#\d+;')
            xmlcharref.setParseAction(lambda t: '\\u' + hex(int(t[0][2:-1]))[2:])
            return xmlcharref.transformString(ret)

    # build list of single arg builtins, tolerant of Python version, that can be used as parse actions
    singleArgBuiltins = []
    import __builtin__
    for fname in "sum len sorted reversed list tuple set any all min max".split():
        try:
            singleArgBuiltins.append(getattr(__builtin__,fname))
        except AttributeError:
            continue

_generatorType = type((y for y in range(1)))

def _xml_escape(data):
    """Escape &, <, >, ", ', etc. in a string of data."""

    # ampersand must be replaced first
    from_symbols = '&><"\''
    to_symbols = ('&'+s+';' for s in "amp gt lt quot apos".split())
    for from_,to_ in zip(from_symbols, to_symbols):
        data = data.replace(from_, to_)
    return data

alphas     = string.ascii_uppercase + string.ascii_lowercase
nums       = "0123456789"
hexnums    = nums + "ABCDEFabcdef"
alphanums  = alphas + nums
_bslash    = chr(92)
printables = "".join(c for c in string.printable if c not in string.whitespace)

class ParseBaseException(Exception):
    """base exception class for all parsing runtime exceptions"""
    # Performance tuning: we construct a *lot* of these, so keep this
    # constructor as small and fast as possible
    def __init__( self, pstr, loc=0, msg=None, elem=None ):
        self.loc = loc
        if msg is None:
            self.msg = pstr
            self.pstr = ""
        else:
            self.msg = msg
            self.pstr = pstr
        self.parserElement = elem
        self.args = (pstr, loc, msg)

    @classmethod
    def _from_exception(cls, pe):
        """
        internal factory method to simplify creating one type of ParseException
        from another - avoids having __init__ signature conflicts among subclasses
        """
        return cls(pe.pstr, pe.loc, pe.msg, pe.parserElement)

    def __getattr__( self, aname ):
        """supported attributes by name are:
           - lineno - returns the line number of the exception text
           - col - returns the column number of the exception text
           - line - returns the line containing the exception text
        """
        if( aname == "lineno" ):
            return lineno( self.loc, self.pstr )
        elif( aname in ("col", "column") ):
            return col( self.loc, self.pstr )
        elif( aname == "line" ):
            return line( self.loc, self.pstr )
        else:
            raise AttributeError(aname)

    def __str__( self ):
        return "%s (at char %d), (line:%d, col:%d)" % \
                ( self.msg, self.loc, self.lineno, self.column )
    def __repr__( self ):
        return _ustr(self)
    def markInputline( self, markerString = ">!<" ):
        """Extracts the exception line from the input string, and marks
           the location of the exception with a special symbol.
        """
        line_str = self.line
        line_column = self.column - 1
        if markerString:
            line_str = "".join((line_str[:line_column],
                                markerString, line_str[line_column:]))
        return line_str.strip()
    def __dir__(self):
        return "lineno col line".split() + dir(type(self))

class ParseException(ParseBaseException):
    """
    Exception thrown when parse expressions don't match class;
    supported attributes by name are:
    - lineno - returns the line number of the exception text
    - col - returns the column number of the exception text
    - line - returns the line containing the exception text

    Example::

        try:
            Word(nums).setName("integer").parseString("ABC")
        except ParseException as pe:
            print(pe)
            print("column: {}".format(pe.col))

    prints::

       Expected integer (at char 0), (line:1, col:1)
        column: 1

    """

    @staticmethod
    def explain(exc, depth=16):
        """
        Method to take an exception and translate the Python internal traceback into a list
        of the pyparsing expressions that caused the exception to be raised.

        Parameters:

         - exc - exception raised during parsing (need not be a ParseException, in support
           of Python exceptions that might be raised in a parse action)
         - depth (default=16) - number of levels back in the stack trace to list expression
           and function names; if None, the full stack trace names will be listed; if 0, only
           the failing input line, marker, and exception string will be shown

        Returns a multi-line string listing the ParserElements and/or function names in the
        exception's stack trace.

        Note: the diagnostic output will include string representations of the expressions
        that failed to parse. These representations will be more helpful if you use `setName` to
        give identifiable names to your expressions. Otherwise they will use the default string
        forms, which may be cryptic to read.

        explain() is only supported under Python 3.
        """
        import inspect

        if depth is None:
            depth = sys.getrecursionlimit()
        ret = []
        if isinstance(exc, ParseBaseException):
            ret.append(exc.line)
            ret.append(' ' * (exc.col - 1) + '^')
        ret.append("{0}: {1}".format(type(exc).__name__, exc))

        if depth > 0:
            callers = inspect.getinnerframes(exc.__traceback__, context=depth)
            seen = set()
            for i, ff in enumerate(callers[-depth:]):
                frm = ff[0]

                f_self = frm.f_locals.get('self', None)
                if isinstance(f_self, ParserElement):
                    if frm.f_code.co_name not in ('parseImpl', '_parseNoCache'):
                        continue
                    if f_self in seen:
                        continue
                    seen.add(f_self)

                    self_type = type(f_self)
                    ret.append("{0}.{1} - {2}".format(self_type.__module__,
                                                      self_type.__name__,
                                                      f_self))
                elif f_self is not None:
                    self_type = type(f_self)
                    ret.append("{0}.{1}".format(self_type.__module__,
                                                self_type.__name__))
                else:
                    code = frm.f_code
                    if code.co_name in ('wrapper', '<module>'):
                        continue

                    ret.append("{0}".format(code.co_name))

                depth -= 1
                if not depth:
                    break

        return '\n'.join(ret)


class ParseFatalException(ParseBaseException):
    """user-throwable exception thrown when inconsistent parse content
       is found; stops all parsing immediately"""
    pass

class ParseSyntaxException(ParseFatalException):
    """just like :class:`ParseFatalException`, but thrown internally
    when an :class:`ErrorStop<And._ErrorStop>` ('-' operator) indicates
    that parsing is to stop immediately because an unbacktrackable
    syntax error has been found.
    """
    pass

#~ class ReparseException(ParseBaseException):
    #~ """Experimental class - parse actions can raise this exception to cause
       #~ pyparsing to reparse the input string:
        #~ - with a modified input string, and/or
        #~ - with a modified start location
       #~ Set the values of the ReparseException in the constructor, and raise the
       #~ exception in a parse action to cause pyparsing to use the new string/location.
       #~ Setting the values as None causes no change to be made.
       #~ """
    #~ def __init_( self, newstring, restartLoc ):
        #~ self.newParseText = newstring
        #~ self.reparseLoc = restartLoc

class RecursiveGrammarException(Exception):
    """exception thrown by :class:`ParserElement.validate` if the
    grammar could be improperly recursive
    """
    def __init__( self, parseElementList ):
        self.parseElementTrace = parseElementList

    def __str__( self ):
        return "RecursiveGrammarException: %s" % self.parseElementTrace

class _ParseResultsWithOffset(object):
    def __init__(self,p1,p2):
        self.tup = (p1,p2)
    def __getitem__(self,i):
        return self.tup[i]
    def __repr__(self):
        return repr(self.tup[0])
    def setOffset(self,i):
        self.tup = (self.tup[0],i)

class ParseResults(object):
    """Structured parse results, to provide multiple means of access to
    the parsed data:

       - as a list (``len(results)``)
       - by list index (``results[0], results[1]``, etc.)
       - by attribute (``results.<resultsName>`` - see :class:`ParserElement.setResultsName`)

    Example::

        integer = Word(nums)
        date_str = (integer.setResultsName("year") + '/'
                        + integer.setResultsName("month") + '/'
                        + integer.setResultsName("day"))
        # equivalent form:
        # date_str = integer("year") + '/' + integer("month") + '/' + integer("day")

        # parseString returns a ParseResults object
        result = date_str.parseString("1999/12/31")

        def test(s, fn=repr):
            print("%s -> %s" % (s, fn(eval(s))))
        test("list(result)")
        test("result[0]")
        test("result['month']")
        test("result.day")
        test("'month' in result")
        test("'minutes' in result")
        test("result.dump()", str)

    prints::

        list(result) -> ['1999', '/', '12', '/', '31']
        result[0] -> '1999'
        result['month'] -> '12'
        result.day -> '31'
        'month' in result -> True
        'minutes' in result -> False
        result.dump() -> ['1999', '/', '12', '/', '31']
        - day: 31
        - month: 12
        - year: 1999
    """
    def __new__(cls, toklist=None, name=None, asList=True, modal=True ):
        if isinstance(toklist, cls):
            return toklist
        retobj = object.__new__(cls)
        retobj.__doinit = True
        return retobj

    # Performance tuning: we construct a *lot* of these, so keep this
    # constructor as small and fast as possible
    def __init__( self, toklist=None, name=None, asList=True, modal=True, isinstance=isinstance ):
        if self.__doinit:
            self.__doinit = False
            self.__name = None
            self.__parent = None
            self.__accumNames = {}
            self.__asList = asList
            self.__modal = modal
            if toklist is None:
                toklist = []
            if isinstance(toklist, list):
                self.__toklist = toklist[:]
            elif isinstance(toklist, _generatorType):
                self.__toklist = list(toklist)
            else:
                self.__toklist = [toklist]
            self.__tokdict = dict()

        if name is not None and name:
            if not modal:
                self.__accumNames[name] = 0
            if isinstance(name,int):
                name = _ustr(name) # will always return a str, but use _ustr for consistency
            self.__name = name
            if not (isinstance(toklist, (type(None), basestring, list)) and toklist in (None,'',[])):
                if isinstance(toklist,basestring):
                    toklist = [ toklist ]
                if asList:
                    if isinstance(toklist,ParseResults):
                        self[name] = _ParseResultsWithOffset(ParseResults(toklist.__toklist), 0)
                    else:
                        self[name] = _ParseResultsWithOffset(ParseResults(toklist[0]),0)
                    self[name].__name = name
                else:
                    try:
                        self[name] = toklist[0]
                    except (KeyError,TypeError,IndexError):
                        self[name] = toklist

    def __getitem__( self, i ):
        if isinstance( i, (int,slice) ):
            return self.__toklist[i]
        else:
            if i not in self.__accumNames:
                return self.__tokdict[i][-1][0]
            else:
                return ParseResults([ v[0] for v in self.__tokdict[i] ])

    def __setitem__( self, k, v, isinstance=isinstance ):
        if isinstance(v,_ParseResultsWithOffset):
            self.__tokdict[k] = self.__tokdict.get(k,list()) + [v]
            sub = v[0]
        elif isinstance(k,(int,slice)):
            self.__toklist[k] = v
            sub = v
        else:
            self.__tokdict[k] = self.__tokdict.get(k,list()) + [_ParseResultsWithOffset(v,0)]
            sub = v
        if isinstance(sub,ParseResults):
            sub.__parent = wkref(self)

    def __delitem__( self, i ):
        if isinstance(i,(int,slice)):
            mylen = len( self.__toklist )
            del self.__toklist[i]

            # convert int to slice
            if isinstance(i, int):
                if i < 0:
                    i += mylen
                i = slice(i, i+1)
            # get removed indices
            removed = list(range(*i.indices(mylen)))
            removed.reverse()
            # fixup indices in token dictionary
            for name,occurrences in self.__tokdict.items():
                for j in removed:
                    for k, (value, position) in enumerate(occurrences):
                        occurrences[k] = _ParseResultsWithOffset(value, position - (position > j))
        else:
            del self.__tokdict[i]

    def __contains__( self, k ):
        return k in self.__tokdict

    def __len__( self ): return len( self.__toklist )
    def __bool__(self): return ( not not self.__toklist )
    __nonzero__ = __bool__
    def __iter__( self ): return iter( self.__toklist )
    def __reversed__( self ): return iter( self.__toklist[::-1] )
    def _iterkeys( self ):
        if hasattr(self.__tokdict, "iterkeys"):
            return self.__tokdict.iterkeys()
        else:
            return iter(self.__tokdict)

    def _itervalues( self ):
        return (self[k] for k in self._iterkeys())

    def _iteritems( self ):
        return ((k, self[k]) for k in self._iterkeys())

    if PY_3:
        keys = _iterkeys
        """Returns an iterator of all named result keys."""

        values = _itervalues
        """Returns an iterator of all named result values."""

        items = _iteritems
        """Returns an iterator of all named result key-value tuples."""

    else:
        iterkeys = _iterkeys
        """Returns an iterator of all named result keys (Python 2.x only)."""

        itervalues = _itervalues
        """Returns an iterator of all named result values (Python 2.x only)."""

        iteritems = _iteritems
        """Returns an iterator of all named result key-value tuples (Python 2.x only)."""

        def keys( self ):
            """Returns all named result keys (as a list in Python 2.x, as an iterator in Python 3.x)."""
            return list(self.iterkeys())

        def values( self ):
            """Returns all named result values (as a list in Python 2.x, as an iterator in Python 3.x)."""
            return list(self.itervalues())

        def items( self ):
            """Returns all named result key-values (as a list of tuples in Python 2.x, as an iterator in Python 3.x)."""
            return list(self.iteritems())

    def haskeys( self ):
        """Since keys() returns an iterator, this method is helpful in bypassing
           code that looks for the existence of any defined results names."""
        return bool(self.__tokdict)

    def pop( self, *args, **kwargs):
        """
        Removes and returns item at specified index (default= ``last``).
        Supports both ``list`` and ``dict`` semantics for ``pop()``. If
        passed no argument or an integer argument, it will use ``list``
        semantics and pop tokens from the list of parsed tokens. If passed
        a non-integer argument (most likely a string), it will use ``dict``
        semantics and pop the corresponding value from any defined results
        names. A second default return value argument is supported, just as in
        ``dict.pop()``.

        Example::

            def remove_first(tokens):
                tokens.pop(0)
            print(OneOrMore(Word(nums)).parseString("0 123 321")) # -> ['0', '123', '321']
            print(OneOrMore(Word(nums)).addParseAction(remove_first).parseString("0 123 321")) # -> ['123', '321']

            label = Word(alphas)
            patt = label("LABEL") + OneOrMore(Word(nums))
            print(patt.parseString("AAB 123 321").dump())

            # Use pop() in a parse action to remove named result (note that corresponding value is not
            # removed from list form of results)
            def remove_LABEL(tokens):
                tokens.pop("LABEL")
                return tokens
            patt.addParseAction(remove_LABEL)
            print(patt.parseString("AAB 123 321").dump())

        prints::

            ['AAB', '123', '321']
            - LABEL: AAB

            ['AAB', '123', '321']
        """
        if not args:
            args = [-1]
        for k,v in kwargs.items():
            if k == 'default':
                args = (args[0], v)
            else:
                raise TypeError("pop() got an unexpected keyword argument '%s'" % k)
        if (isinstance(args[0], int) or
                        len(args) == 1 or
                        args[0] in self):
            index = args[0]
            ret = self[index]
            del self[index]
            return ret
        else:
            defaultvalue = args[1]
            return defaultvalue

    def get(self, key, defaultValue=None):
        """
        Returns named result matching the given key, or if there is no
        such name, then returns the given ``defaultValue`` or ``None`` if no
        ``defaultValue`` is specified.

        Similar to ``dict.get()``.

        Example::

            integer = Word(nums)
            date_str = integer("year") + '/' + integer("month") + '/' + integer("day")

            result = date_str.parseString("1999/12/31")
            print(result.get("year")) # -> '1999'
            print(result.get("hour", "not specified")) # -> 'not specified'
            print(result.get("hour")) # -> None
        """
        if key in self:
            return self[key]
        else:
            return defaultValue

    def insert( self, index, insStr ):
        """
        Inserts new element at location index in the list of parsed tokens.

        Similar to ``list.insert()``.

        Example::

            print(OneOrMore(Word(nums)).parseString("0 123 321")) # -> ['0', '123', '321']

            # use a parse action to insert the parse location in the front of the parsed results
            def insert_locn(locn, tokens):
                tokens.insert(0, locn)
            print(OneOrMore(Word(nums)).addParseAction(insert_locn).parseString("0 123 321")) # -> [0, '0', '123', '321']
        """
        self.__toklist.insert(index, insStr)
        # fixup indices in token dictionary
        for name,occurrences in self.__tokdict.items():
            for k, (value, position) in enumerate(occurrences):
                occurrences[k] = _ParseResultsWithOffset(value, position + (position > index))

    def append( self, item ):
        """
        Add single element to end of ParseResults list of elements.

        Example::

            print(OneOrMore(Word(nums)).parseString("0 123 321")) # -> ['0', '123', '321']

            # use a parse action to compute the sum of the parsed integers, and add it to the end
            def append_sum(tokens):
                tokens.append(sum(map(int, tokens)))
            print(OneOrMore(Word(nums)).addParseAction(append_sum).parseString("0 123 321")) # -> ['0', '123', '321', 444]
        """
        self.__toklist.append(item)

    def extend( self, itemseq ):
        """
        Add sequence of elements to end of ParseResults list of elements.

        Example::

            patt = OneOrMore(Word(alphas))

            # use a parse action to append the reverse of the matched strings, to make a palindrome
            def make_palindrome(tokens):
                tokens.extend(reversed([t[::-1] for t in tokens]))
                return ''.join(tokens)
            print(patt.addParseAction(make_palindrome).parseString("lskdj sdlkjf lksd")) # -> 'lskdjsdlkjflksddsklfjkldsjdksl'
        """
        if isinstance(itemseq, ParseResults):
            self.__iadd__(itemseq)
        else:
            self.__toklist.extend(itemseq)

    def clear( self ):
        """
        Clear all elements and results names.
        """
        del self.__toklist[:]
        self.__tokdict.clear()

    def __getattr__( self, name ):
        try:
            return self[name]
        except KeyError:
            return ""

        if name in self.__tokdict:
            if name not in self.__accumNames:
                return self.__tokdict[name][-1][0]
            else:
                return ParseResults([ v[0] for v in self.__tokdict[name] ])
        else:
            return ""

    def __add__( self, other ):
        ret = self.copy()
        ret += other
        return ret

    def __iadd__( self, other ):
        if other.__tokdict:
            offset = len(self.__toklist)
            addoffset = lambda a: offset if a<0 else a+offset
            otheritems = other.__tokdict.items()
            otherdictitems = [(k, _ParseResultsWithOffset(v[0],addoffset(v[1])) )
                                for (k,vlist) in otheritems for v in vlist]
            for k,v in otherdictitems:
                self[k] = v
                if isinstance(v[0],ParseResults):
                    v[0].__parent = wkref(self)

        self.__toklist += other.__toklist
        self.__accumNames.update( other.__accumNames )
        return self

    def __radd__(self, other):
        if isinstance(other,int) and other == 0:
            # useful for merging many ParseResults using sum() builtin
            return self.copy()
        else:
            # this may raise a TypeError - so be it
            return other + self

    def __repr__( self ):
        return "(%s, %s)" % ( repr( self.__toklist ), repr( self.__tokdict ) )

    def __str__( self ):
        return '[' + ', '.join(_ustr(i) if isinstance(i, ParseResults) else repr(i) for i in self.__toklist) + ']'

    def _asStringList( self, sep='' ):
        out = []
        for item in self.__toklist:
            if out and sep:
                out.append(sep)
            if isinstance( item, ParseResults ):
                out += item._asStringList()
            else:
                out.append( _ustr(item) )
        return out

    def asList( self ):
        """
        Returns the parse results as a nested list of matching tokens, all converted to strings.

        Example::

            patt = OneOrMore(Word(alphas))
            result = patt.parseString("sldkj lsdkj sldkj")
            # even though the result prints in string-like form, it is actually a pyparsing ParseResults
            print(type(result), result) # -> <class 'pyparsing.ParseResults'> ['sldkj', 'lsdkj', 'sldkj']

            # Use asList() to create an actual list
            result_list = result.asList()
            print(type(result_list), result_list) # -> <class 'list'> ['sldkj', 'lsdkj', 'sldkj']
        """
        return [res.asList() if isinstance(res,ParseResults) else res for res in self.__toklist]

    def asDict( self ):
        """
        Returns the named parse results as a nested dictionary.

        Example::

            integer = Word(nums)
            date_str = integer("year") + '/' + integer("month") + '/' + integer("day")

            result = date_str.parseString('12/31/1999')
            print(type(result), repr(result)) # -> <class 'pyparsing.ParseResults'> (['12', '/', '31', '/', '1999'], {'day': [('1999', 4)], 'year': [('12', 0)], 'month': [('31', 2)]})

            result_dict = result.asDict()
            print(type(result_dict), repr(result_dict)) # -> <class 'dict'> {'day': '1999', 'year': '12', 'month': '31'}

            # even though a ParseResults supports dict-like access, sometime you just need to have a dict
            import json
            print(json.dumps(result)) # -> Exception: TypeError: ... is not JSON serializable
            print(json.dumps(result.asDict())) # -> {"month": "31", "day": "1999", "year": "12"}
        """
        if PY_3:
            item_fn = self.items
        else:
            item_fn = self.iteritems

        def toItem(obj):
            if isinstance(obj, ParseResults):
                if obj.haskeys():
                    return obj.asDict()
                else:
                    return [toItem(v) for v in obj]
            else:
                return obj

        return dict((k,toItem(v)) for k,v in item_fn())

    def copy( self ):
        """
        Returns a new copy of a :class:`ParseResults` object.
        """
        ret = ParseResults( self.__toklist )
        ret.__tokdict = dict(self.__tokdict.items())
        ret.__parent = self.__parent
        ret.__accumNames.update( self.__accumNames )
        ret.__name = self.__name
        return ret

    def asXML( self, doctag=None, namedItemsOnly=False, indent="", formatted=True ):
        """
        (Deprecated) Returns the parse results as XML. Tags are created for tokens and lists that have defined results names.
        """
        nl = "\n"
        out = []
        namedItems = dict((v[1],k) for (k,vlist) in self.__tokdict.items()
                                                            for v in vlist)
        nextLevelIndent = indent + "  "

        # collapse out indents if formatting is not desired
        if not formatted:
            indent = ""
            nextLevelIndent = ""
            nl = ""

        selfTag = None
        if doctag is not None:
            selfTag = doctag
        else:
            if self.__name:
                selfTag = self.__name

        if not selfTag:
            if namedItemsOnly:
                return ""
            else:
                selfTag = "ITEM"

        out += [ nl, indent, "<", selfTag, ">" ]

        for i,res in enumerate(self.__toklist):
            if isinstance(res,ParseResults):
                if i in namedItems:
                    out += [ res.asXML(namedItems[i],
                                        namedItemsOnly and doctag is None,
                                        nextLevelIndent,
                                        formatted)]
                else:
                    out += [ res.asXML(None,
                                        namedItemsOnly and doctag is None,
                                        nextLevelIndent,
                                        formatted)]
            else:
                # individual token, see if there is a name for it
                resTag = None
                if i in namedItems:
                    resTag = namedItems[i]
                if not resTag:
                    if namedItemsOnly:
                        continue
                    else:
                        resTag = "ITEM"
                xmlBodyText = _xml_escape(_ustr(res))
                out += [ nl, nextLevelIndent, "<", resTag, ">",
                                                xmlBodyText,
                                                "</", resTag, ">" ]

        out += [ nl, indent, "</", selfTag, ">" ]
        return "".join(out)

    def __lookup(self,sub):
        for k,vlist in self.__tokdict.items():
            for v,loc in vlist:
                if sub is v:
                    return k
        return None

    def getName(self):
        r"""
        Returns the results name for this token expression. Useful when several
        different expressions might match at a particular location.

        Example::

            integer = Word(nums)
            ssn_expr = Regex(r"\d\d\d-\d\d-\d\d\d\d")
            house_number_expr = Suppress('#') + Word(nums, alphanums)
            user_data = (Group(house_number_expr)("house_number")
                        | Group(ssn_expr)("ssn")
                        | Group(integer)("age"))
            user_info = OneOrMore(user_data)

            result = user_info.parseString("22 111-22-3333 #221B")
            for item in result:
                print(item.getName(), ':', item[0])

        prints::

            age : 22
            ssn : 111-22-3333
            house_number : 221B
        """
        if self.__name:
            return self.__name
        elif self.__parent:
            par = self.__parent()
            if par:
                return par.__lookup(self)
            else:
                return None
        elif (len(self) == 1 and
               len(self.__tokdict) == 1 and
               next(iter(self.__tokdict.values()))[0][1] in (0,-1)):
            return next(iter(self.__tokdict.keys()))
        else:
            return None

    def dump(self, indent='', depth=0, full=True):
        """
        Diagnostic method for listing out the contents of
        a :class:`ParseResults`. Accepts an optional ``indent`` argument so
        that this string can be embedded in a nested display of other data.

        Example::

            integer = Word(nums)
            date_str = integer("year") + '/' + integer("month") + '/' + integer("day")

            result = date_str.parseString('12/31/1999')
            print(result.dump())

        prints::

            ['12', '/', '31', '/', '1999']
            - day: 1999
            - month: 31
            - year: 12
        """
        out = []
        NL = '\n'
        out.append( indent+_ustr(self.asList()) )
        if full:
            if self.haskeys():
                items = sorted((str(k), v) for k,v in self.items())
                for k,v in items:
                    if out:
                        out.append(NL)
                    out.append( "%s%s- %s: " % (indent,('  '*depth), k) )
                    if isinstance(v,ParseResults):
                        if v:
                            out.append( v.dump(indent,depth+1) )
                        else:
                            out.append(_ustr(v))
                    else:
                        out.append(repr(v))
            elif any(isinstance(vv,ParseResults) for vv in self):
                v = self
                for i,vv in enumerate(v):
                    if isinstance(vv,ParseResults):
                        out.append("\n%s%s[%d]:\n%s%s%s" % (indent,('  '*(depth)),i,indent,('  '*(depth+1)),vv.dump(indent,depth+1) ))
                    else:
                        out.append("\n%s%s[%d]:\n%s%s%s" % (indent,('  '*(depth)),i,indent,('  '*(depth+1)),_ustr(vv)))

        return "".join(out)

    def pprint(self, *args, **kwargs):
        """
        Pretty-printer for parsed results as a list, using the
        `pprint <https://docs.python.org/3/library/pprint.html>`_ module.
        Accepts additional positional or keyword args as defined for
        `pprint.pprint <https://docs.python.org/3/library/pprint.html#pprint.pprint>`_ .

        Example::

            ident = Word(alphas, alphanums)
            num = Word(nums)
            func = Forward()
            term = ident | num | Group('(' + func + ')')
            func <<= ident + Group(Optional(delimitedList(term)))
            result = func.parseString("fna a,b,(fnb c,d,200),100")
            result.pprint(width=40)

        prints::

            ['fna',
             ['a',
              'b',
              ['(', 'fnb', ['c', 'd', '200'], ')'],
              '100']]
        """
        pprint.pprint(self.asList(), *args, **kwargs)

    # add support for pickle protocol
    def __getstate__(self):
        return ( self.__toklist,
                 ( self.__tokdict.copy(),
                   self.__parent is not None and self.__parent() or None,
                   self.__accumNames,
                   self.__name ) )

    def __setstate__(self,state):
        self.__toklist = state[0]
        (self.__tokdict,
         par,
         inAccumNames,
         self.__name) = state[1]
        self.__accumNames = {}
        self.__accumNames.update(inAccumNames)
        if par is not None:
            self.__parent = wkref(par)
        else:
            self.__parent = None

    def __getnewargs__(self):
        return self.__toklist, self.__name, self.__asList, self.__modal

    def __dir__(self):
        return (dir(type(self)) + list(self.keys()))

MutableMapping.register(ParseResults)

def col (loc,strg):
    """Returns current column within a string, counting newlines as line separators.
   The first column is number 1.

   Note: the default parsing behavior is to expand tabs in the input string
   before starting the parsing process.  See
   :class:`ParserElement.parseString` for more
   information on parsing strings containing ``<TAB>`` s, and suggested
   methods to maintain a consistent view of the parsed string, the parse
   location, and line and column positions within the parsed string.
   """
    s = strg
    return 1 if 0<loc<len(s) and s[loc-1] == '\n' else loc - s.rfind("\n", 0, loc)

def lineno(loc,strg):
    """Returns current line number within a string, counting newlines as line separators.
    The first line is number 1.

    Note - the default parsing behavior is to expand tabs in the input string
    before starting the parsing process.  See :class:`ParserElement.parseString`
    for more information on parsing strings containing ``<TAB>`` s, and
    suggested methods to maintain a consistent view of the parsed string, the
    parse location, and line and column positions within the parsed string.
    """
    return strg.count("\n",0,loc) + 1

def line( loc, strg ):
    """Returns the line of text containing loc within a string, counting newlines as line separators.
       """
    lastCR = strg.rfind("\n", 0, loc)
    nextCR = strg.find("\n", loc)
    if nextCR >= 0:
        return strg[lastCR+1:nextCR]
    else:
        return strg[lastCR+1:]

def _defaultStartDebugAction( instring, loc, expr ):
    print (("Match " + _ustr(expr) + " at loc " + _ustr(loc) + "(%d,%d)" % ( lineno(loc,instring), col(loc,instring) )))

def _defaultSuccessDebugAction( instring, startloc, endloc, expr, toks ):
    print ("Matched " + _ustr(expr) + " -> " + str(toks.asList()))

def _defaultExceptionDebugAction( instring, loc, expr, exc ):
    print ("Exception raised:" + _ustr(exc))

def nullDebugAction(*args):
    """'Do-nothing' debug action, to suppress debugging output during parsing."""
    pass

# Only works on Python 3.x - nonlocal is toxic to Python 2 installs
#~ 'decorator to trim function calls to match the arity of the target'
#~ def _trim_arity(func, maxargs=3):
    #~ if func in singleArgBuiltins:
        #~ return lambda s,l,t: func(t)
    #~ limit = 0
    #~ foundArity = False
    #~ def wrapper(*args):
        #~ nonlocal limit,foundArity
        #~ while 1:
            #~ try:
                #~ ret = func(*args[limit:])
                #~ foundArity = True
                #~ return ret
            #~ except TypeError:
                #~ if limit == maxargs or foundArity:
                    #~ raise
                #~ limit += 1
                #~ continue
    #~ return wrapper

# this version is Python 2.x-3.x cross-compatible
'decorator to trim function calls to match the arity of the target'








# define ranges in language character sets
if PY_3:
    setattr(pyparsing_unicode, "العربية", pyparsing_unicode.Arabic)
    setattr(pyparsing_unicode, "中文", pyparsing_unicode.Chinese)
    setattr(pyparsing_unicode, "кириллица", pyparsing_unicode.Cyrillic)
    setattr(pyparsing_unicode, "Ελληνικά", pyparsing_unicode.Greek)
    setattr(pyparsing_unicode, "עִברִית", pyparsing_unicode.Hebrew)
    setattr(pyparsing_unicode, "日本語", pyparsing_unicode.Japanese)
    setattr(pyparsing_unicode.Japanese, "漢字", pyparsing_unicode.Japanese.Kanji)
    setattr(pyparsing_unicode.Japanese, "カタカナ", pyparsing_unicode.Japanese.Katakana)
    setattr(pyparsing_unicode.Japanese, "ひらがな", pyparsing_unicode.Japanese.Hiragana)
    setattr(pyparsing_unicode, "한국어", pyparsing_unicode.Korean)
    setattr(pyparsing_unicode, "ไทย", pyparsing_unicode.Thai)
    setattr(pyparsing_unicode, "देवनागरी", pyparsing_unicode.Devanagari)


if __name__ == "__main__":

    selectToken    = CaselessLiteral("select")
    fromToken      = CaselessLiteral("from")

    ident          = Word(alphas, alphanums + "_$")

    columnName     = delimitedList(ident, ".", combine=True).setParseAction(upcaseTokens)
    columnNameList = Group(delimitedList(columnName)).setName("columns")
    columnSpec     = ('*' | columnNameList)

    tableName      = delimitedList(ident, ".", combine=True).setParseAction(upcaseTokens)
    tableNameList  = Group(delimitedList(tableName)).setName("tables")

    simpleSQL      = selectToken("command") + columnSpec("columns") + fromToken + tableNameList("tables")

    # demo runTests method, including embedded comments in test string
    simpleSQL.runTests("""
        # '*' as column list and dotted table name
        select * from SYS.XYZZY

        # caseless match on "SELECT", and casts back to "select"
        SELECT * from XYZZY, ABC

        # list of column names, and mixed case SELECT keyword
        Select AA,BB,CC from Sys.dual

        # multiple tables
        Select A, B, C from Sys.dual, Table2

        # invalid SELECT keyword - should fail
        Xelect A, B, C from Sys.dual

        # incomplete command - should fail
        Select

        # invalid column name - should fail
        Select ^^^ frox Sys.dual

        """)

    pyparsing_common.number.runTests("""
        100
        -100
        +100
        3.14159
        6.02e23
        1e-12
        """)

    # any int or real number, returned as float
    pyparsing_common.fnumber.runTests("""
        100
        -100
        +100
        3.14159
        6.02e23
        1e-12
        """)

    pyparsing_common.hex_integer.runTests("""
        100
        FF
        """)

    import uuid
    pyparsing_common.uuid.setParseAction(tokenMap(uuid.UUID))
    pyparsing_common.uuid.runTests("""
        12345678-1234-5678-1234-567812345678
        """)
