=============================
What's New in Pyparsing 3.0.0
=============================

:author: Paul McGuire

:date: June, 2020

:abstract: This document summarizes the changes made
    in the 3.0.0 release of pyparsing.

.. sectnum::    :depth: 4

.. contents::   :depth: 4


New Features
============

Railroad diagramming
--------------------
An excellent new enhancement is the new railroad diagram
generator for documenting pyparsing parsers::

    import pyparsing as pp
    from pyparsing.diagram import to_railroad, railroad_to_html
    from pathlib import Path

    # define a simple grammar for parsing street addresses such
    # as "123 Main Street"
    #     number word...
    number = pp.Word(pp.nums).setName("number")
    name = pp.Word(pp.alphas).setName("word")[1, ...]

    parser = number("house_number") + name("street")
    parser.setName("street address")

    # construct railroad track diagram for this parser and
    # save as HTML
    rr = to_railroad(parser)
    Path('parser_rr_diag.html').write_text(railroad_to_html(rr))

(Contributed by Michael Milton)

Shortened tracebacks
--------------------
Cleaned up default tracebacks when getting a ``ParseException`` when calling
``parseString``. Exception traces should now stop at the call in ``parseString``,
and not include the internal traceback frames. (If the full traceback
is desired, then set ``ParserElement.verbose_traceback`` to ``True``.)

Refactored/added diagnostic flags
---------------------------------
Expanded ``__diag__`` and ``__compat__`` to actual classes instead of
just namespaces, to add some helpful behavior:

- ``enable()`` and ``disable()`` methods to give extra
  help when setting or clearing flags (detects invalid
  flag names, detects when trying to set a ``__compat__`` flag
  that is no longer settable). Use these methods now to
  set or clear flags, instead of directly setting to ``True`` or
  ``False``::

        import pyparsing as pp
        pp.__diag__.enable("warn_multiple_tokens_in_named_alternation")

- ``__diag__.enable_all_warnings()`` is another helper that sets
  all "warn*" diagnostics to ``True``::

        pp.__diag__.enable_all_warnings()

- added new warning, ``"warn_on_match_first_with_lshift_operator"`` to
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

- ``"warn_on_parse_using_empty_Forward"`` - warns that a ``Forward``
  has been included in a grammar, but no expression was
  attached to it using ``'<<='`` or ``'<<'``

- ``"warn_on_assignment_to_Forward"`` - warns that a ``Forward`` has
  been created, but was probably later overwritten by
  erroneously using ``'='`` instead of ``'<<='`` (this is a common
  mistake when using Forwards)
  (**currently not working on PyPy**)

New / improved examples
-----------------------
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

- ``__diag__`` now uses ``enable()`` and ``disable()`` methods to
  enable specific diagnostic values (instead of setting them
  to ``True`` or ``False``). ``__diag__.enable_all_warnings()`` has
  also been added.


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
  Use ``__diag__.warn_multiple_tokens_in_named_alternation``
  to help identify those expressions in your parsers that
  will have changed as a result.

- Removed support for running ``python setup.py test``. The setuptools
  maintainers consider the ``test`` command deprecated (see
  <https://github.com/pypa/setuptools/issues/1684>). To run the Pyparsing test,
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

- Fixed ``FutureWarning`` that sometimes are raised when ``'['`` passed as a
  character to ``Word``.


Acknowledgments
===============
And finally, many thanks to those who helped in the restructuring
of the pyparsing code base as part of this release. Pyparsing now
has more standard package structure, more standard unit tests,
and more standard code formatting (using black). Special thanks
to jdufresne, klahnakoski, mattcarmody, and ckeygusuz,
tmiguelt, and toonarmycaptain to name just
a few.
