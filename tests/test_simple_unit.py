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
from datetime import datetime

ppt = pp.pyparsing_test

# Test spec data class for specifying simple pyparsing test cases
PpTestSpec = namedtuple("PpTestSpec", "desc expr text parse_fn "
                                      "expected_list expected_dict expected_fail_locn")
PpTestSpec.__new__.__defaults__ = ('', pp.Empty(), '', 'parseString', None, None, None)


class PyparsingExpressionTestCase(unittest.TestCase):

    def runTest(self, desc='', expr=pp.Empty(), text='', parse_fn="parseString", expected_list=None, expected_dict=None, expected_fail_locn=None):
        # for each spec in the class's tests list, create a subtest
        # that will either:
        #  - parse the string with expected success, display the
        #    results, and validate the returned ParseResults
        #  - or parse the string with expected failure, display the
        #    error message and mark the error location, and validate
        #    the location against an expected value
        test_spec = PpTestSpec(desc, expr, text, parse_fn, expected_list, expected_dict, expected_fail_locn)
        test_spec.expr.streamline()
        print("\n{0} - {1}({2})".format(test_spec.desc,
                                        type(test_spec.expr).__name__,
                                        test_spec.expr))

        parsefn = getattr(test_spec.expr, test_spec.parse_fn)
        if test_spec.expected_fail_locn is None:
            # expect success
            result = parsefn(test_spec.text)
            if test_spec.parse_fn == 'parseString':
                print(result.dump())
                # compare results against given list and/or dict
                if test_spec.expected_list is not None:
                    self.assertEqual(test_spec.expected_list, result.asList())
                if test_spec.expected_dict is not None:
                    self.assertEqual(test_spec.expected_dict, result.asDict())
            elif test_spec.parse_fn == 'transformString':
                print(result)
                # compare results against given list and/or dict
                if test_spec.expected_list is not None:
                    self.assertEqual([result], test_spec.expected_list)
            elif test_spec.parse_fn == 'searchString':
                print(result)
                # compare results against given list and/or dict
                if test_spec.expected_list is not None:
                    self.assertEqual([result], test_spec.expected_list)
        else:
            # expect fail
            try:
                parsefn(test_spec.text)
            except Exception as exc:
                if not hasattr(exc, '__traceback__'):
                    # Python 2 compatibility
                    from sys import exc_info
                    etype, value, traceback = exc_info()
                    exc.__traceback__ = traceback
                print(pp.ParseException.explain(exc))
                self.assertEqual(exc.loc, test_spec.expected_fail_locn)
            else:
                self.assertTrue(False, "failed to raise expected exception")


# =========== TEST DEFINITIONS START HERE ==============

class TestLiteral(PyparsingExpressionTestCase):
    def test_simple_match(self):
        self.runTest(
            desc="Simple match",
            expr=pp.Literal("xyz"),
            text="xyz",
            expected_list=["xyz"],
        )

    def test_simple_match_after_skipping_whitespace(self):
        self.runTest(
            desc="Simple match after skipping whitespace",
            expr=pp.Literal("xyz"),
            text="  xyz",
            expected_list=["xyz"],
        )

    def test_simple_fail_parse_an_empty_string(self):
        self.runTest(
            desc="Simple fail - parse an empty string",
            expr=pp.Literal("xyz"),
            text="",
            expected_fail_locn=0,
        )

    def test_Simple_fail___parse_a_mismatching_string(self):
        self.runTest(
            desc="Simple fail - parse a mismatching string",
            expr=pp.Literal("xyz"),
            text="xyu",
            expected_fail_locn=0,
        )

    def test_simple_fail_parse_a_partially_matching_string(self):
        self.runTest(
            desc="Simple fail - parse a partially matching string",
            expr=pp.Literal("xyz"),
            text="xy",
            expected_fail_locn=0,
        )

    def test_fail_parse_a_partially_matching_string_by_matching_individual_letters(self):
        self.runTest(
            desc="Fail - parse a partially matching string by matching individual letters",
            expr=pp.Literal("x") + pp.Literal("y") + pp.Literal("z"),
            text="xy",
            expected_fail_locn=2,
        )


