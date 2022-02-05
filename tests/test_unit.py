#
# test_unit.py
#
# Unit tests for pyparsing module
#
# Copyright 2002-2021, Paul McGuire
#
#

import contextlib
import datetime
import re
import sys
import warnings
from types import SimpleNamespace
from io import StringIO
from textwrap import dedent
from typing import Any
import unittest

import pyparsing as pp
from examples.jsonParser import jsonObject
from pyparsing import ParserElement, ParseException, ParseFatalException
from tests.json_parser_tests import test1, test2, test3, test4, test5
import platform

ppc = pp.pyparsing_common
ppt = pp.pyparsing_test

# see which Python implementation we are running
python_impl = platform.python_implementation()
CPYTHON_ENV = python_impl == "CPython"
IRON_PYTHON_ENV = python_impl == "IronPython"
JYTHON_ENV = python_impl == "Jython"
PYPY_ENV = python_impl == "PyPy"

# get full stack traces during testing
pp.ParserElement.verbose_stacktrace = True


# simple utility for flattening nested lists
def flatten(nested_list):
    if not isinstance(nested_list, list):
        return [nested_list]
    if not nested_list:
        return nested_list
    return flatten(nested_list[0]) + flatten(nested_list[1:])


class resetting:
    def __init__(self, *args):
        ob = args[0]
        attrnames = args[1:]
        self.ob = ob
        self.save_attrs = attrnames
        self.save_values = [getattr(ob, attrname) for attrname in attrnames]

    def __enter__(self):
        pass

    def __exit__(self, *args):
        for attr, value in zip(self.save_attrs, self.save_values):
            setattr(self.ob, attr, value)


def find_all_re_matches(patt, s):
    ret = []
    start = 0
    if isinstance(patt, str):
        patt = re.compile(patt)
    while True:
        found = patt.search(s, pos=start)
        if found:
            ret.append(found)
            start = found.end()
        else:
            break
    return ret


def current_method_name(level=2):
    import traceback

    stack = traceback.extract_stack(limit=level)
    return stack[0].name


def __():
    return current_method_name(3) + ": "


class TestCase(unittest.TestCase):
    @contextlib.contextmanager
    def assertRaises(self, expected_exception_type: Any, msg: Any = None):
        """
        Simple wrapper to print out the exceptions raised after assertRaises
        """
        with super().assertRaises(expected_exception_type, msg=msg) as ar:
            yield

        if getattr(ar, "exception", None) is not None:
            print(
                "Raised expected exception: {}: {}".format(
                    type(ar.exception).__name__, str(ar.exception)
                )
            )
        else:
            print(
                "Expected {} exception not raised".format(
                    expected_exception_type.__name__
                )
            )
        return ar

    @contextlib.contextmanager
    def assertDoesNotWarn(self, warning_type: type = UserWarning, msg: str = None):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("error")
            try:
                yield
            except Exception as e:
                if msg is None:
                    msg = "unexpected warning {} raised".format(e)
                if isinstance(e, warning_type):
                    self.fail("{}: {}".format(msg, e))
                else:
                    raise


class Test01_PyparsingTestInit(TestCase):
    def runTest(self):
        print(
            "Beginning test of pyparsing, version",
            pp.__version__,
            pp.__version_time__,
        )
        print("Python version", sys.version)
        print("__version_info__     :", pp.__version_info__)
        print("__version_info__ repr:", repr(pp.__version_info__))


class Test01a_PyparsingEnvironmentTests(TestCase):
    def runTest(self):
        # test warnings enable detection
        # fmt: off
        tests = [
            (([], "",), False),
            ((["d", ], "",), True),
            ((["d", "i:::pyparsing", ], "",), False),
            ((["d:::pyparsing", ], "",), True),
            ((["d:::pyparsing", "i", ], "",), False),
            ((["d:::blah", ], "",), False),
            ((["i", ], "",), False),
            (([], "1",), True),
            ((["d", ], "1",), True),
            ((["d", "i:::pyparsing", ], "1",), False),
            ((["d:::pyparsing", ], "1",), True),
            ((["d:::pyparsing", "i", ], "1",), False),
            ((["d:::blah", ], "1",), True),
            ((["i", ], "1",), False),
        ]
        # fmt: on

        all_success = True
        for args, expected in tests:
            message = "{} should be {}".format(args, expected)
            print(message, end=" -> ")
            actual = pp.core._should_enable_warnings(*args)
            print("PASS" if actual == expected else "FAIL")
            if actual != expected:
                all_success = False
        self.assertTrue(all_success, "failed warnings enable test")


class Test01b_PyparsingUnitTestUtilitiesTests(TestCase):
    def runTest(self):
        with ppt.reset_pyparsing_context():
            pp.enable_diag(pp.Diagnostics.warn_on_parse_using_empty_Forward)

            # test assertDoesNotWarn raises an AssertionError
            with self.assertRaises(AssertionError):
                with self.assertDoesNotWarn(
                    msg="warned when parsing with an empty Forward expression warning was suppressed",
                ):
                    base = pp.Forward()
                    try:
                        print(base.parseString("x"))
                    except ParseException as pe:
                        pass


