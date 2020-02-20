#
# test_examples.py
#
import unittest
from importlib import import_module

from mo_files import File

from pyparsing.testing import reset_pyparsing_context

modules = [f.name for f in File("examples").children]


class TestAllExamples(unittest.TestCase):
    pass


def _single_test(name):
    def output(self):
        with reset_pyparsing_context():
            import_module("examples." + name)

    return output


for f in File("examples").children:
    if f.extension == "py":
        setattr(TestAllExamples, "test_" + f.name, _single_test(f.name))


# class TestExamples(unittest.TestCase):
#
#     def _run(self, name):
#         module = import_module("examples." + name)
#
#     def test_numerics(self):
#         self._run("numerics")
#
#     def test_tap(self):
#         self._run("TAP")
#
#     def test_roman_numerals(self):
#         self._run("romanNumerals")
#
#     def test_sexp_parser(self):
#         self._run("sexpParser")
#
#     def test_oc(self):
#         self._run("oc")
#
#     def test_delta_time(self):
#         self._run("delta_time")
#
#     def test_eval_arith(self):
#         self._run("eval_arith")
#
#     def test_select_parser(self):
#         self._run("select_parser")
