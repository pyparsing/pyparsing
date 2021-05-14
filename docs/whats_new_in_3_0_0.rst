=============================
What's New in Pyparsing 3.0.0
=============================

:author: Paul McGuire

:date: December, 2020

:abstract: This document summarizes the changes made
    in the 3.0.0 release of pyparsing.

.. sectnum::    :depth: 4

.. contents::   :depth: 4


New Features
============

Railroad diagramming
--------------------
An excellent new enhancement is the new railroad diagram
generator for documenting pyparsing parsers. You need to install
`Railroad-Diagram Generator package` https://pypi.org/project/railroad-diagrams/ to test this example::

    import pyparsing as pp

    # define a simple grammar for parsing street addresses such
    # as "123 Main Street"
    #     number word...
    number = pp.Word(pp.nums).setName("number")
    name = pp.Word(pp.alphas).setName("word")[1, ...]

    parser = number("house_number") + name("street")
    parser.setName("street address")

    # construct railroad track diagram for this parser and
    # save as HTML
    parser.create_diagram('parser_rr_diag.html')

(Contributed by Michael Milton)

Refactored/added diagnostic flags
---------------------------------
Expanded ``__diag__`` and ``__compat__`` to actual classes instead of
just namespaces, to add some helpful behavior:

- ``pyparsing.enable_diag()`` and ``pyparsing.disable_diag()`` methods to give extra
  help when setting or clearing flags (detects invalid
  flag names, detects when trying to set a ``__compat__`` flag
  that is no longer settable). Use these methods now to
  set or clear flags, instead of directly setting to ``True`` or
  ``False``::

        import pyparsing as pp
        pp.enable_diag(pp.Diagnostics.warn_multiple_tokens_in_named_alternation)

- ``pyparsing.enable_all_warnings()`` is another helper that sets
  all "warn*" diagnostics to ``True``::

        pp.enable_all_warnings()

- added new warning, ``warn_on_match_first_with_lshift_operator`` to
  warn when using ``'<<'`` with a ``'|'`` ``MatchFirst`` operator,
  which will
  create an unintended expression due to precedence of operations.

  Example: This statement will erroneously define the ``fwd`` expression
  as just ``expr_a``, even though ``expr_a | expr_b`` was intended,
  since ``'<<'`` operator has precedence over ``'|'``::

      fwd << expr_a | expr_b

  To correct this, use the ``'<<='`` operator (preferred) or parentheses
  to override operator precedence::

        fwd <<= expr_a | expr_b

  or::

        fwd << (expr_a | expr_b)

- ``warn_on_parse_using_empty_Forward`` - warns that a ``Forward``
  has been included in a grammar, but no expression was
  attached to it using ``'<<='`` or ``'<<'``

- ``warn_on_assignment_to_Forward`` - warns that a ``Forward`` has
  been created, but was probably later overwritten by
  erroneously using ``'='`` instead of ``'<<='`` (this is a common
  mistake when using Forwards)
  (**currently not working on PyPy**)

New Located class to replace locatedExpr helper method
------------------------------------------------------
The new ``Located`` class will replace the current ``locatedExpr`` method for
marking parsed results with the start and end locations of the parsed data in
the input string.  ``locatedExpr`` had several bugs, and returned its results
in a hard-to-use format (location data and results names were mixed in with
the located expression's parsed results, and wrapped in an unnecessary extra
nesting level).

For this code::

        wd = Word(alphas)
        for match in locatedExpr(wd).searchString("ljsdf123lksdjjf123lkkjj1222"):
            print(match)

the docs for ``locaatedExpr`` show this output::

        [[0, 'ljsdf', 5]]
        [[8, 'lksdjjf', 15]]
        [[18, 'lkkjj', 23]]

The parsed values and the start and end locations are merged into a single
nested ParseResults (and any results names in the parsed values are also
merged in with the start and end location names).

Using ``Located``, the output is::

        [0, ['ljsdf'], 5]
        [8, ['lksdjjf'], 15]
        [18, ['lkkjj'], 23]

With ``Located``, the parsed expression values and results names are kept
separate in the second parsed value, and there is no extra grouping level
on the whole result.

The existing ``locatedExpr`` is retained for backward-compatibility, but will be
deprecated in a future release.

New IndentedBlock class to replace indentedBlock helper method
--------------------------------------------------------------
The new ``IndentedBlock`` class will replace the current ``indentedBlock`` method
for defining indented blocks of text, similar to Python source code. Using
``IndentedBlock``, the expression instance itself keeps track of the indent stack,
so a separate external ``indentStack`` variable is no longer required.