class Test02_WithoutPackrat(ppt.TestParseResultsAsserts, TestCase):
    suite_context = None
    save_suite_context = None

    def setUp(self):
        self.suite_context.restore()

    def test000_assert_packrat_status(self):
        print("Packrat enabled:", ParserElement._packratEnabled)
        self.assertFalse(ParserElement._packratEnabled, "packrat enabled")

    def testScanStringWithOverlap(self):
        parser = pp.Word(pp.alphas, exact=3)
        without_overlaps = sum(t for t, s, e in parser.scanString("ABCDEFGHI")).asList()
        self.assertEqual(
            ["ABC", "DEF", "GHI"],
            without_overlaps,
            msg="scanString without overlaps failed",
        )
        with_overlaps = sum(
            t for t, s, e in parser.scanString("ABCDEFGHI", overlap=True)
        ).asList()
        self.assertEqual(
            ["ABC", "BCD", "CDE", "DEF", "EFG", "FGH", "GHI"],
            with_overlaps,
            msg="scanString with overlaps failed",
        )

    def testCombineWithResultsNames(self):
        # test case reproducing Issue #350
        from pyparsing import White, alphas, Word

        parser = White(' \t').set_results_name('indent') + Word(alphas).set_results_name('word')
        result = parser.parse_string('    test')
        print(result.dump())
        self.assertParseResultsEquals(result, ['    ', 'test'], {'indent': '    ', 'word': 'test'})

        parser = White(' \t') + Word(alphas).set_results_name('word')
        result = parser.parse_string('    test')
        print(result.dump())
        self.assertParseResultsEquals(result, ['    ', 'test'], {'word': 'test'})

    def testTransformString(self):
        make_int_with_commas = ppc.integer().addParseAction(
            lambda t: "{:,}".format(t[0])
        )
        lower_case_words = pp.Word(pp.alphas.lower(), asKeyword=True) + pp.Optional(
            pp.White()
        )
        nested_list = pp.nestedExpr().addParseAction(pp.ParseResults.asList)
        transformer = make_int_with_commas | nested_list | lower_case_words.suppress()

        in_string = (
            "I wish to buy 12345 shares of Acme Industries (as a gift to my (ex)wife)"
        )
        print(in_string)
        out_string = transformer.transformString(in_string)
        print(out_string)
        self.assertEqual(
            "I 12,345 Acme Industries asagifttomyexwife",
            out_string,
            msg="failure in transformString",
        )

    def testTransformStringWithLeadingWhitespace(self):
        sample = "\n\ncheck"
        sample = "    check"
        keywords = pp.oneOf("aaa bbb", asKeyword=True)
        ident = ~keywords + pp.Word(pp.alphas)
        ident = pp.Combine(~keywords + pp.Word(pp.alphas))
        # ident.add_parse_action(lambda t: t[0].upper())
        ident.add_parse_action(ppc.upcaseTokens)
        transformed = ident.transformString(sample)

        print(ppt.with_line_numbers(sample))
        print(ppt.with_line_numbers(transformed))
        self.assertEqual(sample.replace("check", "CHECK"), transformed)

    def testTransformStringWithLeadingNotAny(self):
        sample = "print a100"
        keywords = set("print read".split())
        ident = pp.Word(pp.alphas, pp.alphanums).add_condition(
            lambda t: t[0] not in keywords
        )
        print(ident.searchString(sample))

    def testTransformStringWithExpectedLeadingWhitespace(self):
        sample1 = "\n\ncheck aaa"
        sample2 = "    check aaa"
        keywords = pp.oneOf("aaa bbb", asKeyword=True)
        # This construct only works with parse_string, not with scan_string or its siblings
        # ident = ~keywords + pp.Word(pp.alphas)
        ident = pp.Word(pp.alphas)
        ident.add_parse_action(ppc.upcaseTokens)

        for sample in sample1, sample2:
            transformed = (keywords | ident).transformString(sample)
            print(ppt.with_line_numbers(sample))
            print(ppt.with_line_numbers(transformed))
            self.assertEqual(sample.replace("check", "CHECK"), transformed)
            print()

    def testTransformStringWithLeadingWhitespaceFromTranslateProject(self):
        from pyparsing import Keyword, Word, alphas, alphanums, Combine

        block_start = (Keyword("{") | Keyword("BEGIN")).set_name("block_start")
        block_end = (Keyword("}") | Keyword("END")).set_name("block_end")
        reserved_words = block_start | block_end

        # this is the first critical part of this test, an And with a leading NotAny
        # This construct only works with parse_string, not with scan_string or its siblings
        # name_id = ~reserved_words + Word(alphas, alphanums + "_").set_name("name_id")
        name_id = Word(alphas, alphanums + "_").set_name("name_id")

        dialog = name_id("block_id") + (Keyword("DIALOGEX") | Keyword("DIALOG"))(
            "block_type"
        )
        string_table = Keyword("STRINGTABLE")("block_type")

        test_string = (
            """\r\nSTRINGTABLE\r\nBEGIN\r\n// Comment\r\nIDS_1 "Copied"\r\nEND\r\n"""
        )
        print("Original:")
        print(repr(test_string))
        print("Should match:")
        # this is the second critical part of this test, an Or or MatchFirst including dialog
        for parser in (dialog ^ string_table, dialog | string_table):
            result = (reserved_words | parser).transformString(test_string)
            print(repr(result))
            self.assertEqual(
                test_string,
                result,
                "Failed whitespace skipping with NotAny and MatchFirst/Or",
            )

    def testUpdateDefaultWhitespace(self):
        prev_default_whitespace_chars = pp.ParserElement.DEFAULT_WHITE_CHARS
        try:
            pp.dblQuotedString.copyDefaultWhiteChars = False
            pp.ParserElement.setDefaultWhitespaceChars(" \t")
            self.assertEqual(
                set(" \t"),
                set(pp.sglQuotedString.whiteChars),
                "setDefaultWhitespaceChars did not update sglQuotedString",
            )
            self.assertEqual(
                set(prev_default_whitespace_chars),
                set(pp.dblQuotedString.whiteChars),
                "setDefaultWhitespaceChars updated dblQuotedString but should not",
            )
        finally:
            pp.dblQuotedString.copyDefaultWhiteChars = True
            pp.ParserElement.setDefaultWhitespaceChars(prev_default_whitespace_chars)

            self.assertEqual(
                set(prev_default_whitespace_chars),
                set(pp.dblQuotedString.whiteChars),
                "setDefaultWhitespaceChars updated dblQuotedString",
            )

        with ppt.reset_pyparsing_context():
            pp.ParserElement.setDefaultWhitespaceChars(" \t")
            self.assertNotEqual(
                set(prev_default_whitespace_chars),
                set(pp.dblQuotedString.whiteChars),
                "setDefaultWhitespaceChars updated dblQuotedString but should not",
            )

            EOL = pp.LineEnd().suppress().setName("EOL")

            # Identifiers is a string + optional $
            identifier = pp.Combine(pp.Word(pp.alphas) + pp.Optional("$"))

            # Literals (number or double quoted string)
            literal = ppc.number | pp.dblQuotedString
            expression = literal | identifier
            # expression.setName("expression").setDebug()
            # ppc.number.setDebug()
            # ppc.integer.setDebug()

            line_number = ppc.integer

            # Keywords
            PRINT = pp.CaselessKeyword("print")
            print_stmt = PRINT - pp.ZeroOrMore(expression | ";")
            statement = print_stmt
            code_line = pp.Group(line_number + statement + EOL)
            program = pp.ZeroOrMore(code_line)

            test = """\
            10 print 123;
            20 print 234; 567;
            30 print 890
            """

            parsed_program = program.parseString(test)
            print(parsed_program.dump())
            self.assertEqual(
                3,
                len(parsed_program),
                "failed to apply new whitespace chars to existing builtins",
            )

    def testUpdateDefaultWhitespace2(self):
        with ppt.reset_pyparsing_context():
            expr_tests = [
                (pp.dblQuotedString, '"abc"'),
                (pp.sglQuotedString, "'def'"),
                (ppc.integer, "123"),
                (ppc.number, "4.56"),
                (ppc.identifier, "a_bc"),
            ]
            NL = pp.LineEnd()

            for expr, test_str in expr_tests:
                parser = pp.Group(expr[1, ...] + pp.Optional(NL))[1, ...]
                test_string = "\n".join([test_str] * 3)
                result = parser.parseString(test_string, parseAll=True)
                print(result.dump())
                self.assertEqual(1, len(result), "failed {!r}".format(test_string))

            pp.ParserElement.setDefaultWhitespaceChars(" \t")

            for expr, test_str in expr_tests:
                parser = pp.Group(expr[1, ...] + pp.Optional(NL))[1, ...]
                test_string = "\n".join([test_str] * 3)
                result = parser.parseString(test_string, parseAll=True)
                print(result.dump())
                self.assertEqual(3, len(result), "failed {!r}".format(test_string))

            pp.ParserElement.setDefaultWhitespaceChars(" \n\t")

            for expr, test_str in expr_tests:
                parser = pp.Group(expr[1, ...] + pp.Optional(NL))[1, ...]
                test_string = "\n".join([test_str] * 3)
                result = parser.parseString(test_string, parseAll=True)
                print(result.dump())
                self.assertEqual(1, len(result), "failed {!r}".format(test_string))

    def testParseFourFn(self):
        import examples.fourFn as fourFn
        import math

        def test(s, ans):
            fourFn.exprStack[:] = []
            results = fourFn.BNF().parseString(s)
            try:
                resultValue = fourFn.evaluate_stack(fourFn.exprStack)
            except Exception:
                self.assertIsNone(ans, "exception raised for expression {!r}".format(s))
            else:
                self.assertEqual(
                    ans,
                    resultValue,
                    "failed to evaluate {}, got {:f}".format(s, resultValue),
                )
                print(s, "->", resultValue)

        test("9", 9)
        test("-9", -9)
        test("--9", 9)
        test("-E", -math.e)
        test("9 + 3 + 5", 9 + 3 + 5)
        test("9 + 3 / 11", 9 + 3.0 / 11)
        test("(9 + 3)", (9 + 3))
        test("(9+3) / 11", (9 + 3.0) / 11)
        test("9 - 12 - 6", 9 - 12 - 6)
        test("9 - (12 - 6)", 9 - (12 - 6))
        test("2*3.14159", 2 * 3.14159)
        test("3.1415926535*3.1415926535 / 10", 3.1415926535 * 3.1415926535 / 10)
        test("PI * PI / 10", math.pi * math.pi / 10)
        test("PI*PI/10", math.pi * math.pi / 10)
        test("PI^2", math.pi ** 2)
        test("round(PI^2)", round(math.pi ** 2))
        test("6.02E23 * 8.048", 6.02e23 * 8.048)
        test("e / 3", math.e / 3)
        test("sin(PI/2)", math.sin(math.pi / 2))
        test("10+sin(PI/4)^2", 10 + math.sin(math.pi / 4) ** 2)
        test("trunc(E)", int(math.e))
        test("trunc(-E)", int(-math.e))
        test("round(E)", round(math.e))
        test("round(-E)", round(-math.e))
        test("E^PI", math.e ** math.pi)
        test("exp(0)", 1)
        test("exp(1)", math.e)
        test("2^3^2", 2 ** 3 ** 2)
        test("(2^3)^2", (2 ** 3) ** 2)
        test("2^3+2", 2 ** 3 + 2)
        test("2^3+5", 2 ** 3 + 5)
        test("2^9", 2 ** 9)
        test("sgn(-2)", -1)
        test("sgn(0)", 0)
        test("sgn(0.1)", 1)
        test("foo(0.1)", None)
        test("round(E, 3)", round(math.e, 3))
        test("round(PI^2, 3)", round(math.pi ** 2, 3))
        test("sgn(cos(PI/4))", 1)
        test("sgn(cos(PI/2))", 0)
        test("sgn(cos(PI*3/4))", -1)
        test("+(sgn(cos(PI/4)))", 1)
        test("-(sgn(cos(PI/4)))", -1)

    def testParseSQL(self):
        # SQL parser uses packrat parsing, not compatible with LR
        if ParserElement._left_recursion_enabled:
            return

        import examples.simpleSQL as simpleSQL

        def test(s, num_expected_toks, expected_errloc=-1):
            try:
                sqlToks = flatten(simpleSQL.simpleSQL.parseString(s).asList())
                print(s, sqlToks, len(sqlToks))
                self.assertEqual(
                    num_expected_toks,
                    len(sqlToks),
                    "invalid parsed tokens, expected {}, found {} ({})".format(
                        num_expected_toks, len(sqlToks), sqlToks
                    ),
                )
            except ParseException as e:
                if expected_errloc >= 0:
                    self.assertEqual(
                        expected_errloc,
                        e.loc,
                        "expected error at {}, found at {}".format(
                            expected_errloc, e.loc
                        ),
                    )

        test("SELECT * from XYZZY, ABC", 6)
        test("select * from SYS.XYZZY", 5)
        test("Select A from Sys.dual", 5)
        test("Select A,B,C from Sys.dual", 7)
        test("Select A, B, C from Sys.dual", 7)
        test("Select A, B, C from Sys.dual, Table2   ", 8)
        test("Xelect A, B, C from Sys.dual", 0, 0)
        test("Select A, B, C frox Sys.dual", 0, 15)
        test("Select", 0, 6)
        test("Select &&& frox Sys.dual", 0, 7)
        test("Select A from Sys.dual where a in ('RED','GREEN','BLUE')", 12)
        test(
            "Select A from Sys.dual where a in ('RED','GREEN','BLUE') and b in (10,20,30)",
            20,
        )
        test(
            "Select A,b from table1,table2 where table1.id eq table2.id -- test out comparison operators",
            10,
        )

    def testParseConfigFile(self):
        from examples import configParse

        def test(fnam, num_expected_toks, resCheckList):
            print("Parsing", fnam, "...", end=" ")
            with open(fnam) as infile:
                iniFileLines = "\n".join(infile.read().splitlines())
            iniData = configParse.inifile_BNF().parseString(iniFileLines)
            print(len(flatten(iniData.asList())))
            print(list(iniData.keys()))
            self.assertEqual(
                num_expected_toks,
                len(flatten(iniData.asList())),
                "file %s not parsed correctly" % fnam,
            )
            for chkkey, chkexpect in resCheckList:
                var = iniData
                for attr in chkkey.split("."):
                    var = getattr(var, attr)
                print(chkkey, var, chkexpect)
                self.assertEqual(
                    chkexpect,
                    var,
                    "ParseConfigFileTest: failed to parse ini {!r} as expected {!r}, found {}".format(
                        chkkey, chkexpect, var
                    ),
                )
            print("OK")

        test(
            "tests/karthik.ini",
            23,
            [("users.K", "8"), ("users.mod_scheme", "'QPSK'"), ("users.Na", "K+2")],
        )
        test(
            "examples/Setup.ini",
            125,
            [
                ("Startup.audioinf", "M3i"),
                ("Languages.key1", "0x0003"),
                ("test.foo", "bar"),
            ],
        )

    def testParseJSONData(self):
        expected = [
            {
                "glossary": {
                    "GlossDiv": {
                        "GlossList": [
                            {
                                "Abbrev": "ISO 8879:1986",
                                "Acronym": "SGML",
                                "AvogadroNumber": 6.02e23,
                                "EmptyDict": {},
                                "EmptyList": [],
                                "EvenPrimesGreaterThan2": [],
                                "FermatTheoremInMargin": False,
                                "GlossDef": "A meta-markup language, "
                                "used to create markup "
                                "languages such as "
                                "DocBook.",
                                "GlossSeeAlso": ["GML", "XML", "markup"],
                                "GlossTerm": "Standard Generalized " "Markup Language",
                                "ID": "SGML",
                                "LargestPrimeLessThan100": 97,
                                "MapRequiringFiveColors": None,
                                "PrimesLessThan10": [2, 3, 5, 7],
                                "SortAs": "SGML",
                            }
                        ],
                        "title": "S",
                    },
                    "title": "example glossary",
                }
            },
            {
                "menu": {
                    "id": "file",
                    "popup": {
                        "menuitem": [
                            {"onclick": "CreateNewDoc()", "value": "New"},
                            {"onclick": "OpenDoc()", "value": "Open"},
                            {"onclick": "CloseDoc()", "value": "Close"},
                        ]
                    },
                    "value": "File:",
                }
            },
            {
                "widget": {
                    "debug": "on",
                    "image": {
                        "alignment": "center",
                        "hOffset": 250,
                        "name": "sun1",
                        "src": "Images/Sun.png",
                        "vOffset": 250,
                    },
                    "text": {
                        "alignment": "center",
                        "data": "Click Here",
                        "hOffset": 250,
                        "name": "text1",
                        "onMouseUp": "sun1.opacity = (sun1.opacity / 100) * 90;",
                        "size": 36,
                        "style": "bold",
                        "vOffset": 100,
                    },
                    "window": {
                        "height": 500,
                        "name": "main_window",
                        "title": "Sample Konfabulator Widget",
                        "width": 500,
                    },
                }
            },
            {
                "web-app": {
                    "servlet": [
                        {
                            "init-param": {
                                "cachePackageTagsRefresh": 60,
                                "cachePackageTagsStore": 200,
                                "cachePackageTagsTrack": 200,
                                "cachePagesDirtyRead": 10,
                                "cachePagesRefresh": 10,
                                "cachePagesStore": 100,
                                "cachePagesTrack": 200,
                                "cacheTemplatesRefresh": 15,
                                "cacheTemplatesStore": 50,
                                "cacheTemplatesTrack": 100,
                                "configGlossary:adminEmail": "ksm@pobox.com",
                                "configGlossary:installationAt": "Philadelphia, " "PA",
                                "configGlossary:poweredBy": "Cofax",
                                "configGlossary:poweredByIcon": "/images/cofax.gif",
                                "configGlossary:staticPath": "/content/static",
                                "dataStoreClass": "org.cofax.SqlDataStore",
                                "dataStoreConnUsageLimit": 100,
                                "dataStoreDriver": "com.microsoft.jdbc.sqlserver.SQLServerDriver",
                                "dataStoreInitConns": 10,
                                "dataStoreLogFile": "/usr/local/tomcat/logs/datastore.log",
                                "dataStoreLogLevel": "debug",
                                "dataStoreMaxConns": 100,
                                "dataStoreName": "cofax",
                                "dataStorePassword": "dataStoreTestQuery",
                                "dataStoreTestQuery": "SET NOCOUNT "
                                "ON;select "
                                "test='test';",
                                "dataStoreUrl": "jdbc:microsoft:sqlserver://LOCALHOST:1433;DatabaseName=goon",
                                "dataStoreUser": "sa",
                                "defaultFileTemplate": "articleTemplate.htm",
                                "defaultListTemplate": "listTemplate.htm",
                                "jspFileTemplate": "articleTemplate.jsp",
                                "jspListTemplate": "listTemplate.jsp",
                                "maxUrlLength": 500,
                                "redirectionClass": "org.cofax.SqlRedirection",
                                "searchEngineFileTemplate": "forSearchEngines.htm",
                                "searchEngineListTemplate": "forSearchEnginesList.htm",
                                "searchEngineRobotsDb": "WEB-INF/robots.db",
                                "templateLoaderClass": "org.cofax.FilesTemplateLoader",
                                "templateOverridePath": "",
                                "templatePath": "templates",
                                "templateProcessorClass": "org.cofax.WysiwygTemplate",
                                "useDataStore": True,
                                "useJSP": False,
                            },
                            "servlet-class": "org.cofax.cds.CDSServlet",
                            "servlet-name": "cofaxCDS",
                        },
                        {
                            "init-param": {
                                "mailHost": "mail1",
                                "mailHostOverride": "mail2",
                            },
                            "servlet-class": "org.cofax.cds.EmailServlet",
                            "servlet-name": "cofaxEmail",
                        },
                        {
                            "servlet-class": "org.cofax.cds.AdminServlet",
                            "servlet-name": "cofaxAdmin",
                        },
                        {
                            "servlet-class": "org.cofax.cds.FileServlet",
                            "servlet-name": "fileServlet",
                        },
                        {
                            "init-param": {
                                "adminGroupID": 4,
                                "betaServer": True,
                                "dataLog": 1,
                                "dataLogLocation": "/usr/local/tomcat/logs/dataLog.log",
                                "dataLogMaxSize": "",
                                "fileTransferFolder": "/usr/local/tomcat/webapps/content/fileTransferFolder",
                                "log": 1,
                                "logLocation": "/usr/local/tomcat/logs/CofaxTools.log",
                                "logMaxSize": "",
                                "lookInContext": 1,
                                "removePageCache": "/content/admin/remove?cache=pages&id=",
                                "removeTemplateCache": "/content/admin/remove?cache=templates&id=",
                                "templatePath": "toolstemplates/",
                            },
                            "servlet-class": "org.cofax.cms.CofaxToolsServlet",
                            "servlet-name": "cofaxTools",
                        },
                    ],
                    "servlet-mapping": {
                        "cofaxAdmin": "/admin/*",
                        "cofaxCDS": "/",
                        "cofaxEmail": "/cofaxutil/aemail/*",
                        "cofaxTools": "/tools/*",
                        "fileServlet": "/static/*",
                    },
                    "taglib": {
                        "taglib-location": "/WEB-INF/tlds/cofax.tld",
                        "taglib-uri": "cofax.tld",
                    },
                }
            },
            {
                "menu": {
                    "header": "SVG Viewer",
                    "items": [
                        {"id": "Open"},
                        {"id": "OpenNew", "label": "Open New"},
                        None,
                        {"id": "ZoomIn", "label": "Zoom In"},
                        {"id": "ZoomOut", "label": "Zoom Out"},
                        {"id": "OriginalView", "label": "Original View"},
                        None,
                        {"id": "Quality"},
                        {"id": "Pause"},
                        {"id": "Mute"},
                        None,
                        {"id": "Find", "label": "Find..."},
                        {"id": "FindAgain", "label": "Find Again"},
                        {"id": "Copy"},
                        {"id": "CopyAgain", "label": "Copy Again"},
                        {"id": "CopySVG", "label": "Copy SVG"},
                        {"id": "ViewSVG", "label": "View SVG"},
                        {"id": "ViewSource", "label": "View Source"},
                        {"id": "SaveAs", "label": "Save As"},
                        None,
                        {"id": "Help"},
                        {"id": "About", "label": "About Adobe CVG Viewer..."},
                    ],
                }
            },
        ]

        for t, exp_result in zip((test1, test2, test3, test4, test5), expected):
            result = jsonObject.parseString(t)
            self.assertEqual(exp_result, result[0])

    def testParseCommaSeparatedValues(self):
        testData = [
            "a,b,c,100.2,,3",
            "d, e, j k , m  ",
            "'Hello, World', f, g , , 5.1,x",
            "John Doe, 123 Main St., Cleveland, Ohio",
            "Jane Doe, 456 St. James St., Los Angeles , California   ",
            "",
        ]
        testVals = [
            [(3, "100.2"), (4, ""), (5, "3")],
            [(2, "j k"), (3, "m")],
            [(0, "'Hello, World'"), (2, "g"), (3, "")],
            [(0, "John Doe"), (1, "123 Main St."), (2, "Cleveland"), (3, "Ohio")],
            [
                (0, "Jane Doe"),
                (1, "456 St. James St."),
                (2, "Los Angeles"),
                (3, "California"),
            ],
        ]
        for line, tests in zip(testData, testVals):
            print("Parsing: %r ->" % line, end=" ")
            results = ppc.comma_separated_list.parseString(line)
            print(results)
            for t in tests:
                if not (len(results) > t[0] and results[t[0]] == t[1]):
                    print("$$$", results.dump())
                    print("$$$", results[0])
                self.assertTrue(
                    len(results) > t[0] and results[t[0]] == t[1],
                    "failed on %s, item %d s/b '%s', got '%s'"
                    % (line, t[0], t[1], str(results.asList())),
                )

    def testParseEBNF(self):
        from examples import ebnf

        print("Constructing EBNF parser with pyparsing...")

        grammar = """
        syntax = (syntax_rule), {(syntax_rule)};
        syntax_rule = meta_identifier, '=', definitions_list, ';';
        definitions_list = single_definition, {'|', single_definition};
        single_definition = syntactic_term, {',', syntactic_term};
        syntactic_term = syntactic_factor,['-', syntactic_factor];
        syntactic_factor = [integer, '*'], syntactic_primary;
        syntactic_primary = optional_sequence | repeated_sequence |
          grouped_sequence | meta_identifier | terminal_string;
        optional_sequence = '[', definitions_list, ']';
        repeated_sequence = '{', definitions_list, '}';
        grouped_sequence = '(', definitions_list, ')';
        (*
        terminal_string = "'", character - "'", {character - "'"}, "'" |
          '"', character - '"', {character - '"'}, '"';
         meta_identifier = letter, {letter | digit};
        integer = digit, {digit};
        *)
        """

        table = {}
        table["terminal_string"] = pp.quotedString
        table["meta_identifier"] = pp.Word(pp.alphas + "_", pp.alphas + "_" + pp.nums)
        table["integer"] = pp.Word(pp.nums)

        print("Parsing EBNF grammar with EBNF parser...")
        parsers = ebnf.parse(grammar, table)
        ebnf_parser = parsers["syntax"]
        print("-", "\n- ".join(parsers.keys()))
        self.assertEqual(
            13, len(list(parsers.keys())), "failed to construct syntax grammar"
        )

        print("Parsing EBNF grammar with generated EBNF parser...")
        parsed_chars = ebnf_parser.parseString(grammar)
        parsed_char_len = len(parsed_chars)

        print("],\n".join(str(parsed_chars.asList()).split("],")))
        self.assertEqual(
            98,
            len(flatten(parsed_chars.asList())),
            "failed to tokenize grammar correctly",
        )

    def testParseIDL(self):
        from examples import idlParse

        def test(strng, numToks, expectedErrloc=0):
            print(strng)
            try:
                bnf = idlParse.CORBA_IDL_BNF()
                tokens = bnf.parseString(strng)
                print("tokens = ")
                tokens.pprint()
                tokens = flatten(tokens.asList())
                print(len(tokens))
                self.assertEqual(
                    numToks,
                    len(tokens),
                    "error matching IDL string, {} -> {}".format(strng, str(tokens)),
                )
            except ParseException as err:
                print(err.line)
                print(" " * (err.column - 1) + "^")
                print(err)
                self.assertEqual(
                    0,
                    numToks,
                    "unexpected ParseException while parsing {}, {}".format(
                        strng, str(err)
                    ),
                )
                self.assertEqual(
                    expectedErrloc,
                    err.loc,
                    "expected ParseException at %d, found exception at %d"
                    % (expectedErrloc, err.loc),
                )

        test(
            """
            /*
             * a block comment *
             */
            typedef string[10] tenStrings;
            typedef sequence<string> stringSeq;
            typedef sequence< sequence<string> > stringSeqSeq;

            interface QoSAdmin {
                stringSeq method1(in string arg1, inout long arg2);
                stringSeqSeq method2(in string arg1, inout long arg2, inout long arg3);
                string method3();
              };
            """,
            59,
        )
        test(
            """
            /*
             * a block comment *
             */
            typedef string[10] tenStrings;
            typedef
                /** ** *** **** *
                 * a block comment *
                 */
                sequence<string> /*comment inside an And */ stringSeq;
            /* */  /**/ /***/ /****/
            typedef sequence< sequence<string> > stringSeqSeq;

            interface QoSAdmin {
                stringSeq method1(in string arg1, inout long arg2);
                stringSeqSeq method2(in string arg1, inout long arg2, inout long arg3);
                string method3();
              };
            """,
            59,
        )
        test(
            r"""
              const string test="Test String\n";
              const long  a = 0;
              const long  b = -100;
              const float c = 3.14159;
              const long  d = 0x007f7f7f;
              exception TestException
                {
                string msg;
                sequence<string> dataStrings;
                };

              interface TestInterface
                {
                void method1(in string arg1, inout long arg2);
                };
            """,
            60,
        )
        test(
            """
            module Test1
              {
              exception TestException
                {
                string msg;
                ];

              interface TestInterface
                {
                void method1(in string arg1, inout long arg2)
                  raises (TestException);
                };
              };
            """,
            0,
            56,
        )
        test(
            """
            module Test1
              {
              exception TestException
                {
                string msg;
                };

              };
            """,
            13,
        )

    def testParseVerilog(self):
        pass

    def testScanString(self):

        testdata = """
            <table border="0" cellpadding="3" cellspacing="3" frame="" width="90%">
                <tr align="left" valign="top">
                        <td><b>Name</b></td>
                        <td><b>IP Address</b></td>
                        <td><b>Location</b></td>
                </tr>
                <tr align="left" valign="top" bgcolor="#c7efce">
                        <td>time-a.nist.gov</td>
                        <td>129.6.15.28</td>
                        <td>NIST, Gaithersburg, Maryland</td>
                </tr>
                <tr align="left" valign="top">
                        <td>time-b.nist.gov</td>
                        <td>129.6.15.29</td>
                        <td>NIST, Gaithersburg, Maryland</td>
                </tr>
                <tr align="left" valign="top" bgcolor="#c7efce">
                        <td>time-a.timefreq.bldrdoc.gov</td>
                        <td>132.163.4.101</td>
                        <td>NIST, Boulder, Colorado</td>
                </tr>
                <tr align="left" valign="top">
                        <td>time-b.timefreq.bldrdoc.gov</td>
                        <td>132.163.4.102</td>
                        <td>NIST, Boulder, Colorado</td>
                </tr>
                <tr align="left" valign="top" bgcolor="#c7efce">
                        <td>time-c.timefreq.bldrdoc.gov</td>
                        <td>132.163.4.103</td>
                        <td>NIST, Boulder, Colorado</td>
                </tr>
            </table>
            """
        integer = pp.Word(pp.nums)
        ipAddress = pp.Combine(integer + "." + integer + "." + integer + "." + integer)
        tdStart = pp.Suppress("<td>")
        tdEnd = pp.Suppress("</td>")
        timeServerPattern = (
            tdStart
            + ipAddress("ipAddr")
            + tdEnd
            + tdStart
            + pp.CharsNotIn("<")("loc")
            + tdEnd
        )
        servers = [
            srvr.ipAddr
            for srvr, startloc, endloc in timeServerPattern.scanString(testdata)
        ]

        print(servers)
        self.assertEqual(
            [
                "129.6.15.28",
                "129.6.15.29",
                "132.163.4.101",
                "132.163.4.102",
                "132.163.4.103",
            ],
            servers,
            "failed scanString()",
        )

        # test for stringEnd detection in scanString
        foundStringEnds = [r for r in pp.StringEnd().scanString("xyzzy")]
        print(foundStringEnds)
        self.assertTrue(foundStringEnds, "Failed to find StringEnd in scanString")

    def testQuotedStrings(self):
        testData = """
                'a valid single quoted string'
                'an invalid single quoted string
                 because it spans lines'
                "a valid double quoted string"
                "an invalid double quoted string
                 because it spans lines"
            """
        print(testData)

        sglStrings = [
            (t[0], b, e) for (t, b, e) in pp.sglQuotedString.scanString(testData)
        ]
        print(sglStrings)
        self.assertTrue(
            len(sglStrings) == 1
            and (sglStrings[0][1] == 17 and sglStrings[0][2] == 47),
            "single quoted string failure",
        )

        dblStrings = [
            (t[0], b, e) for (t, b, e) in pp.dblQuotedString.scanString(testData)
        ]
        print(dblStrings)
        self.assertTrue(
            len(dblStrings) == 1
            and (dblStrings[0][1] == 154 and dblStrings[0][2] == 184),
            "double quoted string failure",
        )

        allStrings = [
            (t[0], b, e) for (t, b, e) in pp.quotedString.scanString(testData)
        ]
        print(allStrings)
        self.assertTrue(
            len(allStrings) == 2
            and (allStrings[0][1] == 17 and allStrings[0][2] == 47)
            and (allStrings[1][1] == 154 and allStrings[1][2] == 184),
            "quoted string failure",
        )

        escapedQuoteTest = r"""
                'This string has an escaped (\') quote character'
                "This string has an escaped (\") quote character"
            """

        sglStrings = [
            (t[0], b, e)
            for (t, b, e) in pp.sglQuotedString.scanString(escapedQuoteTest)
        ]
        print(sglStrings)
        self.assertTrue(
            len(sglStrings) == 1
            and (sglStrings[0][1] == 17 and sglStrings[0][2] == 66),
            "single quoted string escaped quote failure (%s)" % str(sglStrings[0]),
        )

        dblStrings = [
            (t[0], b, e)
            for (t, b, e) in pp.dblQuotedString.scanString(escapedQuoteTest)
        ]
        print(dblStrings)
        self.assertTrue(
            len(dblStrings) == 1
            and (dblStrings[0][1] == 83 and dblStrings[0][2] == 132),
            "double quoted string escaped quote failure (%s)" % str(dblStrings[0]),
        )

        allStrings = [
            (t[0], b, e) for (t, b, e) in pp.quotedString.scanString(escapedQuoteTest)
        ]
        print(allStrings)
        self.assertTrue(
            len(allStrings) == 2
            and (
                allStrings[0][1] == 17
                and allStrings[0][2] == 66
                and allStrings[1][1] == 83
                and allStrings[1][2] == 132
            ),
            "quoted string escaped quote failure (%s)"
            % ([str(s[0]) for s in allStrings]),
        )

        dblQuoteTest = r"""
                'This string has an doubled ('') quote character'
                "This string has an doubled ("") quote character"
            """
        sglStrings = [
            (t[0], b, e) for (t, b, e) in pp.sglQuotedString.scanString(dblQuoteTest)
        ]
        print(sglStrings)
        self.assertTrue(
            len(sglStrings) == 1
            and (sglStrings[0][1] == 17 and sglStrings[0][2] == 66),
            "single quoted string escaped quote failure (%s)" % str(sglStrings[0]),
        )
        dblStrings = [
            (t[0], b, e) for (t, b, e) in pp.dblQuotedString.scanString(dblQuoteTest)
        ]
        print(dblStrings)
        self.assertTrue(
            len(dblStrings) == 1
            and (dblStrings[0][1] == 83 and dblStrings[0][2] == 132),
            "double quoted string escaped quote failure (%s)" % str(dblStrings[0]),
        )
        allStrings = [
            (t[0], b, e) for (t, b, e) in pp.quotedString.scanString(dblQuoteTest)
        ]
        print(allStrings)
        self.assertTrue(
            len(allStrings) == 2
            and (
                allStrings[0][1] == 17
                and allStrings[0][2] == 66
                and allStrings[1][1] == 83
                and allStrings[1][2] == 132
            ),
            "quoted string escaped quote failure (%s)"
            % ([str(s[0]) for s in allStrings]),
        )

        print(
            "testing catastrophic RE backtracking in implementation of dblQuotedString"
        )
        for expr, test_string in [
            (pp.dblQuotedString, '"' + "\\xff" * 500),
            (pp.sglQuotedString, "'" + "\\xff" * 500),
            (pp.quotedString, '"' + "\\xff" * 500),
            (pp.quotedString, "'" + "\\xff" * 500),
            (pp.QuotedString('"'), '"' + "\\xff" * 500),
            (pp.QuotedString("'"), "'" + "\\xff" * 500),
        ]:
            expr.parseString(test_string + test_string[0])
            try:
                expr.parseString(test_string)
            except Exception:
                continue

        # test invalid endQuoteChar
        with self.assertRaises(
            ValueError, msg="issue raising error for invalid endQuoteChar"
        ):
            expr = pp.QuotedString('"', endQuoteChar=" ")

    def testCaselessOneOf(self):
        caseless1 = pp.oneOf("d a b c aA B A C", caseless=True)
        caseless1str = str(caseless1)
        print(caseless1str)
        caseless2 = pp.oneOf("d a b c Aa B A C", caseless=True)
        caseless2str = str(caseless2)
        print(caseless2str)
        self.assertEqual(
            caseless1str.upper(),
            caseless2str.upper(),
            "oneOf not handling caseless option properly",
        )
        self.assertNotEqual(
            caseless1str, caseless2str, "Caseless option properly sorted"
        )

        res = caseless1[...].parseString("AAaaAaaA")
        print(res)
        self.assertEqual(4, len(res), "caseless1 oneOf failed")
        self.assertEqual(
            "aA" * 4, "".join(res), "caseless1 CaselessLiteral return failed"
        )

        res = caseless2[...].parseString("AAaaAaaA")
        print(res)
        self.assertEqual(4, len(res), "caseless2 oneOf failed")
        self.assertEqual(
            "Aa" * 4, "".join(res), "caseless1 CaselessLiteral return failed"
        )

    def testCommentParser(self):
        print("verify processing of C and HTML comments")
        testdata = """
        /* */
        /** **/
        /**/
        /***/
        /****/
        /* /*/
        /** /*/
        /*** /*/
        /*
         ablsjdflj
         */
        """
        foundLines = [
            pp.lineno(s, testdata) for t, s, e in pp.cStyleComment.scanString(testdata)
        ]
        self.assertEqual(
            list(range(11))[2:],
            foundLines,
            "only found C comments on lines " + str(foundLines),
        )
        testdata = """
        <!-- -->
        <!--- --->
        <!---->
        <!----->
        <!------>
        <!-- /-->
        <!--- /-->
        <!---- /-->
        <!---- /- ->
        <!---- / -- >
        <!--
         ablsjdflj
         -->
        """
        foundLines = [
            pp.lineno(s, testdata) for t, s, e in pp.htmlComment.scanString(testdata)
        ]
        self.assertEqual(
            list(range(11))[2:],
            foundLines,
            "only found HTML comments on lines " + str(foundLines),
        )

        # test C++ single line comments that have line terminated with '\' (should continue comment to following line)
        testSource = r"""
            // comment1
            // comment2 \
            still comment 2
            // comment 3
            """
        self.assertEqual(
            41,
            len(pp.cppStyleComment.searchString(testSource)[1][0]),
            r"failed to match single-line comment with '\' at EOL",
        )

    def testParseExpressionResults(self):
        a = pp.Word("a", pp.alphas).setName("A")
        b = pp.Word("b", pp.alphas).setName("B")
        c = pp.Word("c", pp.alphas).setName("C")
        ab = (a + b).setName("AB")
        abc = (ab + c).setName("ABC")
        word = pp.Word(pp.alphas).setName("word")

        words = pp.Group(pp.OneOrMore(~a + word)).setName("words")

        phrase = (
            words("Head")
            + pp.Group(a + pp.Optional(b + pp.Optional(c)))("ABC")
            + words("Tail")
        )

        results = phrase.parseString("xavier yeti alpha beta charlie will beaver")
        print(results, results.Head, results.ABC, results.Tail)
        for key, ln in [("Head", 2), ("ABC", 3), ("Tail", 2)]:
            self.assertEqual(
                ln,
                len(results[key]),
                "expected %d elements in %s, found %s" % (ln, key, str(results[key])),
            )

    def testParseKeyword(self):
        kw = pp.Keyword("if")
        lit = pp.Literal("if")

        def test(s, litShouldPass, kwShouldPass):
            print("Test", s)
            print("Match Literal", end=" ")
            try:
                print(lit.parseString(s))
            except Exception:
                print("failed")
                if litShouldPass:
                    self.fail("Literal failed to match %s, should have" % s)
            else:
                if not litShouldPass:
                    self.fail("Literal matched %s, should not have" % s)

            print("Match Keyword", end=" ")
            try:
                print(kw.parseString(s))
            except Exception:
                print("failed")
                if kwShouldPass:
                    self.fail("Keyword failed to match %s, should have" % s)
            else:
                if not kwShouldPass:
                    self.fail("Keyword matched %s, should not have" % s)

        test("ifOnlyIfOnly", True, False)
        test("if(OnlyIfOnly)", True, True)
        test("if (OnlyIf Only)", True, True)

        kw = pp.Keyword("if", caseless=True)

        test("IFOnlyIfOnly", False, False)
        test("If(OnlyIfOnly)", False, True)
        test("iF (OnlyIf Only)", False, True)

        with self.assertRaises(
            ValueError, msg="failed to warn empty string passed to Keyword"
        ):
            kw = pp.Keyword("")

    def testParseExpressionResultsAccumulate(self):
        num = pp.Word(pp.nums).setName("num")("base10*")
        hexnum = pp.Combine("0x" + pp.Word(pp.nums)).setName("hexnum")("hex*")
        name = pp.Word(pp.alphas).setName("word")("word*")
        list_of_num = pp.delimitedList(hexnum | num | name, ",")

        tokens = list_of_num.parseString("1, 0x2, 3, 0x4, aaa")
        print(tokens.dump())
        self.assertParseResultsEquals(
            tokens,
            expected_list=["1", "0x2", "3", "0x4", "aaa"],
            expected_dict={
                "base10": ["1", "3"],
                "hex": ["0x2", "0x4"],
                "word": ["aaa"],
            },
        )

        lbrack = pp.Literal("(").suppress()
        rbrack = pp.Literal(")").suppress()
        integer = pp.Word(pp.nums).setName("int")
        variable = pp.Word(pp.alphas, max=1).setName("variable")
        relation_body_item = (
            variable | integer | pp.quotedString().setParseAction(pp.removeQuotes)
        )
        relation_name = pp.Word(pp.alphas + "_", pp.alphanums + "_")
        relation_body = lbrack + pp.Group(pp.delimitedList(relation_body_item)) + rbrack
        Goal = pp.Dict(pp.Group(relation_name + relation_body))
        Comparison_Predicate = pp.Group(variable + pp.oneOf("< >") + integer)("pred*")
        Query = Goal("head") + ":-" + pp.delimitedList(Goal | Comparison_Predicate)

        test = """Q(x,y,z):-Bloo(x,"Mitsis",y),Foo(y,z,1243),y>28,x<12,x>3"""

        queryRes = Query.parseString(test)
        print(queryRes.dump())
        self.assertParseResultsEquals(
            queryRes.pred,
            expected_list=[["y", ">", "28"], ["x", "<", "12"], ["x", ">", "3"]],
            msg="Incorrect list for attribute pred, %s" % str(queryRes.pred.asList()),
        )

    def testReStringRange(self):
        testCases = (
            r"[A-Z]",
            r"[A-A]",
            r"[A-Za-z]",
            r"[A-z]",
            r"[\ -\~]",
            r"[\0x20-0]",
            r"[\0x21-\0x7E]",
            r"[\0xa1-\0xfe]",
            r"[\040-0]",
            r"[A-Za-z0-9]",
            r"[A-Za-z0-9_]",
            r"[A-Za-z0-9_$]",
            r"[A-Za-z0-9_$\-]",
            r"[^0-9\\]",
            r"[a-zA-Z]",
            r"[/\^~]",
            r"[=\+\-!]",
            r"[A-]",
            r"[-A]",
            r"[\x21]",
            r"[а-яА-ЯёЁA-Z$_\041α-ω]",
            r"[\0xc0-\0xd6\0xd8-\0xf6\0xf8-\0xff]",
            r"[\0xa1-\0xbf\0xd7\0xf7]",
            r"[\0xc0-\0xd6\0xd8-\0xf6\0xf8-\0xff]",
            r"[\0xa1-\0xbf\0xd7\0xf7]",
        )
        expectedResults = (
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "A",
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz",
            " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~",
            " !\"#$%&'()*+,-./0",
            "!\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~",
            "¡¢£¤¥¦§¨©ª«¬­®¯°±²³´µ¶·¸¹º»¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþ",
            " !\"#$%&'()*+,-./0",
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_",
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_$",
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_$-",
            "0123456789\\",
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "/^~",
            "=+-!",
            "A-",
            "-A",
            "!",
            "абвгдежзийклмнопрстуфхцчшщъыьэюяАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯёЁABCDEFGHIJKLMNOPQRSTUVWXYZ$_!αβγδεζηθικλμνξοπρςστυφχψω",
            "ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ",
            "¡¢£¤¥¦§¨©ª«¬\xad®¯°±²³´µ¶·¸¹º»¼½¾¿×÷",
            pp.alphas8bit,
            pp.punc8bit,
        )
        for test in zip(testCases, expectedResults):
            t, exp = test
            res = pp.srange(t)
            # print(t, "->", res)
            self.assertEqual(
                exp,
                res,
                "srange error, srange({!r})->'{!r}', expected '{!r}'".format(
                    t, res, exp
                ),
            )

    def testSkipToParserTests(self):
        thingToFind = pp.Literal("working")
        testExpr = (
            pp.SkipTo(pp.Literal(";"), include=True, ignore=pp.cStyleComment)
            + thingToFind
        )

        def test_parse(someText):
            print(testExpr.parseString(someText))

        # This first test works, as the SkipTo expression is immediately following the ignore expression (cStyleComment)
        test_parse("some text /* comment with ; in */; working")
        # This second test previously failed, as there is text following the ignore expression, and before the SkipTo expression.
        test_parse("some text /* comment with ; in */some other stuff; working")

        # tests for optional failOn argument
        testExpr = (
            pp.SkipTo(
                pp.Literal(";"), include=True, ignore=pp.cStyleComment, failOn="other"
            )
            + thingToFind
        )
        test_parse("some text /* comment with ; in */; working")

        with self.assertRaisesParseException():
            test_parse("some text /* comment with ; in */some other stuff; working")

        # test that we correctly create named results
        text = "prefixDATAsuffix"
        data = pp.Literal("DATA")
        suffix = pp.Literal("suffix")
        expr = pp.SkipTo(data + suffix)("prefix") + data + suffix
        result = expr.parseString(text)
        self.assertTrue(
            isinstance(result.prefix, str),
            "SkipTo created with wrong saveAsList attribute",
        )

        alpha_word = (~pp.Literal("end") + pp.Word(pp.alphas, asKeyword=True)).setName(
            "alpha"
        )
        num_word = pp.Word(pp.nums, asKeyword=True).setName("int")

        def test(expr, test_string, expected_list, expected_dict):
            if (expected_list, expected_dict) == (None, None):
                with self.assertRaises(
                    Exception, msg="{} failed to parse {!r}".format(expr, test_string)
                ):
                    expr.parseString(test_string)
            else:
                result = expr.parseString(test_string)
                self.assertParseResultsEquals(
                    result, expected_list=expected_list, expected_dict=expected_dict
                )

        # ellipses for SkipTo
        e = ... + pp.Literal("end")
        test(e, "start 123 end", ["start 123 ", "end"], {"_skipped": ["start 123 "]})

        e = pp.Suppress(...) + pp.Literal("end")
        test(e, "start 123 end", ["end"], {})

        e = pp.Literal("start") + ... + pp.Literal("end")
        test(e, "start 123 end", ["start", "123 ", "end"], {"_skipped": ["123 "]})

        e = ... + pp.Literal("middle") + ... + pp.Literal("end")
        test(
            e,
            "start 123 middle 456 end",
            ["start 123 ", "middle", "456 ", "end"],
            {"_skipped": ["start 123 ", "456 "]},
        )

        e = pp.Suppress(...) + pp.Literal("middle") + ... + pp.Literal("end")
        test(
            e,
            "start 123 middle 456 end",
            ["middle", "456 ", "end"],
            {"_skipped": ["456 "]},
        )

        e = pp.Literal("start") + ...
        test(e, "start 123 end", None, None)

        e = pp.And(["start", ..., "end"])
        test(e, "start 123 end", ["start", "123 ", "end"], {"_skipped": ["123 "]})

        e = pp.And([..., "end"])
        test(e, "start 123 end", ["start 123 ", "end"], {"_skipped": ["start 123 "]})

        e = "start" + (num_word | ...) + "end"
        test(e, "start 456 end", ["start", "456", "end"], {})
        test(
            e,
            "start 123 456 end",
            ["start", "123", "456 ", "end"],
            {"_skipped": ["456 "]},
        )
        test(e, "start end", ["start", "", "end"], {"_skipped": ["missing <int>"]})

        # e = define_expr('"start" + (num_word | ...)("inner") + "end"')
        # test(e, "start 456 end", ['start', '456', 'end'], {'inner': '456'})

        e = "start" + (alpha_word[...] & num_word[...] | ...) + "end"
        test(e, "start 456 red end", ["start", "456", "red", "end"], {})
        test(e, "start red 456 end", ["start", "red", "456", "end"], {})
        test(
            e,
            "start 456 red + end",
            ["start", "456", "red", "+ ", "end"],
            {"_skipped": ["+ "]},
        )
        test(e, "start red end", ["start", "red", "end"], {})
        test(e, "start 456 end", ["start", "456", "end"], {})
        test(e, "start end", ["start", "end"], {})
        test(e, "start 456 + end", ["start", "456", "+ ", "end"], {"_skipped": ["+ "]})

        e = "start" + (alpha_word[1, ...] & num_word[1, ...] | ...) + "end"
        test(e, "start 456 red end", ["start", "456", "red", "end"], {})
        test(e, "start red 456 end", ["start", "red", "456", "end"], {})
        test(
            e,
            "start 456 red + end",
            ["start", "456", "red", "+ ", "end"],
            {"_skipped": ["+ "]},
        )
        test(e, "start red end", ["start", "red ", "end"], {"_skipped": ["red "]})
        test(e, "start 456 end", ["start", "456 ", "end"], {"_skipped": ["456 "]})
        test(
            e,
            "start end",
            ["start", "", "end"],
            {"_skipped": ["missing <{{alpha}... & {int}...}>"]},
        )
        test(e, "start 456 + end", ["start", "456 + ", "end"], {"_skipped": ["456 + "]})

        e = "start" + (alpha_word | ...) + (num_word | ...) + "end"
        test(e, "start red 456 end", ["start", "red", "456", "end"], {})
        test(
            e,
            "start red end",
            ["start", "red", "", "end"],
            {"_skipped": ["missing <int>"]},
        )
        test(
            e,
            "start end",
            ["start", "", "", "end"],
            {"_skipped": ["missing <alpha>", "missing <int>"]},
        )

        e = pp.Literal("start") + ... + "+" + ... + "end"
        test(
            e,
            "start red + 456 end",
            ["start", "red ", "+", "456 ", "end"],
            {"_skipped": ["red ", "456 "]},
        )

    def testEllipsisRepetition(self):

        word = pp.Word(pp.alphas).setName("word")
        num = pp.Word(pp.nums).setName("num")

        exprs = [
            word[...] + num,
            word[0, ...] + num,
            word[1, ...] + num,
            word[2, ...] + num,
            word[..., 3] + num,
            word[2] + num,
        ]

        expected_res = [
            r"([abcd]+ )*\d+",
            r"([abcd]+ )*\d+",
            r"([abcd]+ )+\d+",
            r"([abcd]+ ){2,}\d+",
            r"([abcd]+ ){0,3}\d+",
            r"([abcd]+ ){2}\d+",
        ]

        tests = ["aa bb cc dd 123", "bb cc dd 123", "cc dd 123", "dd 123", "123"]

        all_success = True
        for expr, expected_re in zip(exprs, expected_res):
            successful_tests = [t for t in tests if re.match(expected_re, t)]
            failure_tests = [t for t in tests if not re.match(expected_re, t)]
            success1, _ = expr.runTests(successful_tests)
            success2, _ = expr.runTests(failure_tests, failureTests=True)
            all_success = all_success and success1 and success2
            if not all_success:
                print("Failed expression:", expr)
                break

        self.assertTrue(all_success, "failed getItem_ellipsis test")

    def testEllipsisRepetitionWithResultsNames(self):
        label = pp.Word(pp.alphas)
        val = ppc.integer()
        parser = label("label") + pp.ZeroOrMore(val)("values")

        _, results = parser.runTests(
            """
            a 1
            b 1 2 3
            c
            """
        )
        expected = [
            (["a", 1], {"label": "a", "values": [1]}),
            (["b", 1, 2, 3], {"label": "b", "values": [1, 2, 3]}),
            (["c"], {"label": "c", "values": []}),
        ]
        for obs, exp in zip(results, expected):
            test, result = obs
            exp_list, exp_dict = exp
            self.assertParseResultsEquals(
                result, expected_list=exp_list, expected_dict=exp_dict
            )

        parser = label("label") + val[...]("values")

        _, results = parser.runTests(
            """
            a 1
            b 1 2 3
            c
            """
        )
        expected = [
            (["a", 1], {"label": "a", "values": [1]}),
            (["b", 1, 2, 3], {"label": "b", "values": [1, 2, 3]}),
            (["c"], {"label": "c", "values": []}),
        ]
        for obs, exp in zip(results, expected):
            test, result = obs
            exp_list, exp_dict = exp
            self.assertParseResultsEquals(
                result, expected_list=exp_list, expected_dict=exp_dict
            )

        pt = pp.Group(val("x") + pp.Suppress(",") + val("y"))
        parser = label("label") + pt[...]("points")
        _, results = parser.runTests(
            """
            a 1,1
            b 1,1 2,2 3,3
            c
            """
        )
        expected = [
            (["a", [1, 1]], {"label": "a", "points": [{"x": 1, "y": 1}]}),
            (
                ["b", [1, 1], [2, 2], [3, 3]],
                {
                    "label": "b",
                    "points": [{"x": 1, "y": 1}, {"x": 2, "y": 2}, {"x": 3, "y": 3}],
                },
            ),
            (["c"], {"label": "c", "points": []}),
        ]
        for obs, exp in zip(results, expected):
            test, result = obs
            exp_list, exp_dict = exp
            self.assertParseResultsEquals(
                result, expected_list=exp_list, expected_dict=exp_dict
            )

    def testCustomQuotes(self):
        testString = r"""
            sdlfjs :sdf\:jls::djf: sl:kfsjf
            sdlfjs -sdf\:jls::--djf: sl-kfsjf
            sdlfjs -sdf\:::jls::--djf: sl:::-kfsjf
            sdlfjs ^sdf\:jls^^--djf^ sl-kfsjf
            sdlfjs ^^^==sdf\:j=lz::--djf: sl=^^=kfsjf
            sdlfjs ==sdf\:j=ls::--djf: sl==kfsjf^^^
        """
        print(testString)

        colonQuotes = pp.QuotedString(":", "\\", "::")
        dashQuotes = pp.QuotedString("-", "\\", "--")
        hatQuotes = pp.QuotedString("^", "\\")
        hatQuotes1 = pp.QuotedString("^", "\\", "^^")
        dblEqQuotes = pp.QuotedString("==", "\\")

        def test(label, quoteExpr, expected):
            print(label)
            print(quoteExpr.pattern)
            print(quoteExpr.searchString(testString))
            print(quoteExpr.searchString(testString)[0][0])
            print(f"{expected}")
            self.assertEqual(
                expected,
                quoteExpr.searchString(testString)[0][0],
                "failed to match {}, expected '{}', got '{}'".format(
                    quoteExpr, expected, quoteExpr.searchString(testString)[0]
                ),
            )
            print()

        test("colonQuotes", colonQuotes, r"sdf:jls:djf")
        test("dashQuotes", dashQuotes, r"sdf:jls::-djf: sl")
        test("hatQuotes", hatQuotes, r"sdf:jls")
        test("hatQuotes1", hatQuotes1, r"sdf:jls^--djf")
        test("dblEqQuotes", dblEqQuotes, r"sdf:j=ls::--djf: sl")
        test("::: quotes", pp.QuotedString(":::"), "jls::--djf: sl")
        test("==-- quotes", pp.QuotedString("==", endQuoteChar="--"), r"sdf\:j=lz::")
        test(
            "^^^ multiline quotes",
            pp.QuotedString("^^^", multiline=True),
            r"""==sdf\:j=lz::--djf: sl=^^=kfsjf
            sdlfjs ==sdf\:j=ls::--djf: sl==kfsjf""",
        )
        with self.assertRaises(ValueError):
            pp.QuotedString("", "\\")

    def testCustomQuotes2(self):

        qs = pp.QuotedString(quote_char=".[", end_quote_char="].")
        print(qs.reString)
        self.assertParseAndCheckList(qs, ".[...].", ['...'])
        self.assertParseAndCheckList(qs, ".[].", [''])
        self.assertParseAndCheckList(qs, ".[]].", [']'])
        self.assertParseAndCheckList(qs, ".[]]].", [']]'])

        qs = pp.QuotedString(quote_char="+*", end_quote_char="*+")
        print(qs.reString)
        self.assertParseAndCheckList(qs, "+*...*+", ['...'])
        self.assertParseAndCheckList(qs, "+**+", [''])
        self.assertParseAndCheckList(qs, "+***+", ['*'])
        self.assertParseAndCheckList(qs, "+****+", ['**'])

        qs = pp.QuotedString(quote_char="*/", end_quote_char="/*")
        print(qs.reString)
        self.assertParseAndCheckList(qs, "*/.../*", ['...'])
        self.assertParseAndCheckList(qs, "*//*", [''])
        self.assertParseAndCheckList(qs, "*///*", ['/'])
        self.assertParseAndCheckList(qs, "*////*", ['//'])

    def testRepeater(self):
        if ParserElement._packratEnabled or ParserElement._left_recursion_enabled:
            print("skipping this test, not compatible with memoization")
            return

        first = pp.Word("abcdef").setName("word1")
        bridge = pp.Word(pp.nums).setName("number")
        second = pp.matchPreviousLiteral(first).setName("repeat(word1Literal)")

        seq = first + bridge + second

        tests = [
            ("abc12abc", True),
            ("abc12aabc", False),
            ("abc12cba", True),
            ("abc12bca", True),
        ]

        for tst, expected in tests:
            found = False
            for tokens, start, end in seq.scanString(tst):
                f, b, s = tokens
                print(f, b, s)
                found = True
            if not found:
                print("No literal match in", tst)
            self.assertEqual(
                expected,
                found,
                "Failed repeater for test: {}, matching {}".format(tst, str(seq)),
            )
        print()

        # retest using matchPreviousExpr instead of matchPreviousLiteral
        second = pp.matchPreviousExpr(first).setName("repeat(word1expr)")
        seq = first + bridge + second

        tests = [("abc12abc", True), ("abc12cba", False), ("abc12abcdef", False)]

        for tst, expected in tests:
            found = False
            for tokens, start, end in seq.scanString(tst):
                print(tokens)
                found = True
            if not found:
                print("No expression match in", tst)
            self.assertEqual(
                expected,
                found,
                "Failed repeater for test: {}, matching {}".format(tst, str(seq)),
            )

        print()

        first = pp.Word("abcdef").setName("word1")
        bridge = pp.Word(pp.nums).setName("number")
        second = pp.matchPreviousExpr(first).setName("repeat(word1)")
        seq = first + bridge + second
        csFirst = seq.setName("word-num-word")
        csSecond = pp.matchPreviousExpr(csFirst)
        compoundSeq = csFirst + ":" + csSecond
        compoundSeq.streamline()
        print(compoundSeq)

        tests = [
            ("abc12abc:abc12abc", True),
            ("abc12cba:abc12abc", False),
            ("abc12abc:abc12abcdef", False),
        ]

        for tst, expected in tests:
            found = False
            for tokens, start, end in compoundSeq.scanString(tst):
                print("match:", tokens)
                found = True
                break
            if not found:
                print("No expression match in", tst)
            self.assertEqual(
                expected,
                found,
                "Failed repeater for test: {}, matching {}".format(tst, str(seq)),
            )

        print()
        eFirst = pp.Word(pp.nums)
        eSecond = pp.matchPreviousExpr(eFirst)
        eSeq = eFirst + ":" + eSecond

        tests = [("1:1A", True), ("1:10", False)]

        for tst, expected in tests:
            found = False
            for tokens, start, end in eSeq.scanString(tst):
                print(tokens)
                found = True
            if not found:
                print("No match in", tst)
            self.assertEqual(
                expected,
                found,
                "Failed repeater for test: {}, matching {}".format(tst, str(seq)),
            )

    def testRepeater2(self):
        """test matchPreviousLiteral with empty repeater"""

        if ParserElement._packratEnabled or ParserElement._left_recursion_enabled:
            print("skipping this test, not compatible with memoization")
            return

        first = pp.Optional(pp.Word("abcdef").setName("words1"))
        bridge = pp.Word(pp.nums).setName("number")
        second = pp.matchPreviousLiteral(first).setName("repeat(word1Literal)")

        seq = first + bridge + second

        tst = "12"
        expected = ["12"]
        result = seq.parseString(tst)
        print(result.dump())

        self.assertParseResultsEquals(result, expected_list=expected)

    def testRepeater3(self):
        """test matchPreviousLiteral with multiple repeater tokens"""

        if ParserElement._packratEnabled or ParserElement._left_recursion_enabled:
            print("skipping this test, not compatible with memoization")
            return

        first = pp.Word("a") + pp.Word("d")
        bridge = pp.Word(pp.nums).setName("number")
        second = pp.matchPreviousLiteral(first)  # ("second")

        seq = first + bridge + second

        tst = "aaaddd12aaaddd"
        expected = ["aaa", "ddd", "12", "aaa", "ddd"]
        result = seq.parseString(tst)
        print(result.dump())

        self.assertParseResultsEquals(result, expected_list=expected)

    def testRepeater4(self):
        """test matchPreviousExpr with multiple repeater tokens"""

        if ParserElement._packratEnabled or ParserElement._left_recursion_enabled:
            print("skipping this test, not compatible with memoization")
            return

        first = pp.Group(pp.Word(pp.alphas) + pp.Word(pp.alphas))
        bridge = pp.Word(pp.nums)

        # no matching is used - this is just here for a sanity check
        # second = pp.Group(pp.Word(pp.alphas) + pp.Word(pp.alphas))("second")
        # second = pp.Group(pp.Word(pp.alphas) + pp.Word(pp.alphas)).setResultsName("second")

        # ISSUE: when matchPreviousExpr returns multiple tokens the matching tokens are nested an extra level deep.
        #           This behavior is not seen with a single return token (see testRepeater5 directly below.)
        second = pp.matchPreviousExpr(first)

        expr = first + bridge.suppress() + second

        tst = "aaa ddd 12 aaa ddd"
        expected = [["aaa", "ddd"], ["aaa", "ddd"]]
        result = expr.parseString(tst)
        print(result.dump())

        self.assertParseResultsEquals(result, expected_list=expected)

    def testRepeater5(self):
        """a simplified testRepeater4 to examine matchPreviousExpr with a single repeater token"""

        if ParserElement._packratEnabled or ParserElement._left_recursion_enabled:
            print("skipping this test, not compatible with memoization")
            return

        first = pp.Word(pp.alphas)
        bridge = pp.Word(pp.nums)
        second = pp.matchPreviousExpr(first)

        expr = first + bridge.suppress() + second

        tst = "aaa 12 aaa"
        expected = tst.replace("12", "").split()
        result = expr.parseString(tst)
        print(result.dump())

        self.assertParseResultsEquals(result, expected_list=expected)

    def testRecursiveCombine(self):
        testInput = "myc(114)r(11)dd"
        stream = pp.Forward()
        stream <<= pp.Optional(pp.Word(pp.alphas)) + pp.Optional(
            "(" + pp.Word(pp.nums) + ")" + stream
        )
        expected = ["".join(stream.parseString(testInput))]
        print(expected)

        stream = pp.Forward()
        stream << pp.Combine(
            pp.Optional(pp.Word(pp.alphas))
            + pp.Optional("(" + pp.Word(pp.nums) + ")" + stream)
        )
        testVal = stream.parseString(testInput)
        print(testVal)

        self.assertParseResultsEquals(testVal, expected_list=expected)

    def testHTMLEntities(self):
        html_source = dedent(
            """\
            This &amp; that
            2 &gt; 1
            0 &lt; 1
            Don&apos;t get excited!
            I said &quot;Don&apos;t get excited!&quot;
            Copyright &copy; 2021
            Dot &longrightarrow; &dot;
            """
        )
        transformer = pp.common_html_entity.add_parse_action(pp.replace_html_entity)
        transformed = transformer.transform_string(html_source)
        print(transformed)

        expected = dedent(
            """\
            This & that
            2 > 1
            0 < 1
            Don't get excited!
            I said "Don't get excited!"
            Copyright © 2021
            Dot ⟶ ˙
            """
        )
        self.assertEqual(expected, transformed)

    def testInfixNotationBasicArithEval(self):
        import ast

        integer = pp.Word(pp.nums).setParseAction(lambda t: int(t[0]))
        variable = pp.Word(pp.alphas, exact=1)
        operand = integer | variable

        expop = pp.Literal("^")
        signop = pp.oneOf("+ -")
        multop = pp.oneOf("* /")
        plusop = pp.oneOf("+ -")
        factop = pp.Literal("!")

        expr = pp.infixNotation(
            operand,
            [
                (factop, 1, pp.opAssoc.LEFT),
                (expop, 2, pp.opAssoc.RIGHT),
                (signop, 1, pp.opAssoc.RIGHT),
                (multop, 2, pp.opAssoc.LEFT),
                (plusop, 2, pp.opAssoc.LEFT),
            ],
        )

        test = [
            "9 + 2 + 3",
            "9 + 2 * 3",
            "(9 + 2) * 3",
            "(9 + -2) * 3",
            "(9 + --2) * 3",
            "(9 + -2) * 3^2^2",
            "(9! + -2) * 3^2^2",
            "M*X + B",
            "M*(X + B)",
            "1+2*-3^4*5+-+-6",
            "3!!",
        ]
        expected = """[[9, '+', 2, '+', 3]]
                    [[9, '+', [2, '*', 3]]]
                    [[[9, '+', 2], '*', 3]]
                    [[[9, '+', ['-', 2]], '*', 3]]
                    [[[9, '+', ['-', ['-', 2]]], '*', 3]]
                    [[[9, '+', ['-', 2]], '*', [3, '^', [2, '^', 2]]]]
                    [[[[9, '!'], '+', ['-', 2]], '*', [3, '^', [2, '^', 2]]]]
                    [[['M', '*', 'X'], '+', 'B']]
                    [['M', '*', ['X', '+', 'B']]]
                    [[1, '+', [2, '*', ['-', [3, '^', 4]], '*', 5], '+', ['-', ['+', ['-', 6]]]]]
                    [[3, '!', '!']]""".split(
            "\n"
        )
        expected = [ast.literal_eval(x.strip()) for x in expected]
        for test_str, exp_list in zip(test, expected):
            self.assertParseAndCheckList(expr, test_str, exp_list, verbose=True)

    def testInfixNotationEvalBoolExprUsingAstClasses(self):
        boolVars = {"True": True, "False": False}

        class BoolOperand:
            reprsymbol = ""

            def __init__(self, t):
                self.args = t[0][0::2]

            def __str__(self):
                sep = " %s " % self.reprsymbol
                return "(" + sep.join(map(str, self.args)) + ")"

        class BoolAnd(BoolOperand):
            reprsymbol = "&"

            def __bool__(self):
                for a in self.args:
                    if isinstance(a, str):
                        v = boolVars[a]
                    else:
                        v = bool(a)
                    if not v:
                        return False
                return True

        class BoolOr(BoolOperand):
            reprsymbol = "|"

            def __bool__(self):
                for a in self.args:
                    if isinstance(a, str):
                        v = boolVars[a]
                    else:
                        v = bool(a)
                    if v:
                        return True
                return False

        class BoolNot:
            def __init__(self, t):
                self.arg = t[0][1]

            def __str__(self):
                return "~" + str(self.arg)

            def __bool__(self):
                if isinstance(self.arg, str):
                    v = boolVars[self.arg]
                else:
                    v = bool(self.arg)
                return not v

        boolOperand = pp.Word(pp.alphas, max=1, asKeyword=True) | pp.oneOf("True False")
        boolExpr = pp.infixNotation(
            boolOperand,
            [
                ("not", 1, pp.opAssoc.RIGHT, BoolNot),
                ("and", 2, pp.opAssoc.LEFT, BoolAnd),
                ("or", 2, pp.opAssoc.LEFT, BoolOr),
            ],
        )
        test = [
            "p and not q",
            "not not p",
            "not(p and q)",
            "q or not p and r",
            "q or not p or not r",
            "q or not (p and r)",
            "p or q or r",
            "p or q or r and False",
            "(p or q or r) and False",
        ]

        boolVars["p"] = True
        boolVars["q"] = False
        boolVars["r"] = True
        print("p =", boolVars["p"])
        print("q =", boolVars["q"])
        print("r =", boolVars["r"])
        print()
        for t in test:
            res = boolExpr.parseString(t)
            print(t, "\n", res[0], "=", bool(res[0]), "\n")
            expected = eval(t, {}, boolVars)
            self.assertEqual(
                expected, bool(res[0]), "failed boolean eval test {}".format(t)
            )

    def testInfixNotationMinimalParseActionCalls(self):
        count = 0

        def evaluate_int(t):
            nonlocal count
            value = int(t[0])
            print("evaluate_int", value)
            count += 1
            return value

        integer = pp.Word(pp.nums).setParseAction(evaluate_int)
        variable = pp.Word(pp.alphas, exact=1)
        operand = integer | variable

        expop = pp.Literal("^")
        signop = pp.oneOf("+ -")
        multop = pp.oneOf("* /")
        plusop = pp.oneOf("+ -")
        factop = pp.Literal("!")

        expr = pp.infixNotation(
            operand,
            [
                ("!", 1, pp.opAssoc.LEFT),
                ("^", 2, pp.opAssoc.LEFT),
                (signop, 1, pp.opAssoc.RIGHT),
                (multop, 2, pp.opAssoc.LEFT),
                (plusop, 2, pp.opAssoc.LEFT),
            ],
        )

        test = ["9"]
        for t in test:
            count = 0
            print("%r => %s (count=%d)" % (t, expr.parseString(t), count))
            self.assertEqual(1, count, "count evaluated too many times!")

    def testInfixNotationWithParseActions(self):
        word = pp.Word(pp.alphas)

        def supLiteral(s):
            """Returns the suppressed literal s"""
            return pp.Literal(s).suppress()

        def booleanExpr(atom):
            ops = [
                (supLiteral("!"), 1, pp.opAssoc.RIGHT, lambda s, l, t: ["!", t[0][0]]),
                (pp.oneOf("= !="), 2, pp.opAssoc.LEFT),
                (supLiteral("&"), 2, pp.opAssoc.LEFT, lambda s, l, t: ["&", t[0]]),
                (supLiteral("|"), 2, pp.opAssoc.LEFT, lambda s, l, t: ["|", t[0]]),
            ]
            return pp.infixNotation(atom, ops)

        f = booleanExpr(word) + pp.StringEnd()

        tests = [
            ("bar = foo", [["bar", "=", "foo"]]),
            (
                "bar = foo & baz = fee",
                ["&", [["bar", "=", "foo"], ["baz", "=", "fee"]]],
            ),
        ]
        for test, expected in tests:
            print(test)
            results = f.parseString(test)
            print(results)
            self.assertParseResultsEquals(results, expected_list=expected)
            print()

    def testInfixNotationGrammarTest5(self):
        expop = pp.Literal("**")
        signop = pp.oneOf("+ -")
        multop = pp.oneOf("* /")
        plusop = pp.oneOf("+ -")

        class ExprNode:
            def __init__(self, tokens):
                self.tokens = tokens[0]

            def eval(self):
                return None

        class NumberNode(ExprNode):
            def eval(self):
                return self.tokens

        class SignOp(ExprNode):
            def eval(self):
                mult = {"+": 1, "-": -1}[self.tokens[0]]
                return mult * self.tokens[1].eval()

        class BinOp(ExprNode):
            opn_map = {}

            def eval(self):
                ret = self.tokens[0].eval()
                for op, operand in zip(self.tokens[1::2], self.tokens[2::2]):
                    ret = self.opn_map[op](ret, operand.eval())
                return ret

        class ExpOp(BinOp):
            opn_map = {"**": lambda a, b: b ** a}

        class MultOp(BinOp):
            import operator

            opn_map = {"*": operator.mul, "/": operator.truediv}

        class AddOp(BinOp):
            import operator

            opn_map = {"+": operator.add, "-": operator.sub}

        operand = ppc.number().setParseAction(NumberNode)
        expr = pp.infixNotation(
            operand,
            [
                (expop, 2, pp.opAssoc.LEFT, (lambda pr: [pr[0][::-1]], ExpOp)),
                (signop, 1, pp.opAssoc.RIGHT, SignOp),
                (multop, 2, pp.opAssoc.LEFT, MultOp),
                (plusop, 2, pp.opAssoc.LEFT, AddOp),
            ],
        )

        tests = """\
            2+7
            2**3
            2**3**2
            3**9
            3**3**2
            """

        for t in tests.splitlines():
            t = t.strip()
            if not t:
                continue

            parsed = expr.parseString(t)
            eval_value = parsed[0].eval()
            self.assertEqual(
                eval(t),
                eval_value,
                "Error evaluating {!r}, expected {!r}, got {!r}".format(
                    t, eval(t), eval_value
                ),
            )

    def testInfixNotationExceptions(self):
        num = pp.Word(pp.nums)

        # arity 3 with None opExpr - should raise ValueError
        with self.assertRaises(ValueError):
            expr = pp.infixNotation(num, [(None, 3, pp.opAssoc.LEFT)])

        # arity 3 with invalid tuple - should raise ValueError
        with self.assertRaises(ValueError):
            expr = pp.infixNotation(num, [(("+", "-", "*"), 3, pp.opAssoc.LEFT)])

        # left arity > 3 - should raise ValueError
        with self.assertRaises(ValueError):
            expr = pp.infixNotation(num, [("*", 4, pp.opAssoc.LEFT)])

        # right arity > 3 - should raise ValueError
        with self.assertRaises(ValueError):
            expr = pp.infixNotation(num, [("*", 4, pp.opAssoc.RIGHT)])

        # assoc not from opAssoc - should raise ValueError
        with self.assertRaises(ValueError):
            expr = pp.infixNotation(num, [("*", 2, "LEFT")])

    def testInfixNotationWithNonOperators(self):
        # left arity 2 with None expr
        # right arity 2 with None expr
        num = pp.Word(pp.nums).addParseAction(pp.tokenMap(int))
        ident = ppc.identifier()
        for assoc in (pp.opAssoc.LEFT, pp.opAssoc.RIGHT):
            expr = pp.infixNotation(
                num | ident, [(None, 2, assoc), ("+", 2, pp.opAssoc.LEFT)]
            )
            self.assertParseAndCheckList(expr, "3x+2", [[[3, "x"], "+", 2]])

    def testInfixNotationTernaryOperator(self):
        # left arity 3
        # right arity 3
        num = pp.Word(pp.nums).addParseAction(pp.tokenMap(int))
        for assoc in (pp.opAssoc.LEFT, pp.opAssoc.RIGHT):
            expr = pp.infixNotation(
                num, [("+", 2, pp.opAssoc.LEFT), (("?", ":"), 3, assoc)]
            )
            self.assertParseAndCheckList(
                expr, "3 + 2? 12: 13", [[[3, "+", 2], "?", 12, ":", 13]]
            )

    def testParseResultsPickle(self):
        import pickle

        # test 1
        body = pp.makeHTMLTags("BODY")[0]
        result = body.parseString("<BODY BGCOLOR='#00FFBB' FGCOLOR=black>")
        print(result.dump())

        for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
            print("Test pickle dump protocol", protocol)
            try:
                pickleString = pickle.dumps(result, protocol)
            except Exception as e:
                print("dumps exception:", e)
                newresult = pp.ParseResults()
            else:
                newresult = pickle.loads(pickleString)
                print(newresult.dump())

            self.assertEqual(
                result.dump(),
                newresult.dump(),
                "Error pickling ParseResults object (protocol=%d)" % protocol,
            )

    def testParseResultsPickle2(self):
        import pickle

        word = pp.Word(pp.alphas + "'.")
        salutation = pp.OneOrMore(word)
        comma = pp.Literal(",")
        greetee = pp.OneOrMore(word)
        endpunc = pp.oneOf("! ?")
        greeting = (
            salutation("greeting")
            + pp.Suppress(comma)
            + greetee("greetee")
            + endpunc("punc*")[1, ...]
        )

        string = "Good morning, Miss Crabtree!"

        result = greeting.parseString(string)
        self.assertParseResultsEquals(
            result,
            ["Good", "morning", "Miss", "Crabtree", "!"],
            {
                "greeting": ["Good", "morning"],
                "greetee": ["Miss", "Crabtree"],
                "punc": ["!"],
            },
        )
        print(result.dump())

        for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
            print("Test pickle dump protocol", protocol)
            try:
                pickleString = pickle.dumps(result, protocol)
            except Exception as e:
                print("dumps exception:", e)
                newresult = pp.ParseResults()
            else:
                newresult = pickle.loads(pickleString)
            print(newresult.dump())
            self.assertEqual(
                newresult.dump(),
                result.dump(),
                "failed to pickle/unpickle ParseResults: expected {!r}, got {!r}".format(
                    result, newresult
                ),
            )

    def testParseResultsPickle3(self):
        import pickle

        # result with aslist=False
        res_not_as_list = pp.Word("ABC").parseString("BABBAB")

        # result with aslist=True
        res_as_list = pp.Group(pp.Word("ABC")).parseString("BABBAB")

        # result with modal=True
        res_modal = pp.Word("ABC")("name").parseString("BABBAB")
        # self.assertTrue(res_modal._modal)

        # result with modal=False
        res_not_modal = pp.Word("ABC")("name*").parseString("BABBAB")
        # self.assertFalse(res_not_modal._modal)

        for result in (res_as_list, res_not_as_list, res_modal, res_not_modal):
            for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
                print("Test pickle dump protocol", protocol)
                try:
                    pickleString = pickle.dumps(result, protocol)
                except Exception as e:
                    print("dumps exception:", e)
                    newresult = pp.ParseResults()
                else:
                    newresult = pickle.loads(pickleString)
                print(newresult.dump())
                self.assertEqual(
                    newresult.dump(),
                    result.dump(),
                    "failed to pickle/unpickle ParseResults: expected {!r}, got {!r}".format(
                        result, newresult
                    ),
                )

    def testParseResultsInsertWithResultsNames(self):
        test_string = "1 2 3 dice rolled first try"

        wd = pp.Word(pp.alphas)
        num = ppc.number

        expr = (
            pp.Group(num[1, ...])("nums")
            + wd("label")
            + pp.Group(wd[...])("additional")
        )

        result = expr.parseString(test_string)
        print("Pre-insert")
        print(result.dump())

        result.insert(1, sum(result.nums))

        print("\nPost-insert")
        print(result.dump())

        self.assertParseResultsEquals(
            result,
            expected_list=[[1, 2, 3], 6, "dice", ["rolled", "first", "try"]],
            expected_dict={
                "additional": ["rolled", "first", "try"],
                "label": "dice",
                "nums": [1, 2, 3],
            },
        )

    def testParseResultsStringListUsingCombine(self):
        test_string = "1 2 3 dice rolled first try"

        wd = pp.Word(pp.alphas)
        num = ppc.number

        expr = pp.Combine(
            pp.Group(num[1, ...])("nums")
            + wd("label")
            + pp.Group(wd[...])("additional"),
            joinString="/",
            adjacent=False,
        )
        self.assertEqual("123/dice/rolledfirsttry", expr.parseString(test_string)[0])

    def testParseResultsAcceptingACollectionTypeValue(self):
        # from Issue #276 - ParseResults parameterizes generic types if passed as the value of toklist parameter
        # https://github.com/pyparsing/pyparsing/issues/276?notification_referrer_id=MDE4Ok5vdGlmaWNhdGlvblRocmVhZDE4MzU4NDYwNzI6MzgzODc1
        #
        # behavior of ParseResults code changed with Python 3.9

        results_with_int = pp.ParseResults(toklist=int, name="type_", asList=False)
        self.assertEqual(int, results_with_int["type_"])

        results_with_tuple = pp.ParseResults(toklist=tuple, name="type_", asList=False)
        self.assertEqual(tuple, results_with_tuple["type_"])

    def testParseResultsReturningDunderAttribute(self):
        # from Issue #208
        parser = pp.Word(pp.alphas)("A")
        result = parser.parseString("abc")
        print(result.dump())
        self.assertEqual("abc", result.A)
        self.assertEqual("", result.B)
        with self.assertRaises(AttributeError):
            result.__xyz__

    def testMatchOnlyAtCol(self):
        """successfully use matchOnlyAtCol helper function"""

        expr = pp.Word(pp.nums)
        expr.setParseAction(pp.matchOnlyAtCol(5))
        largerExpr = pp.ZeroOrMore(pp.Word("A")) + expr + pp.ZeroOrMore(pp.Word("A"))

        res = largerExpr.parseString("A A 3 A")
        print(res.dump())

    def testMatchOnlyAtColErr(self):
        """raise a ParseException in matchOnlyAtCol with incorrect col"""

        expr = pp.Word(pp.nums)
        expr.setParseAction(pp.matchOnlyAtCol(1))
        largerExpr = pp.ZeroOrMore(pp.Word("A")) + expr + pp.ZeroOrMore(pp.Word("A"))

        with self.assertRaisesParseException():
            largerExpr.parseString("A A 3 A")

    def testParseResultsWithNamedTuple(self):
        expr = pp.Literal("A")("Achar")
        expr.setParseAction(pp.replaceWith(tuple(["A", "Z"])))

        res = expr.parseString("A")
        print(repr(res))
        print(res.Achar)
        self.assertParseResultsEquals(
            res,
            expected_dict={"Achar": ("A", "Z")},
            msg="Failed accessing named results containing a tuple, "
            "got {!r}".format(res.Achar),
        )

    def testParserElementAddOperatorWithOtherTypes(self):
        """test the overridden "+" operator with other data types"""

        # ParserElement + str
        expr = pp.Word(pp.alphas)("first") + pp.Word(pp.alphas)("second") + "suf"
        result = expr.parseString("spam eggs suf")
        print(result)

        expected_l = ["spam", "eggs", "suf"]
        self.assertParseResultsEquals(
            result, expected_l, msg="issue with ParserElement + str"
        )

        # str + ParserElement
        expr = "pre" + pp.Word(pp.alphas)("first") + pp.Word(pp.alphas)("second")
        result = expr.parseString("pre spam eggs")
        print(result)

        expected_l = ["pre", "spam", "eggs"]
        self.assertParseResultsEquals(
            result, expected_l, msg="issue with str + ParserElement"
        )

        # ParserElement + int
        expr = None
        with self.assertRaises(TypeError, msg="failed to warn ParserElement + int"):
            expr = pp.Word(pp.alphas)("first") + pp.Word(pp.alphas)("second") + 12
        self.assertEqual(expr, None)

        # int + ParserElement
        expr = None
        with self.assertRaises(TypeError, msg="failed to warn int + ParserElement"):
            expr = 12 + pp.Word(pp.alphas)("first") + pp.Word(pp.alphas)("second")
        self.assertEqual(expr, None)

    def testParserElementSubOperatorWithOtherTypes(self):
        """test the overridden "-" operator with other data types"""

        # ParserElement - str
        expr = pp.Word(pp.alphas)("first") + pp.Word(pp.alphas)("second") - "suf"
        result = expr.parseString("spam eggs suf")
        print(result)
        expected = ["spam", "eggs", "suf"]
        self.assertParseResultsEquals(
            result, expected, msg="issue with ParserElement - str"
        )

        # str - ParserElement
        expr = "pre" - pp.Word(pp.alphas)("first") + pp.Word(pp.alphas)("second")
        result = expr.parseString("pre spam eggs")
        print(result)
        expected = ["pre", "spam", "eggs"]
        self.assertParseResultsEquals(
            result, expected, msg="issue with str - ParserElement"
        )

        # ParserElement - int
        expr = None
        with self.assertRaises(TypeError, msg="failed to warn ParserElement - int"):
            expr = pp.Word(pp.alphas)("first") + pp.Word(pp.alphas)("second") - 12
        self.assertEqual(expr, None)

        # int - ParserElement
        expr = None
        with self.assertRaises(TypeError, msg="failed to warn int - ParserElement"):
            expr = 12 - pp.Word(pp.alphas)("first") + pp.Word(pp.alphas)("second")
        self.assertEqual(expr, None)

    def testParserElementMulOperatorWithTuples(self):
        """test ParserElement "*" with various tuples"""

        # ParserElement * (None, n)
        expr = pp.Word(pp.alphas)("first") + pp.Word(pp.nums)("second*") * (None, 3)

        results1 = expr.parseString("spam")
        print(results1.dump())
        expected = ["spam"]
        self.assertParseResultsEquals(
            results1, expected, msg="issue with ParserElement * w/ optional matches"
        )

        results2 = expr.parseString("spam 12 23 34")
        print(results2.dump())
        expected = ["spam", "12", "23", "34"]
        self.assertParseResultsEquals(
            results2, expected, msg="issue with ParserElement * w/ optional matches"
        )

        # ParserElement * (1, 1)
        expr = pp.Word(pp.alphas)("first") + pp.Word(pp.nums)("second*") * (1, 1)
        results = expr.parseString("spam 45")
        print(results.dump())

        expected = ["spam", "45"]
        self.assertParseResultsEquals(
            results, expected, msg="issue with ParserElement * (1, 1)"
        )

        # ParserElement * (1, 1+n)
        expr = pp.Word(pp.alphas)("first") + pp.Word(pp.nums)("second*") * (1, 3)

        results1 = expr.parseString("spam 100")
        print(results1.dump())
        expected = ["spam", "100"]
        self.assertParseResultsEquals(
            results1, expected, msg="issue with ParserElement * (1, 1+n)"
        )

        results2 = expr.parseString("spam 100 200 300")
        print(results2.dump())
        expected = ["spam", "100", "200", "300"]
        self.assertParseResultsEquals(
            results2, expected, msg="issue with ParserElement * (1, 1+n)"
        )

        # ParserElement * (lesser, greater)
        expr = pp.Word(pp.alphas)("first") + pp.Word(pp.nums)("second*") * (2, 3)

        results1 = expr.parseString("spam 1 2")
        print(results1.dump())
        expected = ["spam", "1", "2"]
        self.assertParseResultsEquals(
            results1, expected, msg="issue with ParserElement * (lesser, greater)"
        )

        results2 = expr.parseString("spam 1 2 3")
        print(results2.dump())
        expected = ["spam", "1", "2", "3"]
        self.assertParseResultsEquals(
            results2, expected, msg="issue with ParserElement * (lesser, greater)"
        )

        # ParserElement * (greater, lesser)
        with self.assertRaises(
            ValueError, msg="ParserElement * (greater, lesser) should raise error"
        ):
            expr = pp.Word(pp.alphas)("first") + pp.Word(pp.nums)("second") * (3, 2)

        # ParserElement * (str, str)
        with self.assertRaises(
            TypeError, msg="ParserElement * (str, str) should raise error"
        ):
            expr = pp.Word(pp.alphas)("first") + pp.Word(pp.nums)("second") * ("2", "3")

    def testParserElementMulByZero(self):
        alpwd = pp.Word(pp.alphas)
        numwd = pp.Word(pp.nums)

        test_string = "abd def ghi jkl"

        parser = alpwd * 2 + numwd * 0 + alpwd * 2
        self.assertParseAndCheckList(
            parser, test_string, expected_list=test_string.split()
        )

        parser = alpwd * 2 + numwd * (0, 0) + alpwd * 2
        self.assertParseAndCheckList(
            parser, test_string, expected_list=test_string.split()
        )

    def testParserElementMulOperatorWithOtherTypes(self):
        """test the overridden "*" operator with other data types"""

        # ParserElement * str
        with self.assertRaises(TypeError, msg="ParserElement * str should raise error"):
            expr = pp.Word(pp.alphas)("first") + pp.Word(pp.nums)("second") * "3"

        # str * ParserElement
        with self.assertRaises(TypeError, msg="str * ParserElement should raise error"):
            expr = pp.Word(pp.alphas)("first") + "3" * pp.Word(pp.nums)("second")

        # ParserElement * int
        expr = pp.Word(pp.alphas)("first") + pp.Word(pp.nums)("second*") * 2
        results = expr.parseString("spam 11 22")

        print(results.dump())
        expected = ["spam", "11", "22"]
        self.assertParseResultsEquals(
            results, expected, msg="issue with ParserElement * int"
        )

        # int * ParserElement
        expr = pp.Word(pp.alphas)("first") + 2 * pp.Word(pp.nums)("second*")
        results = expr.parseString("spam 111 222")

        print(results.dump())
        expected = ["spam", "111", "222"]
        self.assertParseResultsEquals(
            results, expected, msg="issue with int * ParserElement"
        )

    def testParserElementMatchFirstOperatorWithOtherTypes(self):
        """test the overridden "|" operator with other data types"""

        # ParserElement | int
        expr = None
        with self.assertRaises(TypeError, msg="failed to warn ParserElement | int"):
            expr = pp.Word(pp.alphas)("first") + (pp.Word(pp.alphas)("second") | 12)
        self.assertEqual(expr, None)

        # int | ParserElement
        expr = None
        with self.assertRaises(TypeError, msg="failed to warn int | ParserElement"):
            expr = pp.Word(pp.alphas)("first") + (12 | pp.Word(pp.alphas)("second"))
        self.assertEqual(expr, None)

    def testParserElementMatchLongestWithOtherTypes(self):
        """test the overridden "^" operator with other data types"""

        # ParserElement ^ str
        expr = pp.Word(pp.alphas)("first") + (pp.Word(pp.nums)("second") ^ "eggs")
        result = expr.parseString("spam eggs")
        print(result)

        expected = ["spam", "eggs"]
        self.assertParseResultsEquals(
            result, expected, msg="issue with ParserElement ^ str"
        )

        # str ^ ParserElement
        expr = ("pre" ^ pp.Word("pr")("first")) + pp.Word(pp.alphas)("second")
        result = expr.parseString("pre eggs")
        print(result)

        expected = ["pre", "eggs"]
        self.assertParseResultsEquals(
            result, expected, msg="issue with str ^ ParserElement"
        )

        # ParserElement ^ int
        expr = None
        with self.assertRaises(TypeError, msg="failed to warn ParserElement ^ int"):
            expr = pp.Word(pp.alphas)("first") + (pp.Word(pp.alphas)("second") ^ 54)
        self.assertEqual(expr, None)

        # int ^ ParserElement
        expr = None
        with self.assertRaises(TypeError, msg="failed to warn int ^ ParserElement"):
            expr = pp.Word(pp.alphas)("first") + (65 ^ pp.Word(pp.alphas)("second"))
        self.assertEqual(expr, None)

    def testParserElementEachOperatorWithOtherTypes(self):
        """test the overridden "&" operator with other data types"""

        # ParserElement & str
        expr = pp.Word(pp.alphas)("first") + (pp.Word(pp.alphas)("second") & "and")
        with self.assertRaisesParseException(msg="issue with ParserElement & str"):
            result = expr.parseString("spam and eggs")

        # str & ParserElement
        expr = pp.Word(pp.alphas)("first") + ("and" & pp.Word(pp.alphas)("second"))
        result = expr.parseString("spam and eggs")

        print(result.dump())
        expected_l = ["spam", "and", "eggs"]
        expected_d = {"first": "spam", "second": "eggs"}
        self.assertParseResultsEquals(
            result,
            expected_list=expected_l,
            expected_dict=expected_d,
            msg="issue with str & ParserElement",
        )

        # ParserElement & int
        expr = None
        with self.assertRaises(TypeError, msg="failed to warn ParserElement & int"):
            expr = pp.Word(pp.alphas)("first") + (pp.Word(pp.alphas) & 78)
        self.assertEqual(expr, None)

        # int & ParserElement
        expr = None
        with self.assertRaises(TypeError, msg="failed to warn int & ParserElement"):
            expr = pp.Word(pp.alphas)("first") + (89 & pp.Word(pp.alphas))
        self.assertEqual(expr, None)

    def testParserElementPassedThreeArgsToMultiplierShorthand(self):
        """test the ParserElement form expr[m,n,o]"""

        with self.assertRaises(
            TypeError, msg="failed to warn three index arguments to expr[m, n, o]"
        ):
            expr = pp.Word(pp.alphas)[2, 3, 4]

    def testParserElementPassedStrToMultiplierShorthand(self):
        """test the ParserElement form expr[str]"""

        with self.assertRaises(
            TypeError, msg="failed to raise expected error using string multiplier"
        ):
            expr2 = pp.Word(pp.alphas)["2"]

    def testParseResultsNewEdgeCases(self):
        """test less common paths of ParseResults.__new__()"""

        parser = pp.Word(pp.alphas)[...]
        result = parser.parseString("sldkjf sldkjf")

        # hasattr uses __getattr__, which for ParseResults will return "" if the
        # results name is not defined. So hasattr() won't work with ParseResults.
        # Have to use __contains__ instead to test for existence.
        # self.assertFalse(hasattr(result, "A"))
        self.assertFalse("A" in result)

        # create new ParseResults w/ None
        result1 = pp.ParseResults(None)
        print(result1.dump())
        self.assertParseResultsEquals(
            result1, [], msg="ParseResults(None) should return empty ParseResults"
        )

        # create new ParseResults w/ integer name
        result2 = pp.ParseResults(name=12)
        print(result2.dump())
        self.assertEqual(
            "12",
            result2.getName(),
            "ParseResults int name should be accepted and converted to str",
        )

        # create new ParseResults w/ generator type
        gen = (a for a in range(1, 6))
        result3 = pp.ParseResults(gen)
        print(result3.dump())
        expected3 = [1, 2, 3, 4, 5]
        self.assertParseResultsEquals(
            result3, expected3, msg="issue initializing ParseResults w/ gen type"
        )

    def testParseResultsReversed(self):
        """test simple case of reversed(ParseResults)"""

        tst = "1 2 3 4 5"
        expr = pp.OneOrMore(pp.Word(pp.nums))
        result = expr.parseString(tst)

        reversed_list = [ii for ii in reversed(result)]
        print(reversed_list)
        expected = ["5", "4", "3", "2", "1"]
        self.assertEqual(
            expected, reversed_list, msg="issue calling reversed(ParseResults)"
        )

    def testParseResultsValues(self):
        """test simple case of ParseResults.values()"""

        expr = pp.Word(pp.alphas)("first") + pp.Word(pp.alphas)("second")
        result = expr.parseString("spam eggs")

        values_set = set(result.values())
        print(values_set)
        expected = {"spam", "eggs"}
        self.assertEqual(
            expected, values_set, msg="issue calling ParseResults.values()"
        )

    def testParseResultsAppend(self):
        """test simple case of ParseResults.append()"""

        # use a parse action to compute the sum of the parsed integers, and add it to the end
        def append_sum(tokens):
            tokens.append(sum(map(int, tokens)))

        expr = pp.OneOrMore(pp.Word(pp.nums)).addParseAction(append_sum)
        result = expr.parseString("0 123 321")

        expected = ["0", "123", "321", 444]
        print(result.dump())
        self.assertParseResultsEquals(
            result, expected, msg="issue with ParseResults.append()"
        )

    def testParseResultsClear(self):
        """test simple case of ParseResults.clear()"""

        tst = "spam eggs"
        expr = pp.Word(pp.alphas)("first") + pp.Word(pp.alphas)("second")
        result = expr.parseString(tst)

        print(result.dump())
        self.assertParseResultsEquals(
            result, ["spam", "eggs"], msg="issue with ParseResults before clear()"
        )

        result.clear()

        print(result.dump())
        self.assertParseResultsEquals(
            result,
            expected_list=[],
            expected_dict={},
            msg="issue with ParseResults.clear()",
        )

    def testParseResultsExtendWithString(self):
        """test ParseResults.extend() with input of type str"""

        # use a parse action to append the reverse of the matched strings to make a palindrome
        def make_palindrome(tokens):
            tokens.extend(reversed([t[::-1] for t in tokens]))

        tst = "abc def ghi"
        expr = pp.OneOrMore(pp.Word(pp.alphas))
        result = expr.addParseAction(make_palindrome).parseString(tst)
        print(result.dump())

        expected = ["abc", "def", "ghi", "ihg", "fed", "cba"]
        self.assertParseResultsEquals(
            result, expected, msg="issue with ParseResults.extend(str)"
        )

    def testParseResultsExtendWithParseResults(self):
        """test ParseResults.extend() with input of type ParseResults"""

        expr = pp.OneOrMore(pp.Word(pp.alphas))
        result1 = expr.parseString("spam eggs")
        result2 = expr.parseString("foo bar")

        result1.extend(result2)
        print(result1.dump())
        expected = ["spam", "eggs", "foo", "bar"]
        self.assertParseResultsEquals(
            result1, expected, msg="issue with ParseResults.extend(ParseResults)"
        )

    def testParseResultsWithNestedNames(self):
        from pyparsing import (
            Dict,
            Literal,
            Group,
            Optional,
            Regex,
            QuotedString,
            oneOf,
            Or,
            CaselessKeyword,
            ZeroOrMore,
        )

        RELATION_SYMBOLS = "= > < >= <= <> =="

        def _set_info(string, location, tokens):
            for t in tokens:
                try:
                    t["_info_"] = (string, location)
                except TypeError:
                    pass
            tokens["_info_"] = (string, location)

        def keywords(name):
            words = "any all within encloses adj".split()
            return Or(map(CaselessKeyword, words))

        charString1 = Group(Regex(r'[^()=<>"/\s]+'))("identifier")
        charString1.addParseAction(_set_info)
        charString2 = Group(QuotedString('"', "\\"))("quoted")
        charString2.addParseAction(_set_info)

        term = Group(charString1 | charString2)
        modifier_key = charString1

        # relations
        comparitor_symbol = oneOf(RELATION_SYMBOLS)
        named_comparitors = keywords("comparitors")
        comparitor = Group(comparitor_symbol | named_comparitors)("comparitor")
        comparitor.addParseAction(_set_info)

        def modifier_list1(key):
            modifier = Dict(
                Literal("/")
                + Group(modifier_key(key))("name")
                + Optional(comparitor_symbol("symbol") + term("value"))
            )("modifier")
            modifier.addParseAction(_set_info)
            return ZeroOrMore(modifier)("modifier_list")

        def modifier_list2(key):
            modifier = Dict(
                Literal("/")
                + Group(modifier_key(key))("name")
                + Optional(comparitor_symbol("symbol") + term("value")),
                asdict=True,
            )("modifier")
            modifier.addParseAction(_set_info)
            return ZeroOrMore(modifier)("modifier_list")

        def modifier_list3(key):
            modifier = Group(  # this line is different from the others, must group to get results names
                Dict(
                    Literal("/")
                    + Group(modifier_key(key))("name")
                    + Optional(comparitor_symbol("symbol") + term("value"))
                )
            )
            modifier.addParseAction(_set_info)
            return ZeroOrMore(modifier)("modifier_list")

        def modifier_list4(key):
            modifier = Dict(
                Literal("/")
                + Group(modifier_key(key))("name")
                + Optional(comparitor_symbol("symbol") + term("value")),
                asdict=True,
            )
            modifier.addParseAction(_set_info)
            return ZeroOrMore(modifier)("modifier_list")

        for modifier_list_fn in (
            modifier_list1,
            modifier_list2,
            modifier_list3,
            modifier_list4,
        ):
            modifier_parser = modifier_list_fn("default")

            result = modifier_parser.parseString("/respectaccents/ignoreaccents")
            for r in result:
                print(r)
                print(r.get("_info_"))
            self.assertEqual([0, 15], [r["_info_"][1] for r in result])

    def testParseResultsFromDict(self):
        """test helper classmethod ParseResults.from_dict()"""

        dict = {
            "first": "123",
            "second": 456,
            "third": {"threeStr": "789", "threeInt": 789},
        }
        name = "trios"
        result = pp.ParseResults.from_dict(dict, name=name)

        print(result.dump())
        expected = {name: dict}
        self.assertParseResultsEquals(
            result,
            expected_dict=expected,
            msg="issue creating ParseResults.from _dict()",
        )

    def testParseResultsDir(self):
        """test dir(ParseResults)"""

        dict = {"first": "123", "second": "456", "third": "789"}
        name = "trios"
        result = pp.ParseResults.from_dict(dict, name=name)
        dir_result = dir(result)

        print(dir_result)
        self.assertIn(
            name, dir_result, msg="name value wasn't returned by dir(ParseResults)"
        )
        self.assertIn(
            "asList", dir_result, msg="asList was not returned by dir(ParseResults)"
        )

    def testParseResultsInsert(self):
        """test ParseResults.insert() with named tokens"""

        from random import randint

        result = pp.Word(pp.alphas)[...].parseString("A B C D E F G H I J")
        compare_list = result.asList()

        print(result)
        print(compare_list)

        for s in "abcdefghij":
            index = randint(-5, 5)
            result.insert(index, s)
            compare_list.insert(index, s)

        print(result)
        print(compare_list)

        self.assertParseResultsEquals(
            result, compare_list, msg="issue with ParseResults.insert()"
        )

    def testParseResultsAddingSuppressedTokenWithResultsName(self):
        parser = "aaa" + (pp.NoMatch() | pp.Suppress("-"))("B")
        try:
            dd = parser.parse_string("aaa -").as_dict()
        except RecursionError:
            self.fail("fail getting named result when empty")

    def testParseResultsBool(self):
        result = pp.Word(pp.alphas)[...].parseString("AAA")
        self.assertTrue(result, "non-empty ParseResults evaluated as False")

        result = pp.Word(pp.alphas)[...].parseString("")
        self.assertFalse(result, "empty ParseResults evaluated as True")

        result["A"] = 0
        self.assertTrue(result, "ParseResults with empty list but containing a results name evaluated as False")

    def testIgnoreString(self):
        """test ParserElement.ignore() passed a string arg"""

        tst = "I like totally like love pickles"
        expr = pp.Word(pp.alphas)[...].ignore("like")
        result = expr.parseString(tst)

        print(result)
        expected = ["I", "totally", "love", "pickles"]
        self.assertParseResultsEquals(result, expected, msg="issue with ignore(string)")

    def testParseHTMLTags(self):
        test = """
            <BODY>
            <BODY BGCOLOR="#00FFCC">
            <BODY BGCOLOR="#00FFAA"/>
            <BODY BGCOLOR='#00FFBB' FGCOLOR=black>
            <BODY/>
            </BODY>
        """
        results = [
            ("startBody", False, "", ""),
            ("startBody", False, "#00FFCC", ""),
            ("startBody", True, "#00FFAA", ""),
            ("startBody", False, "#00FFBB", "black"),
            ("startBody", True, "", ""),
            ("endBody", False, "", ""),
        ]

        bodyStart, bodyEnd = pp.makeHTMLTags("BODY")
        resIter = iter(results)
        for t, s, e in (bodyStart | bodyEnd).scanString(test):
            print(test[s:e], "->", t)
            (expectedType, expectedEmpty, expectedBG, expectedFG) = next(resIter)

            print(t.dump())
            if "startBody" in t:
                self.assertEqual(
                    expectedEmpty,
                    bool(t.empty),
                    "expected {} token, got {}".format(
                        expectedEmpty and "empty" or "not empty",
                        t.empty and "empty" or "not empty",
                    ),
                )
                self.assertEqual(
                    expectedBG,
                    t.bgcolor,
                    "failed to match BGCOLOR, expected {}, got {}".format(
                        expectedBG, t.bgcolor
                    ),
                )
                self.assertEqual(
                    expectedFG,
                    t.fgcolor,
                    "failed to match FGCOLOR, expected {}, got {}".format(
                        expectedFG, t.bgcolor
                    ),
                )
            elif "endBody" in t:
                print("end tag")
                pass
            else:
                print("BAD!!!")

    def testSetParseActionUncallableErr(self):
        """raise a TypeError in setParseAction() by adding uncallable arg"""

        expr = pp.Literal("A")("Achar")
        uncallable = 12

        with self.assertRaises(TypeError):
            expr.setParseAction(uncallable)

        res = expr.parseString("A")
        print(res.dump())

    def testMulWithNegativeNumber(self):
        """raise a ValueError in __mul__ by multiplying a negative number"""

        with self.assertRaises(ValueError):
            pp.Literal("A")("Achar") * (-1)

    def testMulWithEllipsis(self):
        """multiply an expression with Ellipsis as ``expr * ...`` to match ZeroOrMore"""

        expr = pp.Literal("A")("Achar") * ...
        res = expr.parseString("A")
        self.assertEqual(["A"], res.asList(), "expected expr * ... to match ZeroOrMore")
        print(res.dump())

    def testUpcaseDowncaseUnicode(self):
        import sys

        ppu = pp.pyparsing_unicode

        a = "\u00bfC\u00f3mo esta usted?"
        if not JYTHON_ENV:
            ualphas = ppu.alphas
        else:
            ualphas = "".join(
                chr(i)
                for i in list(range(0xD800)) + list(range(0xE000, sys.maxunicode))
                if chr(i).isalpha()
            )
        uword = pp.Word(ualphas).setParseAction(ppc.upcaseTokens)

        print = lambda *args: None
        print(uword.searchString(a))

        uword = pp.Word(ualphas).setParseAction(ppc.downcaseTokens)

        print(uword.searchString(a))

        kw = pp.Keyword("mykey", caseless=True).setParseAction(ppc.upcaseTokens)(
            "rname"
        )
        ret = kw.parseString("mykey")
        print(ret.rname)
        self.assertEqual(
            "MYKEY", ret.rname, "failed to upcase with named result (pyparsing_common)"
        )

        kw = pp.Keyword("MYKEY", caseless=True).setParseAction(ppc.downcaseTokens)(
            "rname"
        )
        ret = kw.parseString("mykey")
        print(ret.rname)
        self.assertEqual("mykey", ret.rname, "failed to upcase with named result")

        if not IRON_PYTHON_ENV:
            # test html data
            html = "<TR class=maintxt bgColor=#ffffff> \
                <TD vAlign=top>Производитель, модель</TD> \
                <TD vAlign=top><STRONG>BenQ-Siemens CF61</STRONG></TD> \
            "  # .decode('utf-8')

            # 'Manufacturer, model
            text_manuf = "Производитель, модель"
            manufacturer = pp.Literal(text_manuf)

            td_start, td_end = pp.makeHTMLTags("td")
            manuf_body = (
                td_start.suppress()
                + manufacturer
                + pp.SkipTo(td_end)("cells*")
                + td_end.suppress()
            )

    def testParseUsingRegex(self):

        signedInt = pp.Regex(r"[-+][0-9]+")
        unsignedInt = pp.Regex(r"[0-9]+")
        simpleString = pp.Regex(r'("[^\"]*")|(\'[^\']*\')')
        namedGrouping = pp.Regex(r'("(?P<content>[^\"]*)")')
        compiledRE = pp.Regex(re.compile(r"[A-Z]+"))

        def testMatch(expression, instring, shouldPass, expectedString=None):
            if shouldPass:
                try:
                    result = expression.parseString(instring)
                    print(
                        "{} correctly matched {}".format(
                            repr(expression), repr(instring)
                        )
                    )
                    if expectedString != result[0]:
                        print("\tbut failed to match the pattern as expected:")
                        print(
                            "\tproduced %s instead of %s"
                            % (repr(result[0]), repr(expectedString))
                        )
                    return True
                except pp.ParseException:
                    print(
                        "%s incorrectly failed to match %s"
                        % (repr(expression), repr(instring))
                    )
            else:
                try:
                    result = expression.parseString(instring)
                    print(
                        "{} incorrectly matched {}".format(
                            repr(expression), repr(instring)
                        )
                    )
                    print("\tproduced %s as a result" % repr(result[0]))
                except pp.ParseException:
                    print(
                        "%s correctly failed to match %s"
                        % (repr(expression), repr(instring))
                    )
                    return True
            return False

        # These should fail
        self.assertTrue(
            testMatch(signedInt, "1234 foo", False), "Re: (1) passed, expected fail"
        )
        self.assertTrue(
            testMatch(signedInt, "    +foo", False), "Re: (2) passed, expected fail"
        )
        self.assertTrue(
            testMatch(unsignedInt, "abc", False), "Re: (3) passed, expected fail"
        )
        self.assertTrue(
            testMatch(unsignedInt, "+123 foo", False), "Re: (4) passed, expected fail"
        )
        self.assertTrue(
            testMatch(simpleString, "foo", False), "Re: (5) passed, expected fail"
        )
        self.assertTrue(
            testMatch(simpleString, "\"foo bar'", False),
            "Re: (6) passed, expected fail",
        )
        self.assertTrue(
            testMatch(simpleString, "'foo bar\"", False),
            "Re: (7) passed, expected fail",
        )

        # These should pass
        self.assertTrue(
            testMatch(signedInt, "   +123", True, "+123"),
            "Re: (8) failed, expected pass",
        )
        self.assertTrue(
            testMatch(signedInt, "+123", True, "+123"), "Re: (9) failed, expected pass"
        )
        self.assertTrue(
            testMatch(signedInt, "+123 foo", True, "+123"),
            "Re: (10) failed, expected pass",
        )
        self.assertTrue(
            testMatch(signedInt, "-0 foo", True, "-0"), "Re: (11) failed, expected pass"
        )
        self.assertTrue(
            testMatch(unsignedInt, "123 foo", True, "123"),
            "Re: (12) failed, expected pass",
        )
        self.assertTrue(
            testMatch(unsignedInt, "0 foo", True, "0"), "Re: (13) failed, expected pass"
        )
        self.assertTrue(
            testMatch(simpleString, '"foo"', True, '"foo"'),
            "Re: (14) failed, expected pass",
        )
        self.assertTrue(
            testMatch(simpleString, "'foo bar' baz", True, "'foo bar'"),
            "Re: (15) failed, expected pass",
        )

        self.assertTrue(
            testMatch(compiledRE, "blah", False), "Re: (16) passed, expected fail"
        )
        self.assertTrue(
            testMatch(compiledRE, "BLAH", True, "BLAH"),
            "Re: (17) failed, expected pass",
        )

        self.assertTrue(
            testMatch(namedGrouping, '"foo bar" baz', True, '"foo bar"'),
            "Re: (16) failed, expected pass",
        )
        ret = namedGrouping.parseString('"zork" blah')
        print(ret)
        print(list(ret.items()))
        print(ret.content)
        self.assertEqual("zork", ret.content, "named group lookup failed")
        self.assertEqual(
            simpleString.parseString('"zork" blah')[0],
            ret[0],
            "Regex not properly returning ParseResults for named vs. unnamed groups",
        )

        try:
            print("lets try an invalid RE")
            invRe = pp.Regex("(\"[^\"]*\")|('[^']*'").re
        except Exception as e:
            print("successfully rejected an invalid RE:", end=" ")
            print(e)
        else:
            self.fail("failed to reject invalid RE")

        with self.assertRaises(
            ValueError, msg="failed to warn empty string passed to Regex"
        ):
            invRe = pp.Regex("")

    def testRegexAsType(self):

        test_str = "sldkjfj 123 456 lsdfkj"

        print("return as list of match groups")
        expr = pp.Regex(r"\w+ (\d+) (\d+) (\w+)", asGroupList=True)
        expected_group_list = [tuple(test_str.split()[1:])]
        result = expr.parseString(test_str)
        print(result.dump())
        print(expected_group_list)
        self.assertParseResultsEquals(
            result,
            expected_list=expected_group_list,
            msg="incorrect group list returned by Regex)",
        )

        print("return as re.match instance")
        expr = pp.Regex(
            r"\w+ (?P<num1>\d+) (?P<num2>\d+) (?P<last_word>\w+)", asMatch=True
        )
        result = expr.parseString(test_str)
        print(result.dump())
        print(result[0].groups())
        print(expected_group_list)
        self.assertEqual(
            {"num1": "123", "num2": "456", "last_word": "lsdfkj"},
            result[0].groupdict(),
            "invalid group dict from Regex(asMatch=True)",
        )
        self.assertEqual(
            expected_group_list[0],
            result[0].groups(),
            "incorrect group list returned by Regex(asMatch)",
        )

    def testRegexSub(self):

        print("test sub with string")
        expr = pp.Regex(r"<title>").sub("'Richard III'")
        result = expr.transformString("This is the title: <title>")
        print(result)
        self.assertEqual(
            "This is the title: 'Richard III'",
            result,
            "incorrect Regex.sub result with simple string",
        )

        print("test sub with re string")
        expr = pp.Regex(r"([Hh]\d):\s*(.*)").sub(r"<\1>\2</\1>")
        result = expr.transformString(
            "h1: This is the main heading\nh2: This is the sub-heading"
        )
        print(result)
        self.assertEqual(
            "<h1>This is the main heading</h1>\n<h2>This is the sub-heading</h2>",
            result,
            "incorrect Regex.sub result with re string",
        )

        print("test sub with re string (Regex returns re.match)")
        expr = pp.Regex(r"([Hh]\d):\s*(.*)", asMatch=True).sub(r"<\1>\2</\1>")
        result = expr.transformString(
            "h1: This is the main heading\nh2: This is the sub-heading"
        )
        print(result)
        self.assertEqual(
            "<h1>This is the main heading</h1>\n<h2>This is the sub-heading</h2>",
            result,
            "incorrect Regex.sub result with re string",
        )

        print("test sub with callable that return str")
        expr = pp.Regex(r"<(.*?)>").sub(lambda m: m.group(1).upper())
        result = expr.transformString("I want this in upcase: <what? what?>")
        print(result)
        self.assertEqual(
            "I want this in upcase: WHAT? WHAT?",
            result,
            "incorrect Regex.sub result with callable",
        )

        with self.assertRaises(TypeError):
            pp.Regex(r"<(.*?)>", asMatch=True).sub(lambda m: m.group(1).upper())

        with self.assertRaises(TypeError):
            pp.Regex(r"<(.*?)>", asGroupList=True).sub(lambda m: m.group(1).upper())

        with self.assertRaises(TypeError):
            pp.Regex(r"<(.*?)>", asGroupList=True).sub("")

    def testRegexInvalidType(self):
        """test Regex of an invalid type"""

        with self.assertRaises(TypeError, msg="issue with Regex of type int"):
            expr = pp.Regex(12)

    def testPrecededBy(self):

        num = pp.Word(pp.nums).setParseAction(lambda t: int(t[0]))
        interesting_num = pp.PrecededBy(pp.Char("abc")("prefix*")) + num
        semi_interesting_num = pp.PrecededBy("_") + num
        crazy_num = pp.PrecededBy(pp.Word("^", "$%^")("prefix*"), 10) + num
        boring_num = ~pp.PrecededBy(pp.Char("abc_$%^" + pp.nums)) + num
        very_boring_num = pp.PrecededBy(pp.WordStart()) + num
        finicky_num = pp.PrecededBy(pp.Word("^", "$%^"), retreat=3) + num

        s = "c384 b8324 _9293874 _293 404 $%^$^%$2939"
        print(s)
        for expr, expected_list, expected_dict in [
            (interesting_num, [384, 8324], {"prefix": ["c", "b"]}),
            (semi_interesting_num, [9293874, 293], {}),
            (boring_num, [404], {}),
            (crazy_num, [2939], {"prefix": ["^%$"]}),
            (finicky_num, [2939], {}),
            (very_boring_num, [404], {}),
        ]:
            # print(expr.searchString(s))
            result = sum(expr.searchString(s))
            print(result.dump())
            self.assertParseResultsEquals(result, expected_list, expected_dict)

        # infinite loop test - from Issue #127
        string_test = "notworking"
        # negs = pp.Or(['not', 'un'])('negs')
        negs_pb = pp.PrecededBy("not", retreat=100)("negs_lb")
        # negs_pb = pp.PrecededBy(negs, retreat=100)('negs_lb')
        pattern = (negs_pb + pp.Literal("working"))("main")

        results = pattern.searchString(string_test)
        try:
            print(results.dump())
        except RecursionError:
            self.fail("got maximum excursion limit exception")
        else:
            print("got maximum excursion limit exception")

    def testCountedArray(self):

        testString = "2 5 7 6 0 1 2 3 4 5 0 3 5 4 3"

        integer = pp.Word(pp.nums).setParseAction(lambda t: int(t[0]))
        countedField = pp.countedArray(integer)

        r = pp.OneOrMore(pp.Group(countedField)).parseString(testString)
        print(testString)
        print(r)

        self.assertParseResultsEquals(
            r, expected_list=[[5, 7], [0, 1, 2, 3, 4, 5], [], [5, 4, 3]]
        )

    # addresses bug raised by Ralf Vosseler
    def testCountedArrayTest2(self):

        testString = "2 5 7 6 0 1 2 3 4 5 0 3 5 4 3"

        integer = pp.Word(pp.nums).setParseAction(lambda t: int(t[0]))
        countedField = pp.countedArray(integer)

        dummy = pp.Word("A")
        r = pp.OneOrMore(pp.Group(dummy ^ countedField)).parseString(testString)
        print(testString)
        print(r)

        self.assertParseResultsEquals(
            r, expected_list=[[5, 7], [0, 1, 2, 3, 4, 5], [], [5, 4, 3]]
        )

    def testCountedArrayTest3(self):

        int_chars = "_" + pp.alphas
        array_counter = pp.Word(int_chars).setParseAction(
            lambda t: int_chars.index(t[0])
        )

        #             123456789012345678901234567890
        testString = "B 5 7 F 0 1 2 3 4 5 _ C 5 4 3"

        integer = pp.Word(pp.nums).setParseAction(lambda t: int(t[0]))
        countedField = pp.countedArray(integer, intExpr=array_counter)

        r = pp.OneOrMore(pp.Group(countedField)).parseString(testString)
        print(testString)
        print(r)

        self.assertParseResultsEquals(
            r, expected_list=[[5, 7], [0, 1, 2, 3, 4, 5], [], [5, 4, 3]]
        )

    def testCountedArrayTest4(self):
        ppc = pp.pyparsing_common

        # array counter contains several fields - first field *must* be the number of
        # items in the array
        # - number of elements
        # - type of elements
        # - source of elements
        counter_with_metadata = (
            ppc.integer("count") + ppc.identifier("type") + ppc.identifier("source")
        )

        countedField = pp.countedArray(
            pp.Word(pp.alphanums), intExpr=counter_with_metadata
        )

        testString = (
            "5 string input item1 item2 item3 item4 item5 0 int user 2 int file 3 8"
        )
        r = pp.Group(countedField("items"))[...].parseString(testString, parseAll=True)

        print(testString)
        print(r.dump())
        print("type = {!r}".format(r.type))
        print("source = {!r}".format(r.source))

        self.assertParseResultsEquals(
            r,
            expected_list=[
                ["item1", "item2", "item3", "item4", "item5"],
                [],
                ["3", "8"],
            ],
        )

        self.assertParseResultsEquals(
            r[0],
            expected_dict={
                "count": 5,
                "source": "input",
                "type": "string",
                "items": ["item1", "item2", "item3", "item4", "item5"],
            },
        )

        # parse with additional fields between the count and the actual list items
        count_with_metadata = ppc.integer + pp.Word(pp.alphas)("type")
        typed_array = pp.countedArray(
            pp.Word(pp.alphanums), intExpr=count_with_metadata
        )("items")
        result = typed_array.parseString("3 bool True True False")
        print(result.dump())

        self.assertParseResultsEquals(
            result,
            expected_list=["True", "True", "False"],
            expected_dict={"type": "bool", "items": ["True", "True", "False"]},
        )

    def testLineStart(self):

        pass_tests = [
            """\
            AAA
            BBB
            """,
            """\
            AAA...
            BBB
            """,
        ]
        fail_tests = [
            """\
            AAA...
            ...BBB
            """,
            """\
            AAA  BBB
            """,
        ]

        # cleanup test strings
        pass_tests = [
            "\n".join(s.lstrip() for s in t.splitlines()).replace(".", " ")
            for t in pass_tests
        ]
        fail_tests = [
            "\n".join(s.lstrip() for s in t.splitlines()).replace(".", " ")
            for t in fail_tests
        ]

        test_patt = pp.Word("A") - pp.LineStart() + pp.Word("B")
        print(test_patt.streamline())
        success = test_patt.runTests(pass_tests)[0]
        self.assertTrue(success, "failed LineStart passing tests (1)")

        success = test_patt.runTests(fail_tests, failureTests=True)[0]
        self.assertTrue(success, "failed LineStart failure mode tests (1)")

        with ppt.reset_pyparsing_context():
            print(r"no \n in default whitespace chars")
            pp.ParserElement.setDefaultWhitespaceChars(" ")

            test_patt = pp.Word("A") - pp.LineStart() + pp.Word("B")
            print(test_patt.streamline())
            # should fail the pass tests too, since \n is no longer valid whitespace and we aren't parsing for it
            success = test_patt.runTests(pass_tests, failureTests=True)[0]
            self.assertTrue(success, "failed LineStart passing tests (2)")

            success = test_patt.runTests(fail_tests, failureTests=True)[0]
            self.assertTrue(success, "failed LineStart failure mode tests (2)")

            test_patt = (
                pp.Word("A")
                - pp.LineEnd().suppress()
                + pp.LineStart()
                + pp.Word("B")
                + pp.LineEnd().suppress()
            )
            print(test_patt.streamline())
            success = test_patt.runTests(pass_tests)[0]
            self.assertTrue(success, "failed LineStart passing tests (3)")

            success = test_patt.runTests(fail_tests, failureTests=True)[0]
            self.assertTrue(success, "failed LineStart failure mode tests (3)")

    def testLineStart2(self):

        test = """\
        AAA 1
        AAA 2

          AAA

        B AAA

        """

        test = dedent(test)
        print(pp.testing.with_line_numbers(test))

        print("normal parsing")
        for t, s, e in (pp.LineStart() + "AAA").scanString(test):
            print(s, e, pp.lineno(s, test), pp.line(s, test), repr(t))
            print()
            self.assertEqual(
                "A", t[0][0], "failed LineStart with insignificant newlines"
            )

        print(r"parsing without \n in whitespace chars")
        with ppt.reset_pyparsing_context():
            pp.ParserElement.setDefaultWhitespaceChars(" ")
            for t, s, e in (pp.LineStart() + "AAA").scanString(test):
                print(s, e, pp.lineno(s, test), pp.line(s, test), repr(test[s]))
                print()
                self.assertEqual(
                    "A", t[0][0], "failed LineStart with insignificant newlines"
                )

    def testLineStartWithLeadingSpaces(self):
        # testing issue #272
        # reverted in 3.0.2 - LineStart() + expr will match expr even if there
        # are leading spaces. To force "only at column 1" matching, use
        # AtLineStart(expr).
        instring = dedent(
            """
            a
             b
              c
            d
            e
             f
              g
            """
        )
        print(pp.testing.with_line_numbers(instring))

        alpha_line = (
            pp.LineStart().leaveWhitespace()
            + pp.Word(pp.alphas)
            + pp.LineEnd().suppress()
        )

        tests = [
            alpha_line,
            pp.Group(alpha_line),
            alpha_line | pp.Word("_"),
            alpha_line | alpha_line,
            pp.MatchFirst([alpha_line, alpha_line]),
            alpha_line ^ pp.Word("_"),
            alpha_line ^ alpha_line,
            pp.Or([alpha_line, pp.Word("_")]),
            pp.LineStart() + pp.Word(pp.alphas) + pp.LineEnd().suppress(),
            pp.And([pp.LineStart(), pp.Word(pp.alphas), pp.LineEnd().suppress()]),
        ]
        fails = []
        for test in tests:
            print(test.searchString(instring))
            if ["a", "b", "c", "d", "e", "f", "g"] != flatten(
                sum(test.search_string(instring)).as_list()
            ):
                fails.append(test)
        if fails:
            self.fail(
                "failed LineStart tests:\n{}".format(
                    "\n".join(str(expr) for expr in fails)
                )
            )

    def testAtLineStart(self):
        test = dedent(
            """\
        AAA this line
        AAA and this line
          AAA but not this one
        B AAA and definitely not this one
        """
        )

        expr = pp.AtLineStart("AAA") + pp.restOfLine
        for t in expr.search_string(test):
            print(t)

        self.assertEqual(
            ["AAA", " this line", "AAA", " and this line"],
            sum(expr.search_string(test)).as_list(),
        )

    def testStringStart(self):
        self.assertParseAndCheckList(
            pp.StringStart() + pp.Word(pp.nums), "123", ["123"]
        )
        self.assertParseAndCheckList(
            pp.StringStart() + pp.Word(pp.nums), "   123", ["123"]
        )
        self.assertParseAndCheckList(pp.StringStart() + "123", "123", ["123"])
        self.assertParseAndCheckList(pp.StringStart() + "123", "   123", ["123"])
        self.assertParseAndCheckList(pp.AtStringStart(pp.Word(pp.nums)), "123", ["123"])

        self.assertParseAndCheckList(pp.AtStringStart("123"), "123", ["123"])

        with self.assertRaisesParseException():
            pp.AtStringStart(pp.Word(pp.nums)).parse_string("    123")

        with self.assertRaisesParseException():
            pp.AtStringStart("123").parse_string("    123")

    def testStringStartAndLineStartInsideAnd(self):
        # fmt: off
        P_MTARG = (
                pp.StringStart()
                + pp.Word("abcde")
                + pp.StringEnd()
        )

        P_MTARG2 = (
                pp.LineStart()
                + pp.Word("abcde")
                + pp.StringEnd()
        )

        P_MTARG3 = (
                pp.AtLineStart(pp.Word("abcde"))
                + pp.StringEnd()
        )
        # fmt: on

        def test(expr, string):
            expr.streamline()
            print(expr, repr(string), end=" ")
            print(expr.parse_string(string))

        test(P_MTARG, "aaa")
        test(P_MTARG2, "aaa")
        test(P_MTARG2, "\naaa")
        test(P_MTARG2, "   aaa")
        test(P_MTARG2, "\n   aaa")

        with self.assertRaisesParseException():
            test(P_MTARG3, "   aaa")
        with self.assertRaisesParseException():
            test(P_MTARG3, "\n   aaa")

    def testLineAndStringEnd(self):

        NLs = pp.OneOrMore(pp.lineEnd)
        bnf1 = pp.delimitedList(pp.Word(pp.alphanums).leaveWhitespace(), NLs)
        bnf2 = pp.Word(pp.alphanums) + pp.stringEnd
        bnf3 = pp.Word(pp.alphanums) + pp.SkipTo(pp.stringEnd)
        tests = [
            ("testA\ntestB\ntestC\n", ["testA", "testB", "testC"]),
            ("testD\ntestE\ntestF", ["testD", "testE", "testF"]),
            ("a", ["a"]),
        ]

        for test, expected in tests:
            res1 = bnf1.parseString(test)
            print(res1, "=?", expected)
            self.assertParseResultsEquals(
                res1,
                expected_list=expected,
                msg="Failed lineEnd/stringEnd test (1): "
                + repr(test)
                + " -> "
                + str(res1),
            )

            res2 = bnf2.searchString(test)[0]
            print(res2, "=?", expected[-1:])
            self.assertParseResultsEquals(
                res2,
                expected_list=expected[-1:],
                msg="Failed lineEnd/stringEnd test (2): "
                + repr(test)
                + " -> "
                + str(res2),
            )

            res3 = bnf3.parseString(test)
            first = res3[0]
            rest = res3[1]
            # ~ print res3.dump()
            print(repr(rest), "=?", repr(test[len(first) + 1 :]))
            self.assertEqual(
                rest,
                test[len(first) + 1 :],
                "Failed lineEnd/stringEnd test (3): "
                + repr(test)
                + " -> "
                + str(res3.asList()),
            )
            print()

        k = pp.Regex(r"a+", flags=re.S + re.M)
        k = k.parseWithTabs()
        k = k.leaveWhitespace()

        tests = [
            (r"aaa", ["aaa"]),
            (r"\naaa", None),
            (r"a\naa", None),
            (r"aaa\n", None),
        ]
        for i, (src, expected) in enumerate(tests):
            print(i, repr(src).replace("\\\\", "\\"), end=" ")
            if expected is None:
                with self.assertRaisesParseException():
                    k.parseString(src, parseAll=True)
            else:
                res = k.parseString(src, parseAll=True)
                self.assertParseResultsEquals(
                    res, expected, msg="Failed on parseAll=True test %d" % i
                )

    def testVariableParseActionArgs(self):
        pa3 = lambda s, l, t: t
        pa2 = lambda l, t: t
        pa1 = lambda t: t
        pa0 = lambda: None

        class Callable3:
            def __call__(self, s, l, t):
                return t

        class Callable2:
            def __call__(self, l, t):
                return t

        class Callable1:
            def __call__(self, t):
                return t

        class Callable0:
            def __call__(self):
                return

        class CallableS3:
            @staticmethod
            def __call__(s, l, t):
                return t

        class CallableS2:
            @staticmethod
            def __call__(l, t):
                return t

        class CallableS1:
            @staticmethod
            def __call__(t):
                return t

        class CallableS0:
            @staticmethod
            def __call__():
                return

        class CallableC3:
            @classmethod
            def __call__(cls, s, l, t):
                return t

        class CallableC2:
            @classmethod
            def __call__(cls, l, t):
                return t

        class CallableC1:
            @classmethod
            def __call__(cls, t):
                return t

        class CallableC0:
            @classmethod
            def __call__(cls):
                return

        class parseActionHolder:
            @staticmethod
            def pa3(s, l, t):
                return t

            @staticmethod
            def pa2(l, t):
                return t

            @staticmethod
            def pa1(t):
                return t

            @staticmethod
            def pa0():
                return

        def paArgs(*args):
            print(args)
            return args[2]

        class ClassAsPA0:
            def __init__(self):
                pass

            def __str__(self):
                return "A"

        class ClassAsPA1:
            def __init__(self, t):
                print("making a ClassAsPA1")
                self.t = t

            def __str__(self):
                return self.t[0]

        class ClassAsPA2:
            def __init__(self, l, t):
                self.t = t

            def __str__(self):
                return self.t[0]

        class ClassAsPA3:
            def __init__(self, s, l, t):
                self.t = t

            def __str__(self):
                return self.t[0]

        class ClassAsPAStarNew(tuple):
            def __new__(cls, *args):
                print("make a ClassAsPAStarNew", args)
                return tuple.__new__(cls, *args[2].asList())

            def __str__(self):
                return "".join(self)

        A = pp.Literal("A").setParseAction(pa0)
        B = pp.Literal("B").setParseAction(pa1)
        C = pp.Literal("C").setParseAction(pa2)
        D = pp.Literal("D").setParseAction(pa3)
        E = pp.Literal("E").setParseAction(Callable0())
        F = pp.Literal("F").setParseAction(Callable1())
        G = pp.Literal("G").setParseAction(Callable2())
        H = pp.Literal("H").setParseAction(Callable3())
        I = pp.Literal("I").setParseAction(CallableS0())
        J = pp.Literal("J").setParseAction(CallableS1())
        K = pp.Literal("K").setParseAction(CallableS2())
        L = pp.Literal("L").setParseAction(CallableS3())
        M = pp.Literal("M").setParseAction(CallableC0())
        N = pp.Literal("N").setParseAction(CallableC1())
        O = pp.Literal("O").setParseAction(CallableC2())
        P = pp.Literal("P").setParseAction(CallableC3())
        Q = pp.Literal("Q").setParseAction(paArgs)
        R = pp.Literal("R").setParseAction(parseActionHolder.pa3)
        S = pp.Literal("S").setParseAction(parseActionHolder.pa2)
        T = pp.Literal("T").setParseAction(parseActionHolder.pa1)
        U = pp.Literal("U").setParseAction(parseActionHolder.pa0)
        V = pp.Literal("V")

        # fmt: off
        gg = pp.OneOrMore(
            A | B | C | D | E | F | G | H | I | J | K | L | M | N | O | P | Q | R | S | U | V | B | T
        )
        # fmt: on
        testString = "VUTSRQPONMLKJIHGFEDCBA"
        res = gg.parseString(testString)
        print(res)
        self.assertParseResultsEquals(
            res,
            expected_list=list(testString),
            msg="Failed to parse using variable length parse actions",
        )

        A = pp.Literal("A").setParseAction(ClassAsPA0)
        B = pp.Literal("B").setParseAction(ClassAsPA1)
        C = pp.Literal("C").setParseAction(ClassAsPA2)
        D = pp.Literal("D").setParseAction(ClassAsPA3)
        E = pp.Literal("E").setParseAction(ClassAsPAStarNew)

        # fmt: off
        gg = pp.OneOrMore(
            A | B | C | D | E | F | G | H | I | J | K | L | M | N | O | P | Q | R | S | T | U | V
        )
        # fmt: on
        testString = "VUTSRQPONMLKJIHGFEDCBA"
        res = gg.parseString(testString)
        print(list(map(str, res)))
        self.assertEqual(
            list(testString),
            list(map(str, res)),
            "Failed to parse using variable length parse actions "
            "using class constructors as parse actions",
        )

    def testSingleArgException(self):

        testMessage = "just one arg"
        try:
            raise pp.ParseFatalException(testMessage)
        except pp.ParseBaseException as pbe:
            print("Received expected exception:", pbe)
            raisedMsg = pbe.msg
            self.assertEqual(
                testMessage, raisedMsg, "Failed to get correct exception message"
            )

    def testOriginalTextFor(self):
        def rfn(t):
            return "%s:%d" % (t.src, len("".join(t)))

        makeHTMLStartTag = lambda tag: pp.originalTextFor(
            pp.makeHTMLTags(tag)[0], asString=False
        )

        # use the lambda, Luke
        start = makeHTMLStartTag("IMG")

        # don't replace our fancy parse action with rfn,
        # append rfn to the list of parse actions
        start.addParseAction(rfn)

        text = """_<img src="images/cal.png"
            alt="cal image" width="16" height="15">_"""
        s = start.transformString(text)
        print(s)
        self.assertTrue(
            s.startswith("_images/cal.png:"), "failed to preserve input s properly"
        )
        self.assertTrue(
            s.endswith("77_"), "failed to return full original text properly"
        )

        tag_fields = makeHTMLStartTag("IMG").searchString(text)[0]
        print(sorted(tag_fields.keys()))
        self.assertEqual(
            ["alt", "empty", "height", "src", "startImg", "tag", "width"],
            sorted(tag_fields.keys()),
            "failed to preserve results names in originalTextFor",
        )

    def testPackratParsingCacheCopy(self):

        integer = pp.Word(pp.nums).setName("integer")
        id = pp.Word(pp.alphas + "_", pp.alphanums + "_")
        simpleType = pp.Literal("int")
        arrayType = simpleType + ("[" + pp.delimitedList(integer) + "]")[...]
        varType = arrayType | simpleType
        varDec = varType + pp.delimitedList(id + pp.Optional("=" + integer)) + ";"

        codeBlock = pp.Literal("{}")

        funcDef = (
            pp.Optional(varType | "void")
            + id
            + "("
            + (pp.delimitedList(varType + id) | "void" | pp.empty)
            + ")"
            + codeBlock
        )

        program = varDec | funcDef
        input = "int f(){}"
        self.assertParseAndCheckList(
            program,
            input,
            ["int", "f", "(", ")", "{}"],
            msg="Error in packrat parsing",
            verbose=True,
        )

    def testPackratParsingCacheCopyTest2(self):

        DO, AA = list(map(pp.Keyword, "DO AA".split()))
        LPAR, RPAR = list(map(pp.Suppress, "()"))
        identifier = ~AA + pp.Word("Z")

        function_name = identifier.copy()
        # ~ function_name = ~AA + Word("Z")  #identifier.copy()
        expr = pp.Forward().setName("expr")
        expr <<= pp.Group(
            function_name + LPAR + pp.Optional(pp.delimitedList(expr)) + RPAR
        ).setName("functionCall") | identifier.setName(
            "ident"
        )  # .setDebug()#.setBreak()

        stmt = DO + pp.Group(pp.delimitedList(identifier + ".*" | expr))
        result = stmt.parseString("DO Z")
        print(result.asList())
        self.assertEqual(
            1, len(result[1]), "packrat parsing is duplicating And term exprs"
        )

    def testParseResultsDel(self):
        grammar = pp.OneOrMore(pp.Word(pp.nums))("ints") + pp.OneOrMore(
            pp.Word(pp.alphas)
        )("words")
        res = grammar.parseString("123 456 ABC DEF")
        print(res.dump())
        origInts = res.ints.asList()
        origWords = res.words.asList()
        del res[1]
        del res["words"]
        print(res.dump())
        self.assertEqual("ABC", res[1], "failed to delete 0'th element correctly")
        self.assertEqual(
            origInts,
            res.ints.asList(),
            "updated named attributes, should have updated list only",
        )
        self.assertEqual("", res.words, "failed to update named attribute correctly")
        self.assertEqual(
            "DEF", res[-1], "updated list, should have updated named attributes only"
        )

    def testWithAttributeParseAction(self):
        """
        This unit test checks withAttribute in these ways:

        * Argument forms as keywords and tuples
        * Selecting matching tags by attribute
        * Case-insensitive attribute matching
        * Correctly matching tags having the attribute, and rejecting tags not having the attribute

        (Unit test written by voigts as part of the Google Highly Open Participation Contest)
        """

        data = """
        <a>1</a>
        <a b="x">2</a>
        <a B="x">3</a>
        <a b="X">4</a>
        <a b="y">5</a>
        <a class="boo">8</ a>
        """
        tagStart, tagEnd = pp.makeHTMLTags("a")

        expr = tagStart + pp.Word(pp.nums)("value") + tagEnd

        expected = (
            [
                ["a", ["b", "x"], False, "2", "</a>"],
                ["a", ["b", "x"], False, "3", "</a>"],
            ],
            [
                ["a", ["b", "x"], False, "2", "</a>"],
                ["a", ["b", "x"], False, "3", "</a>"],
            ],
            [["a", ["class", "boo"], False, "8", "</a>"]],
        )

        for attrib, exp in zip(
            [
                pp.withAttribute(b="x"),
                # withAttribute(B="x"),
                pp.withAttribute(("b", "x")),
                # withAttribute(("B", "x")),
                pp.withClass("boo"),
            ],
            expected,
        ):

            tagStart.setParseAction(attrib)
            result = expr.searchString(data)

            print(result.dump())
            self.assertParseResultsEquals(
                result,
                expected_list=exp,
                msg="Failed test, expected {}, got {}".format(
                    expected, result.asList()
                ),
            )

    def testNestedExpressions(self):
        """
        This unit test checks nestedExpr in these ways:
        - use of default arguments
        - use of non-default arguments (such as a pyparsing-defined comment
          expression in place of quotedString)
        - use of a custom content expression
        - use of a pyparsing expression for opener and closer is *OPTIONAL*
        - use of input data containing nesting delimiters
        - correct grouping of parsed tokens according to nesting of opening
          and closing delimiters in the input string

        (Unit test written by christoph... as part of the Google Highly Open Participation Contest)
        """

        # All defaults. Straight out of the example script. Also, qualifies for
        # the bonus: note the fact that (Z | (E^F) & D) is not parsed :-).
        # Tests for bug fixed in 1.4.10
        print("Test defaults:")
        teststring = "((ax + by)*C) (Z | (E^F) & D)"

        expr = pp.nestedExpr()

        expected = [[["ax", "+", "by"], "*C"]]
        result = expr.parseString(teststring)
        print(result.dump())
        self.assertParseResultsEquals(
            result,
            expected_list=expected,
            msg="Defaults didn't work. That's a bad sign. Expected: {}, got: {}".format(
                expected, result
            ),
        )

        # Going through non-defaults, one by one; trying to think of anything
        # odd that might not be properly handled.

        # Change opener
        print("\nNon-default opener")
        teststring = "[[ ax + by)*C)"
        expected = [[["ax", "+", "by"], "*C"]]
        expr = pp.nestedExpr("[")
        self.assertParseAndCheckList(
            expr,
            teststring,
            expected,
            "Non-default opener didn't work. Expected: {}, got: {}".format(
                expected, result
            ),
            verbose=True,
        )

        # Change closer
        print("\nNon-default closer")

        teststring = "((ax + by]*C]"
        expected = [[["ax", "+", "by"], "*C"]]
        expr = pp.nestedExpr(closer="]")
        self.assertParseAndCheckList(
            expr,
            teststring,
            expected,
            "Non-default closer didn't work. Expected: {}, got: {}".format(
                expected, result
            ),
            verbose=True,
        )

        # #Multicharacter opener, closer
        # opener = "bar"
        # closer = "baz"
        print("\nLiteral expressions for opener and closer")

        opener, closer = map(pp.Literal, "bar baz".split())
        expr = pp.nestedExpr(
            opener, closer, content=pp.Regex(r"([^b ]|b(?!a)|ba(?![rz]))+")
        )

        teststring = "barbar ax + bybaz*Cbaz"
        expected = [[["ax", "+", "by"], "*C"]]
        self.assertParseAndCheckList(
            expr,
            teststring,
            expected,
            "Multicharacter opener and closer didn't work. Expected: {}, got: {}".format(
                expected, result
            ),
            verbose=True,
        )

        # Lisp-ish comments
        print("\nUse ignore expression (1)")
        comment = pp.Regex(r";;.*")
        teststring = """
        (let ((greeting "Hello, world!")) ;;(foo bar
           (display greeting))
        """

        expected = [
            [
                "let",
                [["greeting", '"Hello,', 'world!"']],
                ";;(foo bar",
                ["display", "greeting"],
            ]
        ]
        expr = pp.nestedExpr(ignoreExpr=comment)
        self.assertParseAndCheckList(
            expr,
            teststring,
            expected,
            'Lisp-ish comments (";; <...> $") didn\'t work. Expected: {}, got: {}'.format(
                expected, result
            ),
            verbose=True,
        )

        # Lisp-ish comments, using a standard bit of pyparsing, and an Or.
        print("\nUse ignore expression (2)")
        comment = ";;" + pp.restOfLine

        teststring = """
        (let ((greeting "Hello, )world!")) ;;(foo bar
           (display greeting))
        """

        expected = [
            [
                "let",
                [["greeting", '"Hello, )world!"']],
                ";;",
                "(foo bar",
                ["display", "greeting"],
            ]
        ]
        expr = pp.nestedExpr(ignoreExpr=(comment ^ pp.quotedString))
        self.assertParseAndCheckList(
            expr,
            teststring,
            expected,
            'Lisp-ish comments (";; <...> $") and quoted strings didn\'t work. Expected: {}, got: {}'.format(
                expected, result
            ),
            verbose=True,
        )

    def testNestedExpressions2(self):
        """test nestedExpr with conditions that explore other paths

        identical opener and closer
        opener and/or closer of type other than string or iterable
        multi-character opener and/or closer
        single character opener and closer with ignoreExpr=None
        multi-character opener and/or closer with ignoreExpr=None
        """

        name = pp.Word(pp.alphanums + "_")

        # identical opener and closer
        with self.assertRaises(
            ValueError, msg="matching opener and closer should raise error"
        ):
            expr = name + pp.nestedExpr(opener="{", closer="{")

        # opener and/or closer of type other than string or iterable
        with self.assertRaises(
            ValueError, msg="opener and closer as ints should raise error"
        ):
            expr = name + pp.nestedExpr(opener=12, closer=18)

        # multi-character opener and/or closer
        tstMulti = "aName {{ outer {{ 'inner with opener {{ and closer }} in quoted string' }} }}"
        expr = name + pp.nestedExpr(opener="{{", closer="}}")
        result = expr.parseString(tstMulti)
        expected = [
            "aName",
            ["outer", ["'inner with opener {{ and closer }} in quoted string'"]],
        ]
        print(result.dump())
        self.assertParseResultsEquals(
            result, expected, msg="issue with multi-character opener and closer"
        )

        # single character opener and closer with ignoreExpr=None
        tst = (
            "aName { outer { 'inner with opener { and closer } in quoted string' }} }}"
        )
        expr = name + pp.nestedExpr(opener="{", closer="}", ignoreExpr=None)
        singleCharResult = expr.parseString(tst)
        print(singleCharResult.dump())

        # multi-character opener and/or closer with ignoreExpr=None
        expr = name + pp.nestedExpr(opener="{{", closer="}}", ignoreExpr=None)
        multiCharResult = expr.parseString(tstMulti)
        print(multiCharResult.dump())

        self.assertParseResultsEquals(
            singleCharResult,
            multiCharResult.asList(),
            msg="using different openers and closers shouldn't affect resulting ParseResults",
        )

    def testWordMinMaxArgs(self):
        parsers = [
            "A" + pp.Word(pp.nums),
            "A" + pp.Word(pp.nums, min=1),
            "A" + pp.Word(pp.nums, max=6),
            "A" + pp.Word(pp.nums, min=1, max=6),
            "A" + pp.Word(pp.nums, min=1),
            "A" + pp.Word(pp.nums, min=2),
            "A" + pp.Word(pp.nums, min=2, max=6),
            pp.Word("A", pp.nums),
            pp.Word("A", pp.nums, min=1),
            pp.Word("A", pp.nums, max=6),
            pp.Word("A", pp.nums, min=1, max=6),
            pp.Word("A", pp.nums, min=1),
            pp.Word("A", pp.nums, min=2),
            pp.Word("A", pp.nums, min=2, max=6),
            pp.Word(pp.alphas, pp.nums),
            pp.Word(pp.alphas, pp.nums, min=1),
            pp.Word(pp.alphas, pp.nums, max=6),
            pp.Word(pp.alphas, pp.nums, min=1, max=6),
            pp.Word(pp.alphas, pp.nums, min=1),
            pp.Word(pp.alphas, pp.nums, min=2),
            pp.Word(pp.alphas, pp.nums, min=2, max=6),
        ]

        fails = []
        for p in parsers:
            print(p, getattr(p, "reString", "..."), end=" ", flush=True)
            try:
                p.parseString("A123")
            except Exception as e:
                print("      <<< FAIL")
                fails.append(p)
            else:
                print()
        if fails:
            self.fail("{} failed to match".format(",".join(str(f) for f in fails)))

    def testWordExclude(self):

        allButPunc = pp.Word(pp.printables, excludeChars=".,:;-_!?")

        test = "Hello, Mr. Ed, it's Wilbur!"
        result = allButPunc.searchString(test).asList()
        print(result)
        self.assertEqual(
            [["Hello"], ["Mr"], ["Ed"], ["it's"], ["Wilbur"]],
            result,
            "failed WordExcludeTest",
        )

    def testWordMinOfZero(self):
        """test a Word with min=0"""

        with self.assertRaises(ValueError, msg="expected min 0 to error"):
            expr = pp.Word(pp.nums, min=0, max=10)

    @staticmethod
    def setup_testWordMaxGreaterThanZeroAndAsKeyword():
        # fmt: off
        bool_operand = (
                pp.Word(pp.alphas, max=1, asKeyword=True)
                | pp.one_of("True False")
        )
        test_string = "p q r False"
        return SimpleNamespace(**locals())
        # fmt: on

    def testWordMaxGreaterThanZeroAndAsKeyword1(self):
        """test a Word with max>0 and asKeyword=True"""
        setup = self.setup_testWordMaxGreaterThanZeroAndAsKeyword()

        result = setup.bool_operand[...].parseString(setup.test_string)
        self.assertParseAndCheckList(
            setup.bool_operand[...],
            setup.test_string,
            setup.test_string.split(),
            msg=__() + "Failed to parse Word(max=1, asKeyword=True)",
            verbose=True,
        )

    def testWordMaxGreaterThanZeroAndAsKeyword2(self):
        """test a Word with max>0 and asKeyword=True"""
        setup = self.setup_testWordMaxGreaterThanZeroAndAsKeyword()

        with self.assertRaisesParseException(
            msg=__() + "failed to detect Word with max > 0 and asKeyword=True"
        ):
            setup.bool_operand.parseString("abc")

    def testCharAsKeyword(self):
        """test a Char with asKeyword=True"""

        grade = pp.OneOrMore(pp.Char("ABCDF", asKeyword=True))

        # all single char words
        result = grade.parseString("B B C A D")

        print(result)
        expected = ["B", "B", "C", "A", "D"]
        self.assertParseResultsEquals(
            result, expected, msg="issue with Char asKeyword=True"
        )

        # NOT all single char words
        test2 = "B BB C A D"
        result2 = grade.parseString(test2)

        print(result2)
        expected2 = ["B"]
        self.assertParseResultsEquals(
            result2, expected2, msg="issue with Char asKeyword=True parsing 2 chars"
        )

    def testCharsNotIn(self):
        """test CharsNotIn initialized with various arguments"""

        vowels = "AEIOU"
        tst = "bcdfghjklmnpqrstvwxyz"

        # default args
        consonants = pp.CharsNotIn(vowels)
        result = consonants.parseString(tst)
        print(result)
        self.assertParseResultsEquals(
            result, [tst], msg="issue with CharsNotIn w/ default args"
        )

        # min = 0
        with self.assertRaises(ValueError, msg="issue with CharsNotIn w/ min=0"):
            consonants = pp.CharsNotIn(vowels, min=0)

        # max > 0
        consonants = pp.CharsNotIn(vowels, max=5)
        result = consonants.parseString(tst)
        print(result)
        self.assertParseResultsEquals(
            result, [tst[:5]], msg="issue with CharsNotIn w max > 0"
        )

        # exact > 0
        consonants = pp.CharsNotIn(vowels, exact=10)
        result = consonants.parseString(tst[:10])
        print(result)
        self.assertParseResultsEquals(
            result, [tst[:10]], msg="issue with CharsNotIn w/ exact > 0"
        )

        # min > length
        consonants = pp.CharsNotIn(vowels, min=25)
        with self.assertRaisesParseException(msg="issue with CharsNotIn min > tokens"):
            result = consonants.parseString(tst)

    def testParseAll(self):

        testExpr = pp.Word("A")

        tests = [
            ("AAAAA", False, True),
            ("AAAAA", True, True),
            ("AAABB", False, True),
            ("AAABB", True, False),
        ]
        for s, parseAllFlag, shouldSucceed in tests:
            try:
                print(
                    "'{}' parseAll={} (shouldSucceed={})".format(
                        s, parseAllFlag, shouldSucceed
                    )
                )
                testExpr.parseString(s, parseAll=parseAllFlag)
                self.assertTrue(
                    shouldSucceed, "successfully parsed when should have failed"
                )
            except ParseException as pe:
                print(pe.explain())
                self.assertFalse(
                    shouldSucceed, "failed to parse when should have succeeded"
                )

        # add test for trailing comments
        testExpr.ignore(pp.cppStyleComment)

        tests = [
            ("AAAAA //blah", False, True),
            ("AAAAA //blah", True, True),
            ("AAABB //blah", False, True),
            ("AAABB //blah", True, False),
        ]
        for s, parseAllFlag, shouldSucceed in tests:
            try:
                print(
                    "'{}' parseAll={} (shouldSucceed={})".format(
                        s, parseAllFlag, shouldSucceed
                    )
                )
                testExpr.parseString(s, parseAll=parseAllFlag)
                self.assertTrue(
                    shouldSucceed, "successfully parsed when should have failed"
                )
            except ParseException as pe:
                print(pe.explain())
                self.assertFalse(
                    shouldSucceed, "failed to parse when should have succeeded"
                )

        # add test with very long expression string
        # testExpr = pp.MatchFirst([pp.Literal(c) for c in pp.printables if c != 'B'])[1, ...]
        anything_but_an_f = pp.OneOrMore(
            pp.MatchFirst([pp.Literal(c) for c in pp.printables if c != "f"])
        )
        testExpr = pp.Word("012") + anything_but_an_f

        tests = [
            ("00aab", False, True),
            ("00aab", True, True),
            ("00aaf", False, True),
            ("00aaf", True, False),
        ]
        for s, parseAllFlag, shouldSucceed in tests:
            try:
                print(
                    "'{}' parseAll={} (shouldSucceed={})".format(
                        s, parseAllFlag, shouldSucceed
                    )
                )
                testExpr.parseString(s, parseAll=parseAllFlag)
                self.assertTrue(
                    shouldSucceed, "successfully parsed when should have failed"
                )
            except ParseException as pe:
                print(pe.explain())
                self.assertFalse(
                    shouldSucceed, "failed to parse when should have succeeded"
                )

    def testGreedyQuotedStrings(self):

        src = """\
           "string1", "strin""g2"
           'string1', 'string2'
           ^string1^, ^string2^
           <string1>, <string2>"""

        testExprs = (
            pp.sglQuotedString,
            pp.dblQuotedString,
            pp.quotedString,
            pp.QuotedString('"', escQuote='""'),
            pp.QuotedString("'", escQuote="''"),
            pp.QuotedString("^"),
            pp.QuotedString("<", endQuoteChar=">"),
        )
        for expr in testExprs:
            strs = pp.delimitedList(expr).searchString(src)
            print(strs)
            self.assertTrue(
                bool(strs), "no matches found for test expression '%s'" % expr
            )
            for lst in strs:
                self.assertEqual(
                    2, len(lst), "invalid match found for test expression '%s'" % expr
                )

        src = """'ms1',1,0,'2009-12-22','2009-12-22 10:41:22') ON DUPLICATE KEY UPDATE sent_count = sent_count + 1, mtime = '2009-12-22 10:41:22';"""
        tok_sql_quoted_value = pp.QuotedString(
            "'", "\\", "''", True, False
        ) ^ pp.QuotedString('"', "\\", '""', True, False)
        tok_sql_computed_value = pp.Word(pp.nums)
        tok_sql_identifier = pp.Word(pp.alphas)

        val = tok_sql_quoted_value | tok_sql_computed_value | tok_sql_identifier
        vals = pp.delimitedList(val)
        print(vals.parseString(src))
        self.assertEqual(
            5, len(vals.parseString(src)), "error in greedy quote escaping"
        )

    def testQuotedStringEscapedQuotes(self):
        quoted = pp.QuotedString('"', escQuote='""')
        res = quoted.parseString('"like ""SQL"""')
        print(res.asList())
        self.assertEqual(['like "SQL"'], res.asList())

        # Issue #263 - handle case when the escQuote is not a repeated character
        quoted = pp.QuotedString("y", escChar=None, escQuote="xy")
        res = quoted.parseString("yaaay")
        self.assertEqual(["aaa"], res.asList())
        res = quoted.parseString("yaaaxyaaay")
        print(res.asList())
        self.assertEqual(["aaayaaa"], res.asList())

    def testWordBoundaryExpressions(self):

        ws = pp.WordStart()
        we = pp.WordEnd()
        vowel = pp.oneOf(list("AEIOUY"))
        consonant = pp.oneOf(list("BCDFGHJKLMNPQRSTVWXZ"))

        leadingVowel = ws + vowel
        trailingVowel = vowel + we
        leadingConsonant = ws + consonant
        trailingConsonant = consonant + we
        internalVowel = ~ws + vowel + ~we

        bnf = leadingVowel | trailingVowel

        tests = """\
        ABC DEF GHI
          JKL MNO PQR
        STU VWX YZ  """.splitlines()
        tests.append("\n".join(tests))

        expectedResult = [
            [["D", "G"], ["A"], ["C", "F"], ["I"], ["E"], ["A", "I"]],
            [["J", "M", "P"], [], ["L", "R"], ["O"], [], ["O"]],
            [["S", "V"], ["Y"], ["X", "Z"], ["U"], [], ["U", "Y"]],
            [
                ["D", "G", "J", "M", "P", "S", "V"],
                ["A", "Y"],
                ["C", "F", "L", "R", "X", "Z"],
                ["I", "O", "U"],
                ["E"],
                ["A", "I", "O", "U", "Y"],
            ],
        ]

        for t, expected in zip(tests, expectedResult):
            print(t)
            results = [
                flatten(e.searchString(t).asList())
                for e in [
                    leadingConsonant,
                    leadingVowel,
                    trailingConsonant,
                    trailingVowel,
                    internalVowel,
                    bnf,
                ]
            ]
            print(results)
            print()
            self.assertEqual(
                expected,
                results,
                "Failed WordBoundaryTest, expected {}, got {}".format(
                    expected, results
                ),
            )

    def testWordBoundaryExpressions2(self):
        from itertools import product
        ws1 = pp.WordStart(pp.alphas)
        ws2 = pp.WordStart(wordChars=pp.alphas)
        ws3 = pp.WordStart(word_chars=pp.alphas)
        we1 = pp.WordEnd(pp.alphas)
        we2 = pp.WordEnd(wordChars=pp.alphas)
        we3 = pp.WordEnd(word_chars=pp.alphas)

        for i, (ws, we) in enumerate(product((ws1, ws2, ws3), (we1, we2, we3))):
            try:
                expr = ("(" + ws + pp.Word(pp.alphas) + we + ")")
                expr.parseString("(abc)")
            except pp.ParseException as pe:
                self.fail(f"Test {i} failed: {pe}")
            else:
                pass

    def testRequiredEach(self):

        parser = pp.Keyword("bam") & pp.Keyword("boo")
        try:
            res1 = parser.parseString("bam boo")
            print(res1.asList())
            res2 = parser.parseString("boo bam")
            print(res2.asList())
        except ParseException:
            failed = True
        else:
            failed = False
            self.assertFalse(failed, "invalid logic in Each")

            self.assertEqual(
                set(res1),
                set(res2),
                "Failed RequiredEachTest, expected "
                + str(res1.asList())
                + " and "
                + str(res2.asList())
                + "to contain same words in any order",
            )

    def testOptionalEachTest1(self):

        for the_input in [
            "Tal Weiss Major",
            "Tal Major",
            "Weiss Major",
            "Major",
            "Major Tal",
            "Major Weiss",
            "Major Tal Weiss",
        ]:
            print(the_input)
            parser1 = (pp.Optional("Tal") + pp.Optional("Weiss")) & pp.Keyword("Major")
            parser2 = pp.Optional(
                pp.Optional("Tal") + pp.Optional("Weiss")
            ) & pp.Keyword("Major")
            p1res = parser1.parseString(the_input)
            p2res = parser2.parseString(the_input)
            self.assertEqual(
                p1res.asList(),
                p2res.asList(),
                "Each failed to match with nested Optionals, "
                + str(p1res.asList())
                + " should match "
                + str(p2res.asList()),
            )

    def testOptionalEachTest2(self):

        word = pp.Word(pp.alphanums + "_").setName("word")
        with_stmt = "with" + pp.OneOrMore(pp.Group(word("key") + "=" + word("value")))(
            "overrides"
        )
        using_stmt = "using" + pp.Regex("id-[0-9a-f]{8}")("id")
        modifiers = pp.Optional(with_stmt("with_stmt")) & pp.Optional(
            using_stmt("using_stmt")
        )

        self.assertEqual("with foo=bar bing=baz using id-deadbeef", modifiers)
        self.assertNotEqual(
            "with foo=bar bing=baz using id-deadbeef using id-feedfeed", modifiers
        )

    def testOptionalEachTest3(self):

        foo = pp.Literal("foo")
        bar = pp.Literal("bar")

        openBrace = pp.Suppress(pp.Literal("{"))
        closeBrace = pp.Suppress(pp.Literal("}"))

        exp = openBrace + (foo[1, ...]("foo") & bar[...]("bar")) + closeBrace

        tests = """\
            {foo}
            {bar foo bar foo bar foo}
            """.splitlines()
        for test in tests:
            test = test.strip()
            if not test:
                continue
            self.assertParseAndCheckList(
                exp,
                test,
                test.strip("{}").split(),
                "failed to parse Each expression {!r}".format(test),
                verbose=True,
            )

        with self.assertRaisesParseException():
            exp.parseString("{bar}")

    def testOptionalEachTest4(self):

        expr = (~ppc.iso8601_date + ppc.integer("id")) & (
            pp.Group(ppc.iso8601_date)("date*")[...]
        )

        expr.runTests(
            """
            1999-12-31 100 2001-01-01
            42
            """
        )

    def testEachWithParseFatalException(self):

        option_expr = pp.Keyword("options") - "(" + ppc.integer + ")"
        step_expr1 = pp.Keyword("step") - "(" + ppc.integer + ")"
        step_expr2 = pp.Keyword("step") - "(" + ppc.integer + "Z" + ")"
        step_expr = step_expr1 ^ step_expr2

        parser = option_expr & step_expr[...]
        tests = [
            (
                "options(100) step(A)",
                "Expected integer, found 'A'  (at char 18), (line:1, col:19)",
            ),
            (
                "step(A) options(100)",
                "Expected integer, found 'A'  (at char 5), (line:1, col:6)",
            ),
            (
                "options(100) step(100A)",
                """Expected 'Z', found 'A'  (at char 21), (line:1, col:22)""",
            ),
            (
                "options(100) step(22) step(100ZA)",
                """Expected ')', found 'A'  (at char 31), (line:1, col:32)""",
            ),
        ]
        test_lookup = dict(tests)

        success, output = parser.runTests((t[0] for t in tests), failureTests=True)
        for test_str, result in output:
            self.assertEqual(
                test_lookup[test_str],
                str(result),
                "incorrect exception raised for test string {!r}".format(test_str),
            )

    def testEachWithMultipleMatch(self):
        size = "size" + pp.oneOf("S M L XL")
        color = pp.Group(
            "color" + pp.oneOf("red orange yellow green blue purple white black brown")
        )
        size.setName("size_spec")
        color.setName("color_spec")

        spec0 = size("size") & color[...]("colors")
        spec1 = size("size") & color[1, ...]("colors")

        for spec in (spec0, spec1):
            for test, expected_dict in [
                (
                    "size M color red color yellow",
                    {
                        "colors": [["color", "red"], ["color", "yellow"]],
                        "size": ["size", "M"],
                    },
                ),
                (
                    "color green size M color red color yellow",
                    {
                        "colors": [
                            ["color", "green"],
                            ["color", "red"],
                            ["color", "yellow"],
                        ],
                        "size": ["size", "M"],
                    },
                ),
            ]:
                result = spec.parseString(test, parseAll=True)
                self.assertParseResultsEquals(result, expected_dict=expected_dict)

    def testSumParseResults(self):

        samplestr1 = "garbage;DOB 10-10-2010;more garbage\nID PARI12345678;more garbage"
        samplestr2 = "garbage;ID PARI12345678;more garbage\nDOB 10-10-2010;more garbage"
        samplestr3 = "garbage;DOB 10-10-2010"
        samplestr4 = "garbage;ID PARI12345678;more garbage- I am cool"

        res1 = "ID:PARI12345678 DOB:10-10-2010 INFO:"
        res2 = "ID:PARI12345678 DOB:10-10-2010 INFO:"
        res3 = "ID: DOB:10-10-2010 INFO:"
        res4 = "ID:PARI12345678 DOB: INFO: I am cool"

        dob_ref = "DOB" + pp.Regex(r"\d{2}-\d{2}-\d{4}")("dob")
        id_ref = "ID" + pp.Word(pp.alphanums, exact=12)("id")
        info_ref = "-" + pp.restOfLine("info")

        person_data = dob_ref | id_ref | info_ref

        tests = (samplestr1, samplestr2, samplestr3, samplestr4)
        results = (res1, res2, res3, res4)
        for test, expected in zip(tests, results):
            person = sum(person_data.searchString(test))
            result = "ID:{} DOB:{} INFO:{}".format(person.id, person.dob, person.info)
            print(test)
            print(expected)
            print(result)
            for pd in person_data.searchString(test):
                print(pd.dump())
            print()
            self.assertEqual(
                expected,
                result,
                "Failed to parse '{}' correctly, \nexpected '{}', got '{}'".format(
                    test, expected, result
                ),
            )

    def testMarkInputLine(self):

        samplestr1 = "DOB 100-10-2010;more garbage\nID PARI12345678;more garbage"

        dob_ref = "DOB" + pp.Regex(r"\d{2}-\d{2}-\d{4}")("dob")

        try:
            res = dob_ref.parseString(samplestr1)
        except ParseException as pe:
            outstr = pe.markInputline()
            print(outstr)
            self.assertEqual(
                "DOB >!<100-10-2010;more garbage",
                outstr,
                "did not properly create marked input line",
            )
        else:
            self.fail("test construction failed - should have raised an exception")

    def testLocatedExpr(self):
        #             012345678901234567890123456789012345678901234567890
        samplestr1 = "DOB 10-10-2010;more garbage;ID PARI12345678  ;more garbage"

        id_ref = pp.locatedExpr("ID" + pp.Word(pp.alphanums, exact=12)("id"))

        res = id_ref.searchString(samplestr1)[0][0]
        print(res.dump())
        self.assertEqual(
            "ID PARI12345678",
            samplestr1[res.locn_start : res.locn_end],
            "incorrect location calculation",
        )

    def testLocatedExprUsingLocated(self):
        #             012345678901234567890123456789012345678901234567890
        samplestr1 = "DOB 10-10-2010;more garbage;ID PARI12345678  ;more garbage"

        id_ref = pp.Located("ID" + pp.Word(pp.alphanums, exact=12)("id"))

        res = id_ref.searchString(samplestr1)[0]
        print(res.dump())
        self.assertEqual(
            "ID PARI12345678",
            samplestr1[res.locn_start : res.locn_end],
            "incorrect location calculation",
        )
        self.assertParseResultsEquals(
            res,
            [28, ["ID", "PARI12345678"], 43],
            {"locn_end": 43, "locn_start": 28, "value": {"id": "PARI12345678"}},
        )
        self.assertEqual("PARI12345678", res.value.id)

        # if Located has a results name, handle appropriately
        id_ref = pp.Located("ID" + pp.Word(pp.alphanums, exact=12)("id"))("loc")

        res = id_ref.searchString(samplestr1)[0]
        print(res.dump())
        self.assertEqual(
            "ID PARI12345678",
            samplestr1[res.loc.locn_start : res.loc.locn_end],
            "incorrect location calculation",
        )
        self.assertParseResultsEquals(
            res.loc,
            [28, ["ID", "PARI12345678"], 43],
            {"locn_end": 43, "locn_start": 28, "value": {"id": "PARI12345678"}},
        )
        self.assertEqual("PARI12345678", res.loc.value.id)

        wd = pp.Word(pp.alphas)
        test_string = "ljsdf123lksdjjf123lkkjj1222"
        pp_matches = pp.Located(wd).searchString(test_string)
        re_matches = find_all_re_matches("[a-z]+", test_string)
        for pp_match, re_match in zip(pp_matches, re_matches):
            self.assertParseResultsEquals(
                pp_match, [re_match.start(), [re_match.group(0)], re_match.end()]
            )
            print(pp_match)
            print(re_match)
            print(pp_match.value)

    def testPop(self):
        source = "AAA 123 456 789 234"
        patt = pp.Word(pp.alphas)("name") + pp.Word(pp.nums) * (1,)

        result = patt.parseString(source)
        tests = [
            (0, "AAA", ["123", "456", "789", "234"]),
            (None, "234", ["123", "456", "789"]),
            ("name", "AAA", ["123", "456", "789"]),
            (-1, "789", ["123", "456"]),
        ]
        for test in tests:
            idx, val, remaining = test
            if idx is not None:
                ret = result.pop(idx)
            else:
                ret = result.pop()
            print("EXP:", val, remaining)
            print("GOT:", ret, result.asList())
            print(ret, result.asList())
            self.assertEqual(
                val,
                ret,
                "wrong value returned, got {!r}, expected {!r}".format(ret, val),
            )
            self.assertEqual(
                remaining,
                result.asList(),
                "list is in wrong state after pop, got {!r}, expected {!r}".format(
                    result.asList(), remaining
                ),
            )
            print()

        prevlist = result.asList()
        ret = result.pop("name", default="noname")
        print(ret)
        print(result.asList())
        self.assertEqual(
            "noname",
            ret,
            "default value not successfully returned, got {!r}, expected {!r}".format(
                ret, "noname"
            ),
        )
        self.assertEqual(
            prevlist,
            result.asList(),
            "list is in wrong state after pop, got {!r}, expected {!r}".format(
                result.asList(), remaining
            ),
        )

    def testPopKwargsErr(self):
        """raise a TypeError in pop by adding invalid named args"""

        source = "AAA 123 456 789 234"
        patt = pp.Word(pp.alphas)("name") + pp.Word(pp.nums) * (1,)
        result = patt.parseString(source)
        print(result.dump())

        with self.assertRaises(TypeError):
            result.pop(notDefault="foo")

    def testAddCondition(self):

        numParser = pp.Word(pp.nums)
        numParser.addParseAction(lambda s, l, t: int(t[0]))
        numParser.addCondition(lambda s, l, t: t[0] % 2)
        numParser.addCondition(lambda s, l, t: t[0] >= 7)

        result = numParser.searchString("1 2 3 4 5 6 7 8 9 10")
        print(result.asList())
        self.assertEqual(
            [[7], [9]], result.asList(), "failed to properly process conditions"
        )

        numParser = pp.Word(pp.nums)
        numParser.addParseAction(lambda s, l, t: int(t[0]))
        rangeParser = numParser("from_") + pp.Suppress("-") + numParser("to")

        result = rangeParser.searchString("1-4 2-4 4-3 5 6 7 8 9 10")
        print(result.asList())
        self.assertEqual(
            [[1, 4], [2, 4], [4, 3]],
            result.asList(),
            "failed to properly process conditions",
        )

        rangeParser.addCondition(
            lambda t: t.to > t.from_, message="from must be <= to", fatal=False
        )
        result = rangeParser.searchString("1-4 2-4 4-3 5 6 7 8 9 10")
        print(result.asList())
        self.assertEqual(
            [[1, 4], [2, 4]], result.asList(), "failed to properly process conditions"
        )

        rangeParser = numParser("from_") + pp.Suppress("-") + numParser("to")
        rangeParser.addCondition(
            lambda t: t.to > t.from_, message="from must be <= to", fatal=True
        )
        try:
            result = rangeParser.searchString("1-4 2-4 4-3 5 6 7 8 9 10")
            self.fail("failed to interrupt parsing on fatal condition failure")
        except ParseFatalException:
            print("detected fatal condition")

    def testPatientOr(self):
        # Two expressions and a input string which could - syntactically - be matched against
        # both expressions. The "Literal" expression is considered invalid though, so this PE
        # should always detect the "Word" expression.
        def validate(token):
            if token[0] == "def":
                raise pp.ParseException("signalling invalid token")
            return token

        a = pp.Word("de").setName("Word")  # .setDebug()
        b = pp.Literal("def").setName("Literal").setParseAction(validate)  # .setDebug()
        c = pp.Literal("d").setName("d")  # .setDebug()

        # The "Literal" expressions's ParseAction is not executed directly after syntactically
        # detecting the "Literal" Expression but only after the Or-decision has been made
        # (which is too late)...
        try:
            result = (a ^ b ^ c).parseString("def")
            self.assertEqual(
                ["de"],
                result.asList(),
                "failed to select longest match, chose %s" % result,
            )
        except ParseException:
            failed = True
        else:
            failed = False

        if failed:
            self.fail(
                "invalid logic in Or, fails on longest match with exception in parse action"
            )

        # from issue #93
        word = pp.Word(pp.alphas).setName("word")
        word_1 = (
            pp.Word(pp.alphas).setName("word_1").addCondition(lambda t: len(t[0]) == 1)
        )

        a = word + (word_1 + word ^ word)
        b = word * 3
        c = a ^ b
        c.streamline()
        print(c)
        test_string = "foo bar temp"
        result = c.parseString(test_string)
        print(test_string, "->", result.asList())

        self.assertEqual(
            test_string.split(), result.asList(), "failed to match longest choice"
        )

    def testEachWithOptionalWithResultsName(self):

        result = (pp.Optional("foo")("one") & pp.Optional("bar")("two")).parseString(
            "bar foo"
        )
        print(result.dump())
        self.assertEqual(sorted(["one", "two"]), sorted(result.keys()))

    def testUnicodeExpression(self):

        z = "a" | pp.Literal("\u1111")
        z.streamline()
        try:
            z.parseString("b")
        except ParseException as pe:
            self.assertEqual(
                r"""Expected {'a' | 'ᄑ'}""",
                pe.msg,
                "Invalid error message raised, got %r" % pe.msg,
            )

    def testSetName(self):

        a = pp.oneOf("a b c")
        b = pp.oneOf("d e f")
        arith_expr = pp.infixNotation(
            pp.Word(pp.nums),
            [
                (pp.oneOf("* /"), 2, pp.opAssoc.LEFT),
                (pp.oneOf("+ -"), 2, pp.opAssoc.LEFT),
            ],
        )
        arith_expr2 = pp.infixNotation(
            pp.Word(pp.nums), [(("?", ":"), 3, pp.opAssoc.LEFT)]
        )
        recursive = pp.Forward()
        recursive <<= a + (b + recursive)[...]

        tests = [
            a,
            b,
            (a | b),
            arith_expr,
            arith_expr.expr,
            arith_expr2,
            arith_expr2.expr,
            recursive,
            pp.delimitedList(pp.Word(pp.nums).setName("int")),
            pp.countedArray(pp.Word(pp.nums).setName("int")),
            pp.nestedExpr(),
            pp.makeHTMLTags("Z"),
            (pp.anyOpenTag, pp.anyCloseTag),
            pp.commonHTMLEntity,
            pp.commonHTMLEntity.setParseAction(pp.replaceHTMLEntity).transformString(
                "lsdjkf &lt;lsdjkf&gt;&amp;&apos;&quot;&xyzzy;"
            ),
        ]

        expected = map(
            str.strip,
            """\
            a | b | c
            d | e | f
            {a | b | c | d | e | f}
            Forward: + | - term
            + | - term
            Forward: ?: term
            ?: term
            Forward: {a | b | c [{d | e | f : ...}]...}
            int [, int]...
            (len) int...
            nested () expression
            (<Z>, </Z>)
            (<any tag>, </any tag>)
            common HTML entity
            lsdjkf <lsdjkf>&'"&xyzzy;""".splitlines(),
        )

        for t, e in zip(tests, expected):
            tname = str(t)
            print(tname)
            self.assertEqual(
                e,
                tname,
                "expression name mismatch, expected {} got {}".format(e, tname),
            )

    def testTrimArityExceptionMasking(self):

        invalid_message = "<lambda>() missing 1 required positional argument: 't'"
        try:
            pp.Word("a").setParseAction(lambda t: t[0] + 1).parseString("aaa")
        except Exception as e:
            exc_msg = str(e)
            self.assertNotEqual(
                exc_msg,
                invalid_message,
                "failed to catch TypeError thrown in _trim_arity",
            )

    def testTrimArityExceptionMaskingTest2(self):
        # construct deep call tree
        def A():
            import traceback

            traceback.print_stack(limit=2)

            invalid_message = "<lambda>() missing 1 required positional argument: 't'"
            try:
                pp.Word("a").setParseAction(lambda t: t[0] + 1).parseString("aaa")
            except Exception as e:
                exc_msg = str(e)
                self.assertNotEqual(
                    exc_msg,
                    invalid_message,
                    "failed to catch TypeError thrown in _trim_arity",
                )

        def B():
            A()

        def C():
            B()

        def D():
            C()

        def E():
            D()

        def F():
            E()

        def G():
            F()

        def H():
            G()

        def J():
            H()

        def K():
            J()

        K()

    def testClearParseActions(self):

        realnum = ppc.real()
        self.assertEqual(
            3.14159,
            realnum.parseString("3.14159")[0],
            "failed basic real number parsing",
        )

        # clear parse action that converts to float
        realnum.setParseAction(None)
        self.assertEqual(
            "3.14159", realnum.parseString("3.14159")[0], "failed clearing parse action"
        )

        # add a new parse action that tests if a '.' is prsent
        realnum.addParseAction(lambda t: "." in t[0])
        self.assertEqual(
            True,
            realnum.parseString("3.14159")[0],
            "failed setting new parse action after clearing parse action",
        )

    def testOneOrMoreStop(self):

        test = "BEGIN aaa bbb ccc END"
        BEGIN, END = map(pp.Keyword, "BEGIN,END".split(","))
        body_word = pp.Word(pp.alphas).setName("word")
        for ender in (END, "END", pp.CaselessKeyword("END")):
            expr = BEGIN + pp.OneOrMore(body_word, stopOn=ender) + END
            self.assertEqual(
                expr, test, "Did not successfully stop on ending expression %r" % ender
            )

            expr = BEGIN + body_word[...].stopOn(ender) + END
            self.assertEqual(
                expr, test, "Did not successfully stop on ending expression %r" % ender
            )

        number = pp.Word(pp.nums + ",.()").setName("number with optional commas")
        parser = pp.OneOrMore(pp.Word(pp.alphanums + "-/."), stopOn=number)(
            "id"
        ).setParseAction(" ".join) + number("data")
        self.assertParseAndCheckList(
            parser,
            "        XXX Y/123          1,234.567890",
            ["XXX Y/123", "1,234.567890"],
            "Did not successfully stop on ending expression %r" % number,
            verbose=True,
        )

    def testZeroOrMoreStop(self):
        test = "BEGIN END"
        BEGIN, END = map(pp.Keyword, "BEGIN,END".split(","))
        body_word = pp.Word(pp.alphas).setName("word")
        for ender in (END, "END", pp.CaselessKeyword("END")):
            expr = BEGIN + pp.ZeroOrMore(body_word, stopOn=ender) + END
            self.assertEqual(
                expr, test, "Did not successfully stop on ending expression %r" % ender
            )

            expr = BEGIN + body_word[0, ...].stopOn(ender) + END
            self.assertEqual(
                expr, test, "Did not successfully stop on ending expression %r" % ender
            )

    def testNestedAsDict(self):

        equals = pp.Literal("=").suppress()
        lbracket = pp.Literal("[").suppress()
        rbracket = pp.Literal("]").suppress()
        lbrace = pp.Literal("{").suppress()
        rbrace = pp.Literal("}").suppress()

        value_dict = pp.Forward()
        value_list = pp.Forward()
        value_string = pp.Word(pp.alphanums + "@. ")

        value = value_list ^ value_dict ^ value_string
        values = pp.Group(pp.delimitedList(value, ","))
        # ~ values              = delimitedList(value, ",").setParseAction(lambda toks: [toks.asList()])

        value_list <<= lbracket + values + rbracket

        identifier = pp.Word(pp.alphanums + "_.")

        assignment = pp.Group(identifier + equals + pp.Optional(value))
        assignments = pp.Dict(pp.delimitedList(assignment, ";"))
        value_dict <<= lbrace + assignments + rbrace

        response = assignments

        rsp = (
            "username=goat; errors={username=[already taken, too short]}; empty_field="
        )
        result_dict = response.parseString(rsp).asDict()
        print(result_dict)
        self.assertEqual(
            "goat",
            result_dict["username"],
            "failed to process string in ParseResults correctly",
        )
        self.assertEqual(
            ["already taken", "too short"],
            result_dict["errors"]["username"],
            "failed to process nested ParseResults correctly",
        )

    def testTraceParseActionDecorator(self):
        @pp.traceParseAction
        def convert_to_int(t):
            return int(t[0])

        class Z:
            def __call__(self, other):
                return other[0] * 1000

        integer = pp.Word(pp.nums).addParseAction(convert_to_int)
        integer.addParseAction(pp.traceParseAction(lambda t: t[0] * 10))
        integer.addParseAction(pp.traceParseAction(Z()))
        integer.parseString("132")

    def testRunTests(self):
        integer = pp.Word(pp.nums).setParseAction(lambda t: int(t[0]))
        intrange = integer("start") + "-" + integer("end")
        intrange.addCondition(
            lambda t: t.end > t.start,
            message="invalid range, start must be <= end",
            fatal=True,
        )
        intrange.addParseAction(lambda t: list(range(t.start, t.end + 1)))

        indices = pp.delimitedList(intrange | integer)
        indices.addParseAction(lambda t: sorted(set(t)))

        tests = """\
            # normal data
            1-3,2-4,6,8-10,16

            # lone integer
            11"""
        results = indices.runTests(tests, printResults=False)[1]

        expectedResults = [[1, 2, 3, 4, 6, 8, 9, 10, 16], [11]]
        for res, expected in zip(results, expectedResults):
            print(res[1].asList())
            print(expected)
            self.assertEqual(expected, res[1].asList(), "failed test: " + str(expected))

        tests = """\
            # invalid range
            1-2, 3-1, 4-6, 7, 12
            """
        success = indices.runTests(tests, printResults=False, failureTests=True)[0]
        self.assertTrue(success, "failed to raise exception on improper range test")

    def testRunTestsPostParse(self):
        integer = ppc.integer
        fraction = integer("numerator") + "/" + integer("denominator")

        accum = []

        def eval_fraction(test, result):
            accum.append((test, result.asList()))
            return "eval: {}".format(result.numerator / result.denominator)

        success = fraction.runTests(
            """\
            1/2
            1/0
        """,
            postParse=eval_fraction,
        )[0]
        print(success)

        self.assertTrue(success, "failed to parse fractions in RunTestsPostParse")

        expected_accum = [("1/2", [1, "/", 2]), ("1/0", [1, "/", 0])]
        self.assertEqual(
            expected_accum, accum, "failed to call postParse method during runTests"
        )

    def testConvertToDateErr(self):
        """raise a ParseException in convertToDate with incompatible date str"""

        expr = pp.Word(pp.alphanums + "-")
        expr.addParseAction(ppc.convertToDate())

        with self.assertRaisesParseException():
            expr.parseString("1997-07-error")

    def testConvertToDatetimeErr(self):
        """raise a ParseException in convertToDatetime with incompatible datetime str"""

        expr = pp.Word(pp.alphanums + "-")
        expr.addParseAction(ppc.convertToDatetime())

        with self.assertRaisesParseException():
            expr.parseString("1997-07-error")

    def testCommonExpressions(self):
        import ast

        success = ppc.mac_address.runTests(
            """
            AA:BB:CC:DD:EE:FF
            AA.BB.CC.DD.EE.FF
            AA-BB-CC-DD-EE-FF
            """
        )[0]
        self.assertTrue(success, "error in parsing valid MAC address")

        success = ppc.mac_address.runTests(
            """
            # mixed delimiters
            AA.BB:CC:DD:EE:FF
            """,
            failureTests=True,
        )[0]
        self.assertTrue(success, "error in detecting invalid mac address")

        success = ppc.ipv4_address.runTests(
            """
            0.0.0.0
            1.1.1.1
            127.0.0.1
            1.10.100.199
            255.255.255.255
            """
        )[0]
        self.assertTrue(success, "error in parsing valid IPv4 address")

        success = ppc.ipv4_address.runTests(
            """
            # out of range value
            256.255.255.255
            """,
            failureTests=True,
        )[0]
        self.assertTrue(success, "error in detecting invalid IPv4 address")

        success = ppc.ipv6_address.runTests(
            """
            2001:0db8:85a3:0000:0000:8a2e:0370:7334
            2134::1234:4567:2468:1236:2444:2106
            0:0:0:0:0:0:A00:1
            1080::8:800:200C:417A
            ::A00:1

            # loopback address
            ::1

            # the null address
            ::

            # ipv4 compatibility form
            ::ffff:192.168.0.1
            """
        )[0]
        self.assertTrue(success, "error in parsing valid IPv6 address")

        success = ppc.ipv6_address.runTests(
            """
            # too few values
            1080:0:0:0:8:800:200C

            # too many ::'s, only 1 allowed
            2134::1234:4567::2444:2106
            """,
            failureTests=True,
        )[0]
        self.assertTrue(success, "error in detecting invalid IPv6 address")

        success = ppc.number.runTests(
            """
            100
            -100
            +100
            3.14159
            6.02e23
            1e-12
            """
        )[0]
        self.assertTrue(success, "error in parsing valid numerics")

        success = ppc.sci_real.runTests(
            """
            1e12
            -1e12
            3.14159
            6.02e23
            """
        )[0]
        self.assertTrue(success, "error in parsing valid scientific notation reals")

        # any int or real number, returned as float
        success = ppc.fnumber.runTests(
            """
            100
            -100
            +100
            3.14159
            6.02e23
            1e-12
            """
        )[0]
        self.assertTrue(success, "error in parsing valid numerics")

        success, results = ppc.iso8601_date.runTests(
            """
            1997
            1997-07
            1997-07-16
            """
        )
        self.assertTrue(success, "error in parsing valid iso8601_date")
        expected = [("1997", None, None), ("1997", "07", None), ("1997", "07", "16")]
        for r, exp in zip(results, expected):
            self.assertEqual(
                exp,
                (r[1].year, r[1].month, r[1].day),
                "failed to parse date into fields",
            )

        success, results = (
            ppc.iso8601_date()
            .addParseAction(ppc.convertToDate())
            .runTests(
                """
            1997-07-16
            """
            )
        )
        self.assertTrue(
            success, "error in parsing valid iso8601_date with parse action"
        )
        self.assertEqual(
            datetime.date(1997, 7, 16),
            results[0][1][0],
            "error in parsing valid iso8601_date with parse action - incorrect value",
        )

        success, results = ppc.iso8601_datetime.runTests(
            """
            1997-07-16T19:20+01:00
            1997-07-16T19:20:30+01:00
            1997-07-16T19:20:30.45Z
            1997-07-16 19:20:30.45
            """
        )
        self.assertTrue(success, "error in parsing valid iso8601_datetime")

        success, results = (
            ppc.iso8601_datetime()
            .addParseAction(ppc.convertToDatetime())
            .runTests(
                """
            1997-07-16T19:20:30.45
            """
            )
        )

        self.assertTrue(success, "error in parsing valid iso8601_datetime")
        self.assertEqual(
            datetime.datetime(1997, 7, 16, 19, 20, 30, 450000),
            results[0][1][0],
            "error in parsing valid iso8601_datetime - incorrect value",
        )

        success = ppc.uuid.runTests(
            """
            123e4567-e89b-12d3-a456-426655440000
            """
        )[0]
        self.assertTrue(success, "failed to parse valid uuid")

        success = ppc.fraction.runTests(
            """
            1/2
            -15/16
            -3/-4
            """
        )[0]
        self.assertTrue(success, "failed to parse valid fraction")

        success = ppc.mixed_integer.runTests(
            """
            1/2
            -15/16
            -3/-4
            1 1/2
            2 -15/16
            0 -3/-4
            12
            """
        )[0]
        self.assertTrue(success, "failed to parse valid mixed integer")

        success, results = ppc.number.runTests(
            """
            100
            -3
            1.732
            -3.14159
            6.02e23"""
        )
        self.assertTrue(success, "failed to parse numerics")

        for test, result in results:
            expected = ast.literal_eval(test)
            self.assertEqual(
                expected,
                result[0],
                "numeric parse failed (wrong value) ({} should be {})".format(
                    result[0], expected
                ),
            )
            self.assertEqual(
                type(expected),
                type(result[0]),
                "numeric parse failed (wrong type) ({} should be {})".format(
                    type(result[0]), type(expected)
                ),
            )

    def testCommonUrl(self):
        url_good_tests = """\
            http://foo.com/blah_blah
            http://foo.com/blah_blah/
            http://foo.com/blah_blah_(wikipedia)
            http://foo.com/blah_blah_(wikipedia)_(again)
            http://www.example.com/wpstyle/?p=364
            https://www.example.com/foo/?bar=baz&inga=42&quux
            http://✪df.ws/123
            http://userid:password@example.com:8080
            http://userid:password@example.com:8080/
            http://userid@example.com
            http://userid@example.com/
            http://userid@example.com:8080
            http://userid@example.com:8080/
            http://userid:password@example.com
            http://userid:password@example.com/
            http://142.42.1.1/
            http://142.42.1.1:8080/
            http://➡.ws/䨹
            http://⌘.ws
            http://⌘.ws/
            http://foo.com/blah_(wikipedia)#cite-1
            http://foo.com/blah_(wikipedia)_blah#cite-1
            http://foo.com/unicode_(✪)_in_parens
            http://foo.com/(something)?after=parens
            http://☺.damowmow.com/
            http://code.google.com/events/#&product=browser
            http://j.mp
            ftp://foo.bar/baz
            http://foo.bar/?q=Test%20URL-encoded%20stuff
            http://مثال.إختبار
            """
        success, report = ppc.url.runTests(url_good_tests)
        self.assertTrue(success)

        url_bad_tests = """\
            http://
            http://.
            http://..
            http://../
            http://?
            http://??
            http://??/
            http://#
            http://##
            http://##/
            # skip: http://foo.bar?q=Spaces should be encoded
            //
            //a
            ///a
            ///
            http:///a
            foo.com
            rdar://1234
            h://test
            http:// shouldfail.com

            :// should fail
            http://foo.bar/foo(bar)baz quux
            ftps://foo.bar/
            http://-error-.invalid/
            # skip: http://a.b--c.de/
            http://-a.b.co
            http://a.b-.co
            http://0.0.0.0
            http://10.1.1.0
            http://10.1.1.255
            http://224.1.1.1
            http://1.1.1.1.1
            http://123.123.123
            http://3628126748
            http://.www.foo.bar/
            # skip: http://www.foo.bar./
            http://.www.foo.bar./
            http://10.1.1.1
            """
        success, report = ppc.url.runTests(url_bad_tests, failure_tests=True)
        self.assertTrue(success)

    def testCommonUrlParts(self):
        from urllib.parse import urlparse

        sample_url = "https://bob:secret@www.example.com:8080/path/to/resource?filter=int#book-mark"

        parts = urlparse(sample_url)
        expected = {
            "scheme": parts.scheme,
            "auth": "{}:{}".format(parts.username, parts.password),
            "host": parts.hostname,
            "port": str(parts.port),
            "path": parts.path,
            "query": parts.query,
            "fragment": parts.fragment,
        }

        self.assertParseAndCheckDict(ppc.url, sample_url, expected, verbose=True)

    def testNumericExpressions(self):

        # disable parse actions that do type conversion so we don't accidentally trigger
        # conversion exceptions when what we want to check is the parsing expression
        real = ppc.real().setParseAction(None)
        sci_real = ppc.sci_real().setParseAction(None)
        signed_integer = ppc.signed_integer().setParseAction(None)

        from itertools import product

        def make_tests():
            leading_sign = ["+", "-", ""]
            leading_digit = ["0", ""]
            dot = [".", ""]
            decimal_digit = ["1", ""]
            e = ["e", "E", ""]
            e_sign = ["+", "-", ""]
            e_int = ["22", ""]
            stray = ["9", ".", ""]

            seen = set()
            seen.add("")
            for parts in product(
                leading_sign,
                stray,
                leading_digit,
                dot,
                decimal_digit,
                stray,
                e,
                e_sign,
                e_int,
                stray,
            ):
                parts_str = "".join(parts).strip()
                if parts_str in seen:
                    continue
                seen.add(parts_str)
                yield parts_str

            print(len(seen) - 1, "tests produced")

        # collect tests into valid/invalid sets, depending on whether they evaluate to valid Python floats or ints
        valid_ints = set()
        valid_reals = set()
        valid_sci_reals = set()
        invalid_ints = set()
        invalid_reals = set()
        invalid_sci_reals = set()

        # check which strings parse as valid floats or ints, and store in related valid or invalid test sets
        for test_str in make_tests():
            if "." in test_str or "e" in test_str.lower():
                try:
                    float(test_str)
                except ValueError:
                    invalid_sci_reals.add(test_str)
                    if "e" not in test_str.lower():
                        invalid_reals.add(test_str)
                else:
                    valid_sci_reals.add(test_str)
                    if "e" not in test_str.lower():
                        valid_reals.add(test_str)

            try:
                int(test_str)
            except ValueError:
                invalid_ints.add(test_str)
            else:
                valid_ints.add(test_str)

        # now try all the test sets against their respective expressions
        all_pass = True
        suppress_results = {"printResults": False}
        for expr, tests, is_fail, fn in zip(
            [real, sci_real, signed_integer] * 2,
            [
                valid_reals,
                valid_sci_reals,
                valid_ints,
                invalid_reals,
                invalid_sci_reals,
                invalid_ints,
            ],
            [False, False, False, True, True, True],
            [float, float, int] * 2,
        ):
            #
            # success, test_results = expr.runTests(sorted(tests, key=len), failureTests=is_fail, **suppress_results)
            # filter_result_fn = (lambda r: isinstance(r, Exception),
            #                     lambda r: not isinstance(r, Exception))[is_fail]
            # print(expr, ('FAIL', 'PASS')[success], "{}valid tests ({})".format(len(tests),
            #                                                                       'in' if is_fail else ''))
            # if not success:
            #     all_pass = False
            #     for test_string, result in test_results:
            #         if filter_result_fn(result):
            #             try:
            #                 test_value = fn(test_string)
            #             except ValueError as ve:
            #                 test_value = str(ve)
            #             print("{!r}: {} {} {}".format(test_string, result,
            #                                                expr.matches(test_string, parseAll=True), test_value))

            success = True
            for t in tests:
                if expr.matches(t, parseAll=True):
                    if is_fail:
                        print(t, "should fail but did not")
                        success = False
                else:
                    if not is_fail:
                        print(t, "should not fail but did")
                        success = False
            print(
                expr,
                ("FAIL", "PASS")[success],
                "{}valid tests ({})".format("in" if is_fail else "", len(tests)),
            )
            all_pass = all_pass and success

        self.assertTrue(all_pass, "failed one or more numeric tests")

    def testTokenMap(self):

        parser = pp.OneOrMore(pp.Word(pp.hexnums)).setParseAction(pp.tokenMap(int, 16))
        success, report = parser.runTests(
            """
            00 11 22 aa FF 0a 0d 1a
            """
        )

        self.assertRunTestResults(
            (success, report),
            [([0, 17, 34, 170, 255, 10, 13, 26], "tokenMap parse action failed")],
            msg="failed to parse hex integers",
        )

    def testParseFile(self):

        s = """
        123 456 789
        """
        input_file = StringIO(s)
        integer = ppc.integer

        results = pp.OneOrMore(integer).parseFile(input_file)
        print(results)

        results = pp.OneOrMore(integer).parseFile("tests/parsefiletest_input_file.txt")
        print(results)

    def testHTMLStripper(self):

        sample = """
        <html>
        Here is some sample <i>HTML</i> text.
        </html>
        """
        read_everything = pp.originalTextFor(pp.OneOrMore(pp.Word(pp.printables)))
        read_everything.addParseAction(ppc.stripHTMLTags)

        result = read_everything.parseString(sample)
        self.assertEqual("Here is some sample HTML text.", result[0].strip())

    def testExprSplitter(self):

        expr = pp.Literal(";") + pp.Empty()
        expr.ignore(pp.quotedString)
        expr.ignore(pp.pythonStyleComment)

        sample = """
        def main():
            this_semi_does_nothing();
            neither_does_this_but_there_are_spaces_afterward();
            a = "a;b"; return a # this is a comment; it has a semicolon!

        def b():
            if False:
                z=1000;b("; in quotes");  c=200;return z
            return ';'

        class Foo(object):
            def bar(self):
                '''a docstring; with a semicolon'''
                a = 10; b = 11; c = 12

                # this comment; has several; semicolons
                if self.spam:
                    x = 12; return x # so; does; this; one
                    x = 15;;; y += x; return y

            def baz(self):
                return self.bar
        """
        expected = [
            ["            this_semi_does_nothing()", ""],
            ["            neither_does_this_but_there_are_spaces_afterward()", ""],
            [
                '            a = "a;b"',
                "return a # this is a comment; it has a semicolon!",
            ],
            ["                z=1000", 'b("; in quotes")', "c=200", "return z"],
            ["            return ';'"],
            ["                '''a docstring; with a semicolon'''"],
            ["                a = 10", "b = 11", "c = 12"],
            ["                # this comment; has several; semicolons"],
            ["                    x = 12", "return x # so; does; this; one"],
            ["                    x = 15", "", "", "y += x", "return y"],
        ]

        exp_iter = iter(expected)
        for line in filter(lambda ll: ";" in ll, sample.splitlines()):
            print(str(list(expr.split(line))) + ",")
            self.assertEqual(
                next(exp_iter), list(expr.split(line)), "invalid split on expression"
            )

        print()

        expected = [
            ["            this_semi_does_nothing()", ";", ""],
            ["            neither_does_this_but_there_are_spaces_afterward()", ";", ""],
            [
                '            a = "a;b"',
                ";",
                "return a # this is a comment; it has a semicolon!",
            ],
            [
                "                z=1000",
                ";",
                'b("; in quotes")',
                ";",
                "c=200",
                ";",
                "return z",
            ],
            ["            return ';'"],
            ["                '''a docstring; with a semicolon'''"],
            ["                a = 10", ";", "b = 11", ";", "c = 12"],
            ["                # this comment; has several; semicolons"],
            ["                    x = 12", ";", "return x # so; does; this; one"],
            [
                "                    x = 15",
                ";",
                "",
                ";",
                "",
                ";",
                "y += x",
                ";",
                "return y",
            ],
        ]
        exp_iter = iter(expected)
        for line in filter(lambda ll: ";" in ll, sample.splitlines()):
            print(str(list(expr.split(line, includeSeparators=True))) + ",")
            self.assertEqual(
                next(exp_iter),
                list(expr.split(line, includeSeparators=True)),
                "invalid split on expression",
            )

        print()

        expected = [
            ["            this_semi_does_nothing()", ""],
            ["            neither_does_this_but_there_are_spaces_afterward()", ""],
            [
                '            a = "a;b"',
                "return a # this is a comment; it has a semicolon!",
            ],
            ["                z=1000", 'b("; in quotes");  c=200;return z'],
            ["                a = 10", "b = 11; c = 12"],
            ["                    x = 12", "return x # so; does; this; one"],
            ["                    x = 15", ";; y += x; return y"],
        ]
        exp_iter = iter(expected)
        for line in sample.splitlines():
            pieces = list(expr.split(line, maxsplit=1))
            print(str(pieces) + ",")
            if len(pieces) == 2:
                exp = next(exp_iter)
                self.assertEqual(
                    exp, pieces, "invalid split on expression with maxSplits=1"
                )
            elif len(pieces) == 1:
                self.assertEqual(
                    0,
                    len(expr.searchString(line)),
                    "invalid split with maxSplits=1 when expr not present",
                )
            else:
                print("\n>>> " + line)
                self.fail("invalid split on expression with maxSplits=1, corner case")

    def testParseFatalException(self):

        with self.assertRaisesParseException(
            exc_type=ParseFatalException, msg="failed to raise ErrorStop exception"
        ):
            expr = "ZZZ" - pp.Word(pp.nums)
            expr.parseString("ZZZ bad")

        # WAS:
        # success = False
        # try:
        #     expr = "ZZZ" - Word(nums)
        #     expr.parseString("ZZZ bad")
        # except ParseFatalException as pfe:
        #     print('ParseFatalException raised correctly')
        #     success = True
        # except Exception as e:
        #     print(type(e))
        #     print(e)
        #
        # self.assertTrue(success, "bad handling of syntax error")

    def testParseFatalException2(self):
        # Fatal exception raised in MatchFirst should not be superseded later non-fatal exceptions
        # addresses Issue #251

        def raise_exception(tokens):
            raise pp.ParseSyntaxException("should raise here")

        test = pp.MatchFirst(
            (
                pp.pyparsing_common.integer + pp.pyparsing_common.identifier
            ).setParseAction(raise_exception)
            | pp.pyparsing_common.number
        )

        with self.assertRaisesParseException(pp.ParseFatalException):
            test.parseString("1s")

    def testParseFatalException3(self):
        # Fatal exception raised in MatchFirst should not be superseded later non-fatal exceptions
        # addresses Issue #251

        test = pp.MatchFirst(
            (pp.pyparsing_common.integer - pp.pyparsing_common.identifier)
            | pp.pyparsing_common.integer
        )

        with self.assertRaisesParseException(pp.ParseFatalException):
            test.parseString("1")

    def testInlineLiteralsUsing(self):

        wd = pp.Word(pp.alphas)

        pp.ParserElement.inlineLiteralsUsing(pp.Suppress)
        result = (wd + "," + wd + pp.oneOf("! . ?")).parseString("Hello, World!")
        self.assertEqual(3, len(result), "inlineLiteralsUsing(Suppress) failed!")

        pp.ParserElement.inlineLiteralsUsing(pp.Literal)
        result = (wd + "," + wd + pp.oneOf("! . ?")).parseString("Hello, World!")
        self.assertEqual(4, len(result), "inlineLiteralsUsing(Literal) failed!")

        pp.ParserElement.inlineLiteralsUsing(pp.CaselessKeyword)
        self.assertParseAndCheckList(
            "SELECT" + wd + "FROM" + wd,
            "select color from colors",
            expected_list=["SELECT", "color", "FROM", "colors"],
            msg="inlineLiteralsUsing(CaselessKeyword) failed!",
            verbose=True,
        )

        pp.ParserElement.inlineLiteralsUsing(pp.CaselessLiteral)
        self.assertParseAndCheckList(
            "SELECT" + wd + "FROM" + wd,
            "select color from colors",
            expected_list=["SELECT", "color", "FROM", "colors"],
            msg="inlineLiteralsUsing(CaselessLiteral) failed!",
            verbose=True,
        )

        integer = pp.Word(pp.nums)
        pp.ParserElement.inlineLiteralsUsing(pp.Literal)
        date_str = integer("year") + "/" + integer("month") + "/" + integer("day")
        self.assertParseAndCheckList(
            date_str,
            "1999/12/31",
            expected_list=["1999", "/", "12", "/", "31"],
            msg="inlineLiteralsUsing(example 1) failed!",
            verbose=True,
        )

        # change to Suppress
        pp.ParserElement.inlineLiteralsUsing(pp.Suppress)
        date_str = integer("year") + "/" + integer("month") + "/" + integer("day")

        self.assertParseAndCheckList(
            date_str,
            "1999/12/31",
            expected_list=["1999", "12", "31"],
            msg="inlineLiteralsUsing(example 2) failed!",
            verbose=True,
        )

    def testCloseMatch(self):

        searchseq = pp.CloseMatch("ATCATCGAATGGA", 2)

        _, results = searchseq.runTests(
            """
            ATCATCGAATGGA
            XTCATCGAATGGX
            ATCATCGAAXGGA
            ATCAXXGAATGGA
            ATCAXXGAATGXA
            ATCAXXGAATGG
            """
        )
        expected = ([], [0, 12], [9], [4, 5], None, None)

        for r, exp in zip(results, expected):
            if exp is not None:
                self.assertEqual(
                    exp,
                    r[1].mismatches,
                    "fail CloseMatch between {!r} and {!r}".format(
                        searchseq.match_string, r[0]
                    ),
                )
            print(
                r[0],
                "exc: %s" % r[1]
                if exp is None and isinstance(r[1], Exception)
                else ("no match", "match")[r[1].mismatches == exp],
            )

    def testCloseMatchCaseless(self):

        searchseq = pp.CloseMatch("ATCATCGAATGGA", 2, caseless=True)

        _, results = searchseq.runTests(
            """
            atcatcgaatgga
            xtcatcgaatggx
            atcatcgaaxgga
            atcaxxgaatgga
            atcaxxgaatgxa
            atcaxxgaatgg
            """
        )
        expected = ([], [0, 12], [9], [4, 5], None, None)

        for r, exp in zip(results, expected):
            if exp is not None:
                self.assertEqual(
                    exp,
                    r[1].mismatches,
                    "fail CaselessCloseMatch between {!r} and {!r}".format(
                        searchseq.match_string, r[0]
                    ),
                )
            print(
                r[0],
                "exc: %s" % r[1]
                if exp is None and isinstance(r[1], Exception)
                else ("no match", "match")[r[1].mismatches == exp],
            )

    def testDefaultKeywordChars(self):

        with self.assertRaisesParseException(
            msg="failed to fail matching keyword using updated keyword chars"
        ):
            pp.Keyword("start").parseString("start1000")

        try:
            pp.Keyword("start", identChars=pp.alphas).parseString("start1000")
        except pp.ParseException:
            self.fail("failed to match keyword using updated keyword chars")

        with ppt.reset_pyparsing_context():
            pp.Keyword.setDefaultKeywordChars(pp.alphas)
            try:
                pp.Keyword("start").parseString("start1000")
            except pp.ParseException:
                self.fail("failed to match keyword using updated keyword chars")

        with self.assertRaisesParseException(
            msg="failed to fail matching keyword using updated keyword chars"
        ):
            pp.CaselessKeyword("START").parseString("start1000")

        try:
            pp.CaselessKeyword("START", identChars=pp.alphas).parseString("start1000")
        except pp.ParseException:
            self.fail("failed to match keyword using updated keyword chars")

        with ppt.reset_pyparsing_context():
            pp.Keyword.setDefaultKeywordChars(pp.alphas)
            try:
                pp.CaselessKeyword("START").parseString("start1000")
            except pp.ParseException:
                self.assertTrue(
                    False, "failed to match keyword using updated keyword chars"
                )

    def testKeywordCopyIdentChars(self):
        a_keyword = pp.Keyword("start", identChars="_")
        b_keyword = a_keyword.copy()
        self.assertEqual(a_keyword.identChars, b_keyword.identChars)

    def testLiteralVsKeyword(self):

        integer = ppc.integer
        literal_expr = integer + pp.Literal("start") + integer
        keyword_expr = integer + pp.Keyword("start") + integer
        caseless_keyword_expr = integer + pp.CaselessKeyword("START") + integer
        word_keyword_expr = (
            integer + pp.Word(pp.alphas, asKeyword=True).setName("word") + integer
        )

        print()
        test_string = "1 start 2"
        print(test_string)
        print(literal_expr, literal_expr.parseString(test_string, parseAll=True))
        print(keyword_expr, keyword_expr.parseString(test_string, parseAll=True))
        print(
            caseless_keyword_expr,
            caseless_keyword_expr.parseString(test_string, parseAll=True),
        )
        print(
            word_keyword_expr, word_keyword_expr.parseString(test_string, parseAll=True)
        )
        print()

        test_string = "3 start4"
        print(test_string)
        print(literal_expr, literal_expr.parseString(test_string, parseAll=True))
        with self.assertRaisesParseException(
            msg="failed to fail matching keyword using updated keyword chars"
        ):
            print(keyword_expr.parseString(test_string, parseAll=True))

        with self.assertRaisesParseException(
            msg="failed to fail matching keyword using updated keyword chars"
        ):
            print(caseless_keyword_expr.parseString(test_string, parseAll=True))

        with self.assertRaisesParseException(
            msg="failed to fail matching keyword using updated keyword chars"
        ):
            print(word_keyword_expr.parseString(test_string, parseAll=True))
        print()

        test_string = "5start 6"
        print(test_string)
        print(literal_expr.parseString(test_string, parseAll=True))
        with self.assertRaisesParseException(
            msg="failed to fail matching keyword using updated keyword chars"
        ):
            print(keyword_expr.parseString(test_string, parseAll=True))

        with self.assertRaisesParseException(
            msg="failed to fail matching keyword using updated keyword chars"
        ):
            print(caseless_keyword_expr.parseString(test_string, parseAll=True))

        with self.assertRaisesParseException(
            msg="failed to fail matching keyword using updated keyword chars"
        ):
            print(word_keyword_expr.parseString(test_string, parseAll=True))

    def testCol(self):

        test = "*\n* \n*   ALF\n*\n"
        initials = [c for i, c in enumerate(test) if pp.col(i, test) == 1]
        print(initials)
        self.assertTrue(
            len(initials) == 4 and all(c == "*" for c in initials), "fail col test"
        )

    def testLiteralException(self):

        for cls in (
            pp.Literal,
            pp.CaselessLiteral,
            pp.Keyword,
            pp.CaselessKeyword,
            pp.Word,
            pp.Regex,
        ):
            expr = cls("xyz")  # .setName('{}_expr'.format(cls.__name__.lower()))

            try:
                expr.parseString(" ")
            except Exception as e:
                print(cls.__name__, str(e))
                self.assertTrue(
                    isinstance(e, pp.ParseBaseException),
                    "class {} raised wrong exception type {}".format(
                        cls.__name__, type(e).__name__
                    ),
                )

    def testParseActionException(self):
        import traceback

        number = pp.Word(pp.nums)

        def number_action():
            raise IndexError  # this is the important line!

        number.setParseAction(number_action)
        symbol = pp.Word("abcd", max=1)
        expr = number | symbol

        try:
            expr.parseString("1 + 2")
        except Exception as e:
            print_traceback = True
            try:
                self.assertTrue(
                    hasattr(e, "__cause__"),
                    "no __cause__ attribute in the raised exception",
                )
                self.assertTrue(
                    e.__cause__ is not None,
                    "__cause__ not propagated to outer exception",
                )
                self.assertEqual(
                    IndexError,
                    type(e.__cause__),
                    "__cause__ references wrong exception",
                )
                print_traceback = False
            finally:
                if print_traceback:
                    traceback.print_exc()
        else:
            self.fail("Expected ParseException not raised")

    # tests Issue #22
    def testParseActionNesting(self):

        vals = pp.OneOrMore(ppc.integer)("int_values")

        def add_total(tokens):
            tokens["total"] = sum(tokens)
            return tokens

        vals.addParseAction(add_total)
        results = vals.parseString("244 23 13 2343")
        print(results.dump())
        self.assertParseResultsEquals(
            results,
            expected_dict={"int_values": [244, 23, 13, 2343], "total": 2623},
            msg="noop parse action changed ParseResults structure",
        )

        name = pp.Word(pp.alphas)("name")
        score = pp.Word(pp.nums + ".")("score")
        nameScore = pp.Group(name + score)
        line1 = nameScore("Rider")

        result1 = line1.parseString("Mauney 46.5")

        print("### before parse action is added ###")
        print("result1.dump():\n" + result1.dump() + "\n")
        before_pa_dict = result1.asDict()

        line1.setParseAction(lambda t: t)

        result1 = line1.parseString("Mauney 46.5")
        after_pa_dict = result1.asDict()

        print("### after parse action was added ###")
        print("result1.dump():\n" + result1.dump() + "\n")
        self.assertEqual(
            before_pa_dict,
            after_pa_dict,
            "noop parse action changed ParseResults structure",
        )

    def testParseActionWithDelimitedList(self):
        class AnnotatedToken(object):
            def __init__(self, kind, elements):
                self.kind = kind
                self.elements = elements

            def __str__(self):
                return 'AnnotatedToken(%r, %r)' % (self.kind, self.elements)

            def __eq__(self, other):
                return type(self) == type(other) and self.kind == other.kind and self.elements == other.elements

            __repr__ = __str__

        def annotate(name):
            def _(t):
                return AnnotatedToken(name, t.asList())
            return _

        identifier = pp.Word(pp.srange('[a-z0-9]'))
        numeral = pp.Word(pp.nums)

        named_number_value = pp.Suppress('(') + numeral + pp.Suppress(')')
        named_number = identifier + named_number_value

        named_number_list = (pp.Suppress('{') +
                             pp.Group(pp.Optional(pp.delimitedList(named_number))) +
                             pp.Suppress('}'))

        # repro but in #345 - delimitedList silently changes contents of named_number
        named_number_value.setParseAction(annotate("val"))

        test_string = "{ x1(1), x2(2) }"
        expected = [['x1', AnnotatedToken("val", ['1']), 'x2', AnnotatedToken("val", ['2'])]]

        self.assertParseAndCheckList(named_number_list, test_string, expected)

    def testParseResultsNameBelowUngroupedName(self):

        rule_num = pp.Regex("[0-9]+")("LIT_NUM*")
        list_num = pp.Group(
            pp.Literal("[")("START_LIST")
            + pp.delimitedList(rule_num)("LIST_VALUES")
            + pp.Literal("]")("END_LIST")
        )("LIST")

        test_string = "[ 1,2,3,4,5,6 ]"
        list_num.runTests(test_string)

        U = list_num.parseString(test_string)
        self.assertTrue(
            "LIT_NUM" not in U.LIST.LIST_VALUES,
            "results name retained as sub in ungrouped named result",
        )

    def testParseResultsNamesInGroupWithDict(self):

        key = ppc.identifier()
        value = ppc.integer()
        lat = ppc.real()
        long = ppc.real()
        EQ = pp.Suppress("=")

        data = (
            lat("lat")
            + long("long")
            + pp.Dict(pp.OneOrMore(pp.Group(key + EQ + value)))
        )
        site = pp.QuotedString('"')("name") + pp.Group(data)("data")

        test_string = '"Golden Gate Bridge" 37.819722 -122.478611 height=746 span=4200'
        site.runTests(test_string)

        a, aEnd = pp.makeHTMLTags("a")
        attrs = a.parseString("<a href='blah'>")
        print(attrs.dump())
        self.assertParseResultsEquals(
            attrs,
            expected_dict={
                "startA": {"href": "blah", "tag": "a", "empty": False},
                "href": "blah",
                "tag": "a",
                "empty": False,
            },
        )

    def testMakeXMLTags(self):
        """test helper function makeXMLTags in simple use case"""

        body, bodyEnd = pp.makeXMLTags("body")
        tst = "<body>Hello</body>"
        expr = body + pp.Word(pp.alphas)("contents") + bodyEnd
        result = expr.parseString(tst)
        print(result.dump())
        self.assertParseResultsEquals(
            result, ["body", False, "Hello", "</body>"], msg="issue using makeXMLTags"
        )

    def testFollowedBy(self):

        expr = pp.Word(pp.alphas)("item") + pp.FollowedBy(ppc.integer("qty"))
        result = expr.parseString("balloon 99", parseAll=False)
        print(result.dump())
        self.assertTrue("qty" in result, "failed to capture results name in FollowedBy")
        self.assertEqual(
            {"item": "balloon", "qty": 99},
            result.asDict(),
            "invalid results name structure from FollowedBy",
        )

    def testSetBreak(self):
        """
        Test behavior of ParserElement.setBreak(), to invoke the debugger before parsing that element is attempted.

        Temporarily monkeypatches pdb.set_trace.
        """
        was_called = False

        def mock_set_trace():
            nonlocal was_called
            was_called = True

        wd = pp.Word(pp.alphas)
        wd.setBreak()

        print("Before parsing with setBreak:", was_called)
        import pdb

        with ppt.reset_pyparsing_context():
            pdb.set_trace = mock_set_trace
            wd.parseString("ABC")

        print("After parsing with setBreak:", was_called)
        self.assertTrue(was_called, "set_trace wasn't called by setBreak")

    def testUnicodeTests(self):

        ppu = pp.pyparsing_unicode

        # verify proper merging of ranges by addition
        kanji_printables = ppu.Japanese.Kanji.printables
        katakana_printables = ppu.Japanese.Katakana.printables
        hiragana_printables = ppu.Japanese.Hiragana.printables
        japanese_printables = ppu.Japanese.printables
        self.assertEqual(
            set(kanji_printables + katakana_printables + hiragana_printables),
            set(japanese_printables),
            "failed to construct ranges by merging Japanese types",
        )

        # verify proper merging of ranges using multiple inheritance
        cjk_printables = ppu.CJK.printables
        self.assertEqual(
            len(set(cjk_printables)),
            len(cjk_printables),
            "CJK contains duplicate characters - all should be unique",
        )

        chinese_printables = ppu.Chinese.printables
        korean_printables = ppu.Korean.printables
        print(
            len(set(chinese_printables + korean_printables + japanese_printables)),
            len(cjk_printables),
        )

        self.assertEqual(
            len(set(chinese_printables + korean_printables + japanese_printables)),
            len(cjk_printables),
            "failed to construct ranges by merging Chinese, Japanese and Korean",
        )

        alphas = ppu.Greek.alphas
        greet = pp.Word(alphas) + "," + pp.Word(alphas) + "!"

        # input string
        hello = "Καλημέρα, κόσμε!"
        result = greet.parseString(hello)
        print(result)
        self.assertParseResultsEquals(
            result,
            expected_list=["Καλημέρα", ",", "κόσμε", "!"],
            msg="Failed to parse Greek 'Hello, World!' using "
            "pyparsing_unicode.Greek.alphas",
        )

        # define a custom unicode range using multiple inheritance
        class Turkish_set(ppu.Latin1, ppu.LatinA):
            pass

        self.assertEqual(
            set(ppu.Latin1.printables + ppu.LatinA.printables),
            set(Turkish_set.printables),
            "failed to construct ranges by merging Latin1 and LatinA (printables)",
        )

        self.assertEqual(
            set(ppu.Latin1.alphas + ppu.LatinA.alphas),
            set(Turkish_set.alphas),
            "failed to construct ranges by merging Latin1 and LatinA (alphas)",
        )

        self.assertEqual(
            set(ppu.Latin1.nums + ppu.LatinA.nums),
            set(Turkish_set.nums),
            "failed to construct ranges by merging Latin1 and LatinA (nums)",
        )

        key = pp.Word(Turkish_set.alphas)
        value = ppc.integer | pp.Word(Turkish_set.alphas, Turkish_set.alphanums)
        EQ = pp.Suppress("=")
        key_value = key + EQ + value

        sample = """\
            şehir=İzmir
            ülke=Türkiye
            nüfus=4279677"""
        result = pp.Dict(pp.OneOrMore(pp.Group(key_value))).parseString(sample)

        print(result.dump())
        self.assertParseResultsEquals(
            result,
            expected_dict={"şehir": "İzmir", "ülke": "Türkiye", "nüfus": 4279677},
            msg="Failed to parse Turkish key-value pairs",
        )

    # Make sure example in indentedBlock docstring actually works!
    def testIndentedBlockExample(self):

        data = dedent(
            """
        def A(z):
          A1
          B = 100
          G = A2
          A2
          A3
        B
        def BB(a,b,c):
          BB1
          def BBA():
            bba1
            bba2
            bba3
        C
        D
        def spam(x,y):
             def eggs(z):
                 pass
        """
        )

        indentStack = [1]
        stmt = pp.Forward()

        identifier = pp.Word(pp.alphas, pp.alphanums)
        funcDecl = (
            "def"
            + identifier
            + pp.Group("(" + pp.Optional(pp.delimitedList(identifier)) + ")")
            + ":"
        )
        func_body = pp.indentedBlock(stmt, indentStack)
        funcDef = pp.Group(funcDecl + func_body)

        rvalue = pp.Forward()
        funcCall = pp.Group(
            identifier + "(" + pp.Optional(pp.delimitedList(rvalue)) + ")"
        )
        rvalue << (funcCall | identifier | pp.Word(pp.nums))
        assignment = pp.Group(identifier + "=" + rvalue)
        stmt <<= funcDef | assignment | identifier

        module_body = pp.OneOrMore(stmt)

        self.assertParseAndCheckList(
            module_body,
            data,
            [
                [
                    "def",
                    "A",
                    ["(", "z", ")"],
                    ":",
                    [["A1"], [["B", "=", "100"]], [["G", "=", "A2"]], ["A2"], ["A3"]],
                ],
                "B",
                [
                    "def",
                    "BB",
                    ["(", "a", "b", "c", ")"],
                    ":",
                    [
                        ["BB1"],
                        [
                            [
                                "def",
                                "BBA",
                                ["(", ")"],
                                ":",
                                [["bba1"], ["bba2"], ["bba3"]],
                            ]
                        ],
                    ],
                ],
                "C",
                "D",
                [
                    "def",
                    "spam",
                    ["(", "x", "y", ")"],
                    ":",
                    [[["def", "eggs", ["(", "z", ")"], ":", [["pass"]]]]],
                ],
            ],
            "Failed indentedBlock example",
            verbose=True,
        )

    def testIndentedBlock(self):
        # parse pseudo-yaml indented text

        EQ = pp.Suppress("=")
        stack = [1]
        key = ppc.identifier
        value = pp.Forward()
        key_value = key + EQ + value
        compound_value = pp.Dict(pp.ungroup(pp.indentedBlock(key_value, stack)))
        value <<= ppc.integer | pp.QuotedString("'") | compound_value
        parser = pp.Dict(pp.OneOrMore(pp.Group(key_value)))

        text = """
            a = 100
            b = 101
            c =
                c1 = 200
                c2 =
                    c21 = 999
                c3 = 'A horse, a horse, my kingdom for a horse'
            d = 505
        """
        text = dedent(text)
        print(text)

        result = parser.parseString(text)
        print(result.dump())
        self.assertEqual(100, result.a, "invalid indented block result")
        self.assertEqual(200, result.c.c1, "invalid indented block result")
        self.assertEqual(999, result.c.c2.c21, "invalid indented block result")

    # exercise indentedBlock with example posted in issue #87
    def testIndentedBlockTest2(self):

        indent_stack = [1]

        key = pp.Word(pp.alphas, pp.alphanums) + pp.Suppress(":")
        stmt = pp.Forward()

        suite = pp.indentedBlock(stmt, indent_stack)
        body = key + suite

        pattern = (
            pp.Word(pp.alphas)
            + pp.Suppress("(")
            + pp.Word(pp.alphas)
            + pp.Suppress(")")
        )
        stmt <<= pattern

        def key_parse_action(toks):
            print("Parsing '%s'..." % toks[0])

        key.setParseAction(key_parse_action)
        header = pp.Suppress("[") + pp.Literal("test") + pp.Suppress("]")
        content = header - pp.OneOrMore(pp.indentedBlock(body, indent_stack, False))

        contents = pp.Forward()
        suites = pp.indentedBlock(content, indent_stack)

        extra = pp.Literal("extra") + pp.Suppress(":") - suites
        contents <<= content | extra

        parser = pp.OneOrMore(contents)

        sample = dedent(
            """
        extra:
            [test]
            one0:
                two (three)
            four0:
                five (seven)
        extra:
            [test]
            one1:
                two (three)
            four1:
                five (seven)
        """
        )

        success, _ = parser.runTests([sample])
        self.assertTrue(success, "Failed indentedBlock test for issue #87")

        sample2 = dedent(
            """
        extra:
            [test]
            one:
                two (three)
            four:
                five (seven)
        extra:
            [test]
            one:
                two (three)
            four:
                five (seven)

            [test]
            one:
                two (three)
            four:
                five (seven)

            [test]
            eight:
                nine (ten)
            eleven:
                twelve (thirteen)

            fourteen:
                fifteen (sixteen)
            seventeen:
                eighteen (nineteen)
        """
        )

        del indent_stack[1:]
        success, _ = parser.runTests([sample2])
        self.assertTrue(success, "Failed indentedBlock multi-block test for issue #87")

    def testIndentedBlockScan(self):
        def get_parser():
            """
            A valid statement is the word "block:", followed by an indent, followed by the letter A only, or another block
            """
            stack = [1]
            block = pp.Forward()
            body = pp.indentedBlock(
                pp.Literal("A") ^ block, indentStack=stack, indent=True
            )
            block <<= pp.Literal("block:") + body
            return block

        # This input string is a perfect match for the parser, so a single match is found
        p1 = get_parser()
        r1 = list(
            p1.scanString(
                dedent(
                    """\
        block:
            A
        """
                )
            )
        )
        self.assertEqual(1, len(r1))

        # This input string is a perfect match for the parser, except for the letter B instead of A, so this will fail (and should)
        p2 = get_parser()
        r2 = list(
            p2.scanString(
                dedent(
                    """\
        block:
            B
        """
                )
            )
        )
        self.assertEqual(0, len(r2))

        # This input string contains both string A and string B, and it finds one match (as it should)
        p3 = get_parser()
        r3 = list(
            p3.scanString(
                dedent(
                    """\
        block:
            A
        block:
            B
        """
                )
            )
        )
        self.assertEqual(1, len(r3))

        # This input string contains both string A and string B, but in a different order.
        p4 = get_parser()
        r4 = list(
            p4.scanString(
                dedent(
                    """\
        block:
            B
        block:
            A
        """
                )
            )
        )
        self.assertEqual(1, len(r4))

        # This is the same as case 3, but with nesting
        p5 = get_parser()
        r5 = list(
            p5.scanString(
                dedent(
                    """\
        block:
            block:
                A
        block:
            block:
                B
        """
                )
            )
        )
        self.assertEqual(1, len(r5))

        # This is the same as case 4, but with nesting
        p6 = get_parser()
        r6 = list(
            p6.scanString(
                dedent(
                    """\
        block:
            block:
                B
        block:
            block:
                A
        """
                )
            )
        )
        self.assertEqual(1, len(r6))

    def testIndentedBlockClass(self):
        data = """\
            A
                100
                101

                102
            B
                200
                201

            C
                300

        """

        integer = ppc.integer
        group = pp.Group(pp.Char(pp.alphas) + pp.IndentedBlock(integer))

        group[...].parseString(data).pprint()

        self.assertParseAndCheckList(
            group[...], data, [["A", [100, 101, 102]], ["B", [200, 201]], ["C", [300]]]
        )

    def testIndentedBlockClass2(self):
        datas = [
            """\
             A
                100
             B
                200
             201
            """,
            """\
             A
                100
             B
                200
               201
            """,
            """\
             A
                100
             B
                200
                  201
            """,
        ]
        integer = ppc.integer
        group = pp.Group(
            pp.Char(pp.alphas) + pp.IndentedBlock(integer, recursive=False)
        )

        for data in datas:
            print()
            print(ppt.with_line_numbers(data))

            print(group[...].parse_string(data).as_list())
            self.assertParseAndCheckList(
                group[...] + integer.suppress(),
                data,
                [["A", [100]], ["B", [200]]],
                verbose=False,
            )

    def testIndentedBlockClassWithRecursion(self):
        data = """\

            A
                100
                101

                102
            B
                b
                    200
                    201

            C
                300

        """

        integer = ppc.integer
        group = pp.Forward()
        group <<= pp.Group(pp.Char(pp.alphas) + pp.IndentedBlock(integer | group))

        print("using searchString")
        print(group.searchString(data))
        # print(sum(group.searchString(data)).dump())

        self.assertParseAndCheckList(
            group[...],
            data,
            [["A", [100, 101, 102]], ["B", [["b", [200, 201]]]], ["C", [300]]],
        )

        print("using parseString")
        print(group[...].parseString(data).dump())

        dotted_int = pp.delimited_list(
            pp.Word(pp.nums), ".", allow_trailing_delim=True, combine=True
        )
        indented_expr = pp.IndentedBlock(dotted_int, recursive=True, grouped=True)
        # indented_expr = pp.Forward()
        # indented_expr <<= pp.IndentedBlock(dotted_int + indented_expr))
        good_data = """\
            1.
                1.1
                    1.1.1
                    1.1.2
            2."""
        bad_data1 = """\
            1.
                1.1
                    1.1.1
                 1.2
            2."""
        bad_data2 = """\
            1.
                1.1
                    1.1.1
               1.2
            2."""
        print("test good indentation")
        print(pp.pyparsing_test.with_line_numbers(good_data))
        print(indented_expr.parseString(good_data, parseAll=True).as_list())
        print()

        print("test bad indentation")
        print(pp.pyparsing_test.with_line_numbers(bad_data1))
        with self.assertRaisesParseException(
            msg="Failed to raise exception with bad indentation 1"
        ):
            indented_expr.parseString(bad_data1, parseAll=True)

        print(pp.pyparsing_test.with_line_numbers(bad_data2))
        with self.assertRaisesParseException(
            msg="Failed to raise exception with bad indentation 2"
        ):
            indented_expr.parseString(bad_data2, parseAll=True)

    def testInvalidDiagSetting(self):
        with self.assertRaises(
            ValueError,
            msg="failed to raise exception when setting non-existent __diag__",
        ):
            pp.__diag__.enable("xyzzy")

        with self.assertWarns(
            UserWarning, msg="failed to warn disabling 'collect_all_And_tokens"
        ):
            pp.__compat__.disable("collect_all_And_tokens")

    def testParseResultsWithNameMatchFirst(self):
        expr_a = pp.Literal("not") + pp.Literal("the") + pp.Literal("bird")
        expr_b = pp.Literal("the") + pp.Literal("bird")
        expr = (expr_a | expr_b)("rexp")

        success, report = expr.runTests(
            """\
            not the bird
            the bird
        """
        )
        results = [rpt[1] for rpt in report]
        self.assertParseResultsEquals(
            results[0], ["not", "the", "bird"], {"rexp": ["not", "the", "bird"]}
        )
        self.assertParseResultsEquals(
            results[1], ["the", "bird"], {"rexp": ["the", "bird"]}
        )

        # test compatibility mode, no longer restoring pre-2.3.1 behavior
        with ppt.reset_pyparsing_context():
            pp.__compat__.collect_all_And_tokens = False
            pp.enable_diag(pp.Diagnostics.warn_multiple_tokens_in_named_alternation)
            expr_a = pp.Literal("not") + pp.Literal("the") + pp.Literal("bird")
            expr_b = pp.Literal("the") + pp.Literal("bird")
            with self.assertWarns(
                UserWarning, msg="failed to warn of And within alternation"
            ):
                expr = (expr_a | expr_b)("rexp")

            with self.assertDoesNotWarn(
                UserWarning, msg="warned when And within alternation warning was suppressed"
            ):
                expr = (expr_a | expr_b).suppress_warning(pp.Diagnostics.warn_multiple_tokens_in_named_alternation)("rexp")

            success, report = expr.runTests(
                """
                not the bird
                the bird
            """
            )
            results = [rpt[1] for rpt in report]
            self.assertParseResultsEquals(
                results[0], ["not", "the", "bird"], {"rexp": ["not", "the", "bird"]}
            )
            self.assertParseResultsEquals(
                results[1], ["the", "bird"], {"rexp": ["the", "bird"]}
            )

    def testParseResultsWithNameOr(self):
        expr_a = pp.Literal("not") + pp.Literal("the") + pp.Literal("bird")
        expr_b = pp.Literal("the") + pp.Literal("bird")
        expr = (expr_a ^ expr_b)("rexp")
        expr.runTests(
            """\
            not the bird
            the bird
        """
        )
        result = expr.parseString("not the bird")
        self.assertParseResultsEquals(
            result, ["not", "the", "bird"], {"rexp": ["not", "the", "bird"]}
        )
        result = expr.parseString("the bird")
        self.assertParseResultsEquals(
            result, ["the", "bird"], {"rexp": ["the", "bird"]}
        )

        expr = (expr_a | expr_b)("rexp")
        expr.runTests(
            """\
            not the bird
            the bird
        """
        )
        result = expr.parseString("not the bird")
        self.assertParseResultsEquals(
            result, ["not", "the", "bird"], {"rexp": ["not", "the", "bird"]}
        )
        result = expr.parseString("the bird")
        self.assertParseResultsEquals(
            result, ["the", "bird"], {"rexp": ["the", "bird"]}
        )

        # test compatibility mode, no longer restoring pre-2.3.1 behavior
        with ppt.reset_pyparsing_context():
            pp.__compat__.collect_all_And_tokens = False
            pp.enable_diag(pp.Diagnostics.warn_multiple_tokens_in_named_alternation)
            expr_a = pp.Literal("not") + pp.Literal("the") + pp.Literal("bird")
            expr_b = pp.Literal("the") + pp.Literal("bird")

            with self.assertWarns(
                UserWarning, msg="failed to warn of And within alternation"
            ):
                expr = (expr_a ^ expr_b)("rexp")

            with self.assertDoesNotWarn(
                UserWarning, msg="warned when And within alternation warning was suppressed"
            ):
                expr = (expr_a ^ expr_b).suppress_warning(pp.Diagnostics.warn_multiple_tokens_in_named_alternation)("rexp")

            expr.runTests(
                """\
                not the bird
                the bird
            """
            )
            self.assertEqual(
                "not the bird".split(), list(expr.parseString("not the bird")["rexp"])
            )
            self.assertEqual(
                "the bird".split(), list(expr.parseString("the bird")["rexp"])
            )

    def testEmptyDictDoesNotRaiseException(self):
        key = pp.Word(pp.alphas)
        value = pp.Word(pp.nums)
        EQ = pp.Suppress("=")
        key_value_dict = pp.dictOf(key, EQ + value)

        print(
            key_value_dict.parseString(
                """\
            a = 10
            b = 20
            """
            ).dump()
        )

        try:
            print(key_value_dict.parseString("").dump())
        except pp.ParseException as pe:
            print(pp.ParseException.explain(pe))
        else:
            self.fail("failed to raise exception when matching empty string")

    def testExplainException(self):
        expr = pp.Word(pp.nums).setName("int") + pp.Word(pp.alphas).setName("word")
        try:
            expr.parseString("123 355")
        except pp.ParseException as pe:
            print(pe.explain(depth=0))

        expr = pp.Word(pp.nums).setName("int") - pp.Word(pp.alphas).setName("word")
        try:
            expr.parseString("123 355 (test using ErrorStop)")
        except pp.ParseSyntaxException as pe:
            print(pe.explain())

        integer = pp.Word(pp.nums).setName("int").addParseAction(lambda t: int(t[0]))
        expr = integer + integer

        def divide_args(t):
            integer.parseString("A")
            return t[0] / t[1]

        expr.addParseAction(divide_args)
        try:
            expr.parseString("123 0")
        except pp.ParseException as pe:
            print(pe.explain())
        except Exception as exc:
            print(pp.ParseBaseException.explain_exception(exc))
            raise

    def testExplainExceptionWithMemoizationCheck(self):
        if pp.ParserElement._left_recursion_enabled or pp.ParserElement._packratEnabled:
            print("test does local memoization enable/disable during test")
            return

        pp.ParserElement.disable_memoization()

        integer = pp.Word(pp.nums).setName("int").addParseAction(lambda t: int(t[0]))
        expr = integer + integer

        def divide_args(t):
            integer.parseString("A")
            return t[0] / t[1]

        expr.addParseAction(divide_args)
        for memo_kind, enable_memo in [
            ("Packrat", pp.ParserElement.enablePackrat),
            ("Left Recursion", pp.ParserElement.enable_left_recursion),
        ]:
            enable_memo(force=True)
            print("Explain for", memo_kind)

            try:
                expr.parseString("123 0")
            except pp.ParseException as pe:
                print(pe.explain())
            except Exception as exc:
                print(pp.ParseBaseException.explain_exception(exc))
                raise

        # make sure we leave the state compatible with everything
        pp.ParserElement.disable_memoization()

    def testCaselessKeywordVsKeywordCaseless(self):
        frule = pp.Keyword("t", caseless=True) + pp.Keyword("yes", caseless=True)
        crule = pp.CaselessKeyword("t") + pp.CaselessKeyword("yes")

        flist = frule.searchString("not yes").asList()
        print(flist)
        clist = crule.searchString("not yes").asList()
        print(clist)
        self.assertEqual(
            flist,
            clist,
            "CaselessKeyword not working the same as Keyword(caseless=True)",
        )

    def testOneOfKeywords(self):
        literal_expr = pp.oneOf("a b c")
        success, _ = literal_expr[...].runTests(
            """
            # literal oneOf tests
            a b c
            a a a
            abc
        """
        )
        self.assertTrue(success, "failed literal oneOf matching")

        keyword_expr = pp.oneOf("a b c", asKeyword=True)
        success, _ = keyword_expr[...].runTests(
            """
            # keyword oneOf tests
            a b c
            a a a
        """
        )
        self.assertTrue(success, "failed keyword oneOf matching")

        success, _ = keyword_expr[...].runTests(
            """
            # keyword oneOf failure tests
            abc
        """,
            failureTests=True,
        )
        self.assertTrue(success, "failed keyword oneOf failure tests")

    def testWarnUngroupedNamedTokens(self):
        """
        - warn_ungrouped_named_tokens_in_collection - flag to enable warnings when a results
          name is defined on a containing expression with ungrouped subexpressions that also
          have results names (default=True)
        """
        with self.assertDoesNotWarn(
            msg="raised {} warning when not enabled".format(
                pp.Diagnostics.warn_ungrouped_named_tokens_in_collection
            )
        ):
            COMMA = pp.Suppress(",").setName("comma")
            coord = ppc.integer("x") + COMMA + ppc.integer("y")
            path = coord[...].setResultsName("path")

        with ppt.reset_pyparsing_context():
            pp.enable_diag(pp.Diagnostics.warn_ungrouped_named_tokens_in_collection)

            COMMA = pp.Suppress(",").setName("comma")
            coord = ppc.integer("x") + COMMA + ppc.integer("y")

            # this should emit a warning
            with self.assertWarns(
                UserWarning,
                msg="failed to warn with named repetition of"
                " ungrouped named expressions",
            ):
                path = coord[...].setResultsName("path")

            with self.assertDoesNotWarn(
                UserWarning,
                msg="warned when named repetition of"
                " ungrouped named expressions warning was suppressed",
            ):
                path = coord[...].suppress_warning(pp.Diagnostics.warn_ungrouped_named_tokens_in_collection).setResultsName("path")

    def testDontWarnUngroupedNamedTokensIfWarningSuppressed(self):
        with ppt.reset_pyparsing_context():
            pp.enable_diag(pp.Diagnostics.warn_ungrouped_named_tokens_in_collection)

            with self.assertDoesNotWarn(
                msg="raised {} warning when warn on ungrouped named tokens was suppressed (original_text_for)".format(
                    pp.Diagnostics.warn_ungrouped_named_tokens_in_collection
                )
            ):
                pp.originalTextFor(pp.Word("ABC")[...])("words")

    def testWarnNameSetOnEmptyForward(self):
        """
        - warn_name_set_on_empty_Forward - flag to enable warnings when a Forward is defined
          with a results name, but has no contents defined (default=False)
        """

        with self.assertDoesNotWarn(
            msg="raised {} warning when not enabled".format(
                pp.Diagnostics.warn_name_set_on_empty_Forward
            )
        ):
            base = pp.Forward()("z")

        with ppt.reset_pyparsing_context():
            pp.enable_diag(pp.Diagnostics.warn_name_set_on_empty_Forward)

            base = pp.Forward()

            with self.assertWarns(
                UserWarning,
                msg="failed to warn when naming an empty Forward expression",
            ):
                base("x")

            with self.assertDoesNotWarn(
                UserWarning,
                msg="warned when naming an empty Forward expression warning was suppressed",
            ):
                base.suppress_warning(pp.Diagnostics.warn_name_set_on_empty_Forward)("x")

    def testWarnParsingEmptyForward(self):
        """
        - warn_on_parse_using_empty_Forward - flag to enable warnings when a Forward
          has no contents defined (default=False)
        """

        with self.assertDoesNotWarn(
            msg="raised {} warning when not enabled".format(
                pp.Diagnostics.warn_on_parse_using_empty_Forward
            )
        ):
            base = pp.Forward()
            try:
                print(base.parseString("x"))
            except ParseException as pe:
                pass

        with ppt.reset_pyparsing_context():
            pp.enable_diag(pp.Diagnostics.warn_on_parse_using_empty_Forward)

            base = pp.Forward()

            with self.assertWarns(
                UserWarning,
                msg="failed to warn when parsing using an empty Forward expression",
            ):
                try:
                    print(base.parseString("x"))
                except ParseException as pe:
                    pass

            with self.assertDoesNotWarn(
                    UserWarning,
                    msg="warned when parsing using an empty Forward expression warning was suppressed",
            ):
                base.suppress_warning(pp.Diagnostics.warn_on_parse_using_empty_Forward)
                try:
                    print(base.parseString("x"))
                except ParseException as pe:
                    pass

    def testWarnIncorrectAssignmentToForward(self):
        """
        - warn_on_parse_using_empty_Forward - flag to enable warnings when a Forward
          has no contents defined (default=False)
        """
        if PYPY_ENV:
            print("warn_on_assignment_to_Forward not supported on PyPy")
            return

        def a_method():
            base = pp.Forward()
            base = pp.Word(pp.alphas)[...] | "(" + base + ")"

        with self.assertDoesNotWarn(
            msg="raised {} warning when not enabled".format(
                pp.Diagnostics.warn_on_assignment_to_Forward
            )
        ):
            a_method()

        with ppt.reset_pyparsing_context():
            pp.enable_diag(pp.Diagnostics.warn_on_assignment_to_Forward)

            with self.assertWarns(
                UserWarning,
                msg="failed to warn when using '=' to assign expression to a Forward",
            ):
                a_method()

            def a_method():
                base = pp.Forward().suppress_warning(pp.Diagnostics.warn_on_assignment_to_Forward)
                base = pp.Word(pp.alphas)[...] | "(" + base + ")"

            with self.assertDoesNotWarn(
                UserWarning,
                msg="warned when using '=' to assign expression to a Forward warning was suppressed",
            ):
                a_method()


    def testWarnOnMultipleStringArgsToOneOf(self):
        """
        - warn_on_multiple_string_args_to_oneof - flag to enable warnings when oneOf is
          incorrectly called with multiple str arguments (default=True)
        """
        with self.assertDoesNotWarn(
            msg="raised {} warning when not enabled".format(
                pp.Diagnostics.warn_on_multiple_string_args_to_oneof
            )
        ):
            a = pp.oneOf("A", "B")

        with ppt.reset_pyparsing_context():
            pp.enable_diag(pp.Diagnostics.warn_on_multiple_string_args_to_oneof)

            with self.assertWarns(
                UserWarning,
                msg="failed to warn when incorrectly calling oneOf(string, string)",
            ):
                a = pp.oneOf("A", "B")

    def testAutonameElements(self):
        with ppt.reset_pyparsing_context():
            pp.enable_diag(pp.Diagnostics.enable_debug_on_named_expressions)

            a = pp.Literal("a")
            b = pp.Literal("b").set_name("bbb")
            z = pp.Literal("z")
            leading_a = a + pp.FollowedBy(z | a | b)

            grammar = (z | leading_a | b)[...] + "a"

            self.assertFalse(a.debug)
            self.assertFalse(a.customName)
            pp.autoname_elements()
            self.assertTrue(a.debug)
            self.assertEqual("a", a.name)
            self.assertEqual("bbb", b.name)

    def testDelimitedListName(self):
        bool_constant = pp.Literal("True") | "true" | "False" | "false"
        bool_list = pp.delimitedList(bool_constant)
        print(bool_list)
        self.assertEqual(
            "{'True' | 'true' | 'False' | 'false'} [, {'True' | 'true' | 'False' | 'false'}]...",
            str(bool_list),
        )

        bool_constant.setName("bool")
        print(bool_constant)
        print(bool_constant.streamline())
        bool_list2 = pp.delimitedList(bool_constant)
        print(bool_constant)
        print(bool_constant.streamline())
        print(bool_list2)
        self.assertEqual("bool [, bool]...", str(bool_list2))

    def testDelimitedListOfStrLiterals(self):
        expr = pp.delimitedList("ABC")
        print(str(expr))
        source = "ABC, ABC,ABC"
        self.assertParseAndCheckList(
            expr, source, [s.strip() for s in source.split(",")]
        )

    def testDelimitedListMinMax(self):
        source = "ABC, ABC,ABC"
        with self.assertRaises(ValueError, msg="min must be greater than 0"):
            pp.delimited_list("ABC", min=0)
        with self.assertRaises(ValueError, msg="max must be greater than, or equal to min"):
            pp.delimited_list("ABC", min=1, max=0)
        with self.assertRaises(pp.ParseException):
            pp.delimited_list("ABC", min=4).parse_string(source)

        source_expr_pairs = [
            ("ABC,  ABC", pp.delimited_list("ABC", max=2)),
            (source, pp.delimited_list("ABC", min=2, max=4)),
        ]
        for source, expr in source_expr_pairs:
            print(str(expr))
            self.assertParseAndCheckList(
                expr, source, [s.strip() for s in source.split(",")]
            )

    def testEnableDebugOnNamedExpressions(self):
        """
        - enable_debug_on_named_expressions - flag to auto-enable debug on all subsequent
          calls to ParserElement.setName() (default=False)
        """
        with ppt.reset_pyparsing_context():
            test_stdout = StringIO()

            with resetting(sys, "stdout", "stderr"):
                sys.stdout = test_stdout
                sys.stderr = test_stdout

                pp.enable_diag(pp.Diagnostics.enable_debug_on_named_expressions)
                integer = pp.Word(pp.nums).setName("integer")

                integer[...].parseString("1 2 3")

            expected_debug_output = dedent(
                """\
                Match integer at loc 0(1,1)
                  1 2 3
                  ^
                Matched integer -> ['1']
                Match integer at loc 2(1,3)
                  1 2 3
                    ^
                Matched integer -> ['2']
                Match integer at loc 4(1,5)
                  1 2 3
                      ^
                Matched integer -> ['3']
                Match integer at loc 5(1,6)
                  1 2 3
                       ^
                Match integer failed, ParseException raised: Expected integer, found end of text  (at char 5), (line:1, col:6)
                """
            )
            output = test_stdout.getvalue()
            print(output)
            self.assertEqual(
                expected_debug_output,
                output,
                "failed to auto-enable debug on named expressions "
                "using enable_debug_on_named_expressions",
            )

    def testEnableDebugOnExpressionWithParseAction(self):

        test_stdout = StringIO()
        with resetting(sys, "stdout", "stderr"):
            sys.stdout = test_stdout
            sys.stderr = test_stdout

            parser = (ppc.integer().setDebug() | pp.Word(pp.alphanums).setDebug())[...]
            parser.setDebug()
            parser.parseString("123 A100")

            # now turn off debug - should only get output for components, not overall parser
            print()
            parser.setDebug(False)
            parser.parseString("123 A100")

        expected_debug_output = dedent(
            """\
            Match [{integer | W:(0-9A-Za-z)}]... at loc 0(1,1)
              123 A100
              ^
            Match integer at loc 0(1,1)
              123 A100
              ^
            Matched integer -> [123]
            Match integer at loc 4(1,5)
              123 A100
                  ^
            Match integer failed, ParseException raised: Expected integer, found 'A100'  (at char 4), (line:1, col:5)
            Match W:(0-9A-Za-z) at loc 4(1,5)
              123 A100
                  ^
            Matched W:(0-9A-Za-z) -> ['A100']
            Match integer at loc 8(1,9)
              123 A100
                      ^
            Match integer failed, ParseException raised: Expected integer, found end of text  (at char 8), (line:1, col:9)
            Match W:(0-9A-Za-z) at loc 8(1,9)
              123 A100
                      ^
            Match W:(0-9A-Za-z) failed, ParseException raised: Expected W:(0-9A-Za-z), found end of text  (at char 8), (line:1, col:9)
            Matched [{integer | W:(0-9A-Za-z)}]... -> [123, 'A100']
            
            Match integer at loc 0(1,1)
              123 A100
              ^
            Matched integer -> [123]
            Match integer at loc 4(1,5)
              123 A100
                  ^
            Match integer failed, ParseException raised: Expected integer, found 'A100'  (at char 4), (line:1, col:5)
            Match W:(0-9A-Za-z) at loc 4(1,5)
              123 A100
                  ^
            Matched W:(0-9A-Za-z) -> ['A100']
            Match integer at loc 8(1,9)
              123 A100
                      ^
            Match integer failed, ParseException raised: Expected integer, found end of text  (at char 8), (line:1, col:9)
            Match W:(0-9A-Za-z) at loc 8(1,9)
              123 A100
                      ^
            Match W:(0-9A-Za-z) failed, ParseException raised: Expected W:(0-9A-Za-z), found end of text  (at char 8), (line:1, col:9)
            """
        )
        output = test_stdout.getvalue()
        print(output)
        self.assertEqual(
            expected_debug_output,
            output,
            "invalid debug output when using parse action",
        )

    def testEnableDebugWithCachedExpressionsMarkedWithAsterisk(self):

        a = pp.Literal("a").setName("A").setDebug()
        b = pp.Literal("b").setName("B").setDebug()
        z = pp.Literal("z").setName("Z").setDebug()
        leading_a = a + pp.FollowedBy(z | a | b)
        leading_a.setName("leading_a").setDebug()

        grammar = (z | leading_a | b)[...] + "a"

        # parse test string and capture debug output
        test_stdout = StringIO()
        with resetting(sys, "stdout", "stderr"):
            sys.stdout = test_stdout
            sys.stderr = test_stdout
            grammar.parseString("aba")

        expected_debug_output = dedent(
            """\
            Match Z at loc 0(1,1)
              aba
              ^
            Match Z failed, ParseException raised: Expected Z, found 'aba'  (at char 0), (line:1, col:1)
            Match leading_a at loc 0(1,1)
              aba
              ^
            Match A at loc 0(1,1)
              aba
              ^
            Matched A -> ['a']
            Match Z at loc 1(1,2)
              aba
               ^
            Match Z failed, ParseException raised: Expected Z, found 'ba'  (at char 1), (line:1, col:2)
            Match A at loc 1(1,2)
              aba
               ^
            Match A failed, ParseException raised: Expected A, found 'ba'  (at char 1), (line:1, col:2)
            Match B at loc 1(1,2)
              aba
               ^
            Matched B -> ['b']
            Matched leading_a -> ['a']
            *Match Z at loc 1(1,2)
              aba
               ^
            *Match Z failed, ParseException raised: Expected Z, found 'ba'  (at char 1), (line:1, col:2)
            Match leading_a at loc 1(1,2)
              aba
               ^
            Match A at loc 1(1,2)
              aba
               ^
            Match A failed, ParseException raised: Expected A, found 'ba'  (at char 1), (line:1, col:2)
            Match leading_a failed, ParseException raised: Expected A, found 'ba'  (at char 1), (line:1, col:2)
            *Match B at loc 1(1,2)
              aba
               ^
            *Matched B -> ['b']
            Match Z at loc 2(1,3)
              aba
                ^
            Match Z failed, ParseException raised: Expected Z, found 'a'  (at char 2), (line:1, col:3)
            Match leading_a at loc 2(1,3)
              aba
                ^
            Match A at loc 2(1,3)
              aba
                ^
            Matched A -> ['a']
            Match Z at loc 3(1,4)
              aba
                 ^
            Match Z failed, ParseException raised: Expected Z, found end of text  (at char 3), (line:1, col:4)
            Match A at loc 3(1,4)
              aba
                 ^
            Match A failed, ParseException raised: Expected A, found end of text  (at char 3), (line:1, col:4)
            Match B at loc 3(1,4)
              aba
                 ^
            Match B failed, ParseException raised: Expected B, found end of text  (at char 3), (line:1, col:4)
            Match leading_a failed, ParseException raised: Expected {Z | A | B}, found end of text  (at char 3), (line:1, col:4)
            Match B at loc 2(1,3)
              aba
                ^
            Match B failed, ParseException raised: Expected B, found 'a'  (at char 2), (line:1, col:3)
            """
        )
        if pp.ParserElement._packratEnabled:
            packrat_status = "enabled"
        else:
            # remove '*' cache markers from expected output
            expected_debug_output = expected_debug_output.replace("*", "")
            packrat_status = "disabled"
        print("Packrat status:", packrat_status)

        output = test_stdout.getvalue()
        print(output)
        self.assertEqual(
            expected_debug_output,
            output,
            (
                "invalid debug output showing cached results marked with '*',"
                " and packrat parsing {}".format(packrat_status)
            ),
        )

    def testUndesirableButCommonPractices(self):
        # While these are valid constructs, and they are not encouraged
        # there is apparently a lot of code out there using these
        # coding styles.
        #
        # Even though they are not encouraged, we shouldn't break them.

        # Create an And using a list of expressions instead of using '+' operator
        expr = pp.And([pp.Word("abc"), pp.Word("123")])
        expr.runTests(
            """
            aaa 333
            b 1
            ababab 32123
        """
        )

        # Passing a single expression to a ParseExpression, when it really wants a sequence
        expr = pp.Or(pp.Or(ppc.integer))
        expr.runTests(
            """
            123
            456
            abc
        """
        )

    def testEnableWarnDiags(self):
        import pprint

        def filtered_vars(var_dict):
            dunders = [nm for nm in var_dict if nm.startswith("__")]
            return {
                k: v
                for k, v in var_dict.items()
                if isinstance(v, bool) and k not in dunders
            }

        pprint.pprint(filtered_vars(vars(pp.__diag__)), width=30)

        warn_names = pp.__diag__._warning_names
        other_names = pp.__diag__._debug_names

        # make sure they are off by default
        for diag_name in warn_names:
            self.assertFalse(
                getattr(pp.__diag__, diag_name),
                "__diag__.{} not set to True".format(diag_name),
            )

        with ppt.reset_pyparsing_context():
            # enable all warn_* diag_names
            pp.enable_all_warnings()
            pprint.pprint(filtered_vars(vars(pp.__diag__)), width=30)

            # make sure they are on after being enabled
            for diag_name in warn_names:
                self.assertTrue(
                    getattr(pp.__diag__, diag_name),
                    "__diag__.{} not set to True".format(diag_name),
                )

            # non-warn diag_names must be enabled individually
            for diag_name in other_names:
                self.assertFalse(
                    getattr(pp.__diag__, diag_name),
                    "__diag__.{} not set to True".format(diag_name),
                )

        # make sure they are off after AutoReset
        for diag_name in warn_names:
            self.assertFalse(
                getattr(pp.__diag__, diag_name),
                "__diag__.{} not set to True".format(diag_name),
            )

    def testWordInternalReRangeWithConsecutiveChars(self):
        self.assertParseAndCheckList(
            pp.Word("ABCDEMNXYZ"),
            "ABCDEMNXYZABCDEMNXYZABCDEMNXYZ",
            ["ABCDEMNXYZABCDEMNXYZABCDEMNXYZ"]
        )

    def testWordInternalReRangesKnownSet(self):
        tests = [
            ("ABCDEMNXYZ", "[A-EMNX-Z]+"),
            (pp.printables, "[!-~]+"),
            (pp.alphanums, "[0-9A-Za-z]+"),
            (pp.pyparsing_unicode.Latin1.printables, "[!-~¡-ÿ]+"),
            (pp.pyparsing_unicode.Latin1.alphanums, "[0-9A-Za-zª²³µ¹ºÀ-ÖØ-öø-ÿ]+"),
            (pp.alphas8bit, "[À-ÖØ-öø-ÿ]+"),
        ]
        failed = []
        for word_string, expected_re in tests:
            try:
                msg = "failed to generate correct internal re for {!r}".format(word_string)
                resultant_re = pp.Word(word_string).reString
                self.assertEqual(
                    expected_re,
                    resultant_re,
                    msg + "; expected {!r} got {!r}".format(expected_re, resultant_re)
                )
            except AssertionError:
                failed.append(msg)

        if failed:
            print("Errors:\n{}".format("\n".join(failed)))
            self.fail("failed to generate correct internal re's")

    def testWordInternalReRanges(self):
        import random

        esc_chars = r"\^-]["
        esc_chars2 = r"*+.?"

        def esc_re_set_char(c):
            return "\\" + c if c in esc_chars else c

        def esc_re_set2_char(c):
            return "\\" + c if c in esc_chars + esc_chars2 else c

        for esc_char in esc_chars + esc_chars2:
            # test escape char as first character in range
            next_char = chr(ord(esc_char) + 1)
            prev_char = chr(ord(esc_char) - 1)
            esc_word = pp.Word(esc_char + next_char)
            expected = r"[{}{}]+".format(
                esc_re_set_char(esc_char),
                esc_re_set_char(next_char),
            )
            print(
                "Testing escape char: {} -> {} re: '{}')".format(
                    esc_char, esc_word, esc_word.reString
                )
            )
            self.assertEqual(
                expected, esc_word.reString, "failed to generate correct internal re"
            )
            test_string = "".join(
                random.choice([esc_char, next_char]) for __ in range(16)
            )
            print(
                "Match '{}' -> {}".format(
                    test_string, test_string == esc_word.parseString(test_string)[0]
                )
            )
            self.assertEqual(
                test_string,
                esc_word.parseString(test_string)[0],
                "Word using escaped range char failed to parse",
            )

            # test escape char as last character in range
            esc_word = pp.Word(prev_char + esc_char)
            expected = r"[{}{}]+".format(
                esc_re_set_char(prev_char),
                esc_re_set_char(esc_char),
            )
            print(
                "Testing escape char: {} -> {} re: '{}')".format(
                    esc_char, esc_word, esc_word.reString
                )
            )
            self.assertEqual(
                expected, esc_word.reString, "failed to generate correct internal re"
            )
            test_string = "".join(
                random.choice([esc_char, prev_char]) for __ in range(16)
            )
            print(
                "Match '{}' -> {}".format(
                    test_string, test_string == esc_word.parseString(test_string)[0]
                )
            )
            self.assertEqual(
                test_string,
                esc_word.parseString(test_string)[0],
                "Word using escaped range char failed to parse",
            )

            # test escape char as first character in range
            next_char = chr(ord(esc_char) + 1)
            prev_char = chr(ord(esc_char) - 1)
            esc_word = pp.Word(esc_char + next_char)
            expected = r"[{}{}]+".format(
                esc_re_set_char(esc_char),
                esc_re_set_char(next_char),
            )
            print(
                "Testing escape char: {} -> {} re: '{}')".format(
                    esc_char, esc_word, esc_word.reString
                )
            )
            self.assertEqual(
                expected, esc_word.reString, "failed to generate correct internal re"
            )
            test_string = "".join(
                random.choice([esc_char, next_char]) for __ in range(16)
            )
            print(
                "Match '{}' -> {}".format(
                    test_string, test_string == esc_word.parseString(test_string)[0]
                )
            )
            self.assertEqual(
                test_string,
                esc_word.parseString(test_string)[0],
                "Word using escaped range char failed to parse",
            )

            # test escape char as only character in range
            esc_word = pp.Word(esc_char, pp.alphas.upper())
            expected = r"{}[A-Z]*".format(esc_re_set2_char(esc_char))
            print(
                "Testing escape char: {} -> {} re: '{}')".format(
                    esc_char, esc_word, esc_word.reString
                )
            )
            self.assertEqual(
                expected, esc_word.reString, "failed to generate correct internal re"
            )
            test_string = esc_char + "".join(
                random.choice(pp.alphas.upper()) for __ in range(16)
            )
            print(
                "Match '{}' -> {}".format(
                    test_string, test_string == esc_word.parseString(test_string)[0]
                )
            )
            self.assertEqual(
                test_string,
                esc_word.parseString(test_string)[0],
                "Word using escaped range char failed to parse",
            )

            # test escape char as only character
            esc_word = pp.Word(esc_char, pp.alphas.upper())
            expected = r"{}[A-Z]*".format(re.escape(esc_char))
            print(
                "Testing escape char: {} -> {} re: '{}')".format(
                    esc_char, esc_word, esc_word.reString
                )
            )
            self.assertEqual(
                expected, esc_word.reString, "failed to generate correct internal re"
            )
            test_string = esc_char + "".join(
                random.choice(pp.alphas.upper()) for __ in range(16)
            )
            print(
                "Match '{}' -> {}".format(
                    test_string, test_string == esc_word.parseString(test_string)[0]
                )
            )
            self.assertEqual(
                test_string,
                esc_word.parseString(test_string)[0],
                "Word using escaped range char failed to parse",
            )
            print()

    def testWordWithIdentChars(self):
        ppu = pp.pyparsing_unicode

        latin_identifier = pp.Word(pp.identchars, pp.identbodychars)("latin*")
        japanese_identifier = pp.Word(
            ppu.Japanese.identchars, ppu.Japanese.identbodychars
        )("japanese*")
        cjk_identifier = pp.Word(ppu.CJK.identchars, ppu.CJK.identbodychars)("cjk*")
        greek_identifier = pp.Word(ppu.Greek.identchars, ppu.Greek.identbodychars)(
            "greek*"
        )
        cyrillic_identifier = pp.Word(
            ppu.Cyrillic.identchars, ppu.Cyrillic.identbodychars
        )("cyrillic*")
        thai_identifier = pp.Word(ppu.Thai.identchars, ppu.Thai.identbodychars)("thai*")
        idents = (
            latin_identifier
            | japanese_identifier
            | cjk_identifier  # must follow japanese_identifier, since CJK is superset
            | thai_identifier
            | greek_identifier
            | cyrillic_identifier
        )

        result = idents[...].parseString(
            "abc_100 кириллицаx_10 日本語f_300 ไทยg_600 def_200 漢字y_300 한국어_中文c_400 Ελληνικάb_500"
        )
        self.assertParseResultsEquals(
            result,
            [
                "abc_100",
                "кириллицаx_10",
                "日本語f_300",
                "ไทยg_600",
                "def_200",
                "漢字y_300",
                "한국어_中文c_400",
                "Ελληνικάb_500",
            ],
            {
                "cjk": ["한국어_中文c_400"],
                "cyrillic": ["кириллицаx_10"],
                "greek": ["Ελληνικάb_500"],
                "japanese": ["日本語f_300", "漢字y_300"],
                "latin": ["abc_100", "def_200"],
                "thai": ["ไทยg_600"],
            },
        )

    def testChainedTernaryOperator(self):
        TERNARY_INFIX = pp.infixNotation(
            ppc.integer, [(("?", ":"), 3, pp.opAssoc.LEFT)]
        )
        self.assertParseAndCheckList(
            TERNARY_INFIX, "1?1:0?1:0", [[1, "?", 1, ":", 0, "?", 1, ":", 0]]
        )

        TERNARY_INFIX = pp.infixNotation(
            ppc.integer, [(("?", ":"), 3, pp.opAssoc.RIGHT)]
        )
        self.assertParseAndCheckList(
            TERNARY_INFIX, "1?1:0?1:0", [[1, "?", 1, ":", [0, "?", 1, ":", 0]]]
        )

    def testOneOfWithDuplicateSymbols(self):
        # test making oneOf with duplicate symbols
        print("verify oneOf handles duplicate symbols")
        try:
            test1 = pp.oneOf("a b c d a")
        except RuntimeError:
            self.fail(
                "still have infinite loop in oneOf with duplicate symbols (string input)"
            )

        print("verify oneOf handles generator input")
        try:
            test1 = pp.oneOf(c for c in "a b c d a" if not c.isspace())
        except RuntimeError:
            self.fail(
                "still have infinite loop in oneOf with duplicate symbols (generator input)"
            )

        print("verify oneOf handles list input")
        try:
            test1 = pp.oneOf("a b c d a".split())
        except RuntimeError:
            self.fail(
                "still have infinite loop in oneOf with duplicate symbols (list input)"
            )

        print("verify oneOf handles set input")
        try:
            test1 = pp.oneOf(set("a b c d a"))
        except RuntimeError:
            self.fail(
                "still have infinite loop in oneOf with duplicate symbols (set input)"
            )

    def testOneOfWithEmptyList(self):
        """test oneOf helper function with an empty list as input"""

        tst = []
        result = pp.oneOf(tst)

        expected = True
        found = isinstance(result, pp.NoMatch)
        self.assertEqual(expected, found)

    def testOneOfWithUnexpectedInput(self):
        """test oneOf with an input that isn't a string or iterable"""

        with self.assertRaises(
            TypeError, msg="failed to warn use of integer for oneOf"
        ):
            expr = pp.oneOf(6)

    def testMatchFirstIteratesOverAllChoices(self):
        # test MatchFirst bugfix
        print("verify MatchFirst iterates properly")
        results = pp.quotedString.parseString("'this is a single quoted string'")
        self.assertTrue(
            len(results) > 0, "MatchFirst error - not iterating over all choices"
        )

    def testStreamlineOfExpressionsAfterSetName(self):
        bool_constant = pp.Literal("True") | "true" | "False" | "false"
        self.assertEqual(
            "{'True' | 'true' | 'False' | 'false'}", str(bool_constant.streamline())
        )
        bool_constant.setName("bool")
        self.assertEqual("bool", str(bool_constant.streamline()))

    def testStreamlineOfSubexpressions(self):
        # verify streamline of subexpressions
        print("verify proper streamline logic")
        compound = pp.Literal("A") + "B" + "C" + "D"
        self.assertEqual(2, len(compound.exprs), "bad test setup")
        print(compound)
        compound.streamline()
        print(compound)
        self.assertEqual(4, len(compound.exprs), "streamline not working")

    def testOptionalWithResultsNameAndNoMatch(self):
        # test for Optional with results name and no match
        print("verify Optional's do not cause match failure if have results name")
        testGrammar = pp.Literal("A") + pp.Optional("B")("gotB") + pp.Literal("C")
        try:
            testGrammar.parseString("ABC")
            testGrammar.parseString("AC")
        except pp.ParseException as pe:
            print(pe.pstr, "->", pe)
            self.fail("error in Optional matching of string %s" % pe.pstr)

    def testReturnOfFurthestException(self):
        # test return of furthest exception
        testGrammar = (
            pp.Literal("A") | (pp.Literal("B") + pp.Literal("C")) | pp.Literal("E")
        )
        try:
            testGrammar.parseString("BC")
            testGrammar.parseString("BD")
        except pp.ParseException as pe:
            print(pe.pstr, "->", pe)
            self.assertEqual("BD", pe.pstr, "wrong test string failed to parse")
            self.assertEqual(
                1, pe.loc, "error in Optional matching, pe.loc=" + str(pe.loc)
            )
            self.assertTrue(
                "found 'D'" in str(pe), "wrong alternative raised exception"
            )

    def testValidateCorrectlyDetectsInvalidLeftRecursion(self):
        # test validate
        print("verify behavior of validate()")
        if IRON_PYTHON_ENV:
            print("disable this test under IronPython")
            return

        def testValidation(grmr, gnam, isValid):
            try:
                grmr.streamline()
                grmr.validate()
                self.assertTrue(isValid, "validate() accepted invalid grammar " + gnam)
            except pp.RecursiveGrammarException as rge:
                print(grmr)
                print(rge)
                self.assertFalse(isValid, "validate() rejected valid grammar " + gnam)

        fwd = pp.Forward()
        g1 = pp.OneOrMore((pp.Literal("A") + "B" + "C") | fwd)
        g2 = ("C" + g1)[...]
        fwd <<= pp.Group(g2)
        testValidation(fwd, "fwd", isValid=True)

        fwd2 = pp.Forward()
        fwd2 <<= pp.Group("A" | fwd2)
        testValidation(fwd2, "fwd2", isValid=False)

        fwd3 = pp.Forward()
        fwd3 <<= pp.Optional("A") + fwd3
        testValidation(fwd3, "fwd3", isValid=False)

    def testGetNameBehavior(self):
        # test getName
        print("verify behavior of getName()")
        aaa = pp.Group(pp.Word("a")("A"))
        bbb = pp.Group(pp.Word("b")("B"))
        ccc = pp.Group(":" + pp.Word("c")("C"))
        g1 = "XXX" + (aaa | bbb | ccc)[...]
        teststring = "XXX b bb a bbb bbbb aa bbbbb :c bbbbbb aaa"
        names = []
        print(g1.parseString(teststring).dump())
        for t in g1.parseString(teststring):
            print(t, repr(t))
            try:
                names.append(t[0].getName())
            except Exception:
                try:
                    names.append(t.getName())
                except Exception:
                    names.append(None)
        print(teststring)
        print(names)
        self.assertEqual(
            [None, "B", "B", "A", "B", "B", "A", "B", None, "B", "A"],
            names,
            "failure in getting names for tokens",
        )

        IF, AND, BUT = map(pp.Keyword, "if and but".split())
        ident = ~(IF | AND | BUT) + pp.Word(pp.alphas)("non-key")
        scanner = pp.OneOrMore(IF | AND | BUT | ident)

        def getNameTester(s, l, t):
            print(t, t.getName())

        ident.addParseAction(getNameTester)
        scanner.parseString("lsjd sldkjf IF Saslkj AND lsdjf")

        # test ParseResults.get() method
        print("verify behavior of ParseResults.get()")
        # use sum() to merge separate groups into single ParseResults
        res = sum(g1.parseString(teststring)[1:])
        print(res.dump())
        print(res.get("A", "A not found"))
        print(res.get("D", "!D"))
        self.assertEqual(
            "aaa", res.get("A", "A not found"), "get on existing key failed"
        )
        self.assertEqual("!D", res.get("D", "!D"), "get on missing key failed")

    def testOptionalBeyondEndOfString(self):
        print("verify handling of Optional's beyond the end of string")
        testGrammar = "A" + pp.Optional("B") + pp.Optional("C") + pp.Optional("D")
        testGrammar.parseString("A")
        testGrammar.parseString("AB")

    def testCreateLiteralWithEmptyString(self):
        # test creating Literal with empty string
        print('verify non-fatal usage of Literal("")')
        with self.assertRaises(
            ValueError, msg="failed to warn use of empty string for Literal"
        ):
            e = pp.Literal("")

    def testLineMethodSpecialCaseAtStart(self):
        # test line() behavior when starting at 0 and the opening line is an \n
        print("verify correct line() behavior when first line is empty string")
        self.assertEqual(
            "",
            pp.line(0, "\nabc\ndef\n"),
            "Error in line() with empty first line in text",
        )
        txt = "\nabc\ndef\n"
        results = [pp.line(i, txt) for i in range(len(txt))]
        self.assertEqual(
            ["", "abc", "abc", "abc", "abc", "def", "def", "def", "def"],
            results,
            "Error in line() with empty first line in text",
        )
        txt = "abc\ndef\n"
        results = [pp.line(i, txt) for i in range(len(txt))]
        self.assertEqual(
            ["abc", "abc", "abc", "abc", "def", "def", "def", "def"],
            results,
            "Error in line() with non-empty first line in text",
        )

    def testRepeatedTokensWhenPackratting(self):
        # test bugfix with repeated tokens when packrat parsing enabled
        print("verify behavior with repeated tokens when packrat parsing is enabled")
        a = pp.Literal("a")
        b = pp.Literal("b")
        c = pp.Literal("c")

        abb = a + b + b
        abc = a + b + c
        aba = a + b + a
        grammar = abb | abc | aba

        self.assertEqual(
            "aba", "".join(grammar.parseString("aba")), "Packrat ABA failure!"
        )

    def testSetResultsNameWithOneOrMoreAndZeroOrMore(self):
        print("verify behavior of setResultsName with OneOrMore and ZeroOrMore")
        stmt = pp.Keyword("test")
        print(stmt[...]("tests").parseString("test test").tests)
        print(stmt[1, ...]("tests").parseString("test test").tests)
        print(pp.Optional(stmt[1, ...]("tests")).parseString("test test").tests)
        print(pp.Optional(stmt[1, ...])("tests").parseString("test test").tests)
        print(
            pp.Optional(pp.delimitedList(stmt))("tests").parseString("test,test").tests
        )
        self.assertEqual(
            2,
            len(stmt[...]("tests").parseString("test test").tests),
            "ZeroOrMore failure with setResultsName",
        )
        self.assertEqual(
            2,
            len(stmt[1, ...]("tests").parseString("test test").tests),
            "OneOrMore failure with setResultsName",
        )
        self.assertEqual(
            2,
            len(pp.Optional(stmt[1, ...]("tests")).parseString("test test").tests),
            "OneOrMore failure with setResultsName",
        )
        self.assertEqual(
            2,
            len(
                pp.Optional(pp.delimitedList(stmt))("tests")
                .parseString("test,test")
                .tests
            ),
            "delimitedList failure with setResultsName",
        )
        self.assertEqual(
            2,
            len((stmt * 2)("tests").parseString("test test").tests),
            "multiplied(1) failure with setResultsName",
        )
        self.assertEqual(
            2,
            len(stmt[..., 2]("tests").parseString("test test").tests),
            "multiplied(2) failure with setResultsName",
        )
        self.assertEqual(
            2,
            len(stmt[1, ...]("tests").parseString("test test").tests),
            "multiplied(3) failure with setResultsName",
        )
        self.assertEqual(
            2,
            len(stmt[2, ...]("tests").parseString("test test").tests),
            "multiplied(3) failure with setResultsName",
        )

    def testParseResultsReprWithResultsNames(self):
        word = pp.Word(pp.printables)("word")
        res = word[...].parseString("test blub")

        print(repr(res))
        print(res["word"])
        print(res.asDict())

        self.assertEqual(
            "ParseResults(['test', 'blub'], {'word': 'blub'})",
            repr(res),
            "incorrect repr for ParseResults with listAllMatches=False",
        )

        word = pp.Word(pp.printables)("word*")
        res = word[...].parseString("test blub")

        print(repr(res))
        print(res["word"])
        print(res.asDict())

        self.assertEqual(
            "ParseResults(['test', 'blub'], {'word': ['test', 'blub']})",
            repr(res),
            "incorrect repr for ParseResults with listAllMatches=True",
        )

    def testWarnUsingLshiftForward(self):

        print(
            "verify that using '<<' operator with a Forward raises a warning if there is a dangling '|' operator"
        )

        fwd = pp.Forward()
        print("unsafe << and |, but diag not enabled, should not warn")
        fwd << pp.Word("a") | pp.Word("b")

        pp.enable_diag(pp.Diagnostics.warn_on_match_first_with_lshift_operator)
        with self.assertWarns(
            UserWarning, msg="failed to warn of using << and | operators"
        ):
            fwd = pp.Forward()
            print("unsafe << and |, should warn")
            fwd << pp.Word("a") | pp.Word("b")

        with self.assertWarns(
            UserWarning,
            msg="failed to warn of using << and | operators (within lambda)",
        ):
            fwd = pp.Forward()
            print("unsafe << and |, should warn")
            fwd_fn = lambda expr1, expr2: fwd << expr1 | expr2
            fwd_fn(pp.Word("a"), pp.Word("b"))

        fwd = pp.Forward()
        print("safe <<= and |, should not warn")
        fwd <<= pp.Word("a") | pp.Word("b")
        c = fwd | pp.Word("c")

        print("safe << and (|), should not warn")
        with self.assertDoesNotWarn(
            "warning raised on safe use of << with Forward and MatchFirst"
        ):
            fwd = pp.Forward()
            fwd << (pp.Word("a") | pp.Word("b"))
            c = fwd | pp.Word("c")

    def testParseExpressionsWithRegex(self):
        from itertools import product

        match_empty_regex = pp.Regex(r"[a-z]*")
        match_nonempty_regex = pp.Regex(r"[a-z]+")

        parser_classes = pp.ParseExpression.__subclasses__()
        test_string = "abc def"
        expected = ["abc"]
        for expr, cls in product(
            (match_nonempty_regex, match_empty_regex), parser_classes
        ):
            print(expr, cls)
            parser = cls([expr])
            parsed_result = parser.parseString(test_string)
            print(parsed_result.dump())
            self.assertParseResultsEquals(parsed_result, expected)

        for expr, cls in product(
            (match_nonempty_regex, match_empty_regex), (pp.MatchFirst, pp.Or)
        ):
            parser = cls([expr, expr])
            print(parser)
            parsed_result = parser.parseString(test_string)
            print(parsed_result.dump())
            self.assertParseResultsEquals(parsed_result, expected)

    def testAssertParseAndCheckDict(self):
        """test assertParseAndCheckDict in test framework"""

        expr = pp.Word(pp.alphas)("item") + pp.Word(pp.nums)("qty")
        self.assertParseAndCheckDict(
            expr, "balloon 25", {"item": "balloon", "qty": "25"}
        )

        exprWithInt = pp.Word(pp.alphas)("item") + ppc.integer("qty")
        self.assertParseAndCheckDict(
            exprWithInt, "rucksack 49", {"item": "rucksack", "qty": 49}
        )

    def testOnlyOnce(self):
        """test class OnlyOnce and its reset method"""

        # use a parse action to compute the sum of the parsed integers,
        # and add it to the end
        def append_sum(tokens):
            tokens.append(sum(map(int, tokens)))

        pa = pp.OnlyOnce(append_sum)
        expr = pp.OneOrMore(pp.Word(pp.nums)).addParseAction(pa)

        result = expr.parseString("0 123 321")
        print(result.dump())
        expected = ["0", "123", "321", 444]
        self.assertParseResultsEquals(
            result, expected, msg="issue with OnlyOnce first call"
        )

        with self.assertRaisesParseException(
            msg="failed to raise exception calling OnlyOnce more than once"
        ):
            result2 = expr.parseString("1 2 3 4 5")

        pa.reset()
        result = expr.parseString("100 200 300")
        print(result.dump())
        expected = ["100", "200", "300", 600]
        self.assertParseResultsEquals(
            result, expected, msg="issue with OnlyOnce after reset"
        )

    def testGoToColumn(self):
        """tests for GoToColumn class"""

        dateExpr = pp.Regex(r"\d\d(\.\d\d){2}")("date")
        numExpr = ppc.number("num")

        sample = """\
            date                Not Important                         value    NotImportant2
            11.11.13       |    useless . useless,21 useless 2     |  14.21  | asmdakldm
            21.12.12       |    fmpaosmfpoamsp 4                   |  41     | ajfa9si90""".splitlines()

        # Column number finds match
        patt = dateExpr + pp.GoToColumn(70).ignore("|") + numExpr + pp.restOfLine

        infile = iter(sample)
        next(infile)

        expecteds = [["11.11.13", 14.21], ["21.12.12", 41]]
        for line, expected in zip(infile, expecteds):
            result = patt.parseString(line)
            print(result)

            self.assertEqual(
                expected, [result.date, result.num], msg="issue with GoToColumn"
            )

        # Column number does NOT match
        patt = dateExpr("date") + pp.GoToColumn(30) + numExpr + pp.restOfLine

        infile = iter(sample)
        next(infile)

        for line in infile:
            with self.assertRaisesParseException(
                msg="issue with GoToColumn not finding match"
            ):
                result = patt.parseString(line)

    def testExceptionExplainVariations(self):
        class Modifier:
            def modify_upper(self, tokens):
                tokens[:] = map(str.upper, tokens)

        modder = Modifier()

        # force an exception in the attached parse action
        # integer has a parse action to convert to an int;
        # this parse action should fail with a TypeError, since
        # str.upper expects a str argument, not an int
        grammar = ppc.integer().addParseAction(modder.modify_upper)

        self_testcase_name = "tests.test_unit." + type(self).__name__

        try:
            grammar.parseString("1000")
        except Exception as e:
            # extract the exception explanation
            explain_str = ParseException.explain_exception(e)
            print(explain_str)
            explain_str_lines = explain_str.splitlines()

            expected = [
                self_testcase_name,
                "pyparsing.core._WordRegex - integer",
                "tests.test_unit.Modifier",
                "pyparsing.results.ParseResults",
            ]

            # verify the list of names shown in the explain "stack"
            self.assertEqual(
                expected, explain_str_lines[-len(expected) :], msg="invalid explain str"
            )

            # check type of raised exception matches explain output
            # (actual exception text varies by Python version, and even
            # by how the exception is raised, so we can only check the
            # type name)
            exception_line = explain_str_lines[-(len(expected) + 1)]
            self.assertTrue(
                exception_line.startswith("TypeError:"),
                msg="unexpected exception line ({!r})".format(exception_line),
            )

    def testMiscellaneousExceptionBits(self):
        pp.ParserElement.verbose_stacktrace = True

        self_testcase_name = "tests.test_unit." + type(self).__name__

        # force a parsing exception - match an integer against "ABC"
        try:
            pp.Word(pp.nums).parseString("ABC")
        except pp.ParseException as pe:
            expected_str = "Expected W:(0-9), found 'ABC'  (at char 0), (line:1, col:1)"
            self.assertEqual(expected_str, str(pe), "invalid ParseException str")
            self.assertEqual(expected_str, repr(pe), "invalid ParseException repr")

            self.assertEqual(
                ">!<ABC", pe.markInputline(), "invalid default mark input line"
            )
            self.assertEqual(
                "ABC", pe.markInputline(""), "invalid mark input line with '' marker"
            )

            # test explain using depth=None, 0, 1
            depth_none_explain_str = pe.explain(depth=None)
            depth_0_explain_str = pe.explain(depth=0)
            depth_1_explain_str = pe.explain(depth=1)
            print(depth_none_explain_str)

            expr_name = "pyparsing.core._WordRegex - W:(0-9)"
            for expected_function in [self_testcase_name, expr_name]:
                self.assertTrue(
                    expected_function in depth_none_explain_str,
                    "{!r} not found in ParseException.explain()".format(
                        expected_function
                    ),
                )
                self.assertFalse(
                    expected_function in depth_0_explain_str,
                    "{!r} found in ParseException.explain(depth=0)".format(
                        expected_function
                    ),
                )

            self.assertTrue(
                expr_name in depth_1_explain_str,
                "{!r} not found in ParseException.explain()".format(expected_function),
            )
            self.assertFalse(
                self_testcase_name in depth_1_explain_str,
                "{!r} not found in ParseException.explain()".format(expected_function),
            )

    def testExpressionDefaultStrings(self):
        expr = pp.Word(pp.nums)
        print(expr)
        self.assertEqual("W:(0-9)", repr(expr))

        expr = pp.Word(pp.nums, exact=3)
        print(expr)
        self.assertEqual("W:(0-9){3}", repr(expr))

        expr = pp.Word(pp.nums, min=2)
        print(expr)
        self.assertEqual("W:(0-9){2,...}", repr(expr))

        expr = pp.Word(pp.nums, max=3)
        print(expr)
        self.assertEqual("W:(0-9){1,3}", repr(expr))

        expr = pp.Word(pp.nums, min=2, max=3)
        print(expr)
        self.assertEqual("W:(0-9){2,3}", repr(expr))

        expr = pp.Char(pp.nums)
        print(expr)
        self.assertEqual("(0-9)", repr(expr))

    def testEmptyExpressionsAreHandledProperly(self):
        from pyparsing.diagram import to_railroad

        for cls in (pp.And, pp.Or, pp.MatchFirst, pp.Each):
            print("testing empty", cls.__name__)
            expr = cls([])
            expr.streamline()
            to_railroad(expr)


