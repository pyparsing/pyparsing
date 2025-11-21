import textwrap

import pytest

import pyparsing as pp
ppt = pp.testing

TAB = chr(9)

@pytest.mark.parametrize(
    "source, options, expected",
    [
        # simple call to with_line_numbers
        ("abcd", {},
         textwrap.dedent(
             """\
                        1
               1234567890
             1:abcd|
             """),
         ),

        # simple call to with_line_numbers with empty string
        ("", {}, ""),

        # simple call to with_line_numbers with single blank line
        ("\n", {}, '  \n  \n1:|\n'),

        # simple call to with_line_numbers with line longer than 99 chars
        ("abcdefghij" * 11, {},
         textwrap.indent(
         textwrap.dedent(
             """\
                                                                                                       1
             1         2         3         4         5         6         7         8         9         0         1
    12345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890
  1:abcdefghijabcdefghijabcdefghijabcdefghijabcdefghijabcdefghijabcdefghijabcdefghijabcdefghijabcdefghijabcdefghij|
             """),
          "  ")),

        # add indent = "...."
        ("abcd", {"indent": "...."},
         textwrap.dedent(
             """\
             ....           1
             ....  1234567890
             ....1:abcd|
             """),
         ),

        # show control characters as ?
        ("ab\tc\ad", {"mark_control": "?"},
         textwrap.indent(
         textwrap.dedent(
             f"""\
                        1         2
               12345678901234567890
             1:ab      c?d|
             """)
         , " "),
        ),

        # show control characters as ?
        ("ab\tc\ad", {"mark_control": "?", "expand_tabs": False},
         textwrap.dedent(
             f"""\
                        1
               1234567890
             1:ab?c?d|
             """)
        ),

        # show control characters as unicode
        ("ab\tc\ad", {"mark_control": "unicode"},
         textwrap.indent(
         textwrap.dedent(
             f"""\
                        1         2
               12345678901234567890
             1:ab␠␠␠␠␠␠c␇d␊
             """)
         , " "),
         ),

        # show space characters as "`"
        ("ab\tc  d", {"mark_spaces": "`", "expand_tabs": False},
         textwrap.dedent(
             f"""\
                       1
              1234567890
            1:ab\tc``d|
            """)
         ),

        # show space characters as unicode
        ("ab\tc\ad", {"mark_spaces": "unicode", "expand_tabs": False},
         textwrap.dedent(
             f"""\
                       1
              1234567890
            1:ab␉c\ad|
            """)
         ),
    ]
)
def test_with_line_numbers(source: str, options: dict, expected: str):
    observed = ppt.with_line_numbers(source, **options)
    print()
    print(observed)
    assert observed == expected
