import unittest
from examples.jsonParser import jsonObject
from examples.simpleBool import boolExpr
from examples.simpleSQL import simpleSQL
from examples.mozillaCalendarParser import calendars
from pyparsing.diagram import to_railroad, railroad_to_html
from pyparsing import Or
import tempfile
import os


class TestRailroadDiagrams(unittest.TestCase):
    def railroad_debug(self) -> bool:
        """
        Returns True if we're in debug mode
        """
        return os.environ.get("RAILROAD_DEBUG", False)

    def get_temp(self):
        """
        Returns an appropriate temporary file for writing a railroad diagram
        """
        return tempfile.NamedTemporaryFile(
            delete=not self.railroad_debug(), mode="w", encoding="utf-8", suffix=".html"
        )

    def test_bool_expr(self):
        with self.get_temp() as temp:
            railroad = to_railroad(boolExpr)
            assert len(railroad) == 3
            temp.write(railroad_to_html(railroad))

            if self.railroad_debug():
                print("bool expr:" + temp.name)

    def test_json(self):
        with self.get_temp() as temp:
            railroad = to_railroad(jsonObject)
            assert len(railroad) == 4
            temp.write(railroad_to_html(railroad))

            if self.railroad_debug():
                print("json: " + temp.name)

    def test_sql(self):
        with self.get_temp() as temp:
            railroad = to_railroad(simpleSQL)
            assert len(railroad) == 7
            temp.write(railroad_to_html(railroad))

            if self.railroad_debug():
                print("sql: " + temp.name)

    def test_calendars(self):
        with self.get_temp() as temp:
            railroad = to_railroad(calendars)
            temp.write(railroad_to_html(railroad))

            if self.railroad_debug():
                print("calendar: " + temp.name)

    def test_none_name(self):
        grammar = Or(["foo", "bar"])
        railroad = to_railroad(grammar)
        assert len(railroad) == 1
        assert railroad[0].name is not None