class Test03_EnablePackratParsing(TestCase):
    def runTest(self):
        Test02_WithoutPackrat.suite_context.restore()

        ParserElement.enablePackrat()

        # SAVE A NEW SUITE CONTEXT
        Test02_WithoutPackrat.suite_context = ppt.reset_pyparsing_context().save()


class Test04_WithPackrat(Test02_WithoutPackrat):
    """
    rerun Test2 tests, now that packrat is enabled
    """

    def test000_assert_packrat_status(self):
        print("Packrat enabled:", ParserElement._packratEnabled)
        print(
            "Packrat cache:",
            type(ParserElement.packrat_cache).__name__,
            getattr(ParserElement.packrat_cache, "size", "- no size attribute -"),
        )
        self.assertTrue(ParserElement._packratEnabled, "packrat not enabled")
        self.assertEqual(
            "_FifoCache",
            type(ParserElement.packrat_cache).__name__,
            msg="incorrect cache type",
        )


class Test05_EnableBoundedPackratParsing(TestCase):
    def runTest(self):
        Test02_WithoutPackrat.suite_context = Test02_WithoutPackrat.save_suite_context
        Test02_WithoutPackrat.suite_context.restore()

        ParserElement.enablePackrat(cache_size_limit=16)

        # SAVE A NEW SUITE CONTEXT
        Test02_WithoutPackrat.suite_context = ppt.reset_pyparsing_context().save()


