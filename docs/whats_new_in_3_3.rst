=============================
What's New in Pyparsing 3.3.x
=============================

:author: Paul McGuire

:date: November, 2025

:abstract: This document summarizes the changes made
    in the 3.3.x releases of pyparsing.

.. contents::   :depth: 4


Supported Python versions
=========================

- Python 3.9 or later is required.

- All unit tests pass with Python 3.14, including the free-threaded build ("3.14t").
  Note: this does not imply that pyparsing is thread-safe; the tests simply
  validate that the library runs without errors under the free-threaded
  interpreter. The test suite does not exercise parsing across multiple
  threads.


New Features
============

- Added AI best-practices guidance for using pyparsing to implement parsers.
  The guidance is stored in ``pyparsing/ai/best_practices.md`` and can be accessed
  programmatically via ``pyparsing.show_best_practices()`` or from the command line
  using ``python -m pyparsing.ai.show_best_practices`` (after installing the
  ``pyparsing`` package).

- Added performance benchmarking tools and documentation:

  - ``tests/perf_pyparsing.py`` runs a suite of benchmarks that exercise different
    parts of the pyparsing library. The script can export results as CSV and append
    to a consolidated data file for cross-version analysis.

  - Runner scripts ``run_perf_all_tags.bat`` (Windows) and ``run_perf_all_tags.sh``
    (Ubuntu/bash) execute the benchmarks across multiple Python versions (3.9–3.14)
    and pyparsing versions (3.1.1 through 3.3.0), aggregating results into
    ``perf_pyparsing.csv`` at the repo root. See ``tests/README.md`` for usage.

- Improved exception formatting robustness: added exception handling around
  ``formatted_message()`` to ensure ``str(exception)`` always returns at least
  some message content, even if formatting fails.


API Changes
===========

Planned deprecations and guidance for migration
-----------------------------------------------

- Beginning with 3.3.0, pyparsing emits ``DeprecationWarning`` for many pre-PEP8
  method names (for example, ``ParserElement.parseString``). The PEP8-compliant
  names were introduced in 3.0.0 (August 2021); the legacy names remain as aliases
  but are planned to be removed in pyparsing 4.0 (no earlier than 2026).

- A utility script was added in 3.2.2 to help migrate code to PEP8-compliant
  names: ``pyparsing/tools/cvt_pyparsing_pep8_names.py``. Run it on one or more
  files; use ``-u`` to update files in place. Example:

  ::

      python -m pyparsing.tools.cvt_pyparsing_pep8_names -u examples/*.py

- Specific deprecations with behavior notes:

  - ``indentedBlock``: When converted using the migration utility, a ``UserWarning``
    is emitted indicating that additional code changes are required. The replacement
    class ``IndentedBlock`` no longer requires passing an external indent stack, and
    it adds support for nested indentation levels and grouping.

  - ``locatedExpr``: When converted using the migration utility, a ``UserWarning``
    is emitted indicating that code changes may be required. The PEP8 replacement
    ``Located`` removes an extra grouping layer from parsed values. If the original
    ``locatedExpr`` was given a results name, the grouping is retained so that the
    results-name nesting remains consistent; in that case, no code changes should be
    required.


Discontinued Features
=====================

- No removals in 3.3.x; however, pre-PEP8 names are now formally deprecated and
  scheduled for removal in 4.0.


Fixed Bugs
==========

- Fixed minor formatting issues in ``pyparsing.testing.with_line_numbers`` discovered
  while developing the TINY language example.

- ``DelimitedList`` and ``nested_expr`` now auto-suppress delimiting commas when the
  delimiter is already a ``Suppress``; this avoids the need for extra wrapping.


New / Enhanced Examples
=======================

- Implemented a TINY language parser and interpreter under ``examples/tiny``. The
  example demonstrates a recommended structure (parser + AST + engine + run) for
  building a small interpreter with pyparsing. The ``docs`` subdirectory includes
  transcripts of the AI session used to create the parser and interpreter.

- Added railroad diagrams for selected examples.


Acknowledgments
===============
Again, thanks to the many contributors who submitted issues, questions, suggestions,
and PRs.
