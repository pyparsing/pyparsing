# module pyparsing.py
#
# Copyright (c) 2003-2022  Paul T. McGuire
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

__doc__ = """
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
(the :meth:`'+'<ParserElement.__add__>` operators create :class:`And` expressions,
and the strings are auto-converted to :class:`Literal` expressions)::

    from pyparsing import Word, alphas

    # define grammar of a greeting
    greet = Word(alphas) + "," + Word(alphas) + "!"

    hello = "Hello, World!"
    print(hello, "->", greet.parse_string(hello))

The program outputs the following::

    Hello, World! -> ['Hello', ',', 'World', '!']

The Python representation of the grammar is quite readable, owing to the
self-explanatory class names, and the use of :class:`'+'<And>`,
:class:`'|'<MatchFirst>`, :class:`'^'<Or>` and :class:`'&'<Each>` operators.

The :class:`ParseResults` object returned from
:class:`ParserElement.parse_string` can be
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
   :class:`ParserElement.set_results_name`
 - access the parsed data, which is returned as a :class:`ParseResults`
   object
 - find some helpful expression short-cuts like :class:`DelimitedList`
   and :class:`one_of`
 - find more useful common expressions in the :class:`pyparsing_common`
   namespace class
"""
from typing import NamedTuple


class version_info(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: str
    serial: int

    @property
    def __version__(self):
        return (
            f"{self.major}.{self.minor}.{self.micro}"
            + (
                f"{'r' if self.releaselevel[0] == 'c' else ''}{self.releaselevel[0]}{self.serial}",
                "",
            )[self.releaselevel == "final"]
        )

    def __str__(self):
        return f"{__name__} {self.__version__} / {__version_time__}"

    def __repr__(self):
        return f"{__name__}.{type(self).__name__}({', '.join('{}={!r}'.format(*nv) for nv in zip(self._fields, self))})"


__version_info__ = version_info(3, 2, 0, "final", 1)
__version_time__ = "13 Oct 2024 09:46 UTC"
__version__ = __version_info__.__version__
__versionTime__ = __version_time__
__author__ = "Paul McGuire <ptmcg.gm+pyparsing@gmail.com>"

from .util import TypeVar, line, C, inspect, UnboundedMemo, lru_cache, col, _UnboundedCache, warnings, cast, _escape_regex_range_chars, lineno, replaced_by_pep8, wraps, Union, types, Iterable, LRUMemo, Callable, itertools
from .exceptions import ParseFatalException, RecursiveGrammarException, ParseSyntaxException, ParseException, ParseBaseException
# from .exceptions import *
from .actions import *
from .core import __diag__, __compat__
from .results import *
# from .core import *
from .core import (tokenMap, Located, ABC, And, Any, AtLineStart, AtStringStart, Callable, CaselessKeyword, CaselessLiteral, Char, CharsNotIn, CloseMatch, Combine, DebugExceptionAction, DebugStartAction, DebugSuccessAction, DelimitedList, Diagnostics, Dict, Each, Empty, Enum, FollowedBy, Forward, Generator, GoToColumn, Group, IndentedBlock, Iterable, Keyword, LineEnd, LineStart, Literal, MatchFirst, NamedTuple, NoMatch, NotAny, OneOrMore, OnlyOnce, Opt, Optional, Or, ParseAction, ParseBaseException, ParseCondition, ParseElementEnhance, ParseException, ParseExpression, ParseFailAction, ParseFatalException, ParseImplReturnType, ParseResults, ParseSyntaxException, ParserElement, Path, PositionToken, PostParseReturnType, PrecededBy, QuotedString, RLock, RecursiveGrammarException, Regex, Sequence, SkipTo, StringEnd, StringStart, Suppress, Tag, TextIO, Token, TokenConverter, Union, White, Word, WordEnd, WordStart, ZeroOrMore, _FifoCache, _LRUMemo, _MAX_INT, _MultipleMatch, _NullToken, _ParseResultsWithOffset, _PendingSkip, _SingleCharLiteral, _UnboundedCache, _UnboundedMemo, _bslash, _charRange, _collapse_string_to_ranges, _default_exception_debug_action, _default_start_debug_action, _default_success_debug_action, _escape_regex_range_chars, _escapedHexChar, _escapedOctChar, _escapedPunc, _flatten, _generatorType, _reBracketExpr, _should_enable_warnings, _singleChar, _single_arg_builtins, _trim_arity, _trim_arity_call_line, abstractmethod, alphanums, alphas, alphas8bit, cached_property, cast, col, conditionAsParseAction, condition_as_parse_action, copy, dblQuotedString, dbl_quoted_string, deque, disable_diag, empty, enable_all_warnings, enable_diag, hexnums, identbodychars, identchars, itemgetter, line, lineEnd, lineStart, line_end, line_start, lineno, matchOnlyAtCol, match_only_at_col, nullDebugAction, null_debug_action, nums, os, ppu, printables, punc8bit, pyparsing_unicode, python_quoted_string, quotedString, quoted_string, re, removeQuotes, remove_quotes, replaceWith, replace_with, replaced_by_pep8, sglQuotedString, sgl_quoted_string, srange, str_type, string, stringEnd, stringStart, string_end, string_start, sys, token_map, traceParseAction, trace_parse_action, traceback, types, typing, unicodeString, unicode_string, warnings, withAttribute, withClass, with_attribute, with_class, wraps)  # type: ignore[misc, assignment]
from .core import _builtin_exprs as core_builtin_exprs
from .helpers import _builtin_exprs as helper_builtin_exprs
from .helpers import (ungroup, anyOpenTag, replace_html_entity, dict_of, html_comment, InfixNotationOperatorSpec, java_style_comment, javaStyleComment, countedArray, match_previous_expr, _htmlEntityMap, counted_array, replaceHTMLEntity, one_of, nested_expr, locatedExpr, pythonStyleComment, InfixNotationOperatorArgType, python_style_comment, common_html_entity, delimited_list, html, htmlComment, originalTextFor, dictOf, infixNotation, matchPreviousExpr, any_open_tag, matchPreviousLiteral, match_previous_literal, restOfLine, infix_notation, oneOf, cppStyleComment, makeHTMLTags, dbl_slash_comment, commonHTMLEntity, OpAssoc, _makeTags, makeXMLTags, opAssoc, any_close_tag, cpp_style_comment, indentedBlock, c_style_comment, make_xml_tags, rest_of_line, nestedExpr, make_html_tags, anyCloseTag, delimitedList, original_text_for, dblSlashComment, cStyleComment)  # type: ignore[misc, assignment]
# from .helpers import *

from .unicode import unicode_set, UnicodeRangeList, pyparsing_unicode as unicode
from .testing import pyparsing_test as testing
from .common import (
    pyparsing_common as common,
    _builtin_exprs as common_builtin_exprs,
)

# Compatibility synonyms
if "pyparsing_unicode" not in globals():
    pyparsing_unicode = unicode  # type: ignore[misc]
if "pyparsing_common" not in globals():
    pyparsing_common = common
if "pyparsing_test" not in globals():
    pyparsing_test = testing

core_builtin_exprs += common_builtin_exprs + helper_builtin_exprs


__all__ = [
    "__version__",
    "__version_time__",
    "__author__",
    "__compat__",
    "__diag__",
    "And",
    "AtLineStart",
    "AtStringStart",
    "CaselessKeyword",
    "CaselessLiteral",
    "CharsNotIn",
    "CloseMatch",
    "Combine",
    "DelimitedList",
    "Dict",
    "Each",
    "Empty",
    "FollowedBy",
    "Forward",
    "GoToColumn",
    "Group",
    "IndentedBlock",
    "Keyword",
    "LineEnd",
    "LineStart",
    "Literal",
    "Located",
    "PrecededBy",
    "MatchFirst",
    "NoMatch",
    "NotAny",
    "OneOrMore",
    "OnlyOnce",
    "OpAssoc",
    "Opt",
    "Optional",
    "Or",
    "ParseBaseException",
    "ParseElementEnhance",
    "ParseException",
    "ParseExpression",
    "ParseFatalException",
    "ParseResults",
    "ParseSyntaxException",
    "ParserElement",
    "PositionToken",
    "QuotedString",
    "RecursiveGrammarException",
    "Regex",
    "SkipTo",
    "StringEnd",
    "StringStart",
    "Suppress",
    "Tag",
    "Token",
    "TokenConverter",
    "White",
    "Word",
    "WordEnd",
    "WordStart",
    "ZeroOrMore",
    "Char",
    "alphanums",
    "alphas",
    "alphas8bit",
    "any_close_tag",
    "any_open_tag",
    "autoname_elements",
    "c_style_comment",
    "col",
    "common_html_entity",
    "condition_as_parse_action",
    "counted_array",
    "cpp_style_comment",
    "dbl_quoted_string",
    "dbl_slash_comment",
    "delimited_list",
    "dict_of",
    "empty",
    "hexnums",
    "html_comment",
    "identchars",
    "identbodychars",
    "infix_notation",
    "java_style_comment",
    "line",
    "line_end",
    "line_start",
    "lineno",
    "make_html_tags",
    "make_xml_tags",
    "match_only_at_col",
    "match_previous_expr",
    "match_previous_literal",
    "nested_expr",
    "null_debug_action",
    "nums",
    "one_of",
    "original_text_for",
    "printables",
    "punc8bit",
    "pyparsing_common",
    "pyparsing_test",
    "pyparsing_unicode",
    "python_style_comment",
    "quoted_string",
    "remove_quotes",
    "replace_with",
    "replace_html_entity",
    "rest_of_line",
    "sgl_quoted_string",
    "srange",
    "string_end",
    "string_start",
    "token_map",
    "trace_parse_action",
    "ungroup",
    "unicode_set",
    "unicode_string",
    "with_attribute",
    "with_class",
    # pre-PEP8 compatibility names
    "__versionTime__",
    "anyCloseTag",
    "anyOpenTag",
    "cStyleComment",
    "commonHTMLEntity",
    "conditionAsParseAction",
    "countedArray",
    "cppStyleComment",
    "dblQuotedString",
    "dblSlashComment",
    "delimitedList",
    "dictOf",
    "htmlComment",
    "indentedBlock",
    "infixNotation",
    "javaStyleComment",
    "lineEnd",
    "lineStart",
    "locatedExpr",
    "makeHTMLTags",
    "makeXMLTags",
    "matchOnlyAtCol",
    "matchPreviousExpr",
    "matchPreviousLiteral",
    "nestedExpr",
    "nullDebugAction",
    "oneOf",
    "opAssoc",
    "originalTextFor",
    "pythonStyleComment",
    "quotedString",
    "removeQuotes",
    "replaceHTMLEntity",
    "replaceWith",
    "restOfLine",
    "sglQuotedString",
    "stringEnd",
    "stringStart",
    "tokenMap",
    "traceParseAction",
    "unicodeString",
    "withAttribute",
    "withClass",
    "common",
    "unicode",
    "testing",
]