class Test06_WithBoundedPackrat(Test02_WithoutPackrat):
    """
    rerun Test2 tests, now with bounded packrat cache
    """

    def test000_assert_packrat_status(self):
        print("Packrat enabled:", ParserElement._packratEnabled)
        print(
            "Packrat cache:",
            type(ParserElement.packrat_cache).__name__,
            getattr(ParserElement.packrat_cache, "size", "- no size attribute -"),
        )
        self.assertTrue(ParserElement._packratEnabled, "packrat not enabled")
        self.assertEqual(
            "_FifoCache",
            type(ParserElement.packrat_cache).__name__,
            msg="incorrect cache type",
        )


class Test07_EnableUnboundedPackratParsing(TestCase):
    def runTest(self):
        Test02_WithoutPackrat.suite_context = Test02_WithoutPackrat.save_suite_context
        Test02_WithoutPackrat.suite_context.restore()

        ParserElement.enablePackrat(cache_size_limit=None)

        # SAVE A NEW SUITE CONTEXT
        Test02_WithoutPackrat.suite_context = ppt.reset_pyparsing_context().save()


class Test08_WithUnboundedPackrat(Test02_WithoutPackrat):
    """
    rerun Test2 tests, now with unbounded packrat cache
    """

    def test000_assert_packrat_status(self):
        print("Packrat enabled:", ParserElement._packratEnabled)
        print(
            "Packrat cache:",
            type(ParserElement.packrat_cache).__name__,
            getattr(ParserElement.packrat_cache, "size", "- no size attribute -"),
        )
        self.assertTrue(ParserElement._packratEnabled, "packrat not enabled")
        self.assertEqual(
            "_UnboundedCache",
            type(ParserElement.packrat_cache).__name__,
            msg="incorrect cache type",
        )


