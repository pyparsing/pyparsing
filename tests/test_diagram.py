import unittest
from io import StringIO
from pathlib import Path
from typing import List

from examples.jsonParser import jsonObject
from examples.simpleBool import boolExpr
from examples.simpleSQL import simpleSQL
from examples.mozillaCalendarParser import calendars
from pyparsing.diagram import to_railroad, railroad_to_html, NamedDiagram
import pyparsing as pp
import tempfile
import os
import sys

print(f"Running {__file__}")
print(sys.version_info)

curdir = Path(__file__).parent


class TestRailroadDiagrams(unittest.TestCase):
    def railroad_debug(self) -> bool:
        """
        Returns True if we're in debug mode (determined by either setting
        environment var, or running in a debugger which sets sys.settrace)
        """
        return os.environ.get("RAILROAD_DEBUG", False) or sys.gettrace()

    def get_temp(self):
        """
        Returns an appropriate temporary file for writing a railroad diagram
        """
        return tempfile.NamedTemporaryFile(
            dir=".",
            delete=not self.railroad_debug(),
            mode="w",
            encoding="utf-8",
            suffix=".html",
        )

    def generate_railroad(
        self, expr: pp.ParserElement, label: str, show_results_names: bool = False
    ) -> List[NamedDiagram]:
        """
        Generate an intermediate list of NamedDiagrams from a pyparsing expression.
        """
        with self.get_temp() as temp:
            railroad = to_railroad(expr, show_results_names=show_results_names)
            # temp.write(railroad_to_html(railroad))

        if self.railroad_debug() or True:
            print(f"{label}: {temp.name}")

        return railroad

    def test_example_rr_diags(self):
        subtests = [
            (jsonObject, "jsonObject", 8),
            (boolExpr, "boolExpr", 5),
            (simpleSQL, "simpleSQL", 20),
            (calendars, "calendars", 13),
        ]
        for example_expr, label, expected_rr_len in subtests:
            with self.subTest(f"{label}: test rr diag without results names"):
                railroad = self.generate_railroad(example_expr, example_expr)
                if len(railroad) != expected_rr_len:
                    diag_html = railroad_to_html(railroad)
                    for line in diag_html.splitlines():
                        if 'h1 class="railroad-heading"' in line:
                            print(line)
                assert len(railroad) == expected_rr_len, f"expected {expected_rr_len}, got {len(railroad)}"

            with self.subTest(f"{label}: test rr diag with results names"):
                railroad = self.generate_railroad(example_expr, example_expr, show_results_names=True)
                if len(railroad) != expected_rr_len:
                    print(railroad_to_html(railroad))
                assert len(railroad) == expected_rr_len, f"expected {expected_rr_len}, got {len(railroad)}"

    def test_nested_forward_with_inner_and_outer_names(self):
        outer = pp.Forward().setName("outer")
        inner = pp.Word(pp.alphas)[...].setName("inner")
        outer <<= inner

        railroad = self.generate_railroad(outer, "inner_outer_names")
        assert len(railroad) == 2
        railroad = self.generate_railroad(
            outer, "inner_outer_names", show_results_names=True
        )
        assert len(railroad) == 2

    def test_nested_forward_with_inner_name_only(self):
        outer = pp.Forward()
        inner = pp.Word(pp.alphas)[...].setName("inner")
        outer <<= inner

        railroad = self.generate_railroad(outer, "inner_only")
        assert len(railroad) == 2
        railroad = self.generate_railroad(outer, "inner_only", show_results_names=True)
        assert len(railroad) == 2

    def test_each_grammar(self):

        grammar = pp.Each(
            [
                pp.Word(pp.nums),
                pp.Word(pp.alphas),
                pp.pyparsing_common.uuid,
            ]
        ).setName("int-word-uuid in any order")
        railroad = self.generate_railroad(grammar, "each_expression")
        assert len(railroad) == 2
        railroad = self.generate_railroad(
            grammar, "each_expression", show_results_names=True
        )
        assert len(railroad) == 2

    def test_none_name(self):
        grammar = pp.Or(["foo", "bar"])
        railroad = to_railroad(grammar)
        assert len(railroad) == 1
        assert railroad[0].name is not None

    def test_none_name2(self):
        grammar = pp.Or(["foo", "bar"]) + pp.Word(pp.nums).setName("integer")
        railroad = to_railroad(grammar)
        assert len(railroad) == 2
        assert railroad[0].name is not None
        railroad = to_railroad(grammar, show_results_names=True)
        assert len(railroad) == 2

    def test_complete_combine_element(self):
        ints = pp.Word(pp.nums)
        grammar = pp.Combine(
            ints("hours")
            + pp.Literal(":")
            + ints("minutes")
            + pp.Literal(":")
            + ints("seconds")
        )
        railroad = to_railroad(grammar)
        assert len(railroad) == 1
        railroad = to_railroad(grammar, show_results_names=True)
        assert len(railroad) == 1

    def test_create_diagram(self):
        ints = pp.Word(pp.nums)
        grammar = pp.Combine(
            ints("hours")
            + pp.Literal(":")
            + ints("minutes")
            + pp.Literal(":")
            + ints("seconds")
        )

        diag_strio = StringIO()
        grammar.create_diagram(output_html=diag_strio)
        diag_str = diag_strio.getvalue().lower()
        tags = "<html> </html> <head> </head> <body> </body>".split()
        assert all(tag in diag_str for tag in tags)

    def test_create_diagram_embed(self):
        ints = pp.Word(pp.nums)
        grammar = pp.Combine(
            ints("hours")
            + pp.Literal(":")
            + ints("minutes")
            + pp.Literal(":")
            + ints("seconds")
        )

        diag_strio = StringIO()
        grammar.create_diagram(output_html=diag_strio, embed=True)
        diag_str = diag_strio.getvalue().lower()
        tags = "<html> </html> <head> </head> <body> </body>".split()
        assert not any(tag in diag_str for tag in tags)


if __name__ == "__main__":
    unittest.main()
