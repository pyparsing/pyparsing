========================
Writing doctest examples
========================

Doctest support is provided in Sphinx by the extension
`sphinx.ext.doctest`_, and its documentation is one
useful resurce for working with the pyparsing doctests.

.. _sphinx.ext.doctest: https://www.sphinx-doc.org/en/master/usage/extensions/doctest.html


Types of doctests
=================

There are two basic forms of doctest, and both are used extensively
in the Pyparsing documentation. Which one to use for a given example
is a decision that needs to be made when writing it, but there are
some factors that usually make the correct choice an obvious one.

Doctest type 1: ``testcode`` / ``testoutput`` blocks
----------------------------------------------------

The first form involves one or potentially two separate code blocks.
The ``testcode`` block contains all of the input code in the form of
a standard Python script. This can optionally be paired with a
second ``testoutput`` block, which if present will contain the output
for the preceding ``testcode`` block.

An example of a ``testcode`` / ``testoutput`` pair, from the docstring
for ``ParserElement.__add__``:


.. code-block:: rst

    Example:

    .. testcode::

        greet = Word(alphas) + "," + Word(alphas) + "!"
        hello = "Hello, World!"
        print(hello, "->", greet.parse_string(hello))

    prints:

    .. testoutput::

        Hello, World! -> ['Hello', ',', 'World', '!']

Examples written like this will be formatted in the rendered HTML/Latex/etc.
documentation **exactly** as if they'd been written as normal code blocks.
There is no visible difference between the code above and this code without
doctest support:

.. code-block:: rst

    Example::

        greet = Word(alphas) + "," + Word(alphas) + "!"
        hello = "Hello, World!"
        print(hello, "->", greet.parse_string(hello))

    prints::

        Hello, World! -> ['Hello', ',', 'World', '!']

However, the advantage to writing doctests is that when ``make doctest``
is run from the ``docs/`` directory, the doctest extension will execute
each ``testcode`` block, and verify that its output exactly matches the
``testoutput`` block (if present).