class Test09_WithLeftRecursionParsing(Test02_WithoutPackrat):
    """
    rerun Test2 tests, now with unbounded left recursion cache
    """

    def setUp(self):
        ParserElement.enable_left_recursion(force=True)

    def tearDown(self):
        default_suite_context.restore()

    def test000_assert_packrat_status(self):
        print("Left-Recursion enabled:", ParserElement._left_recursion_enabled)
        self.assertTrue(
            ParserElement._left_recursion_enabled, "left recursion not enabled"
        )
        self.assertIsInstance(ParserElement.recursion_memos, pp.util.UnboundedMemo)


class Test10_WithLeftRecursionParsingBoundedMemo(Test02_WithoutPackrat):
    """
    rerun Test2 tests, now with bounded left recursion cache
    """

    def setUp(self):
        ParserElement.enable_left_recursion(cache_size_limit=4, force=True)

    def tearDown(self):
        default_suite_context.restore()

    def test000_assert_packrat_status(self):
        print("Left-Recursion enabled:", ParserElement._left_recursion_enabled)
        self.assertTrue(
            ParserElement._left_recursion_enabled, "left recursion not enabled"
        )
        self.assertIsInstance(ParserElement.recursion_memos, pp.util.LRUMemo)
        # check that the cache matches roughly what we expect
        # – it may be larger due to action handling
        self.assertLessEqual(ParserElement.recursion_memos._capacity, 4)
        self.assertGreater(ParserElement.recursion_memos._capacity * 3, 4)


