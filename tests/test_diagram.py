import unittest
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
            temp.write(railroad_to_html(railroad))

        if self.railroad_debug():
            print(f"{label}: {temp.name}")

        return railroad

    def test_bool_expr(self):
        railroad = self.generate_railroad(boolExpr, "boolExpr")
        assert len(railroad) == 5

    def test_json(self):
        railroad = self.generate_railroad(jsonObject, "jsonObject")
        assert len(railroad) == 9

    def test_sql(self):
        railroad = self.generate_railroad(simpleSQL, "simpleSQL")
        assert len(railroad) == 18

    def test_calendars(self):
        railroad = self.generate_railroad(calendars, "calendars")
        assert len(railroad) == 13

    def test_nested_forward_with_inner_and_outer_names(self):
        outer = pp.Forward().setName("outer")
        inner = pp.Word(pp.alphas)[...].setName("inner")
        outer <<= inner

        railroad = self.generate_railroad(outer, "inner_outer_names")
        assert len(railroad) == 2

    def test_nested_forward_with_inner_name_only(self):
        outer = pp.Forward()
        inner = pp.Word(pp.alphas)[...].setName("inner")
        outer <<= inner

        railroad = self.generate_railroad(outer, "inner_only")
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
