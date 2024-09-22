import pytest
from typing import Union, Iterable
import pyparsing as pp
import itertools
import collections


@pytest.mark.parametrize(
    "test_label, input_list, expected_output",
    [
        ("Empty list", [], []),
        ("Flat list", [1, 2, 3], [1, 2, 3]),
        ("Nested list", [[1, 2], [3, 4]], [1, 2, 3, 4]),
        ("Mixed list with single values and lists", [1, [2, 3], 4], [1, 2, 3, 4]),
        ("Deeper nested lists", [1, [2, [3, 4]], 5], [1, 2, 3, 4, 5]),
        ("Deeper nesting with sublists", [[[1], 2], [3]], [1, 2, 3]),
        ("Mixed empty and non-empty nested lists", [[], [1], [2, [3]], [[4, 5]]], [1, 2, 3, 4, 5]),
        ("Deeply nested empty lists", [[[[]]]], []),
        ("Mixed empty lists and non-empty elements", [1, [], 2, [3, []]], [1, 2, 3]),
        ("ParseResults instead of lists", [pp.ParseResults([1, 2]), pp.ParseResults([3, 4])], [1, 2, 3, 4]),
        ("ParseResults with mixed types", [1, pp.ParseResults([2, 3]), 4], [1, 2, 3, 4]),
        ("Nested ParseResults", [pp.ParseResults([1, pp.ParseResults([2, 3])]), 4], [1, 2, 3, 4]),
        ("Empty ParseResults", [pp.ParseResults([]), 1, pp.ParseResults([2, 3])], [1, 2, 3]),
    ]
)
def test_flatten(test_label, input_list, expected_output):
    from pyparsing.util import _flatten

    """Test flatten with various inputs."""
    print(test_label)
    assert _flatten(input_list) == expected_output


@pytest.mark.parametrize(
    "test_label, input_string, re_escape, expected_output",
    [
        ("Empty string", "", True, ""),
        ("Single character", "a", True, "a"),
        ("Two consecutive characters", "ab", True, "ab"),
        ("Two non-consecutive characters", "az", True, "az"),
        ("Three consecutive characters", "abcg", True, "a-cg"),
        ("Full consecutive alphabet", "abcdefghijklmnopqrstuvwxyz", True, "a-z"),
        ("Consecutive characters with special regex chars", "^-]", True, r"\-\]\^"),
        ("Consecutive characters without escaping", "^-]", False, "-]^"),
        ("Mixed consecutive and non-consecutive", "abcxyz", True, "a-cx-z"),
        ("Reversed order input", "cba", True, "a-c"),
        ("Characters with duplicates", "aaxxxddddbbcc", True, "a-dx"),
        ("Non-alphabetic consecutive characters", "012345", True, "0-5"),
        ("Non-alphabetic mixed characters", "@05", True, "05@"),
        ("Non-alphabetic, non-consecutive characters", "02", True, "02"),
        ("Verify range ending with '-' creates valid regex", "*+,-", True, r"*-\-"),
        ("Verify range ending with ']' creates valid regex", r"WXYZ[\]", True, r"W-\]"),
        ("Verify range starting with '^' creates valid regex", "^_`a", True, r"\^-a"),
    ]
)
def test_collapse_string_to_ranges(test_label: str, input_string: Union[str, Iterable[str]], re_escape: bool, expected_output: str):
    """Test collapsing a string into character ranges with and without regex escaping."""
    from pyparsing.util import _collapse_string_to_ranges
    from random import random
    import re

    print(test_label)

    collapsed = _collapse_string_to_ranges(input_string, re_escape)
    print(f"{input_string!r} -> {collapsed!r}")
    assert collapsed == expected_output

    if input_string:
        # assert that this can be used as a valid regex range string
        if re_escape:
            collapsed_re = re.compile(f"[{collapsed}]+")
            match = collapsed_re.match(input_string)
            print(f"re.match:'{collapsed_re.pattern}' -> {match and match[0]!r}")
            assert match is not None and match[0] == input_string

        # for added coverage, randomly shuffle input string
        shuffled = "".join(sorted(list(input_string), key=lambda _: random()))
        collapsed = _collapse_string_to_ranges(shuffled, re_escape)
        print(f"{shuffled!r} -> {collapsed!r}")
        assert collapsed == expected_output

    print()

@pytest.mark.parametrize(
    "test_label, loc, strg, expected_output",
    [
        ("First column, no newline", 0, "abcdef", 1),
        ("Second column, no newline", 1, "abcdef", 2),
        ("First column after newline", 4, "abc\ndef", 1),
        ("Second column after newline", 5, "abc\ndef", 2),
        ("Column after multiple newlines", 9, "abc\ndef\nghi", 2),
        ("Location at start of string", 0, "abcdef", 1),
        ("Location at end of string", 5, "abcdef", 6),
        ("Column after newline at end", 3, "abc\n", 4),
        ("Tab character in the string", 4, "a\tbcd\tef", 5),
        ("Multiple lines with tab", 8, "a\tb\nc\td", 5),
    ]
)
def test_col(test_label, loc, strg, expected_output):
    from pyparsing.util import col

    print(test_label)
    assert col(loc, strg) == expected_output


@pytest.mark.parametrize(
    "test_label, loc, strg, expected_output",
    [
        ("Single line, no newlines", 0, "abcdef", "abcdef"),
        ("First line in multi-line string", 2, "abc\ndef", "abc"),
        ("Second line in multi-line string", 5, "abc\ndef", "def"),
        ("Location at start of second line", 4, "abc\ndef", "def"),
        ("Empty string", 0, "", ""),
        ("Location at newline character", 3, "abc\ndef", "abc"),
        ("Last line without trailing newline", 7, "abc\ndef\nghi", "def"),
        ("Single line with newline at end", 2, "abc\n", "abc"),
        ("Multi-line with multiple newlines", 6, "line1\nline2\nline3", "line2"),
        ("Multi-line with trailing newline", 11, "line1\nline2\nline3\n", "line2"),
    ]
)
def test_line(test_label, loc, strg, expected_output):
    from pyparsing import line

    print(test_label)
    assert line(loc, strg) == expected_output


@pytest.mark.parametrize(
    "test_label, loc, strg, expected_output",
    [
        ("Single line, no newlines", 0, "abcdef", 1),
        ("First line in multi-line string", 2, "abc\ndef", 1),
        ("Second line in multi-line string", 5, "abc\ndef", 2),
        ("Location at start of second line", 4, "abc\ndef", 2),
        ("Multiple newlines, third line", 10, "abc\ndef\nghi", 3),
        ("Empty string", 0, "", 1),
        ("Location at newline character", 3, "abc\ndef", 1),
        ("Last line without trailing newline", 7, "abc\ndef\nghi", 2),
        ("Single line with newline at end", 4, "abc\n", 2),
        ("Multi-line with trailing newline", 12, "line1\nline2\nline3\n", 3),
        ("Location in middle of a tabbed string", 7, "a\tb\nc\td", 2),
    ]
)
def test_lineno(test_label, loc, strg, expected_output):
    from pyparsing import lineno

    assert lineno(loc, strg) == expected_output