class TestCaselessLiteral(PyparsingExpressionTestCase):
    def test_Match_colors_converting_to_consistent_case(self):
        self.runTest(
            desc="Match colors, converting to consistent case",
            expr=(pp.CaselessLiteral("RED")
                  | pp.CaselessLiteral("GREEN")
                  | pp.CaselessLiteral("BLUE"))[...],
            text="red Green BluE blue GREEN green rEd",
            expected_list=['RED', 'GREEN', 'BLUE', 'BLUE', 'GREEN', 'GREEN', 'RED'],
        )


class TestWord(PyparsingExpressionTestCase):
    def test_Simple_Word_match(self):
        self.runTest(
            desc="Simple Word match",
            expr=pp.Word("xy"),
            text="xxyxxyy",
            expected_list=["xxyxxyy"],
        )

    def test_Simple_Word_match_of_two_separate_Words(self):
        self.runTest(
            desc="Simple Word match of two separate Words",
            expr=pp.Word("x") + pp.Word("y"),
            text="xxxxxyy",
            expected_list=["xxxxx", "yy"],
        )

    def test_Simple_Word_match_of_two_separate_Words___implicitly_skips_whitespace(self):
        self.runTest(
            desc="Simple Word match of two separate Words - implicitly skips whitespace",
            expr=pp.Word("x") + pp.Word("y"),
            text="xxxxx yy",
            expected_list=["xxxxx", "yy"],
        )


class TestCombine(PyparsingExpressionTestCase):
    def test_parsing_real_numbers__fail(self):
        self.runTest(
            desc="Parsing real numbers - fail, parsed numbers are in pieces",
            expr=(pp.Word(pp.nums) + '.' + pp.Word(pp.nums))[...],
            text="1.2 2.3 3.1416 98.6",
            expected_list=['1', '.', '2', '2', '.', '3', '3', '.', '1416', '98', '.', '6'],
        )

    def test_parsing_real_numbers__better(self):
        self.runTest(
            desc="Parsing real numbers - better, use Combine to combine multiple tokens into one",
            expr=pp.Combine(pp.Word(pp.nums) + '.' + pp.Word(pp.nums))[...],
            text="1.2 2.3 3.1416 98.6",
            expected_list=['1.2', '2.3', '3.1416', '98.6'],
        )


class TestRepetition(PyparsingExpressionTestCase):
    def test_Match_several_words(self):
        self.runTest(
            desc="Match several words",
            expr=(pp.Word("x") | pp.Word("y"))[...],
            text="xxyxxyyxxyxyxxxy",
            expected_list=['xx', 'y', 'xx', 'yy', 'xx', 'y', 'x', 'y', 'xxx', 'y'],
        )

    def test_Match_several_words_skipping_whitespace(self):
        self.runTest(
            desc="Match several words, skipping whitespace",
            expr=(pp.Word("x") | pp.Word("y"))[...],
            text="x x  y xxy yxx y xyx  xxy",
            expected_list=['x', 'x', 'y', 'xx', 'y', 'y', 'xx', 'y', 'x', 'y', 'x', 'xx', 'y'],
        )

    def test_Match_several_words_skipping_whitespace_old_style(self):
        self.runTest(
            desc="Match several words, skipping whitespace (old style)",
            expr=pp.OneOrMore(pp.Word("x") | pp.Word("y")),
            text="x x  y xxy yxx y xyx  xxy",
            expected_list=['x', 'x', 'y', 'xx', 'y', 'y', 'xx', 'y', 'x', 'y', 'x', 'xx', 'y'],
        )

    def test_Match_words_and_numbers___show_use_of_results_names_to_collect_types_of_tokens(self):
        self.runTest(
            desc="Match words and numbers - show use of results names to collect types of tokens",
            expr=(pp.Word(pp.alphas)("alpha*")
                  | pp.pyparsing_common.integer("int*"))[...],
            text="sdlfj23084ksdfs08234kjsdlfkjd0934",
            expected_list=['sdlfj', 23084, 'ksdfs', 8234, 'kjsdlfkjd', 934],
            expected_dict={'alpha': ['sdlfj', 'ksdfs', 'kjsdlfkjd'], 'int': [23084, 8234, 934]}
        )

    def test_Using_delimitedList_comma_is_the_default_delimiter(self):
        self.runTest(
            desc="Using delimitedList (comma is the default delimiter)",
            expr=pp.delimitedList(pp.Word(pp.alphas)),
            text="xxyx,xy,y,xxyx,yxx, xy",
            expected_list=['xxyx', 'xy', 'y', 'xxyx', 'yxx', 'xy'],
        )

    def test_Using_delimitedList_with_colon_delimiter(self):
        self.runTest(
            desc="Using delimitedList, with ':' delimiter",
            expr=pp.delimitedList(pp.Word(pp.hexnums, exact=2), delim=':', combine=True),
            text="0A:4B:73:21:FE:76",
            expected_list=['0A:4B:73:21:FE:76'],
        )