Here is a simple example of an expression containing an alphabetic key, followed
by an indented list of integers::

    integer = pp.Word(pp.nums)
    group = pp.Group(pp.Char(pp.alphas) + pp.Group(pp.IndentedBlock(integer)))

parses::

    A
        100
        101
    B
        200
        201

as::

    [['A', [100, 101]], ['B', [200, 201]]]

``IndentedBlock`` may also be used to define a recursive indented block (containing nested
indented blocks).

The existing ``indentedBlock`` is retained for backward-compatibility, but will be
deprecated in a future release.

Shortened tracebacks
--------------------
Cleaned up default tracebacks when getting a ``ParseException`` when calling
``parseString``. Exception traces should now stop at the call in ``parseString``,
and not include the internal pyparsing traceback frames. (If the full traceback
is desired, then set ``ParserElement.verbose_traceback`` to ``True``.)

Improved debug logging
----------------------
Debug logging has been improved by:

- Including try/match/fail logging when getting results from the
  packrat cache (previously cache hits did not show debug logging).
  Values returned from the packrat cache are marked with an '*'.

- Improved fail logging, showing the failed text line and marker where
  the failure occurred.

New / improved examples
-----------------------
- ``number_words.py`` includes a parser/evaluator to parse "forty-two"
  and return 42. Also includes example code to generate a railroad
  diagram for this parser.

- ``BigQueryViewParser.py`` added to examples directory, submitted
  by Michael Smedberg.

- ``booleansearchparser.py`` added to examples directory, submitted
  by xecgr. Builds on searchparser.py, adding support for '*'
  wildcards and non-Western alphabets.

- Improvements in ``select_parser.py``, to include new SQL syntax
  from SQLite, submitted by Robert Coup.

- Off-by-one bug found in the ``roman_numerals.py`` example, a bug
  that has been there for about 14 years! Submitted by
  Jay Pedersen.

- A simplified Lua parser has been added to the examples
  (``lua_parser.py``).

- Fixed bug in ``delta_time.py`` example, when using a quantity
  of seconds/minutes/hours/days > 999.

Other new features
------------------
- Enhanced default strings created for Word expressions, now showing
  string ranges if possible. ``Word(alphas)`` would formerly
  print as ``W:(ABCD...)``, now prints as ``W:(A-Za-z)``.

- Added ``ignoreWhitespace(recurse:bool = True)`` and added a
  ``recurse`` argument to ``leaveWhitespace``, both added to provide finer
  control over pyparsing's whitespace skipping. Contributed by
  Michael Milton.

- Added ``ParserElement.recurse()`` method to make it simpler for
  grammar utilities to navigate through the tree of expressions in
  a pyparsing grammar.

- The ``repr()`` string for ``ParseResults`` is now of the form::

    ParseResults([tokens], {named_results})

  The previous form omitted the leading ``ParseResults`` class name,
  and was easily misinterpreted as a ``tuple`` containing a ``list`` and
  a ``dict``.

- Minor reformatting of output from ``runTests`` to make embedded
  comments more visible.

- New ``pyparsing_test`` namespace, assert methods and classes added to support writing
  unit tests.

  - ``assertParseResultsEquals``
  - ``assertParseAndCheckList``
  - ``assertParseAndCheckDict``
  - ``assertRunTestResults``
  - ``assertRaisesParseException``
  - ``reset_pyparsing_context`` context manager, to restore pyparsing
    config settings

- Enhanced error messages and error locations when parsing fails on
  the ``Keyword`` or ``CaselessKeyword`` classes due to the presence of a
  preceding or trailing keyword character.

- Enhanced the ``Regex`` class to be compatible with re's compiled with the
  re-equivalent ``regex`` module. Individual expressions can be built with
  regex compiled expressions using::

    import pyparsing as pp
    import regex

    # would use regex for this expression
    integer_parser = pp.Regex(regex.compile(r'\d+'))

- Fixed handling of ``ParseSyntaxExceptions`` raised as part of ``Each``
  expressions, when sub-expressions contain ``'-'`` backtrack
  suppression.

- Potential performance enhancement when parsing ``Word``
  expressions built from ``pyparsing_unicode`` character sets. ``Word`` now
  internally converts ranges of consecutive characters to regex
  character ranges (converting "0123456789" to "0-9" for instance).


API Changes
===========

- ``enable_diag()`` and ``disable_diag()`` methods to
  enable specific diagnostic values (instead of setting them
  to ``True`` or ``False``). ``enable_all_warnings()`` has
  also been added.

