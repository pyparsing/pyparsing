import unittest
from examples.jsonParser import jsonObject
from examples.simpleBool import boolExpr
from pyparsing.diagram import make_diagram

class TestRailroadDiagrams(unittest.TestCase):
    def test_bool_expre(self):
        diagram = make_diagram(boolExpr)

    def test_json(self):
        diagram = make_diagram(jsonObject)