class TestResultsName(PyparsingExpressionTestCase):
    def test_Match_with_results_name(self):
        self.runTest(
            desc="Match with results name",
            expr=pp.Literal("xyz").setResultsName("value"),
            text="xyz",
            expected_dict={'value': 'xyz'},
            expected_list=['xyz'],
        )

    def test_Match_with_results_name___using_naming_short_cut(self):
        self.runTest(
            desc="Match with results name - using naming short-cut",
            expr=pp.Literal("xyz")("value"),
            text="xyz",
            expected_dict={'value': 'xyz'},
            expected_list=['xyz'],
        )

    def test_Define_multiple_results_names(self):
        self.runTest(
            desc="Define multiple results names",
            expr=pp.Word(pp.alphas, pp.alphanums)("key") + '=' + pp.pyparsing_common.integer("value"),
            text="range=5280",
            expected_dict={'key': 'range', 'value': 5280},
            expected_list=['range', '=', 5280],
        )


class TestGroups(PyparsingExpressionTestCase):
    EQ = pp.Suppress('=')

    def test_Define_multiple_results_names_in_groups(self):
        self.runTest(
            desc="Define multiple results names in groups",
            expr=pp.Group(pp.Word(pp.alphas)("key")
                          + self.EQ
                          + pp.pyparsing_common.number("value"))[...],
            text="range=5280 long=-138.52 lat=46.91",
            expected_list=[['range', 5280], ['long', -138.52], ['lat', 46.91]],
        )

    def test_Define_multiple_results_names_in_groups___use_Dict_to_define_results_names_using_parsed_keys(self):
        self.runTest(
            desc="Define multiple results names in groups - use Dict to define results names using parsed keys",
            expr=pp.Dict(pp.Group(pp.Word(pp.alphas)
                                  + self.EQ
                                  + pp.pyparsing_common.number)[...]),
            text="range=5280 long=-138.52 lat=46.91",
            expected_list=[['range', 5280], ['long', -138.52], ['lat', 46.91]],
            expected_dict={'lat': 46.91, 'long': -138.52, 'range': 5280}
        )

    def test_Define_multiple_value_types(self):
        self.runTest(
            desc="Define multiple value types",
            expr=pp.Dict(pp.Group(pp.Word(pp.alphas)
                                  + self.EQ
                                  + (pp.pyparsing_common.number | pp.oneOf("True False") | pp.QuotedString("'"))
                                  )[...]
                         ),
            text="long=-122.47 lat=37.82 public=True name='Golden Gate Bridge'",
            expected_list=[['long', -122.47], ['lat', 37.82], ['public', 'True'], ['name', 'Golden Gate Bridge']],
            expected_dict={'long': -122.47, 'lat': 37.82, 'public': 'True', 'name': 'Golden Gate Bridge'}
        )