- ``countedArray`` formerly returned its list of items nested
  within another list, so that accessing the items required
  indexing the 0'th element to get the actual list. This
  extra nesting has been removed. In addition, if there are
  other metadata fields parsed between the count and the
  list items, they can be preserved in the resulting list
  if given results names.

- ``ParseException.explain()`` is now an instance method of
  ``ParseException``::

        expr = pp.Word(pp.nums) * 3
        try:
            expr.parseString("123 456 A789")
        except pp.ParseException as pe:
            print(pe.explain(depth=0))

  prints::

        123 456 A789
                ^
        ParseException: Expected W:(0-9), found 'A'  (at char 8), (line:1, col:9)

  To run explain against other exceptions, use
  ``ParseException.explain_exception()``.

- Debug actions now take an added keyword argument ``cache_hit``.
  Now that debug actions are called for expressions matched in the
  packrat parsing cache, debug actions are now called with this extra
  flag, set to True. For custom debug actions, it is necessary to add
  support for this new argument.

- ``ZeroOrMore`` expressions that have results names will now
  include empty lists for their name if no matches are found.
  Previously, no named result would be present. Code that tested
  for the presence of any expressions using ``"if name in results:"``
  will now always return ``True``. This code will need to change to
  ``"if name in results and results[name]:"`` or just
  ``"if results[name]:"``. Also, any parser unit tests that check the
  ``asDict()`` contents will now see additional entries for parsers
  having named ``ZeroOrMore`` expressions, whose values will be ``[]``.

- ``ParserElement.setDefaultWhitespaceChars`` will now update
  whitespace characters on all built-in expressions defined
  in the pyparsing module.


Discontinued Features
=====================

Python 2.x no longer supported
------------------------------
Removed Py2.x support and other deprecated features. Pyparsing
now requires Python 3.5 or later. If you are using an earlier
version of Python, you must use a Pyparsing 2.4.x version.

Other discontinued features
---------------------------
- ``ParseResults.asXML()`` - if used for debugging, switch
  to using ``ParseResults.dump()``; if used for data transfer,
  use ``ParseResults.asDict()`` to convert to a nested Python
  dict, which can then be converted to XML or JSON or
  other transfer format

- ``operatorPrecedence`` synonym for ``infixNotation`` -
  convert to calling ``infixNotation``

- ``commaSeparatedList`` - convert to using
  ``pyparsing_common.comma_separated_list``

- ``upcaseTokens`` and ``downcaseTokens`` - convert to using
  ``pyparsing_common.upcaseTokens`` and ``downcaseTokens``

- ``__compat__.collect_all_And_tokens`` will not be settable to
  ``False`` to revert to pre-2.3.1 results name behavior -
  review use of names for ``MatchFirst`` and Or expressions
  containing ``And`` expressions, as they will return the
  complete list of parsed tokens, not just the first one.
  Use ``pyparsing.enable_diag(pyparsing.Diagnostics.warn_multiple_tokens_in_named_alternation)``
  to help identify those expressions in your parsers that
  will have changed as a result.

- Removed support for running ``python setup.py test``. The setuptools
  maintainers consider the ``test`` command deprecated (see
  <https://github.com/pypa/setuptools/issues/1684>). To run the Pyparsing tests,
  use the command ``tox``.


Fixed Bugs
==========

- Fixed bug in regex definitions for ``real`` and ``sci_real`` expressions in
  ``pyparsing_common``.

- Fixed ``FutureWarning`` raised beginning in Python 3.7 for ``Regex`` expressions
  containing '[' within a regex set.

- Fixed bug in ``PrecededBy`` which caused infinite recursion.

- Fixed bug in ``CloseMatch`` where end location was incorrectly
  computed; and updated ``partial_gene_match.py`` example.

- Fixed bug in ``indentedBlock`` with a parser using two different
  types of nested indented blocks with different indent values,
  but sharing the same indent stack.

- Fixed bug in ``Each`` when using ``Regex``, when ``Regex`` expression would
  get parsed twice.

- Fixed ``FutureWarning`` that sometimes is raised when ``'['`` passed as a
  character to ``Word``.

- Fixed debug logging to show failure location after whitespace skipping.


Acknowledgments
===============
And finally, many thanks to those who helped in the restructuring
of the pyparsing code base as part of this release. Pyparsing now
has more standard package structure, more standard unit tests,
and more standard code formatting (using black). Special thanks
to jdufresne, klahnakoski, mattcarmody, and ckeygusuz,
tmiguelt, and toonarmycaptain to name just a few.
