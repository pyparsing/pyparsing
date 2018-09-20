#
# simple_unit_tests.py
#
# While these unit tests *do* perform low-level unit testing of the classes in pyparsing,
# this testing module should also serve an instructional purpose, to clearly show simple passing
# and failing parse cases of some basic pyparsing expressions.
#
# Copyright (c) 2018  Paul T. McGuire
#

import unittest
import pyparsing as pp
from collections import namedtuple

# Test spec data class for specifying simple pyparsing test cases
PpTestSpec = namedtuple("PpTestSpec", "desc expr text expected_list expected_dict expected_fail_locn")
PpTestSpec.__new__.__defaults__ = ('', pp.Empty(), '', None, None, None)


class PyparsingExpressionTestCase(unittest.TestCase):
    """
    Base pyparsing testing class to parse various pyparsing expressions against
    given text strings. Subclasses must define a class attribute 'tests' which
    is a list of PpTestSpec instances.
    """
    def test_match(self):
        if self.__class__ is PyparsingExpressionTestCase:
            return

        for test_spec in self.tests:
            # for each spec in the class's tests list, create a subtest
            # that will either:
            #  - parse the string with expected success, display the 
            #    results, and validate the returned ParseResults
            #  - or parse the string with expected failure, display the 
            #    error message and mark the error location, and validate
            #    the location against an expected value
            with self.subTest(test_spec=test_spec):
                test_spec.expr.streamline()
                print("\n{} - {}({})".format(test_spec.desc, 
                                             type(test_spec.expr).__name__, 
                                             test_spec.expr))

                if test_spec.expected_fail_locn is None:
                    # expect success
                    result = test_spec.expr.parseString(test_spec.text)
                    print(result.dump())
                    # compare results against given list and/or dict
                    if test_spec.expected_list is not None:
                        self.assertEqual(result.asList(), test_spec.expected_list)
                    if test_spec.expected_dict is not None:
                        self.assertEqual(result.asDict(), test_spec.expected_dict)

                else:
                    # expect fail
                    with self.assertRaises(pp.ParseException) as ar:
                        test_spec.expr.parseString(test_spec.text)
                    print(' ', test_spec.text or "''")
                    print(' ', ' '*ar.exception.loc+'^')
                    print(' ', ar.exception.msg)
                    self.assertEqual(ar.exception.loc, test_spec.expected_fail_locn)



class TestLiteral(PyparsingExpressionTestCase):
    tests = [
        PpTestSpec(
            desc = "Simple match",
            expr = pp.Literal("xyz"),
            text = "xyz",
            expected_list = ["xyz"],
        ),
        PpTestSpec(
            desc = "Simple match after skipping whitespace",
            expr = pp.Literal("xyz"),
            text = "  xyz",
            expected_list = ["xyz"],
        ),
        PpTestSpec(
            desc = "Simple fail - parse an empty string",
            expr = pp.Literal("xyz"),
            text = "",
            expected_fail_locn = 0,
        ),
        PpTestSpec(
            desc = "Simple fail - parse a mismatching string",
            expr = pp.Literal("xyz"),
            text = "xyu",
            expected_fail_locn = 0,
        ),
        PpTestSpec(
            desc = "Simple fail - parse a partially matching string",
            expr = pp.Literal("xyz"),
            text = "xy",
            expected_fail_locn = 0,
        ),
        PpTestSpec(
            desc = "Fail - parse a partially matching string by matching individual letters",
            expr =  pp.Literal("x") + pp.Literal("y") + pp.Literal("z"),
            text = "xy",
            expected_fail_locn = 2,
        ),
    ]


class TestWord(PyparsingExpressionTestCase):
    tests = [
        PpTestSpec(
            desc = "Simple Word match",
            expr = pp.Word("xy"),
            text = "xxyxxyy",
            expected_list = ["xxyxxyy"],
        ),
        PpTestSpec(
            desc = "Simple Word match of two separate Words",
            expr = pp.Word("x") + pp.Word("y"),
            text = "xxxxxyy",
            expected_list = ["xxxxx", "yy"],
        ),
        PpTestSpec(
            desc = "Simple Word match of two separate Words - implicitly skips whitespace",
            expr = pp.Word("x") + pp.Word("y"),
            text = "xxxxx yy",
            expected_list = ["xxxxx", "yy"],
        ),
    ]


class TestResultsName(PyparsingExpressionTestCase):
    tests = [
        PpTestSpec(
            desc = "Match with results name",
            expr = pp.Literal("xyz").setResultsName("value"),
            text = "xyz",
            expected_dict = {'value': 'xyz'},
            expected_list = ['xyz'],
        ),
        PpTestSpec(
            desc = "Match with results name - using naming short-cut",
            expr = pp.Literal("xyz")("value"),
            text = "xyz",
            expected_dict = {'value': 'xyz'},
            expected_list = ['xyz'],
        ),
    ]


class TestParseAction(PyparsingExpressionTestCase):
    tests = [
        PpTestSpec(
            desc = "Match with numeric string converted to int",
            expr = pp.Word("0123456789").addParseAction(lambda t: int(t[0])),
            text = "12345",
            expected_list = [12345],  # note - result is type int, not str 
        ),
    ]
    

if __name__ == '__main__':
    unittest.main()