class Test11_LR1_Recursion(ppt.TestParseResultsAsserts, TestCase):
    """
    Tests for recursive parsing
    """

    suite_context = None
    save_suite_context = None

    def setUp(self):
        recursion_suite_context.restore()

    def tearDown(self):
        default_suite_context.restore()

    def test_repeat_as_recurse(self):
        """repetition rules formulated with recursion"""
        one_or_more = pp.Forward().setName("one_or_more")
        one_or_more <<= one_or_more + "a" | "a"
        self.assertParseResultsEquals(one_or_more.parseString("a"), expected_list=["a"])
        self.assertParseResultsEquals(
            one_or_more.parseString("aaa aa"), expected_list=["a", "a", "a", "a", "a"]
        )
        delimited_list = pp.Forward().setName("delimited_list")
        delimited_list <<= delimited_list + pp.Suppress(",") + "b" | "b"
        self.assertParseResultsEquals(
            delimited_list.parseString("b"), expected_list=["b"]
        )
        self.assertParseResultsEquals(
            delimited_list.parseString("b,b"), expected_list=["b", "b"]
        )
        self.assertParseResultsEquals(
            delimited_list.parseString("b,b , b, b,b"),
            expected_list=["b", "b", "b", "b", "b"],
        )

    def test_binary_recursive(self):
        """parsing of single left-recursive binary operator"""
        expr = pp.Forward().setName("expr")
        num = pp.Word(pp.nums)
        expr <<= expr + "+" - num | num
        self.assertParseResultsEquals(
            expr.parseString("1+2"), expected_list=["1", "+", "2"]
        )
        self.assertParseResultsEquals(
            expr.parseString("1+2+3+4"),
            expected_list=["1", "+", "2", "+", "3", "+", "4"],
        )

    def test_binary_associative(self):
        """associative is preserved for single left-recursive binary operator"""
        expr = pp.Forward().setName("expr")
        num = pp.Word(pp.nums)
        expr <<= pp.Group(expr) + "+" - num | num
        self.assertParseResultsEquals(
            expr.parseString("1+2"), expected_list=[["1"], "+", "2"]
        )
        self.assertParseResultsEquals(
            expr.parseString("1+2+3+4"),
            expected_list=[[[["1"], "+", "2"], "+", "3"], "+", "4"],
        )

    def test_add_sub(self):
        """indirectly left-recursive/associative add/sub calculator"""
        expr = pp.Forward().setName("expr")
        num = pp.Word(pp.nums).setParseAction(lambda t: int(t[0]))
        expr <<= (
            (expr + "+" - num).setParseAction(lambda t: t[0] + t[2])
            | (expr + "-" - num).setParseAction(lambda t: t[0] - t[2])
            | num
        )
        self.assertEqual(expr.parseString("1+2")[0], 3)
        self.assertEqual(expr.parseString("1+2+3")[0], 6)
        self.assertEqual(expr.parseString("1+2-3")[0], 0)
        self.assertEqual(expr.parseString("1-2+3")[0], 2)
        self.assertEqual(expr.parseString("1-2-3")[0], -4)

    def test_math(self):
        """precedence climbing parser for math"""
        # named references
        expr = pp.Forward().setName("expr")
        add_sub = pp.Forward().setName("add_sub")
        mul_div = pp.Forward().setName("mul_div")
        power = pp.Forward().setName("power")
        terminal = pp.Forward().setName("terminal")
        # concrete rules
        number = pp.Word(pp.nums).setParseAction(lambda t: int(t[0]))
        signed = ("+" - expr) | ("-" - expr).setParseAction(lambda t: -t[1])
        group = pp.Suppress("(") - expr - pp.Suppress(")")
        add_sub <<= (
            (add_sub + "+" - mul_div).setParseAction(lambda t: t[0] + t[2])
            | (add_sub + "-" - mul_div).setParseAction(lambda t: t[0] - t[2])
            | mul_div
        )
        mul_div <<= (
            (mul_div + "*" - power).setParseAction(lambda t: t[0] * t[2])
            | (mul_div + "/" - power).setParseAction(lambda t: t[0] / t[2])
            | power
        )
        power <<= (terminal + "^" - power).setParseAction(
            lambda t: t[0] ** t[2]
        ) | terminal
        terminal <<= number | signed | group
        expr <<= add_sub
        # simple add_sub expressions
        self.assertEqual(expr.parseString("1+2")[0], 3)
        self.assertEqual(expr.parseString("1+2+3")[0], 6)
        self.assertEqual(expr.parseString("1+2-3")[0], 0)
        self.assertEqual(expr.parseString("1-2+3")[0], 2)
        self.assertEqual(expr.parseString("1-2-3")[0], -4)
        # precedence overwriting via parentheses
        self.assertEqual(expr.parseString("1+(2+3)")[0], 6)
        self.assertEqual(expr.parseString("1+(2-3)")[0], 0)
        self.assertEqual(expr.parseString("1-(2+3)")[0], -4)
        self.assertEqual(expr.parseString("1-(2-3)")[0], 2)
        # complicated math expressions – same as Python expressions
        self.assertEqual(expr.parseString("1----3")[0], 1 - ---3)
        self.assertEqual(expr.parseString("1+2*3")[0], 1 + 2 * 3)
        self.assertEqual(expr.parseString("1*2+3")[0], 1 * 2 + 3)
        self.assertEqual(expr.parseString("1*2^3")[0], 1 * 2 ** 3)
        self.assertEqual(expr.parseString("4^3^2^1")[0], 4 ** 3 ** 2 ** 1)

    def test_terminate_empty(self):
        """Recursion with ``Empty`` terminates"""
        empty = pp.Forward().setName("e")
        empty <<= empty + pp.Empty() | pp.Empty()
        self.assertParseResultsEquals(empty.parseString(""), expected_list=[])

    def test_non_peg(self):
        """Recursion works for non-PEG operators"""
        expr = pp.Forward().setName("expr")
        expr <<= expr + "a" ^ expr + "ab" ^ expr + "abc" ^ "."
        self.assertParseResultsEquals(
            expr.parseString(".abcabaabc"), expected_list=[".", "abc", "ab", "a", "abc"]
        )


# force clear of packrat parsing flags before saving contexts
pp.ParserElement._packratEnabled = False
pp.ParserElement._parse = pp.ParserElement._parseNoCache

Test02_WithoutPackrat.suite_context = ppt.reset_pyparsing_context().save()
Test02_WithoutPackrat.save_suite_context = ppt.reset_pyparsing_context().save()

default_suite_context = ppt.reset_pyparsing_context().save()
pp.ParserElement.enable_left_recursion()
recursion_suite_context = ppt.reset_pyparsing_context().save()
default_suite_context.restore()