class TestParseAction(PyparsingExpressionTestCase):
    def test_(self):
        self.runTest(
            desc="Parsing real numbers - use parse action to convert to float at parse time",
            expr=pp.Combine(pp.Word(pp.nums) + '.' + pp.Word(pp.nums)).addParseAction(lambda t: float(t[0]))[...],
            text="1.2 2.3 3.1416 98.6",
            expected_list=[1.2, 2.3, 3.1416, 98.6],  # note, these are now floats, not strs
        )

    def test_Match_with_numeric_string_converted_to_int(self):
        self.runTest(
            desc="Match with numeric string converted to int",
            expr=pp.Word("0123456789").addParseAction(lambda t: int(t[0])),
            text="12345",
            expected_list=[12345],  # note - result is type int, not str
        )

    def test_Use_two_parse_actions_to_convert_numeric_string_then_convert_to_datetime(self):
        self.runTest(
            desc="Use two parse actions to convert numeric string, then convert to datetime",
            expr=pp.Word(pp.nums).addParseAction(lambda t: int(t[0]),
                                                 lambda t: datetime.utcfromtimestamp(t[0])),
            text="1537415628",
            expected_list=[datetime(2018, 9, 20, 3, 53, 48)],
        )

    def test_Use_tokenMap_for_parse_actions_that_operate_on_a_single_length_token(self):
        self.runTest(
            desc="Use tokenMap for parse actions that operate on a single-length token",
            expr=pp.Word(pp.nums).addParseAction(pp.tokenMap(int),
                                                 pp.tokenMap(datetime.utcfromtimestamp)),
            text="1537415628",
            expected_list=[datetime(2018, 9, 20, 3, 53, 48)],
        )

    def test_Using_a_built_in_function_that_takes_a_sequence_of_strs_as_a_parse_action1(self):
        self.runTest(
            desc="Using a built-in function that takes a sequence of strs as a parse action",
            expr=pp.Word(pp.hexnums, exact=2)[...].addParseAction(':'.join),
            text="0A4B7321FE76",
            expected_list=['0A:4B:73:21:FE:76'],
        )

    def test_Using_a_built_in_function_that_takes_a_sequence_of_strs_as_a_parse_action2(self):
        self.runTest(
            desc="Using a built-in function that takes a sequence of strs as a parse action",
            expr=pp.Word(pp.hexnums, exact=2)[...].addParseAction(sorted),
            text="0A4B7321FE76",
            expected_list=['0A', '21', '4B', '73', '76', 'FE'],
        )


class TestResultsModifyingParseAction(PyparsingExpressionTestCase):
    @staticmethod
    def compute_stats_parse_action(t):
        # by the time this parse action is called, parsed numeric words
        # have been converted to ints by a previous parse action, so
        # they can be treated as ints
        t['sum'] = sum(t)
        t['ave'] = sum(t) / len(t)
        t['min'] = min(t)
        t['max'] = max(t)

    def test_A_parse_action_that_adds_new_key_values(self):
        self.runTest(
            desc="A parse action that adds new key-values",
            expr=pp.pyparsing_common.integer[...].addParseAction(self.compute_stats_parse_action),
            text="27 1 14 22 89",
            expected_list=[27, 1, 14, 22, 89],
            expected_dict={'ave': 30.6, 'max': 89, 'min': 1, 'sum': 153}
        )


class TestRegex(PyparsingExpressionTestCase):
    def test_parsing_real_numbers_using_regex_instead_of_combine(self):
        self.runTest(
            desc="Parsing real numbers - using Regex instead of Combine",
            expr=pp.Regex(r'\d+\.\d+').addParseAction(lambda t: float(t[0]))[...],
            text="1.2 2.3 3.1416 98.6",
            expected_list=[1.2, 2.3, 3.1416, 98.6],  # note, these are now floats, not strs
        )


class TestParseCondition(PyparsingExpressionTestCase):
    def test_Define_a_condition_to_only_match_numeric_values_that_are_multiples_of_7(self):
        self.runTest(
            desc="Define a condition to only match numeric values that are multiples of 7",
            expr=pp.Word(pp.nums).addCondition(lambda t: int(t[0]) % 7 == 0)[...],
            text="14 35 77 12 28",
            expected_list=['14', '35', '77'],
        )

    def test_Separate_conversion_to_int_and_condition_into_separate_parse_action_conditions(self):
        self.runTest(
            desc="Separate conversion to int and condition into separate parse action/conditions",
            expr=pp.Word(pp.nums).addParseAction(lambda t: int(t[0]))
                .addCondition(lambda t: t[0] % 7 == 0)[...],
            text="14 35 77 12 28",
            expected_list=[14, 35, 77],
                )