Any deviations will be displayed in "ndiff" format. This enhancement
to the standard unified diff will (sometimes) indicate where in each
line the differences occur. (The character-difference highlighting is
frustratingly inconsistent. But at worst ndiff is equivalent to unified
diff, so it's still worth using.)

Testing examples with doctest allows the code used to demonstrate the
pyparsing API to be verified against the *actual* API as it's currently
implemented, and ensures that examples stay current and relevant.

Not all ``testcode`` blocks need a corresponding ``testoutput`` — if a
``testcode`` block is included on its own, the code inside the block will
still be executed, but its output won't be verified. This can be useful
when displaying code that doesn't require demonstration of its output
(or doesn't output anything), as the extension will still verify that
the code can be run without error.

It's also possible to include a *hidden* ``testoutput`` block, which will
beverified against the preceding ``testcode`` but won't be displayed in the
documentation. To hide a ``testoutput`` block (or a ``testcode`` block,
for that matter), add the ``:hide:`` option as an argument to the
directive, i.e.:

.. code-block:: rst

    .. testoutput::
        :hide:

        """Output that won't be shown, but will be verified against the
        preceding testcode block."""

Doctest type 2: ``doctest`` interactive blocks
----------------------------------------------

The second type of doctest is a ``doctest`` block, which takes the form of
an interactive Python REPL session in standard format (using ``>>>`` and
``...`` markers for input lines).

With these tests, output is interleaved with the code, which can be much
easier to follow when there are multiple lines producing output. If an
example would contains multiple ``print()`` calls, rather than first
displaying all of the code in a ``testcode`` block, then all of the
output in a ``testoutput`` block, consider using a ``doctest`` session
so that the reader can follow along each step as it occurs.

A typical ``doctest`` example can be found in the ``ParserElement.ignore``
docstring:

.. code-block:: rst

    Example:

    .. doctest::

        >>> patt = Word(alphas)[...]
        >>> print(patt.parse_string('ablaj /* comment */ lskjd'))
        ['ablaj']

        >>> patt = Word(alphas)[...].ignore(c_style_comment)
        >>> print(patt.parse_string('ablaj /* comment */ lskjd'))
        ['ablaj', 'lskjd']


Setup code for doctest blocks
=============================

The doctest extension is configured with extensive setup code
which is run before each test block. It can be viewed in the
:download:`docs/conf.py <../docs/conf.py>` file — look for the
``doctest_global_setup`` variable near the end of the file.

The setup code is intended to make any useful symbols available
to the tests without them having to be included in each and every
doctest block. If additional modules are needed, feel free to add
them to the global setup. When writing doctests, Pyparsing classes
can be invoked directly, or as members of the ``pp`` alias namespace.
Either way, the definition of those symbols can be assumed without
explicitly importing/defining them.

When using symbols from other aliased namespaces, however, it's a
good idea to establish the alias for the reader at the start of the
example code. Even though these are both defined in the global setup,
showing the establishing lines before referencing ``ppc`` or ``ppu``
in an example makes that example clearer:

.. code-block: py

    ppc = pp.pyparsing_common
    ppu = pp.pyparsing_unicode

However, because those symbols *are* provided by default, they don't
need to be explicitly established for **every** example. Feel free
to omit them after the first use, when writing multiple examples for
a given class or function.

Documenting exceptions
======================

Code that will trigger an exception can be both demonstrated and
verified using doctests (of either type), although when a ``testoutput``
block will demonstrate an exception it should be the only output in
that block — doctest does not support mixing regular output and
exceptions.

Both the ``IGNORE_EXCEPTION_DETAIL`` and ``ELLIPSIS`` doctest options
are enabled by default, which make demonstrating exceptions far more
convenient. Ignoring exception detail means that the full traceback
for an exception can be omitted, as well as the fully-qualified name
of the exception class. As long as the ``Traceback...`` line and the
exception class name match, the doctest will pass. (The exception
message is also verified by default, but read on for more about that.)

This example code, from the ``ParserElement.set_name`` docstring, will
actually output a long traceback, followed by an exception of type
``pyparsing.exceptions.ParseException``. But because the ignore-detail
option is enabled, the doctest will pass with this abbreviated form:

.. code-block:: rst

    .. doctest::

        >>> integer = Word(nums)
        >>> integer.parse_string("ABC")
        Traceback (most recent call last):
        ParseException: Expected W:(0-9) (at char 0), (line:1, col:1)

Relaxing doctest output validation
==================================

For even more flexibility in demonstrating output, the ``ELLIPSIS``
option (enabled by default) means that parts of the output can be
replaced with an ellipsis (three periods, ``...``) which will validate
against any output.

This is an extremely useful tool when the exact output of the code is
unpredictable (for example, when messages include line and column
numbers, or variable data like the current date or a directory path).
The code above could also be written like this, and it would still
pass the doctest:

.. code-block:: rst

    .. doctest::

        >>> integer = Word(nums)
        >>> integer.parse_string("ABC")
        Traceback (most recent call last):
        ParseException: Expected W:(0-9) ...

While this is necessary in some situations, it shouldn't be overused.
The more precisely a doctest validates the output of its example,
the more useful it is, so think twice before employing an ellipsis in
doctest output.

Normalizing whitespace checks
=============================

Another method of relaxing doctest checks that doesn't impact the
test's ability to validate output is the ``NORMALIZE_WHITESPACE``
option. This option isn't enabled by default, but can be turned on
for any doctest block with a directive argument:

.. code-block::  rst

    .. testoutput::
        :options: +NORMALIZE_WHITESPACE

(Note the preceding ``+`` sign, which adds the option to the default
set instead of replacing the default options.)

With normalization activated, any combination of spaces, tabs, and
newlines will compare equal to any other combination.

One advantage this has is permitting long messages to be wrapped
over several lines in the example output. In this example from the
``Keyword`` class docstring, the exception message at the end would
normally be printed as one long line. To make the example readable
without excessive horizontal scrolling, ``NORMALIZE_WHITESPACE``
allows the example output to be broken into multiple lines:

.. code-block:: rst

    .. doctest::
        :options: +NORMALIZE_WHITESPACE

        >>> Keyword("start").parse_string("start")
        ParseResults(['start'], {})
        >>> Keyword("start").parse_string("starting")
        Traceback (most recent call last):
        ParseException: Expected Keyword 'start',
        keyword was immediately followed by keyword character,
        found 'ing'  (at char 5), (line:1, col:6)

Doctests in the Pyparsing codebase
==================================

While the preceding is generally applicable to doctests in any
codebase, there are some issues specific to Pyparsing doctests that
you should be aware of.

``run_tests()`` output
----------------------

There is one scenario in the pyparsing documentation where the
``NORMALIZE_WHITESPACE`` option *must* be used.

When the example code uses the ``ParserElement.run_tests()`` method,
the output will consist of test strings and matches potentially
separated by two blank lines each. (Unless each test is preceded
by a comment, then there will be only one blank line.)

Since ReStructuredText will collapse multiple blank lines in embedded
code, the only way to get the ``run_tests`` output to validate against
the example is to enable ``NORMALIZE_WHITESPACE`` and collapse the
multiple blank lines in the expected output, as well.

Also, "any whitespace compares equal" doesn't mean that *no*
whitespace will be accepted, so the beginning of the ``testoutput``
block MUST include an extra blank line at the start, in order
to match the leading 2 (or 1) blank lines in the output.

So, a valid ``run_tests`` output block consists of the ``testoutput``
directive, the ``:options: +NORMALIZE_WHITESPACE`` argument, then
**TWO blank lines** followed by the output to be verified. This
example, from the ``ParserElement.run_tests`` docstring itself,
demonstrates the required format:

.. code-block:: rst
    :linenos:
    :emphasize-lines: 17,21,22,26,27

    Failing example:

    .. testcode::

        number_expr = pyparsing_common.number.copy()
        result = number_expr.run_tests('''
            100Z
            3.14.159
            ''', failure_tests=True)
        print("Success" if result[0] else "Failed!")

    prints:

    .. testoutput::
        :options: +NORMALIZE_WHITESPACE


        100Z
        100Z
        ^
        ParseException: Expected end of text, found 'Z' ...

        3.14.159
        3.14.159
            ^
        ParseException: Expected end of text, found '.' ...
        FAIL: Expected end of text, found '.' ...
        Success

Note in particular:

- The extra blank line (line 17) before the first line of output, which
  is required to match the *two* blank lines in the actual output.

- Only one blank line (line 22) separating the two tests' output.
  The real output will again contain two blank lines.

- The use of ellipses to abbreviate the expected output (lines 21, 26, 27).

- Exception messages mixed with normal output.

  In this case that presents no problems, because ``run_tests()`` catches
  any exceptions generated and prints their messages as normal output.
  Doctest has no restrictions on normal output, only when the exception
  is raised and a traceback is triggered.

  By the same token, ``IGNORE_EXCEPTION_DETAIL`` is not applicable here
  (there are no exceptions in the expected string, only regular output),
  so the normal string-matching rules apply when comparing expected output
  to actual output.

Two final notes about failing doctests
--------------------------------------

There are two things to watch out for, when attempting to address
doctest failures during a ``make doctest`` run.

Code location references are not useful
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Due to the uncommon structure of the pyparsing namespace (with the
symbols from all of the package's files imported into the top-level
``pyparsing`` namespace, and documented there rather than at their
"home" locations where they're defined), the doctest output for
failing test will not display the correct source location for the
code. Every failing test will be preceded by a reference similar to:

.. code-block::

    File "../pyparsing/core.py", line ?, in default

However, this will be followed by a listing of the code that
produced the failing test. So as long as we write examples
which are not too generic and are sufficiently distinct from
each other (which is good practice anyway), it should be easy
enough to find the failing code.

Diffs on failing tests will include *ALL* differences
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When ``doctest`` displays the NDIFF-format differences between the
expected output and the actual output, it will indicate **EVERY**
difference between them — even the differences that would otherwise
be ignored. The ``IGNORE_TRACEBACK_DETAILS``, ``ELLIPSIS``, and
``NORMALIZE_WHITESPACE`` options do not apply when NDIFF is generating
the comparison ouput for a failed test.

What this means is that, even though the NDIFF flags an ellipsized
section of text as a difference from the actual output, or marks a
difference where an output line has been split into two when the
``NORMALIZE_WHITESPACE`` option is enabled, those differences WILL be
ignored when the doctest is in a passing state. It's important to
focus on the differences that *wouldn't* otherwise be ignored, and
just trust that correcting those differences will result in a passing
test.

For example, consider this failing test:

.. code-block:: shell-session
    :linenos:
    :emphasize-lines: 20-23

    $ make doctest
    ...
    File "../pyparsing/core.py", line ?, in default
    Failed example:
        data_word = Word(alphas)
        label = data_word + FollowedBy(':')

        attr_expr = (
            label + Suppress(':')
            + OneOrMore(data_word, stop_on=label
        ).set_parse_action(' '.join))

        print(attr_expr.parse_string("color: RED"))

        text = "shape: SQUARE posn: upper left color: light blue texture: burlap"

        # print attributes as plain groups
        print(attr_expr[1, ...].parse_string(text))
    Differences (ndiff with -expected +actual):
        - ['color', "RED"]
        ?           ^   ^
        + ['color', 'RED']
        ?           ^   ^
        + ['shape', 'SQUARE', 'posn', 'upper left', 'color', 'light blue', 'texture', 'burlap']
        - ['shape', 'SQUARE',
        - ... 'texture', 'burlap']
    **********************************************************************
    1 item had failures:
       1 of 208 in default
    208 tests in 1 item.
    207 passed and 1 failed.
    ***Test Failed*** 1 failure.

The **only** significant difference is the highlighted one: The wrong
quotes used around the word ``"RED"`` in the expected output. Once that's
changed to ``'RED'``, the doctest will pass. The remaining diff line(s),
where the expected output uses an ellipsis and is split over two lines
(with ``NORMALIZE_WHITESPACE`` enabled), will not fail despite being
shown as differing from the actual output. (Technically it *does* differ,
after all. The configuration simply ignores that difference.)