class TestTransformStringUsingParseActions(PyparsingExpressionTestCase):
    markup_convert_map = {
        '*': 'B',
        '_': 'U',
        '/': 'I',
    }

    def markup_convert(self, t):
        htmltag = self.markup_convert_map[t.markup_symbol]
        return "<{0}>{1}</{2}>".format(htmltag, t.body, htmltag)

    def test_Use_transformString_to_convert_simple_markup_to_HTML(self):
        self.runTest(
            desc="Use transformString to convert simple markup to HTML",
            expr=(pp.oneOf(self.markup_convert_map)('markup_symbol')
                  + "(" + pp.CharsNotIn(")")('body') + ")").addParseAction(self.markup_convert),
            #     0         1         2         3         4
            #     01234567890123456789012345678901234567890123456789
            text="Show in *(bold), _(underscore), or /(italic) type",
            expected_list=['Show in <B>bold</B>, <U>underscore</U>, or <I>italic</I> type'],
            parse_fn='transformString',
        )


class TestCommonHelperExpressions(PyparsingExpressionTestCase):
    def test_A_comma_delimited_list_of_words(self):
        self.runTest(
            desc="A comma-delimited list of words",
            expr=pp.delimitedList(pp.Word(pp.alphas)),
            text="this, that, blah,foo,   bar",
            expected_list=['this', 'that', 'blah', 'foo', 'bar'],
        )

    def test_A_counted_array_of_words(self):
        self.runTest(
            desc="A counted array of words",
            expr=pp.countedArray(pp.Word('ab'))[...],
            text="2 aaa bbb 0 3 abab bbaa abbab",
            expected_list=[['aaa', 'bbb'], [], ['abab', 'bbaa', 'abbab']],
        )

    def test_skipping_comments_with_ignore(self):
        self.runTest(
            desc="skipping comments with ignore",
            expr=(pp.pyparsing_common.identifier('lhs')
                  + '='
                  + pp.pyparsing_common.fnumber('rhs')).ignore(pp.cppStyleComment),
            text="abc_100 = /* value to be tested */ 3.1416",
            expected_list=['abc_100', '=', 3.1416],
            expected_dict={'lhs': 'abc_100', 'rhs': 3.1416},
        )

    def test_some_pre_defined_expressions_in_pyparsing_common_and_building_a_dotted_identifier_with_delimted_list(self):
        self.runTest(
            desc="some pre-defined expressions in pyparsing_common, and building a dotted identifier with delimted_list",
            expr=(pp.pyparsing_common.number("id_num")
                  + pp.delimitedList(pp.pyparsing_common.identifier, '.', combine=True)("name")
                  + pp.pyparsing_common.ipv4_address("ip_address")
                  ),
            text="1001 www.google.com 192.168.10.199",
            expected_list=[1001, 'www.google.com', '192.168.10.199'],
            expected_dict={'id_num': 1001, 'name': 'www.google.com', 'ip_address': '192.168.10.199'},
        )

    def test_using_oneOf_shortcut_for_a_b_c(self):
        self.runTest(
            desc="using oneOf (shortcut for Literal('a') | Literal('b') | Literal('c'))",
            expr=pp.oneOf("a b c")[...],
            text="a b a b b a c c a b b",
            expected_list=['a', 'b', 'a', 'b', 'b', 'a', 'c', 'c', 'a', 'b', 'b'],
        )

    def test_parsing_nested_parentheses(self):
        self.runTest(
            desc="parsing nested parentheses",
            expr=pp.nestedExpr(),
            text="(a b (c) d (e f g ()))",
            expected_list=[['a', 'b', ['c'], 'd', ['e', 'f', 'g', []]]],
        )

    def test_parsing_nested_braces(self):
        self.runTest(
            desc="parsing nested braces",
            expr=(pp.Keyword('if')
                  + pp.nestedExpr()('condition')
                  + pp.nestedExpr('{', '}')('body')),
            #     0         1         2         3
            #     0123456789012345678901234567890123456789
            text='if ((x == y) || !z) {printf("{}");}',
            expected_list=['if', [['x', '==', 'y'], '||', '!z'], ['printf(', '"{}"', ');']],
            expected_dict={'condition': [[['x', '==', 'y'], '||', '!z']],
                           'body': [['printf(', '"{}"', ');']]},
        )


def _get_decl_line_no(cls):
    import inspect
    return inspect.getsourcelines(cls)[1]

