# -*- coding: utf-8 -*-
#
# unitTests.py
#
# Unit tests for pyparsing module
#
# Copyright 2002-2019, Paul McGuire
#
#
from unittest import TestCase, TestSuite, TextTestRunner
import datetime
from pyparsing import ParseException
import pyparsing as pp
ppt = pp.pyparsing_test
import sys
from io import StringIO


# see which Python implementation we are running
CPYTHON_ENV = (sys.platform == "win32")
IRON_PYTHON_ENV = (sys.platform == "cli")
JYTHON_ENV = sys.platform.startswith("java")

TEST_USING_PACKRAT = True
#~ TEST_USING_PACKRAT = False

VERBOSE = True

# simple utility for flattening nested lists
def flatten(L):
    if type(L) is not list: return [L]
    if L == []: return L
    return flatten(L[0]) + flatten(L[1:])

"""
class ParseTest(TestCase):
    def setUp(self):
        pass

    def runTest(self):
        self.assertTrue(1==1, "we've got bigger problems...")

    def tearDown(self):
        pass
"""

class resetting(object):
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

BUFFER_OUTPUT = True

class ParseTestCase(ppt.ParseResultsAsserts, TestCase):
    def __init__(self):
        super().__init__(methodName='_runTest')

    def _runTest(self):

        buffered_stdout = StringIO()

        try:
            with resetting(sys, 'stdout', 'stderr'):
                try:
                    if BUFFER_OUTPUT:
                        sys.stdout = buffered_stdout
                        sys.stderr = buffered_stdout
                    print(">>>> Starting test", str(self))
                    with ppt.reset_pyparsing_context():
                        self.runTest()

                finally:
                    print("<<<< End of test", str(self))
                    print()

        except Exception as exc:
            if BUFFER_OUTPUT:
                print()
                print(buffered_stdout.getvalue())
            raise

    def runTest(self):
        pass

    def __str__(self):
        return self.__class__.__name__

class PyparsingTestInit(ParseTestCase):
    def setUp(self):
        from pyparsing import __version__ as pyparsingVersion, __versionTime__ as pyparsingVersionTime
        print("Beginning test of pyparsing, version", pyparsingVersion, pyparsingVersionTime)
        print("Python version", sys.version)
    def tearDown(self):
        pass


class UpdateDefaultWhitespaceTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp

        prev_default_whitespace_chars = pp.ParserElement.DEFAULT_WHITE_CHARS
        try:
            pp.dblQuotedString.copyDefaultWhiteChars = False
            pp.ParserElement.setDefaultWhitespaceChars(" \t")
            self.assertEqual(set(pp.sglQuotedString.whiteChars), set(" \t"),
                             "setDefaultWhitespaceChars did not update sglQuotedString")
            self.assertEqual(set(pp.dblQuotedString.whiteChars), set(prev_default_whitespace_chars),
                             "setDefaultWhitespaceChars updated dblQuotedString but should not")
        finally:
            pp.dblQuotedString.copyDefaultWhiteChars = True
            pp.ParserElement.setDefaultWhitespaceChars(prev_default_whitespace_chars)

            self.assertEqual(set(pp.dblQuotedString.whiteChars), set(prev_default_whitespace_chars),
                             "setDefaultWhitespaceChars updated dblQuotedString")

        try:
            pp.ParserElement.setDefaultWhitespaceChars(" \t")
            self.assertNotEqual(set(pp.dblQuotedString.whiteChars), set(prev_default_whitespace_chars),
                                "setDefaultWhitespaceChars updated dblQuotedString but should not")

            EOL = pp.LineEnd().suppress().setName("EOL")

            # Identifiers is a string + optional $
            identifier = pp.Combine(pp.Word(pp.alphas) + pp.Optional("$"))

            # Literals (number or double quoted string)
            literal = pp.pyparsing_common.number | pp.dblQuotedString
            expression = literal | identifier
            # expression.setName("expression").setDebug()
            # pp.pyparsing_common.number.setDebug()
            # pp.pyparsing_common.integer.setDebug()

            line_number = pp.pyparsing_common.integer

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
            self.assertEqual(len(parsed_program), 3, "failed to apply new whitespace chars to existing builtins")

        finally:
            pp.ParserElement.setDefaultWhitespaceChars(prev_default_whitespace_chars)

class UpdateDefaultWhitespace2Test(ParseTestCase):
    def runTest(self):
        import pyparsing as pp
        ppc = pp.pyparsing_common

        prev_default_whitespace_chars = pp.ParserElement.DEFAULT_WHITE_CHARS
        try:
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
                test_string = '\n'.join([test_str]*3)
                result = parser.parseString(test_string, parseAll=True)
                print(result.dump())
                self.assertEqual(len(result), 1, "failed {!r}".format(test_string))

            pp.ParserElement.setDefaultWhitespaceChars(" \t")

            for expr, test_str in expr_tests:
                parser = pp.Group(expr[1, ...] + pp.Optional(NL))[1, ...]
                test_string = '\n'.join([test_str]*3)
                result = parser.parseString(test_string, parseAll=True)
                print(result.dump())
                self.assertEqual(len(result), 3, "failed {!r}".format(test_string))

            pp.ParserElement.setDefaultWhitespaceChars(" \n\t")

            for expr, test_str in expr_tests:
                parser = pp.Group(expr[1, ...] + pp.Optional(NL))[1, ...]
                test_string = '\n'.join([test_str]*3)
                result = parser.parseString(test_string, parseAll=True)
                print(result.dump())
                self.assertEqual(len(result), 1, "failed {!r}".format(test_string))

        finally:
            pp.ParserElement.setDefaultWhitespaceChars(prev_default_whitespace_chars)

class ParseFourFnTest(ParseTestCase):
    def runTest(self):
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
                self.assertTrue(resultValue == ans, "failed to evaluate %s, got %f" % (s, resultValue))
                print(s, "->", resultValue)

        test("9", 9)
        test("-9", -9)
        test("--9", 9)
        test("-E", -math.e)
        test("9 + 3 + 6", 9 + 3 + 6)
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
        test("6.02E23 * 8.048", 6.02E23 * 8.048)
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

class ParseSQLTest(ParseTestCase):
    def runTest(self):
        import examples.simpleSQL as simpleSQL

        def test(s, numToks, errloc=-1):
            try:
                sqlToks = flatten(simpleSQL.simpleSQL.parseString(s).asList())
                print(s, sqlToks, len(sqlToks))
                self.assertEqual(len(sqlToks), numToks,
                                 "invalid parsed tokens, expected {}, found {} ({})".format(numToks,
                                                                                            len(sqlToks),
                                                                                            sqlToks))
            except ParseException as e:
                if errloc >= 0:
                    self.assertEqual(e.loc, errloc, "expected error at {}, found at {}".format(errloc, e.loc))

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
        test("Select A from Sys.dual where a in ('RED','GREEN','BLUE') and b in (10,20,30)", 20)
        test("Select A,b from table1,table2 where table1.id eq table2.id -- test out comparison operators", 10)

class ParseConfigFileTest(ParseTestCase):
    def runTest(self):
        from examples import configParse

        def test(fnam, numToks, resCheckList):
            print("Parsing", fnam, "...", end=' ')
            with open(fnam) as infile:
                iniFileLines = "\n".join(infile.read().splitlines())
            iniData = configParse.inifile_BNF().parseString(iniFileLines)
            print(len(flatten(iniData.asList())))
            print(list(iniData.keys()))
            self.assertEqual(len(flatten(iniData.asList())), numToks, "file %s not parsed correctly" % fnam)
            for chk in resCheckList:
                var = iniData
                for attr in chk[0].split('.'):
                    var = getattr(var, attr)
                print(chk[0], var, chk[1])
                self.assertEqual(var, chk[1],
                                 "ParseConfigFileTest: failed to parse ini {!r} as expected {}, found {}".format(chk[0],
                                                                                                                 chk[1],
                                                                                                                 var))
            print("OK")

        test("test/karthik.ini", 23,
                [ ("users.K", "8"),
                  ("users.mod_scheme", "'QPSK'"),
                  ("users.Na", "K+2") ]
                 )
        test("examples/Setup.ini", 125,
                [ ("Startup.audioinf", "M3i"),
                  ("Languages.key1", "0x0003"),
                  ("test.foo", "bar") ])

class ParseJSONDataTest(ParseTestCase):
    def runTest(self):
        from examples.jsonParser import jsonObject
        from test.jsonParserTests import test1, test2, test3, test4, test5

        expected = [
            [['glossary',
             [['title', 'example glossary'],
              ['GlossDiv',
               [['title', 'S'],
                ['GlossList',
                 [[['ID', 'SGML'],
                   ['SortAs', 'SGML'],
                   ['GlossTerm', 'Standard Generalized Markup Language'],
                   ['Acronym', 'SGML'],
                   ['LargestPrimeLessThan100', 97],
                   ['AvogadroNumber', 6.02e+23],
                   ['EvenPrimesGreaterThan2', None],
                   ['PrimesLessThan10', [2, 3, 5, 7]],
                   ['WMDsFound', False],
                   ['IraqAlQaedaConnections', None],
                   ['Abbrev', 'ISO 8879:1986'],
                   ['GlossDef',
                    'A meta-markup language, used to create markup languages such as '
                    'DocBook.'],
                   ['GlossSeeAlso', ['GML', 'XML', 'markup']],
                   ['EmptyDict', []],
                   ['EmptyList', [[]]]]]]]]]
             ]]
            ,
            [['menu',
             [['id', 'file'],
              ['value', 'File:'],
              ['popup',
               [['menuitem',
                 [[['value', 'New'], ['onclick', 'CreateNewDoc()']],
                  [['value', 'Open'], ['onclick', 'OpenDoc()']],
                  [['value', 'Close'], ['onclick', 'CloseDoc()']]]]]]]]]
            ,
            [['widget',
             [['debug', 'on'],
              ['window',
               [['title', 'Sample Konfabulator Widget'],
                ['name', 'main_window'],
                ['width', 500],
                ['height', 500]]],
              ['image',
               [['src', 'Images/Sun.png'],
                ['name', 'sun1'],
                ['hOffset', 250],
                ['vOffset', 250],
                ['alignment', 'center']]],
              ['text',
               [['data', 'Click Here'],
                ['size', 36],
                ['style', 'bold'],
                ['name', 'text1'],
                ['hOffset', 250],
                ['vOffset', 100],
                ['alignment', 'center'],
                ['onMouseUp', 'sun1.opacity = (sun1.opacity / 100) * 90;']]]]]]
            ,
            [['web-app',
             [['servlet',
               [[['servlet-name', 'cofaxCDS'],
                 ['servlet-class', 'org.cofax.cds.CDSServlet'],
                 ['init-param',
                  [['configGlossary:installationAt', 'Philadelphia, PA'],
                   ['configGlossary:adminEmail', 'ksm@pobox.com'],
                   ['configGlossary:poweredBy', 'Cofax'],
                   ['configGlossary:poweredByIcon', '/images/cofax.gif'],
                   ['configGlossary:staticPath', '/content/static'],
                   ['templateProcessorClass', 'org.cofax.WysiwygTemplate'],
                   ['templateLoaderClass', 'org.cofax.FilesTemplateLoader'],
                   ['templatePath', 'templates'],
                   ['templateOverridePath', ''],
                   ['defaultListTemplate', 'listTemplate.htm'],
                   ['defaultFileTemplate', 'articleTemplate.htm'],
                   ['useJSP', False],
                   ['jspListTemplate', 'listTemplate.jsp'],
                   ['jspFileTemplate', 'articleTemplate.jsp'],
                   ['cachePackageTagsTrack', 200],
                   ['cachePackageTagsStore', 200],
                   ['cachePackageTagsRefresh', 60],
                   ['cacheTemplatesTrack', 100],
                   ['cacheTemplatesStore', 50],
                   ['cacheTemplatesRefresh', 15],
                   ['cachePagesTrack', 200],
                   ['cachePagesStore', 100],
                   ['cachePagesRefresh', 10],
                   ['cachePagesDirtyRead', 10],
                   ['searchEngineListTemplate', 'forSearchEnginesList.htm'],
                   ['searchEngineFileTemplate', 'forSearchEngines.htm'],
                   ['searchEngineRobotsDb', 'WEB-INF/robots.db'],
                   ['useDataStore', True],
                   ['dataStoreClass', 'org.cofax.SqlDataStore'],
                   ['redirectionClass', 'org.cofax.SqlRedirection'],
                   ['dataStoreName', 'cofax'],
                   ['dataStoreDriver', 'com.microsoft.jdbc.sqlserver.SQLServerDriver'],
                   ['dataStoreUrl',
                    'jdbc:microsoft:sqlserver://LOCALHOST:1433;DatabaseName=goon'],
                   ['dataStoreUser', 'sa'],
                   ['dataStorePassword', 'dataStoreTestQuery'],
                   ['dataStoreTestQuery', "SET NOCOUNT ON;select test='test';"],
                   ['dataStoreLogFile', '/usr/local/tomcat/logs/datastore.log'],
                   ['dataStoreInitConns', 10],
                   ['dataStoreMaxConns', 100],
                   ['dataStoreConnUsageLimit', 100],
                   ['dataStoreLogLevel', 'debug'],
                   ['maxUrlLength', 500]]]],
                [['servlet-name', 'cofaxEmail'],
                 ['servlet-class', 'org.cofax.cds.EmailServlet'],
                 ['init-param', [['mailHost', 'mail1'], ['mailHostOverride', 'mail2']]]],
                [['servlet-name', 'cofaxAdmin'],
                 ['servlet-class', 'org.cofax.cds.AdminServlet']],
                [['servlet-name', 'fileServlet'],
                 ['servlet-class', 'org.cofax.cds.FileServlet']],
                [['servlet-name', 'cofaxTools'],
                 ['servlet-class', 'org.cofax.cms.CofaxToolsServlet'],
                 ['init-param',
                  [['templatePath', 'toolstemplates/'],
                   ['log', 1],
                   ['logLocation', '/usr/local/tomcat/logs/CofaxTools.log'],
                   ['logMaxSize', ''],
                   ['dataLog', 1],
                   ['dataLogLocation', '/usr/local/tomcat/logs/dataLog.log'],
                   ['dataLogMaxSize', ''],
                   ['removePageCache', '/content/admin/remove?cache=pages&id='],
                   ['removeTemplateCache', '/content/admin/remove?cache=templates&id='],
                   ['fileTransferFolder',
                    '/usr/local/tomcat/webapps/content/fileTransferFolder'],
                   ['lookInContext', 1],
                   ['adminGroupID', 4],
                   ['betaServer', True]]]]]],
              ['servlet-mapping',
               [['cofaxCDS', '/'],
                ['cofaxEmail', '/cofaxutil/aemail/*'],
                ['cofaxAdmin', '/admin/*'],
                ['fileServlet', '/static/*'],
                ['cofaxTools', '/tools/*']]],
              ['taglib',
               [['taglib-uri', 'cofax.tld'],
                ['taglib-location', '/WEB-INF/tlds/cofax.tld']]]]]]
            ,
            [['menu',
              [['header', 'SVG Viewer'],
               ['items',
                [[['id', 'Open']],
                 [['id', 'OpenNew'], ['label', 'Open New']],
                 None,
                 [['id', 'ZoomIn'], ['label', 'Zoom In']],
                 [['id', 'ZoomOut'], ['label', 'Zoom Out']],
                 [['id', 'OriginalView'], ['label', 'Original View']],
                 None,
                 [['id', 'Quality']],
                 [['id', 'Pause']],
                 [['id', 'Mute']],
                 None,
                 [['id', 'Find'], ['label', 'Find...']],
                 [['id', 'FindAgain'], ['label', 'Find Again']],
                 [['id', 'Copy']],
                 [['id', 'CopyAgain'], ['label', 'Copy Again']],
                 [['id', 'CopySVG'], ['label', 'Copy SVG']],
                 [['id', 'ViewSVG'], ['label', 'View SVG']],
                 [['id', 'ViewSource'], ['label', 'View Source']],
                 [['id', 'SaveAs'], ['label', 'Save As']],
                 None,
                 [['id', 'Help']],
                 [['id', 'About'], ['label', 'About Adobe CVG Viewer...']]]]]]]
            ,
            ]

        for t, exp in zip((test1, test2, test3, test4, test5), expected):
            result = jsonObject.parseString(t)
            result.pprint()
            self.assertEqual(result.asList(), exp, "failed test {}".format(t))

class ParseCommaSeparatedValuesTest(ParseTestCase):
    def runTest(self):
        from pyparsing import pyparsing_common as ppc

        testData = [
            "a,b,c,100.2,,3",
            "d, e, j k , m  ",
            "'Hello, World', f, g , , 5.1,x",
            "John Doe, 123 Main St., Cleveland, Ohio",
            "Jane Doe, 456 St. James St., Los Angeles , California   ",
            "",
            ]
        testVals = [
            [(3, '100.2'), (4, ''), (5, '3')],
            [(2, 'j k'), (3, 'm')],
            [(0, "'Hello, World'"), (2, 'g'), (3, '')],
            [(0, 'John Doe'), (1, '123 Main St.'), (2, 'Cleveland'), (3, 'Ohio')],
            [(0, 'Jane Doe'), (1, '456 St. James St.'), (2, 'Los Angeles'), (3, 'California')]
            ]
        for line, tests in zip(testData, testVals):
            print("Parsing: %r ->" % line, end=' ')
            results = ppc.comma_separated_list.parseString(line)
            print(results)
            for t in tests:
                if not(len(results) > t[0] and results[t[0]] == t[1]):
                    print("$$$", results.dump())
                    print("$$$", results[0])
                self.assertTrue(len(results) > t[0] and results[t[0]] == t[1],
                                "failed on %s, item %d s/b '%s', got '%s'" % (line, t[0], t[1], str(results.asList())))

class ParseEBNFTest(ParseTestCase):
    def runTest(self):
        from examples import ebnf
        from pyparsing import Word, quotedString, alphas, nums

        print('Constructing EBNF parser with pyparsing...')

        grammar = '''
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
        '''

        table = {}
        table['terminal_string'] = quotedString
        table['meta_identifier'] = Word(alphas + "_", alphas + "_" + nums)
        table['integer'] = Word(nums)

        print('Parsing EBNF grammar with EBNF parser...')
        parsers = ebnf.parse(grammar, table)
        ebnf_parser = parsers['syntax']
        print("-", "\n- ".join(parsers.keys()))
        self.assertEqual(len(list(parsers.keys())), 13, "failed to construct syntax grammar")

        print('Parsing EBNF grammar with generated EBNF parser...')
        parsed_chars = ebnf_parser.parseString(grammar)
        parsed_char_len = len(parsed_chars)

        print("],\n".join(str(parsed_chars.asList()).split("],")))
        self.assertEqual(len(flatten(parsed_chars.asList())), 98, "failed to tokenize grammar correctly")


class ParseIDLTest(ParseTestCase):
    def runTest(self):
        from examples import idlParse

        def test(strng, numToks, errloc=0):
            print(strng)
            try:
                bnf = idlParse.CORBA_IDL_BNF()
                tokens = bnf.parseString(strng)
                print("tokens = ")
                tokens.pprint()
                tokens = flatten(tokens.asList())
                print(len(tokens))
                self.assertEqual(len(tokens), numToks, "error matching IDL string, %s -> %s" % (strng, str(tokens)))
            except ParseException as err:
                print(err.line)
                print(" " * (err.column-1) + "^")
                print(err)
                self.assertEqual(numToks, 0, "unexpected ParseException while parsing %s, %s" % (strng, str(err)))
                self.assertEqual(err.loc, errloc,
                                 "expected ParseException at %d, found exception at %d" % (errloc, err.loc))

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
            """, 59
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
            """, 59
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
            """, 60
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
            """, 0, 56
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
            """, 13
            )

class ParseVerilogTest(ParseTestCase):
    def runTest(self):
        pass

class ScanStringTest(ParseTestCase):
    def runTest(self):
        from pyparsing import Word, Combine, Suppress, CharsNotIn, nums, StringEnd
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
        integer = Word(nums)
        ipAddress = Combine(integer + "." + integer + "." + integer + "." + integer)
        tdStart = Suppress("<td>")
        tdEnd = Suppress("</td>")
        timeServerPattern = (tdStart + ipAddress("ipAddr") + tdEnd
                             + tdStart + CharsNotIn("<")("loc") + tdEnd)
        servers = [srvr.ipAddr for srvr, startloc, endloc in timeServerPattern.scanString(testdata)]

        print(servers)
        self.assertEqual(servers,
                         ['129.6.15.28', '129.6.15.29', '132.163.4.101', '132.163.4.102', '132.163.4.103'],
                         "failed scanString()")

        # test for stringEnd detection in scanString
        foundStringEnds = [r for r in StringEnd().scanString("xyzzy")]
        print(foundStringEnds)
        self.assertTrue(foundStringEnds, "Failed to find StringEnd in scanString")

class QuotedStringsTest(ParseTestCase):
    def runTest(self):
        from pyparsing import sglQuotedString, dblQuotedString, quotedString, QuotedString
        testData = \
            """
                'a valid single quoted string'
                'an invalid single quoted string
                 because it spans lines'
                "a valid double quoted string"
                "an invalid double quoted string
                 because it spans lines"
            """
        print(testData)

        sglStrings = [(t[0], b, e) for (t, b, e) in sglQuotedString.scanString(testData)]
        print(sglStrings)
        self.assertTrue(len(sglStrings) == 1 and (sglStrings[0][1] == 17 and sglStrings[0][2] == 47),
                        "single quoted string failure")

        dblStrings = [(t[0], b, e) for (t, b, e) in dblQuotedString.scanString(testData)]
        print(dblStrings)
        self.assertTrue(len(dblStrings) == 1 and (dblStrings[0][1] == 154 and dblStrings[0][2] == 184),
                        "double quoted string failure")

        allStrings = [(t[0], b, e) for (t, b, e) in quotedString.scanString(testData)]
        print(allStrings)
        self.assertTrue(len(allStrings) == 2
                        and (allStrings[0][1] == 17
                             and allStrings[0][2] == 47)
                        and (allStrings[1][1] == 154
                             and allStrings[1][2] == 184),
                        "quoted string failure")

        escapedQuoteTest = \
            r"""
                'This string has an escaped (\') quote character'
                "This string has an escaped (\") quote character"
            """

        sglStrings = [(t[0], b, e) for (t, b, e) in sglQuotedString.scanString(escapedQuoteTest)]
        print(sglStrings)
        self.assertTrue(len(sglStrings) == 1 and (sglStrings[0][1] == 17 and sglStrings[0][2] == 66),
                        "single quoted string escaped quote failure (%s)" % str(sglStrings[0]))

        dblStrings = [(t[0], b, e) for (t, b, e) in dblQuotedString.scanString(escapedQuoteTest)]
        print(dblStrings)
        self.assertTrue(len(dblStrings) == 1 and (dblStrings[0][1] == 83 and dblStrings[0][2] == 132),
                        "double quoted string escaped quote failure (%s)" % str(dblStrings[0]))

        allStrings = [(t[0], b, e) for (t, b, e) in quotedString.scanString(escapedQuoteTest)]
        print(allStrings)
        self.assertTrue(len(allStrings) == 2
                        and (allStrings[0][1] == 17
                             and allStrings[0][2] == 66
                             and allStrings[1][1] == 83
                             and allStrings[1][2] == 132),
                        "quoted string escaped quote failure (%s)" % ([str(s[0]) for s in allStrings]))

        dblQuoteTest = \
            r"""
                'This string has an doubled ('') quote character'
                "This string has an doubled ("") quote character"
            """
        sglStrings = [(t[0], b, e) for (t, b, e) in sglQuotedString.scanString(dblQuoteTest)]
        print(sglStrings)
        self.assertTrue(len(sglStrings) == 1 and (sglStrings[0][1] == 17 and sglStrings[0][2] == 66),
                        "single quoted string escaped quote failure (%s)" % str(sglStrings[0]))
        dblStrings = [(t[0], b, e) for (t, b, e) in dblQuotedString.scanString(dblQuoteTest)]
        print(dblStrings)
        self.assertTrue(len(dblStrings) == 1 and (dblStrings[0][1] == 83 and dblStrings[0][2] == 132),
                        "double quoted string escaped quote failure (%s)" % str(dblStrings[0]))
        allStrings = [(t[0], b, e) for (t, b, e) in quotedString.scanString(dblQuoteTest)]
        print(allStrings)
        self.assertTrue(len(allStrings) == 2
                        and (allStrings[0][1] == 17
                             and allStrings[0][2] == 66
                             and allStrings[1][1] == 83
                             and allStrings[1][2] == 132),
                        "quoted string escaped quote failure (%s)" % ([str(s[0]) for s in allStrings]))

        print("testing catastrophic RE backtracking in implementation of dblQuotedString")
        for expr, test_string in [
            (dblQuotedString, '"' + '\\xff' * 500),
            (sglQuotedString, "'" + '\\xff' * 500),
            (quotedString, '"' + '\\xff' * 500),
            (quotedString, "'" + '\\xff' * 500),
            (QuotedString('"'), '"' + '\\xff' * 500),
            (QuotedString("'"), "'" + '\\xff' * 500),
            ]:
            expr.parseString(test_string + test_string[0])
            try:
                expr.parseString(test_string)
            except Exception:
                continue

class CaselessOneOfTest(ParseTestCase):
    def runTest(self):
        from pyparsing import oneOf

        caseless1 = oneOf("d a b c aA B A C", caseless=True)
        caseless1str = str(caseless1)
        print(caseless1str)
        caseless2 = oneOf("d a b c Aa B A C", caseless=True)
        caseless2str = str(caseless2)
        print(caseless2str)
        self.assertEqual(caseless1str.upper(), caseless2str.upper(), "oneOf not handling caseless option properly")
        self.assertNotEqual(caseless1str, caseless2str, "Caseless option properly sorted")

        res = caseless1[...].parseString("AAaaAaaA")
        print(res)
        self.assertEqual(len(res), 4, "caseless1 oneOf failed")
        self.assertEqual("".join(res), "aA" * 4, "caseless1 CaselessLiteral return failed")

        res =caseless2[...].parseString("AAaaAaaA")
        print(res)
        self.assertEqual(len(res), 4, "caseless2 oneOf failed")
        self.assertEqual("".join(res), "Aa" * 4, "caseless1 CaselessLiteral return failed")


class CommentParserTest(ParseTestCase):
    def runTest(self):

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
        foundLines = [pp.lineno(s, testdata)
            for t, s, e in pp.cStyleComment.scanString(testdata)]
        self.assertEqual(foundLines, list(range(11))[2:], "only found C comments on lines " + str(foundLines))
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
        foundLines = [pp.lineno(s, testdata)
            for t, s, e in pp.htmlComment.scanString(testdata)]
        self.assertEqual(foundLines, list(range(11))[2:], "only found HTML comments on lines " + str(foundLines))

        # test C++ single line comments that have line terminated with '\' (should continue comment to following line)
        testSource = r"""
            // comment1
            // comment2 \
            still comment 2
            // comment 3
            """
        self.assertEqual(len(pp.cppStyleComment.searchString(testSource)[1][0]), 41,
                         r"failed to match single-line comment with '\' at EOL")

class ParseExpressionResultsTest(ParseTestCase):
    def runTest(self):
        from pyparsing import Word, alphas, OneOrMore, Optional, Group

        a = Word("a", alphas).setName("A")
        b = Word("b", alphas).setName("B")
        c = Word("c", alphas).setName("C")
        ab = (a + b).setName("AB")
        abc = (ab + c).setName("ABC")
        word = Word(alphas).setName("word")

        words = Group(OneOrMore(~a + word)).setName("words")

        phrase = (words("Head")
                  + Group(a + Optional(b + Optional(c)))("ABC")
                  + words("Tail"))

        results = phrase.parseString("xavier yeti alpha beta charlie will beaver")
        print(results, results.Head, results.ABC, results.Tail)
        for key, ln in [("Head", 2), ("ABC", 3), ("Tail", 2)]:
            self.assertEqual(len(results[key]), ln,
                             "expected %d elements in %s, found %s" % (ln, key, str(results[key])))


class ParseKeywordTest(ParseTestCase):
    def runTest(self):
        from pyparsing import Literal, Keyword

        kw = Keyword("if")
        lit = Literal("if")

        def test(s, litShouldPass, kwShouldPass):
            print("Test", s)
            print("Match Literal", end=' ')
            try:
                print(lit.parseString(s))
            except Exception:
                print("failed")
                if litShouldPass:
                    self.assertTrue(False, "Literal failed to match %s, should have" % s)
            else:
                if not litShouldPass:
                    self.assertTrue(False, "Literal matched %s, should not have" % s)

            print("Match Keyword", end=' ')
            try:
                print(kw.parseString(s))
            except Exception:
                print("failed")
                if kwShouldPass:
                    self.assertTrue(False, "Keyword failed to match %s, should have" % s)
            else:
                if not kwShouldPass:
                    self.assertTrue(False, "Keyword matched %s, should not have" % s)

        test("ifOnlyIfOnly", True, False)
        test("if(OnlyIfOnly)", True, True)
        test("if (OnlyIf Only)", True, True)

        kw = Keyword("if", caseless=True)

        test("IFOnlyIfOnly", False, False)
        test("If(OnlyIfOnly)", False, True)
        test("iF (OnlyIf Only)", False, True)



class ParseExpressionResultsAccumulateTest(ParseTestCase):
    def runTest(self):
        from pyparsing import Word, delimitedList, Combine, alphas, nums

        num=Word(nums).setName("num")("base10*")
        hexnum=Combine("0x"+ Word(nums)).setName("hexnum")("hex*")
        name = Word(alphas).setName("word")("word*")
        list_of_num=delimitedList(hexnum | num | name, ",")

        tokens = list_of_num.parseString('1, 0x2, 3, 0x4, aaa')
        print(tokens.dump())
        self.assertParseResultsEquals(tokens,
                                      expected_list=['1', '0x2', '3', '0x4', 'aaa'],
                                      expected_dict={'base10': ['1', '3'],
                                                    'hex': ['0x2', '0x4'],
                                                    'word': ['aaa']},
                                      )

        from pyparsing import Literal, Word, nums, Group, Dict, alphas, \
            quotedString, oneOf, delimitedList, removeQuotes, alphanums

        lbrack = Literal("(").suppress()
        rbrack = Literal(")").suppress()
        integer = Word(nums).setName("int")
        variable = Word(alphas, max=1).setName("variable")
        relation_body_item = variable | integer | quotedString.copy().setParseAction(removeQuotes)
        relation_name = Word(alphas + "_", alphanums + "_")
        relation_body = lbrack + Group(delimitedList(relation_body_item)) + rbrack
        Goal = Dict(Group(relation_name + relation_body))
        Comparison_Predicate = Group(variable + oneOf("< >") + integer)("pred*")
        Query = Goal("head") + ":-" + delimitedList(Goal | Comparison_Predicate)

        test="""Q(x,y,z):-Bloo(x,"Mitsis",y),Foo(y,z,1243),y>28,x<12,x>3"""

        queryRes = Query.parseString(test)
        print(queryRes.dump())
        self.assertParseResultsEquals(queryRes.pred,
                                      expected_list=[['y', '>', '28'], ['x', '<', '12'], ['x', '>', '3']],
                                      msg="Incorrect list for attribute pred, %s" % str(queryRes.pred.asList())
                                      )

class ReStringRangeTest(ParseTestCase):
    def runTest(self):
        testCases = (
            (r"[A-Z]"),
            (r"[A-A]"),
            (r"[A-Za-z]"),
            (r"[A-z]"),
            (r"[\ -\~]"),
            (r"[\0x20-0]"),
            (r"[\0x21-\0x7E]"),
            (r"[\0xa1-\0xfe]"),
            (r"[\040-0]"),
            (r"[A-Za-z0-9]"),
            (r"[A-Za-z0-9_]"),
            (r"[A-Za-z0-9_$]"),
            (r"[A-Za-z0-9_$\-]"),
            (r"[^0-9\\]"),
            (r"[a-zA-Z]"),
            (r"[/\^~]"),
            (r"[=\+\-!]"),
            (r"[A-]"),
            (r"[-A]"),
            (r"[\x21]"),
            (r"[а-яА-ЯёЁA-Z$_\041α-ω]")
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
            )
        for test in zip(testCases, expectedResults):
            t, exp = test
            res = pp.srange(t)
            #print(t, "->", res)
            self.assertEqual(res, exp, "srange error, srange(%r)->'%r', expected '%r'" % (t, res, exp))

class SkipToParserTests(ParseTestCase):
    def runTest(self):

        from pyparsing import Literal, SkipTo, cStyleComment, ParseBaseException, And, Word, alphas, nums, Optional, NotAny

        thingToFind = Literal('working')
        testExpr = SkipTo(Literal(';'), include=True, ignore=cStyleComment) + thingToFind

        def tryToParse (someText, fail_expected=False):
            try:
                print(testExpr.parseString(someText))
                self.assertFalse(fail_expected, "expected failure but no exception raised")
            except Exception as e:
                print("Exception %s while parsing string %s" % (e, repr(someText)))
                self.assertTrue(fail_expected and isinstance(e, ParseBaseException),
                                "Exception %s while parsing string %s" % (e, repr(someText)))

        # This first test works, as the SkipTo expression is immediately following the ignore expression (cStyleComment)
        tryToParse('some text /* comment with ; in */; working')
        # This second test previously failed, as there is text following the ignore expression, and before the SkipTo expression.
        tryToParse('some text /* comment with ; in */some other stuff; working')

        # tests for optional failOn argument
        testExpr = SkipTo(Literal(';'), include=True, ignore=cStyleComment, failOn='other') + thingToFind
        tryToParse('some text /* comment with ; in */; working')
        tryToParse('some text /* comment with ; in */some other stuff; working', fail_expected=True)

        # test that we correctly create named results
        text = "prefixDATAsuffix"
        data = Literal("DATA")
        suffix = Literal("suffix")
        expr = SkipTo(data + suffix)('prefix') + data + suffix
        result = expr.parseString(text)
        self.assertTrue(isinstance(result.prefix, str), "SkipTo created with wrong saveAsList attribute")

        from pyparsing import Literal, And, Word, alphas, nums, Optional, NotAny
        alpha_word = (~Literal("end") + Word(alphas, asKeyword=True)).setName("alpha")
        num_word = Word(nums, asKeyword=True).setName("int")

        def test(expr, test_string, expected_list, expected_dict):
            if (expected_list, expected_dict) == (None, None):
                with self.assertRaises(Exception, msg="{} failed to parse {!r}".format(expr, test_string)):
                    expr.parseString(test_string)
            else:
                result = expr.parseString(test_string)
                self.assertParseResultsEquals(result, expected_list=expected_list, expected_dict=expected_dict)

        # ellipses for SkipTo
        e = ... + Literal("end")
        test(e, "start 123 end", ['start 123 ', 'end'], {'_skipped': ['start 123 ']})

        e = Literal("start") + ... + Literal("end")
        test(e, "start 123 end", ['start', '123 ', 'end'], {'_skipped': ['123 ']})

        e = Literal("start") + ...
        test(e, "start 123 end", None, None)

        e = And(["start", ..., "end"])
        test(e, "start 123 end", ['start', '123 ', 'end'], {'_skipped': ['123 ']})

        e = And([..., "end"])
        test(e, "start 123 end", ['start 123 ', 'end'], {'_skipped': ['start 123 ']})

        e = "start" + (num_word | ...) + "end"
        test(e, "start 456 end", ['start', '456', 'end'], {})
        test(e, "start 123 456 end", ['start', '123', '456 ', 'end'], {'_skipped': ['456 ']})
        test(e, "start end", ['start', '', 'end'], {'_skipped': ['missing <int>']})

        # e = define_expr('"start" + (num_word | ...)("inner") + "end"')
        # test(e, "start 456 end", ['start', '456', 'end'], {'inner': '456'})

        e = "start" + (alpha_word[...] & num_word[...] | ...) + "end"
        test(e, "start 456 red end", ['start', '456', 'red', 'end'], {})
        test(e, "start red 456 end", ['start', 'red', '456', 'end'], {})
        test(e, "start 456 red + end", ['start', '456', 'red', '+ ', 'end'], {'_skipped': ['+ ']})
        test(e, "start red end", ['start', 'red', 'end'], {})
        test(e, "start 456 end", ['start', '456', 'end'], {})
        test(e, "start end", ['start', 'end'], {})
        test(e, "start 456 + end", ['start', '456', '+ ', 'end'], {'_skipped': ['+ ']})

        e = "start" + (alpha_word[1, ...] & num_word[1, ...] | ...) + "end"
        test(e, "start 456 red end", ['start', '456', 'red', 'end'], {})
        test(e, "start red 456 end", ['start', 'red', '456', 'end'], {})
        test(e, "start 456 red + end", ['start', '456', 'red', '+ ', 'end'], {'_skipped': ['+ ']})
        test(e, "start red end", ['start', 'red ', 'end'], {'_skipped': ['red ']})
        test(e, "start 456 end", ['start', '456 ', 'end'], {'_skipped': ['456 ']})
        test(e, "start end", ['start', '', 'end'], {'_skipped': ['missing <{{alpha}... & {int}...}>']})
        test(e, "start 456 + end", ['start', '456 + ', 'end'], {'_skipped': ['456 + ']})

        e = "start" + (alpha_word | ...) + (num_word | ...) + "end"
        test(e, "start red 456 end", ['start', 'red', '456', 'end'], {})
        test(e, "start red end", ['start', 'red', '', 'end'], {'_skipped': ['missing <int>']})
        test(e, "start end", ['start', '', '', 'end'], {'_skipped': ['missing <alpha>', 'missing <int>']})

        e = Literal("start") + ... + "+" + ... + "end"
        test(e, "start red + 456 end", ['start', 'red ', '+', '456 ', 'end'], {'_skipped': ['red ', '456 ']})

class EllipsisRepetionTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp
        import re

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

        tests = [
            "aa bb cc dd 123",
            "bb cc dd 123",
            "cc dd 123",
            "dd 123",
            "123",
        ]

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

class EllipsisRepetionWithResultsNamesTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp

        label = pp.Word(pp.alphas)
        val = pp.pyparsing_common.integer()
        parser = label('label') + pp.ZeroOrMore(val)('values')

        _, results = parser.runTests("""
            a 1
            b 1 2 3
            c
            """)
        expected = [
            (['a', 1], {'label': 'a', 'values': [1]}),
            (['b', 1, 2, 3], {'label': 'b', 'values': [1, 2, 3]}),
            (['c'], {'label': 'c', 'values': []}),
        ]
        for obs, exp in zip(results, expected):
            test, result = obs
            exp_list, exp_dict = exp
            self.assertParseResultsEquals(result, expected_list=exp_list, expected_dict=exp_dict)

        parser = label('label') + val[...]('values')

        _, results = parser.runTests("""
            a 1
            b 1 2 3
            c
            """)
        expected = [
            (['a', 1], {'label': 'a', 'values': [1]}),
            (['b', 1, 2, 3], {'label': 'b', 'values': [1, 2, 3]}),
            (['c'], {'label': 'c', 'values': []}),
        ]
        for obs, exp in zip(results, expected):
            test, result = obs
            exp_list, exp_dict = exp
            self.assertParseResultsEquals(result, expected_list=exp_list, expected_dict=exp_dict)

        pt = pp.Group(val('x') + pp.Suppress(',') + val('y'))
        parser = label('label') + pt[...]("points")
        _, results = parser.runTests("""
            a 1,1
            b 1,1 2,2 3,3
            c
            """)
        expected = [
            (['a', [1, 1]], {'label': 'a', 'points': [{'x': 1, 'y': 1}]}),
            (['b', [1, 1], [2, 2], [3, 3]], {'label': 'b', 'points': [{'x': 1, 'y': 1},
                                                                        {'x': 2, 'y': 2},
                                                                        {'x': 3, 'y': 3}]}),
            (['c'], {'label': 'c', 'points': []}),
        ]
        for obs, exp in zip(results, expected):
            test, result = obs
            exp_list, exp_dict = exp
            self.assertParseResultsEquals(result, expected_list=exp_list, expected_dict=exp_dict)


class CustomQuotesTest(ParseTestCase):
    def runTest(self):
        from pyparsing import QuotedString

        testString = r"""
            sdlfjs :sdf\:jls::djf: sl:kfsjf
            sdlfjs -sdf\:jls::--djf: sl-kfsjf
            sdlfjs -sdf\:::jls::--djf: sl:::-kfsjf
            sdlfjs ^sdf\:jls^^--djf^ sl-kfsjf
            sdlfjs ^^^==sdf\:j=lz::--djf: sl=^^=kfsjf
            sdlfjs ==sdf\:j=ls::--djf: sl==kfsjf^^^
        """
        colonQuotes = QuotedString(':', '\\', '::')
        dashQuotes  = QuotedString('-', '\\', '--')
        hatQuotes   = QuotedString('^', '\\')
        hatQuotes1  = QuotedString('^', '\\', '^^')
        dblEqQuotes = QuotedString('==', '\\')

        def test(quoteExpr, expected):
            print(quoteExpr.pattern)
            print(quoteExpr.searchString(testString))
            print(quoteExpr.searchString(testString)[0][0])
            print(expected)
            self.assertEqual(quoteExpr.searchString(testString)[0][0],
                             expected,
                             "failed to match %s, expected '%s', got '%s'" % (quoteExpr, expected,
                                                                              quoteExpr.searchString(testString)[0]))
            print()

        test(colonQuotes, r"sdf:jls:djf")
        test(dashQuotes,  r"sdf:jls::-djf: sl")
        test(hatQuotes,   r"sdf:jls")
        test(hatQuotes1,  r"sdf:jls^--djf")
        test(dblEqQuotes, r"sdf:j=ls::--djf: sl")
        test(QuotedString(':::'), 'jls::--djf: sl')
        test(QuotedString('==', endQuoteChar='--'), r'sdf\:j=lz::')
        test(QuotedString('^^^', multiline=True), r"""==sdf\:j=lz::--djf: sl=^^=kfsjf
            sdlfjs ==sdf\:j=ls::--djf: sl==kfsjf""")
        try:
            bad1 = QuotedString('', '\\')
        except SyntaxError as se:
            pass
        else:
            self.assertTrue(False, "failed to raise SyntaxError with empty quote string")

class RepeaterTest(ParseTestCase):
    def runTest(self):
        from pyparsing import matchPreviousLiteral, matchPreviousExpr, Word, nums, ParserElement

        if ParserElement._packratEnabled:
            print("skipping this test, not compatible with packratting")
            return

        first = Word("abcdef").setName("word1")
        bridge = Word(nums).setName("number")
        second = matchPreviousLiteral(first).setName("repeat(word1Literal)")

        seq = first + bridge + second

        tests = [
            ("abc12abc", True),
            ("abc12aabc", False),
            ("abc12cba", True),
            ("abc12bca", True),
        ]

        for tst, result in tests:
            found = False
            for tokens, start, end in seq.scanString(tst):
                f, b, s = tokens
                print(f, b, s)
                found = True
            if not found:
                print("No literal match in", tst)
            self.assertEqual(found, result, "Failed repeater for test: %s, matching %s" % (tst, str(seq)))
        print()

        # retest using matchPreviousExpr instead of matchPreviousLiteral
        second = matchPreviousExpr(first).setName("repeat(word1expr)")
        seq = first + bridge + second

        tests = [
            ("abc12abc", True),
            ("abc12cba", False),
            ("abc12abcdef", False),
            ]

        for tst, result in tests:
            found = False
            for tokens, start, end in seq.scanString(tst):
                print(tokens)
                found = True
            if not found:
                print("No expression match in", tst)
            self.assertEqual(found, result, "Failed repeater for test: %s, matching %s" % (tst, str(seq)))

        print()

        first = Word("abcdef").setName("word1")
        bridge = Word(nums).setName("number")
        second = matchPreviousExpr(first).setName("repeat(word1)")
        seq = first + bridge + second
        csFirst = seq.setName("word-num-word")
        csSecond = matchPreviousExpr(csFirst)
        compoundSeq = csFirst + ":" + csSecond
        compoundSeq.streamline()
        print(compoundSeq)

        tests = [
            ("abc12abc:abc12abc", True),
            ("abc12cba:abc12abc", False),
            ("abc12abc:abc12abcdef", False),
            ]

        for tst, result in tests:
            found = False
            for tokens, start, end in compoundSeq.scanString(tst):
                print("match:", tokens)
                found = True
                break
            if not found:
                print("No expression match in", tst)
            self.assertEqual(found, result, "Failed repeater for test: %s, matching %s" % (tst, str(seq)))

        print()
        eFirst = Word(nums)
        eSecond = matchPreviousExpr(eFirst)
        eSeq = eFirst + ":" + eSecond

        tests = [
            ("1:1A", True),
            ("1:10", False),
            ]

        for tst, result in tests:
            found = False
            for tokens, start, end in eSeq.scanString(tst):
                print(tokens)
                found = True
            if not found:
                print("No match in", tst)
            self.assertEqual(found, result, "Failed repeater for test: %s, matching %s" % (tst, str(seq)))

class RecursiveCombineTest(ParseTestCase):
    def runTest(self):
        from pyparsing import Forward, Word, alphas, nums, Optional, Combine

        testInput = "myc(114)r(11)dd"
        Stream=Forward()
        Stream << Optional(Word(alphas)) + Optional("(" + Word(nums) + ")" + Stream)
        expected = [''.join(Stream.parseString(testInput))]
        print(expected)

        Stream=Forward()
        Stream << Combine(Optional(Word(alphas)) + Optional("(" + Word(nums) + ")" + Stream))
        testVal = Stream.parseString(testInput)
        print(testVal)

        self.assertParseResultsEquals(testVal, expected_list=expected)

class InfixNotationGrammarTest1(ParseTestCase):
    def runTest(self):
        from pyparsing import Word, nums, alphas, Literal, oneOf, infixNotation, opAssoc
        import ast

        integer = Word(nums).setParseAction(lambda t:int(t[0]))
        variable = Word(alphas, exact=1)
        operand = integer | variable

        expop = Literal('^')
        signop = oneOf('+ -')
        multop = oneOf('* /')
        plusop = oneOf('+ -')
        factop = Literal('!')

        expr = infixNotation(operand,
            [(factop, 1, opAssoc.LEFT),
             (expop, 2, opAssoc.RIGHT),
             (signop, 1, opAssoc.RIGHT),
             (multop, 2, opAssoc.LEFT),
             (plusop, 2, opAssoc.LEFT),]
            )

        test = ["9 + 2 + 3",
                "9 + 2 * 3",
                "(9 + 2) * 3",
                "(9 + -2) * 3",
                "(9 + --2) * 3",
                "(9 + -2) * 3^2^2",
                "(9! + -2) * 3^2^2",
                "M*X + B",
                "M*(X + B)",
                "1+2*-3^4*5+-+-6",
                "3!!"]
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
                    [[3, '!', '!']]""".split('\n')
        expected = [ast.literal_eval(x.strip()) for x in expected]
        for test_str, exp_list in zip(test, expected):
            result = expr.parseString(test_str)
            print(test_str, "->", exp_list, "got", result)
            self.assertParseResultsEquals(result, expected_list=exp_list,
                                          msg="mismatched results for infixNotation: got %s, expected %s" %
                                             (result.asList(), exp_list))

class InfixNotationGrammarTest2(ParseTestCase):
    def runTest(self):

        from pyparsing import infixNotation, Word, alphas, oneOf, opAssoc

        boolVars = { "True":True, "False":False }
        class BoolOperand(object):
            reprsymbol = ''
            def __init__(self, t):
                self.args = t[0][0::2]
            def __str__(self):
                sep = " %s " % self.reprsymbol
                return "(" + sep.join(map(str, self.args)) + ")"

        class BoolAnd(BoolOperand):
            reprsymbol = '&'
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
            reprsymbol = '|'
            def __bool__(self):
                for a in self.args:
                    if isinstance(a, str):
                        v = boolVars[a]
                    else:
                        v = bool(a)
                    if v:
                        return True
                return False

        class BoolNot(BoolOperand):
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

        boolOperand = Word(alphas, max=1) | oneOf("True False")
        boolExpr = infixNotation(boolOperand,
            [
            ("not", 1, opAssoc.RIGHT, BoolNot),
            ("and", 2, opAssoc.LEFT,  BoolAnd),
            ("or",  2, opAssoc.LEFT,  BoolOr),
            ])
        test = ["p and not q",
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
            print(t, '\n', res[0], '=', bool(res[0]), '\n')
            expected = eval(t, {}, boolVars)
            self.assertEquals(expected, bool(res[0]))


class InfixNotationGrammarTest3(ParseTestCase):
    def runTest(self):

        from pyparsing import infixNotation, Word, alphas, oneOf, opAssoc, nums, Literal

        global count
        count = 0

        def evaluate_int(t):
            global count
            value = int(t[0])
            print("evaluate_int", value)
            count += 1
            return value

        integer = Word(nums).setParseAction(evaluate_int)
        variable = Word(alphas, exact=1)
        operand = integer | variable

        expop = Literal('^')
        signop = oneOf('+ -')
        multop = oneOf('* /')
        plusop = oneOf('+ -')
        factop = Literal('!')

        expr = infixNotation(operand,
            [
            ("!", 1, opAssoc.LEFT),
            ("^", 2, opAssoc.LEFT),
            (signop, 1, opAssoc.RIGHT),
            (multop, 2, opAssoc.LEFT),
            (plusop, 2, opAssoc.LEFT),
            ])

        test = ["9"]
        for t in test:
            count = 0
            print("%r => %s (count=%d)" % (t, expr.parseString(t), count))
            self.assertEqual(count, 1, "count evaluated too many times!")

class InfixNotationGrammarTest4(ParseTestCase):
    def runTest(self):

        word = pp.Word(pp.alphas)

        def supLiteral(s):
            """Returns the suppressed literal s"""
            return pp.Literal(s).suppress()

        def booleanExpr(atom):
            ops = [
                (supLiteral("!"), 1, pp.opAssoc.RIGHT, lambda s, l, t: ["!", t[0][0]]),
                (pp.oneOf("= !="), 2, pp.opAssoc.LEFT,),
                (supLiteral("&"), 2, pp.opAssoc.LEFT,  lambda s, l, t: ["&", t[0]]),
                (supLiteral("|"), 2, pp.opAssoc.LEFT,  lambda s, l, t: ["|", t[0]])]
            return pp.infixNotation(atom, ops)

        f = booleanExpr(word) + pp.StringEnd()

        tests = [
            ("bar = foo", [['bar', '=', 'foo']]),
            ("bar = foo & baz = fee", ['&', [['bar', '=', 'foo'], ['baz', '=', 'fee']]]),
            ]
        for test, expected in tests:
            print(test)
            results = f.parseString(test)
            print(results)
            self.assertParseResultsEquals(results, expected_list=expected)
            print()

class InfixNotationGrammarTest5(ParseTestCase):

    def runTest(self):
        from pyparsing import infixNotation, opAssoc, pyparsing_common as ppc, Literal, oneOf

        expop = Literal('**')
        signop = oneOf('+ -')
        multop = oneOf('* /')
        plusop = oneOf('+ -')

        class ExprNode(object):
            def __init__(self, tokens):
                self.tokens = tokens[0]

            def eval(self):
                return None

        class NumberNode(ExprNode):
            def eval(self):
                return self.tokens

        class SignOp(ExprNode):
            def eval(self):
                mult = {'+': 1, '-': -1}[self.tokens[0]]
                return mult * self.tokens[1].eval()

        class BinOp(ExprNode):
            def eval(self):
                ret = self.tokens[0].eval()
                for op, operand in zip(self.tokens[1::2], self.tokens[2::2]):
                    ret = self.opn_map[op](ret, operand.eval())
                return ret

        class ExpOp(BinOp):
            opn_map = {'**': lambda a, b: b ** a}

        class MultOp(BinOp):
            import operator
            opn_map = {'*': operator.mul, '/': operator.truediv}

        class AddOp(BinOp):
            import operator
            opn_map = {'+': operator.add, '-': operator.sub}

        operand = ppc.number().setParseAction(NumberNode)
        expr = infixNotation(operand,
                             [
                                 (expop, 2, opAssoc.LEFT, (lambda pr: [pr[0][::-1]], ExpOp)),
                                 (signop, 1, opAssoc.RIGHT, SignOp),
                                 (multop, 2, opAssoc.LEFT, MultOp),
                                 (plusop, 2, opAssoc.LEFT, AddOp),
                             ])

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
            self.assertEqual(eval_value, eval(t),
                             "Error evaluating %r, expected %r, got %r" % (t, eval(t), eval_value))


class PickleTest_Greeting():
    def __init__(self, toks):
        self.salutation = toks[0]
        self.greetee = toks[1]

    def __repr__(self):
        return "%s: {%s}" % (self.__class__.__name__,
            ', '.join('%r: %r' % (k, getattr(self, k)) for k in sorted(self.__dict__)))

class ParseResultsPickleTest(ParseTestCase):
    def runTest(self):
        from pyparsing import makeHTMLTags, ParseResults
        import pickle

        # test 1
        body = makeHTMLTags("BODY")[0]
        result = body.parseString("<BODY BGCOLOR='#00FFBB' FGCOLOR=black>")
        if VERBOSE:
            print(result.dump())
            print()

        for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
            print("Test pickle dump protocol", protocol)
            try:
                pickleString = pickle.dumps(result, protocol)
            except Exception as e:
                print("dumps exception:", e)
                newresult = ParseResults()
            else:
                newresult = pickle.loads(pickleString)
                if VERBOSE:
                    print(newresult.dump())
                    print()

            self.assertEqual(result.dump(), newresult.dump(),
                             "Error pickling ParseResults object (protocol=%d)" % protocol)

        # test 2
        import pyparsing as pp

        word = pp.Word(pp.alphas + "'.")
        salutation = pp.OneOrMore(word)
        comma = pp.Literal(",")
        greetee = pp.OneOrMore(word)
        endpunc = pp.oneOf("! ?")
        greeting = salutation + pp.Suppress(comma) + greetee + pp.Suppress(endpunc)
        greeting.setParseAction(PickleTest_Greeting)

        string = 'Good morning, Miss Crabtree!'

        result = greeting.parseString(string)

        for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
            print("Test pickle dump protocol", protocol)
            try:
                pickleString = pickle.dumps(result, protocol)
            except Exception as e:
                print("dumps exception:", e)
                newresult = ParseResults()
            else:
                newresult = pickle.loads(pickleString)
            print(newresult.dump())
            self.assertEqual(newresult.dump(), result.dump(),
                             "failed to pickle/unpickle ParseResults: expected %r, got %r" % (result, newresult))

class ParseResultsWithNamedTupleTest(ParseTestCase):
    def runTest(self):

        from pyparsing import Literal, replaceWith

        expr = Literal("A")("Achar")
        expr.setParseAction(replaceWith(tuple(["A", "Z"])))

        res = expr.parseString("A")
        print(repr(res))
        print(res.Achar)
        self.assertParseResultsEquals(res, expected_dict={'Achar': ('A', 'Z')},
                                      msg="Failed accessing named results containing a tuple, "
                                         "got {!r}".format(res.Achar))


class ParseHTMLTagsTest(ParseTestCase):
    def runTest(self):
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
            ("startBody", True,  "#00FFAA", ""),
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
                self.assertEqual(bool(t.empty), expectedEmpty,
                                 "expected %s token, got %s" % (expectedEmpty and "empty" or "not empty",
                                                                t.empty and "empty" or "not empty"))
                self.assertEqual(t.bgcolor, expectedBG,
                                 "failed to match BGCOLOR, expected %s, got %s" % (expectedBG, t.bgcolor))
                self.assertEqual(t.fgcolor, expectedFG,
                                 "failed to match FGCOLOR, expected %s, got %s" % (expectedFG, t.bgcolor))
            elif "endBody" in t:
                print("end tag")
                pass
            else:
                print("BAD!!!")


class UpcaseDowncaseUnicode(ParseTestCase):
    def runTest(self):

        import pyparsing as pp
        from pyparsing import pyparsing_unicode as ppu
        from pyparsing import pyparsing_common as ppc
        import sys

        a = '\u00bfC\u00f3mo esta usted?'
        if not JYTHON_ENV:
            ualphas = ppu.alphas
        else:
            ualphas = "".join(chr(i) for i in list(range(0xd800)) + list(range(0xe000, sys.maxunicode))
                                if chr(i).isalpha())
        uword = pp.Word(ualphas).setParseAction(ppc.upcaseTokens)

        print = lambda *args: None
        print(uword.searchString(a))

        uword = pp.Word(ualphas).setParseAction(ppc.downcaseTokens)

        print(uword.searchString(a))

        kw = pp.Keyword('mykey', caseless=True).setParseAction(ppc.upcaseTokens)('rname')
        ret = kw.parseString('mykey')
        print(ret.rname)
        self.assertEqual(ret.rname, 'MYKEY', "failed to upcase with named result (pyparsing_common)")

        kw = pp.Keyword('MYKEY', caseless=True).setParseAction(ppc.downcaseTokens)('rname')
        ret = kw.parseString('mykey')
        print(ret.rname)
        self.assertEqual(ret.rname, 'mykey', "failed to upcase with named result")

        if not IRON_PYTHON_ENV:
            #test html data
            html = "<TR class=maintxt bgColor=#ffffff> \
                <TD vAlign=top>Производитель, модель</TD> \
                <TD vAlign=top><STRONG>BenQ-Siemens CF61</STRONG></TD> \
            "#.decode('utf-8')

            # 'Manufacturer, model
            text_manuf = 'Производитель, модель'
            manufacturer = pp.Literal(text_manuf)

            td_start, td_end = pp.makeHTMLTags("td")
            manuf_body =  td_start.suppress() + manufacturer + pp.SkipTo(td_end)("cells*") + td_end.suppress()

            #~ manuf_body.setDebug()

            #~ for tokens in manuf_body.scanString(html):
                #~ print(tokens)

class ParseUsingRegex(ParseTestCase):
    def runTest(self):

        import re

        signedInt = pp.Regex(r'[-+][0-9]+')
        unsignedInt = pp.Regex(r'[0-9]+')
        simpleString = pp.Regex(r'("[^\"]*")|(\'[^\']*\')')
        namedGrouping = pp.Regex(r'("(?P<content>[^\"]*)")')
        compiledRE = pp.Regex(re.compile(r'[A-Z]+'))

        def testMatch (expression, instring, shouldPass, expectedString=None):
            if shouldPass:
                try:
                    result = expression.parseString(instring)
                    print('%s correctly matched %s' % (repr(expression), repr(instring)))
                    if expectedString != result[0]:
                        print('\tbut failed to match the pattern as expected:')
                        print('\tproduced %s instead of %s' % \
                            (repr(result[0]), repr(expectedString)))
                    return True
                except pp.ParseException:
                    print('%s incorrectly failed to match %s' % \
                        (repr(expression), repr(instring)))
            else:
                try:
                    result = expression.parseString(instring)
                    print('%s incorrectly matched %s' % (repr(expression), repr(instring)))
                    print('\tproduced %s as a result' % repr(result[0]))
                except pp.ParseException:
                    print('%s correctly failed to match %s' % \
                        (repr(expression), repr(instring)))
                    return True
            return False

        # These should fail
        self.assertTrue(testMatch(signedInt, '1234 foo', False), "Re: (1) passed, expected fail")
        self.assertTrue(testMatch(signedInt, '    +foo', False), "Re: (2) passed, expected fail")
        self.assertTrue(testMatch(unsignedInt, 'abc', False), "Re: (3) passed, expected fail")
        self.assertTrue(testMatch(unsignedInt, '+123 foo', False), "Re: (4) passed, expected fail")
        self.assertTrue(testMatch(simpleString, 'foo', False), "Re: (5) passed, expected fail")
        self.assertTrue(testMatch(simpleString, '"foo bar\'', False), "Re: (6) passed, expected fail")
        self.assertTrue(testMatch(simpleString, '\'foo bar"', False), "Re: (7) passed, expected fail")

        # These should pass
        self.assertTrue(testMatch(signedInt, '   +123', True, '+123'), "Re: (8) failed, expected pass")
        self.assertTrue(testMatch(signedInt, '+123', True, '+123'), "Re: (9) failed, expected pass")
        self.assertTrue(testMatch(signedInt, '+123 foo', True, '+123'), "Re: (10) failed, expected pass")
        self.assertTrue(testMatch(signedInt, '-0 foo', True, '-0'), "Re: (11) failed, expected pass")
        self.assertTrue(testMatch(unsignedInt, '123 foo', True, '123'), "Re: (12) failed, expected pass")
        self.assertTrue(testMatch(unsignedInt, '0 foo', True, '0'), "Re: (13) failed, expected pass")
        self.assertTrue(testMatch(simpleString, '"foo"', True, '"foo"'), "Re: (14) failed, expected pass")
        self.assertTrue(testMatch(simpleString, "'foo bar' baz", True, "'foo bar'"), "Re: (15) failed, expected pass")

        self.assertTrue(testMatch(compiledRE, 'blah', False), "Re: (16) passed, expected fail")
        self.assertTrue(testMatch(compiledRE, 'BLAH', True, 'BLAH'), "Re: (17) failed, expected pass")

        self.assertTrue(testMatch(namedGrouping, '"foo bar" baz', True, '"foo bar"'), "Re: (16) failed, expected pass")
        ret = namedGrouping.parseString('"zork" blah')
        print(ret)
        print(list(ret.items()))
        print(ret.content)
        self.assertEqual(ret.content, 'zork', "named group lookup failed")
        self.assertEqual(ret[0], simpleString.parseString('"zork" blah')[0],
                         "Regex not properly returning ParseResults for named vs. unnamed groups")

        try:
            #~ print "lets try an invalid RE"
            invRe = pp.Regex('("[^\"]*")|(\'[^\']*\'')
        except Exception as e:
            print("successfully rejected an invalid RE:", end=' ')
            print(e)
        else:
            self.assertTrue(False, "failed to reject invalid RE")

        invRe = pp.Regex('')

class RegexAsTypeTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp

        test_str = "sldkjfj 123 456 lsdfkj"

        print("return as list of match groups")
        expr = pp.Regex(r"\w+ (\d+) (\d+) (\w+)", asGroupList=True)
        expected_group_list = [tuple(test_str.split()[1:])]
        result = expr.parseString(test_str)
        print(result.dump())
        print(expected_group_list)
        self.assertParseResultsEquals(result, expected_list=expected_group_list,
                                      msg="incorrect group list returned by Regex)")

        print("return as re.match instance")
        expr = pp.Regex(r"\w+ (?P<num1>\d+) (?P<num2>\d+) (?P<last_word>\w+)", asMatch=True)
        result = expr.parseString(test_str)
        print(result.dump())
        print(result[0].groups())
        print(expected_group_list)
        self.assertEqual(result[0].groupdict(), {'num1': '123',  'num2': '456',  'last_word': 'lsdfkj'},
                         'invalid group dict from Regex(asMatch=True)')
        self.assertEqual(result[0].groups(), expected_group_list[0],
                         "incorrect group list returned by Regex(asMatch)")

class RegexSubTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp

        print("test sub with string")
        expr = pp.Regex(r"<title>").sub("'Richard III'")
        result = expr.transformString("This is the title: <title>")
        print(result)
        self.assertEqual(result, "This is the title: 'Richard III'", "incorrect Regex.sub result with simple string")

        print("test sub with re string")
        expr = pp.Regex(r"([Hh]\d):\s*(.*)").sub(r"<\1>\2</\1>")
        result = expr.transformString("h1: This is the main heading\nh2: This is the sub-heading")
        print(result)
        self.assertEqual(result, '<h1>This is the main heading</h1>\n<h2>This is the sub-heading</h2>',
                         "incorrect Regex.sub result with re string")

        print("test sub with re string (Regex returns re.match)")
        expr = pp.Regex(r"([Hh]\d):\s*(.*)", asMatch=True).sub(r"<\1>\2</\1>")
        result = expr.transformString("h1: This is the main heading\nh2: This is the sub-heading")
        print(result)
        self.assertEqual(result, '<h1>This is the main heading</h1>\n<h2>This is the sub-heading</h2>',
                         "incorrect Regex.sub result with re string")

        print("test sub with callable that return str")
        expr = pp.Regex(r"<(.*?)>").sub(lambda m: m.group(1).upper())
        result = expr.transformString("I want this in upcase: <what? what?>")
        print(result)
        self.assertEqual(result, 'I want this in upcase: WHAT? WHAT?', "incorrect Regex.sub result with callable")

        try:
            expr = pp.Regex(r"<(.*?)>", asMatch=True).sub(lambda m: m.group(1).upper())
        except SyntaxError:
            pass
        else:
            self.assertTrue(False, "failed to warn using a Regex.sub(callable) with asMatch=True")

        try:
            expr = pp.Regex(r"<(.*?)>", asGroupList=True).sub(lambda m: m.group(1).upper())
        except SyntaxError:
            pass
        else:
            self.assertTrue(False, "failed to warn using a Regex.sub() with asGroupList=True")

        try:
            expr = pp.Regex(r"<(.*?)>", asGroupList=True).sub("")
        except SyntaxError:
            pass
        else:
            self.assertTrue(False, "failed to warn using a Regex.sub() with asGroupList=True")

class PrecededByTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp

        num = pp.Word(pp.nums).setParseAction(lambda t: int(t[0]))
        interesting_num = pp.PrecededBy(pp.Char("abc")("prefix*")) + num
        semi_interesting_num = pp.PrecededBy('_') + num
        crazy_num = pp.PrecededBy(pp.Word("^", "$%^")("prefix*"), 10) + num
        boring_num = ~pp.PrecededBy(pp.Char("abc_$%^" + pp.nums)) + num
        very_boring_num = pp.PrecededBy(pp.WordStart()) + num
        finicky_num = pp.PrecededBy(pp.Word("^", "$%^"), retreat=3) + num

        s = "c384 b8324 _9293874 _293 404 $%^$^%$2939"
        print(s)
        for expr, expected_list, expected_dict in [
            (interesting_num, [384, 8324], {'prefix': ['c', 'b']}),
            (semi_interesting_num, [9293874, 293], {}),
            (boring_num, [404], {}),
            (crazy_num, [2939], {'prefix': ['^%$']}),
            (finicky_num, [2939], {}),
            (very_boring_num, [404], {}),
            ]:
            print(expr.searchString(s))
            result = sum(expr.searchString(s))
            print(result.dump())
            self.assertParseResultsEquals(result, expected_list, expected_dict)

class CountedArrayTest(ParseTestCase):
    def runTest(self):
        from pyparsing import Word, nums, OneOrMore, countedArray

        testString = "2 5 7 6 0 1 2 3 4 5 0 3 5 4 3"

        integer = Word(nums).setParseAction(lambda t: int(t[0]))
        countedField = countedArray(integer)

        r = OneOrMore(countedField).parseString(testString)
        print(testString)
        print(r)

        self.assertParseResultsEquals(r, expected_list=[[5, 7], [0, 1, 2, 3, 4, 5], [], [5, 4, 3]])

class CountedArrayTest2(ParseTestCase):
    # addresses bug raised by Ralf Vosseler
    def runTest(self):
        from pyparsing import Word, nums, OneOrMore, countedArray

        testString = "2 5 7 6 0 1 2 3 4 5 0 3 5 4 3"

        integer = Word(nums).setParseAction(lambda t: int(t[0]))
        countedField = countedArray(integer)

        dummy = Word("A")
        r = OneOrMore(dummy ^ countedField).parseString(testString)
        print(testString)
        print(r)

        self.assertParseResultsEquals(r, expected_list=[[5, 7], [0, 1, 2, 3, 4, 5], [], [5, 4, 3]])

class CountedArrayTest3(ParseTestCase):
    # test case where counter is not a decimal integer
    def runTest(self):
        from pyparsing import Word, nums, OneOrMore, countedArray, alphas
        int_chars = "_" + alphas
        array_counter = Word(int_chars).setParseAction(lambda t: int_chars.index(t[0]))

        #             123456789012345678901234567890
        testString = "B 5 7 F 0 1 2 3 4 5 _ C 5 4 3"

        integer = Word(nums).setParseAction(lambda t: int(t[0]))
        countedField = countedArray(integer, intExpr=array_counter)

        r = OneOrMore(countedField).parseString(testString)
        print(testString)
        print(r)

        self.assertParseResultsEquals(r, expected_list=[[5, 7], [0, 1, 2, 3, 4, 5], [], [5, 4, 3]])

class LineStartTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp

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
        pass_tests = ['\n'.join(s.lstrip() for s in t.splitlines()).replace('.', ' ') for t in pass_tests]
        fail_tests = ['\n'.join(s.lstrip() for s in t.splitlines()).replace('.', ' ') for t in fail_tests]

        test_patt = pp.Word('A') - pp.LineStart() + pp.Word('B')
        print(test_patt.streamline())
        success = test_patt.runTests(pass_tests)[0]
        self.assertTrue(success, "failed LineStart passing tests (1)")

        success = test_patt.runTests(fail_tests, failureTests=True)[0]
        self.assertTrue(success, "failed LineStart failure mode tests (1)")

        # with resetting(pp.ParserElement, "DEFAULT_WHITE_CHARS"):
        prev_default_whitespace_chars = pp.ParserElement.DEFAULT_WHITE_CHARS
        try:
            print(r'no \n in default whitespace chars')
            pp.ParserElement.setDefaultWhitespaceChars(' ')

            test_patt = pp.Word('A') - pp.LineStart() + pp.Word('B')
            print(test_patt.streamline())
            # should fail the pass tests too, since \n is no longer valid whitespace and we aren't parsing for it
            success = test_patt.runTests(pass_tests, failureTests=True)[0]
            self.assertTrue(success, "failed LineStart passing tests (2)")

            success = test_patt.runTests(fail_tests, failureTests=True)[0]
            self.assertTrue(success, "failed LineStart failure mode tests (2)")

            test_patt = pp.Word('A') - pp.LineEnd().suppress() + pp.LineStart() + pp.Word('B') + pp.LineEnd().suppress()
            print(test_patt.streamline())
            success = test_patt.runTests(pass_tests)[0]
            self.assertTrue(success, "failed LineStart passing tests (3)")

            success = test_patt.runTests(fail_tests, failureTests=True)[0]
            self.assertTrue(success, "failed LineStart failure mode tests (3)")
        finally:
            pp.ParserElement.setDefaultWhitespaceChars(prev_default_whitespace_chars)

        test = """\
        AAA 1
        AAA 2

          AAA

        B AAA

        """

        from textwrap import dedent
        test = dedent(test)
        print(test)

        for t, s, e in (pp.LineStart() + 'AAA').scanString(test):
            print(s, e, pp.lineno(s, test), pp.line(s, test), ord(test[s]))
            print()
            self.assertEqual(test[s], 'A', 'failed LineStart with insignificant newlines')

        # with resetting(pp.ParserElement, "DEFAULT_WHITE_CHARS"):
        try:
            pp.ParserElement.setDefaultWhitespaceChars(' ')
            for t, s, e in (pp.LineStart() + 'AAA').scanString(test):
                print(s, e, pp.lineno(s, test), pp.line(s, test), ord(test[s]))
                print()
                self.assertEqual(test[s], 'A', 'failed LineStart with insignificant newlines')
        finally:
            pp.ParserElement.setDefaultWhitespaceChars(prev_default_whitespace_chars)


class LineAndStringEndTest(ParseTestCase):
    def runTest(self):
        from pyparsing import OneOrMore, lineEnd, alphanums, Word, stringEnd, delimitedList, SkipTo

        NLs = OneOrMore(lineEnd)
        bnf1 = delimitedList(Word(alphanums).leaveWhitespace(), NLs)
        bnf2 = Word(alphanums) + stringEnd
        bnf3 = Word(alphanums) + SkipTo(stringEnd)
        tests = [
            ("testA\ntestB\ntestC\n", ['testA', 'testB', 'testC']),
            ("testD\ntestE\ntestF", ['testD', 'testE', 'testF']),
            ("a", ['a']),
             ]

        for test, expected in tests:
            res1 = bnf1.parseString(test)
            print(res1, '=?', expected)
            self.assertParseResultsEquals(res1, expected_list=expected,
                                          msg="Failed lineEnd/stringEnd test (1): " + repr(test)+ " -> " + str(res1))

            res2 = bnf2.searchString(test)[0]
            print(res2, '=?', expected[-1:])
            self.assertParseResultsEquals(res2, expected_list=expected[-1:],
                                          msg="Failed lineEnd/stringEnd test (2): " + repr(test)+ " -> " + str(res2))

            res3 = bnf3.parseString(test)
            first = res3[0]
            rest = res3[1]
            #~ print res3.dump()
            print(repr(rest), '=?', repr(test[len(first) + 1:]))
            self.assertEqual(rest, test[len(first) + 1:],
                             "Failed lineEnd/stringEnd test (3): " + repr(test)+ " -> " + str(res3.asList()))
            print()

        from pyparsing import Regex
        import re

        k = Regex(r'a+', flags=re.S + re.M)
        k = k.parseWithTabs()
        k = k.leaveWhitespace()

        tests = [
            (r'aaa', ['aaa']),
            (r'\naaa', None),
            (r'a\naa', None),
            (r'aaa\n', None),
            ]
        for i, (src, expected) in enumerate(tests):
            print(i, repr(src).replace('\\\\', '\\'), end=' ')
            if expected is None:
                with self.assertRaisesParseException():
                    k.parseString(src, parseAll=True)
            else:
                res = k.parseString(src, parseAll=True)
                self.assertParseResultsEquals(res, expected, msg="Failed on parseAll=True test %d" % i)

class VariableParseActionArgsTest(ParseTestCase):
    def runTest(self):
        pa3 = lambda s, l, t: t
        pa2 = lambda l, t: t
        pa1 = lambda t: t
        pa0 = lambda : None
        class Callable3(object):
            def __call__(self, s, l, t):
                return t
        class Callable2(object):
            def __call__(self, l, t):
                return t
        class Callable1(object):
            def __call__(self, t):
                return t
        class Callable0(object):
            def __call__(self):
                return
        class CallableS3(object):
            #~ @staticmethod
            def __call__(s, l, t):
                return t
            __call__=staticmethod(__call__)
        class CallableS2(object):
            #~ @staticmethod
            def __call__(l, t):
                return t
            __call__=staticmethod(__call__)
        class CallableS1(object):
            #~ @staticmethod
            def __call__(t):
                return t
            __call__=staticmethod(__call__)
        class CallableS0(object):
            #~ @staticmethod
            def __call__():
                return
            __call__=staticmethod(__call__)
        class CallableC3(object):
            #~ @classmethod
            def __call__(cls, s, l, t):
                return t
            __call__=classmethod(__call__)
        class CallableC2(object):
            #~ @classmethod
            def __call__(cls, l, t):
                return t
            __call__=classmethod(__call__)
        class CallableC1(object):
            #~ @classmethod
            def __call__(cls, t):
                return t
            __call__=classmethod(__call__)
        class CallableC0(object):
            #~ @classmethod
            def __call__(cls):
                return
            __call__=classmethod(__call__)

        class parseActionHolder(object):
            #~ @staticmethod
            def pa3(s, l, t):
                return t
            pa3=staticmethod(pa3)
            #~ @staticmethod
            def pa2(l, t):
                return t
            pa2=staticmethod(pa2)
            #~ @staticmethod
            def pa1(t):
                return t
            pa1=staticmethod(pa1)
            #~ @staticmethod
            def pa0():
                return
            pa0=staticmethod(pa0)

        def paArgs(*args):
            print(args)
            return args[2]

        class ClassAsPA0(object):
            def __init__(self):
                pass
            def __str__(self):
                return "A"

        class ClassAsPA1(object):
            def __init__(self, t):
                print("making a ClassAsPA1")
                self.t = t
            def __str__(self):
                return self.t[0]

        class ClassAsPA2(object):
            def __init__(self, l, t):
                self.t = t
            def __str__(self):
                return self.t[0]

        class ClassAsPA3(object):
            def __init__(self, s, l, t):
                self.t = t
            def __str__(self):
                return self.t[0]

        class ClassAsPAStarNew(tuple):
            def __new__(cls, *args):
                print("make a ClassAsPAStarNew", args)
                return tuple.__new__(cls, *args[2].asList())
            def __str__(self):
                return ''.join(self)

        from pyparsing import Literal, OneOrMore

        A = Literal("A").setParseAction(pa0)
        B = Literal("B").setParseAction(pa1)
        C = Literal("C").setParseAction(pa2)
        D = Literal("D").setParseAction(pa3)
        E = Literal("E").setParseAction(Callable0())
        F = Literal("F").setParseAction(Callable1())
        G = Literal("G").setParseAction(Callable2())
        H = Literal("H").setParseAction(Callable3())
        I = Literal("I").setParseAction(CallableS0())
        J = Literal("J").setParseAction(CallableS1())
        K = Literal("K").setParseAction(CallableS2())
        L = Literal("L").setParseAction(CallableS3())
        M = Literal("M").setParseAction(CallableC0())
        N = Literal("N").setParseAction(CallableC1())
        O = Literal("O").setParseAction(CallableC2())
        P = Literal("P").setParseAction(CallableC3())
        Q = Literal("Q").setParseAction(paArgs)
        R = Literal("R").setParseAction(parseActionHolder.pa3)
        S = Literal("S").setParseAction(parseActionHolder.pa2)
        T = Literal("T").setParseAction(parseActionHolder.pa1)
        U = Literal("U").setParseAction(parseActionHolder.pa0)
        V = Literal("V")

        gg = OneOrMore(A | C | D | E | F | G | H |
                        I | J | K | L | M | N | O | P | Q | R | S | U | V | B | T)
        testString = "VUTSRQPONMLKJIHGFEDCBA"
        res = gg.parseString(testString)
        print(res)
        self.assertParseResultsEquals(res, expected_list=list(testString),
                                      msg="Failed to parse using variable length parse actions")

        A = Literal("A").setParseAction(ClassAsPA0)
        B = Literal("B").setParseAction(ClassAsPA1)
        C = Literal("C").setParseAction(ClassAsPA2)
        D = Literal("D").setParseAction(ClassAsPA3)
        E = Literal("E").setParseAction(ClassAsPAStarNew)

        gg = OneOrMore(A | B | C | D | E | F | G | H |
                        I | J | K | L | M | N | O | P | Q | R | S | T | U | V)
        testString = "VUTSRQPONMLKJIHGFEDCBA"
        res = gg.parseString(testString)
        print(list(map(str, res)))
        self.assertEqual(list(map(str, res)), list(testString),
                         "Failed to parse using variable length parse actions "
                         "using class constructors as parse actions")

class EnablePackratParsing(TestCase):
    def runTest(self):
        from pyparsing import ParserElement
        ParserElement.enablePackrat()

class SingleArgExceptionTest(ParseTestCase):
    def runTest(self):
        from pyparsing import ParseBaseException, ParseFatalException

        msg = ""
        raisedMsg = ""
        testMessage = "just one arg"
        try:
            raise ParseFatalException(testMessage)
        except ParseBaseException as pbe:
            print("Received expected exception:", pbe)
            raisedMsg = pbe.msg
            self.assertEqual(raisedMsg, testMessage, "Failed to get correct exception message")


class OriginalTextForTest(ParseTestCase):
    def runTest(self):
        from pyparsing import makeHTMLTags, originalTextFor

        def rfn(t):
            return "%s:%d" % (t.src, len("".join(t)))

        makeHTMLStartTag = lambda tag: originalTextFor(makeHTMLTags(tag)[0], asString=False)

        # use the lambda, Luke
        start = makeHTMLStartTag('IMG')

        # don't replace our fancy parse action with rfn,
        # append rfn to the list of parse actions
        start.addParseAction(rfn)

        text = '''_<img src="images/cal.png"
            alt="cal image" width="16" height="15">_'''
        s = start.transformString(text)
        if VERBOSE:
            print(s)
        self.assertTrue(s.startswith("_images/cal.png:"), "failed to preserve input s properly")
        self.assertTrue(s.endswith("77_"), "failed to return full original text properly")

        tag_fields = makeHTMLStartTag("IMG").searchString(text)[0]
        if VERBOSE:
            print(sorted(tag_fields.keys()))
            self.assertEqual(sorted(tag_fields.keys()),
                             ['alt', 'empty', 'height', 'src', 'startImg', 'tag', 'width'],
                             'failed to preserve results names in originalTextFor')

class PackratParsingCacheCopyTest(ParseTestCase):
    def runTest(self):
        from pyparsing import Word, nums, delimitedList, Literal, Optional, alphas, alphanums, empty

        integer = Word(nums).setName("integer")
        id = Word(alphas + '_', alphanums + '_')
        simpleType = Literal('int');
        arrayType= simpleType + ('[' + delimitedList(integer) + ']')[...]
        varType = arrayType | simpleType
        varDec  = varType + delimitedList(id + Optional('=' + integer)) + ';'

        codeBlock = Literal('{}')

        funcDef = Optional(varType | 'void') + id + '(' + (delimitedList(varType + id)|'void'|empty) + ')' + codeBlock

        program = varDec | funcDef
        input = 'int f(){}'
        results = program.parseString(input)
        print("Parsed '%s' as %s" % (input, results.asList()))
        self.assertEqual(results.asList(), ['int', 'f', '(', ')', '{}'], "Error in packrat parsing")

class PackratParsingCacheCopyTest2(ParseTestCase):
    def runTest(self):
        from pyparsing import Keyword, Word, Suppress, Forward, Optional, delimitedList, Group

        DO, AA = list(map(Keyword, "DO AA".split()))
        LPAR, RPAR = list(map(Suppress, "()"))
        identifier = ~AA + Word("Z")

        function_name = identifier.copy()
        #~ function_name = ~AA + Word("Z")  #identifier.copy()
        expr = Forward().setName("expr")
        expr << (Group(function_name + LPAR + Optional(delimitedList(expr)) + RPAR).setName("functionCall") |
                    identifier.setName("ident")#.setDebug()#.setBreak()
                  )

        stmt = DO + Group(delimitedList(identifier + ".*" | expr))
        result = stmt.parseString("DO Z")
        print(result.asList())
        self.assertEqual(len(result[1]), 1, "packrat parsing is duplicating And term exprs")

class ParseResultsDelTest(ParseTestCase):
    def runTest(self):
        from pyparsing import OneOrMore, Word, alphas, nums

        grammar = OneOrMore(Word(nums))("ints") + OneOrMore(Word(alphas))("words")
        res = grammar.parseString("123 456 ABC DEF")
        print(res.dump())
        origInts = res.ints.asList()
        origWords = res.words.asList()
        del res[1]
        del res["words"]
        print(res.dump())
        self.assertEqual(res[1], 'ABC', "failed to delete 0'th element correctly")
        self.assertEqual(res.ints.asList(), origInts, "updated named attributes, should have updated list only")
        self.assertEqual(res.words, "", "failed to update named attribute correctly")
        self.assertEqual(res[-1], 'DEF', "updated list, should have updated named attributes only")

class WithAttributeParseActionTest(ParseTestCase):
    def runTest(self):
        """
        This unit test checks withAttribute in these ways:

        * Argument forms as keywords and tuples
        * Selecting matching tags by attribute
        * Case-insensitive attribute matching
        * Correctly matching tags having the attribute, and rejecting tags not having the attribute

        (Unit test written by voigts as part of the Google Highly Open Participation Contest)
        """

        from pyparsing import makeHTMLTags, Word, withAttribute, withClass, nums

        data = """
        <a>1</a>
        <a b="x">2</a>
        <a B="x">3</a>
        <a b="X">4</a>
        <a b="y">5</a>
        <a class="boo">8</ a>
        """
        tagStart, tagEnd = makeHTMLTags("a")

        expr = tagStart + Word(nums)("value") + tagEnd

        expected = ([['a', ['b', 'x'], False, '2', '</a>'],
                     ['a', ['b', 'x'], False, '3', '</a>']],
                    [['a', ['b', 'x'], False, '2', '</a>'],
                     ['a', ['b', 'x'], False, '3', '</a>']],
                    [['a', ['class', 'boo'], False, '8', '</a>']],
                    )

        for attrib, exp in zip([
            withAttribute(b="x"),
            #withAttribute(B="x"),
            withAttribute(("b", "x")),
            #withAttribute(("B", "x")),
            withClass("boo"),
            ], expected):

            tagStart.setParseAction(attrib)
            result = expr.searchString(data)

            print(result.dump())
            self.assertEqual(result.asList(), exp, "Failed test, expected %s, got %s" % (expected, result.asList()))

class NestedExpressionsTest(ParseTestCase):
    def runTest(self):
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
        from pyparsing import nestedExpr, Literal, Regex, restOfLine, quotedString

        #All defaults. Straight out of the example script. Also, qualifies for
        #the bonus: note the fact that (Z | (E^F) & D) is not parsed :-).
        # Tests for bug fixed in 1.4.10
        print("Test defaults:")
        teststring = "((ax + by)*C) (Z | (E^F) & D)"

        expr = nestedExpr()

        expected = [[['ax', '+', 'by'], '*C']]
        result = expr.parseString(teststring)
        print(result.dump())
        self.assertEqual(result.asList(), expected, "Defaults didn't work. That's a bad sign. Expected: %s, got: %s" % (expected, result))

        #Going through non-defaults, one by one; trying to think of anything
        #odd that might not be properly handled.

        #Change opener
        print("\nNon-default opener")
        opener = "["
        teststring = "[[ ax + by)*C)"
        expected = [[['ax', '+', 'by'], '*C']]
        expr = nestedExpr("[")
        result = expr.parseString(teststring)
        print(result.dump())
        self.assertEqual(result.asList(), expected, "Non-default opener didn't work. Expected: %s, got: %s" % (expected, result))

        #Change closer
        print("\nNon-default closer")

        teststring = "((ax + by]*C]"
        expected = [[['ax', '+', 'by'], '*C']]
        expr = nestedExpr(closer="]")
        result = expr.parseString(teststring)
        print(result.dump())
        self.assertEqual(result.asList(), expected, "Non-default closer didn't work. Expected: %s, got: %s" % (expected, result))

        # #Multicharacter opener, closer
        # opener = "bar"
        # closer = "baz"
        print("\nLiteral expressions for opener and closer")

        opener, closer = list(map(Literal, "bar baz".split()))
        expr = nestedExpr(opener, closer,
                    content=Regex(r"([^b ]|b(?!a)|ba(?![rz]))+"))

        teststring = "barbar ax + bybaz*Cbaz"
        expected = [[['ax', '+', 'by'], '*C']]
        # expr = nestedExpr(opener, closer)
        result = expr.parseString(teststring)
        print(result.dump())
        self.assertEqual(result.asList(), expected, "Multicharacter opener and closer didn't work. Expected: %s, got: %s" % (expected, result))

        #Lisp-ish comments
        print("\nUse ignore expression (1)")
        comment = Regex(r";;.*")
        teststring = \
        """
        (let ((greeting "Hello, world!")) ;;(foo bar
           (display greeting))
        """

        expected = [['let', [['greeting', '"Hello,', 'world!"']], ';;(foo bar',\
                         ['display', 'greeting']]]
        expr = nestedExpr(ignoreExpr=comment)
        result = expr.parseString(teststring)
        print(result.dump())
        self.assertEqual(result.asList(), expected , "Lisp-ish comments (\";; <...> $\") didn't work. Expected: %s, got: %s" % (expected, result))


        #Lisp-ish comments, using a standard bit of pyparsing, and an Or.
        print("\nUse ignore expression (2)")
        comment = ';;' + restOfLine

        teststring = \
        """
        (let ((greeting "Hello, )world!")) ;;(foo bar
           (display greeting))
        """

        expected = [['let', [['greeting', '"Hello, )world!"']], ';;', '(foo bar',
                     ['display', 'greeting']]]
        expr = nestedExpr(ignoreExpr=(comment ^ quotedString))
        result = expr.parseString(teststring)
        print(result.dump())
        self.assertEqual(result.asList(), expected ,
                         "Lisp-ish comments (\";; <...> $\") and quoted strings didn't work. Expected: %s, got: %s" % (expected, result))

class WordExcludeTest(ParseTestCase):
    def runTest(self):
        from pyparsing import Word, printables
        allButPunc = Word(printables, excludeChars=".,:;-_!?")

        test = "Hello, Mr. Ed, it's Wilbur!"
        result = allButPunc.searchString(test).asList()
        print(result)
        self.assertEqual(result, [['Hello'], ['Mr'], ['Ed'], ["it's"], ['Wilbur']], "failed WordExcludeTest")

class ParseAllTest(ParseTestCase):
    def runTest(self):
        from pyparsing import Word, cppStyleComment

        testExpr = Word("A")

        tests = [
            ("AAAAA", False, True),
            ("AAAAA", True, True),
            ("AAABB", False, True),
            ("AAABB", True, False),
            ]
        for s, parseAllFlag, shouldSucceed in tests:
            try:
                print("'%s' parseAll=%s (shouldSucceed=%s)" % (s, parseAllFlag, shouldSucceed))
                testExpr.parseString(s, parseAll=parseAllFlag)
                self.assertTrue(shouldSucceed, "successfully parsed when should have failed")
            except ParseException as pe:
                print(pe.explain(pe))
                self.assertFalse(shouldSucceed, "failed to parse when should have succeeded")

        # add test for trailing comments
        testExpr.ignore(cppStyleComment)

        tests = [
            ("AAAAA //blah", False, True),
            ("AAAAA //blah", True, True),
            ("AAABB //blah", False, True),
            ("AAABB //blah", True, False),
            ]
        for s, parseAllFlag, shouldSucceed in tests:
            try:
                print("'%s' parseAll=%s (shouldSucceed=%s)" % (s, parseAllFlag, shouldSucceed))
                testExpr.parseString(s, parseAll=parseAllFlag)
                self.assertTrue(shouldSucceed, "successfully parsed when should have failed")
            except ParseException as pe:
                print(pe.explain(pe))
                self.assertFalse(shouldSucceed, "failed to parse when should have succeeded")

        # add test with very long expression string
        # testExpr = pp.MatchFirst([pp.Literal(c) for c in pp.printables if c != 'B'])[1, ...]
        anything_but_an_f = pp.OneOrMore(pp.MatchFirst([pp.Literal(c) for c in pp.printables if c != 'f']))
        testExpr = pp.Word('012') + anything_but_an_f

        tests = [
            ("00aab", False, True),
            ("00aab", True, True),
            ("00aaf", False, True),
            ("00aaf", True, False),
            ]
        for s, parseAllFlag, shouldSucceed in tests:
            try:
                print("'%s' parseAll=%s (shouldSucceed=%s)" % (s, parseAllFlag, shouldSucceed))
                testExpr.parseString(s, parseAll=parseAllFlag)
                self.assertTrue(shouldSucceed, "successfully parsed when should have failed")
            except ParseException as pe:
                print(pe.explain(pe))
                self.assertFalse(shouldSucceed, "failed to parse when should have succeeded")


class GreedyQuotedStringsTest(ParseTestCase):
    def runTest(self):
        from pyparsing import QuotedString, sglQuotedString, dblQuotedString, quotedString, delimitedList

        src = """\
           "string1", "strin""g2"
           'string1', 'string2'
           ^string1^, ^string2^
           <string1>, <string2>"""

        testExprs = (sglQuotedString, dblQuotedString, quotedString,
                    QuotedString('"', escQuote='""'), QuotedString("'", escQuote="''"),
                    QuotedString("^"), QuotedString("<", endQuoteChar=">"))
        for expr in testExprs:
            strs = delimitedList(expr).searchString(src)
            print(strs)
            self.assertTrue(bool(strs), "no matches found for test expression '%s'"  % expr)
            for lst in strs:
                self.assertEqual(len(lst), 2, "invalid match found for test expression '%s'"  % expr)

        from pyparsing import alphas, nums, Word
        src = """'ms1',1,0,'2009-12-22','2009-12-22 10:41:22') ON DUPLICATE KEY UPDATE sent_count = sent_count + 1, mtime = '2009-12-22 10:41:22';"""
        tok_sql_quoted_value = (
            QuotedString("'", "\\", "''", True, False) ^
            QuotedString('"', "\\", '""', True, False))
        tok_sql_computed_value = Word(nums)
        tok_sql_identifier = Word(alphas)

        val = tok_sql_quoted_value | tok_sql_computed_value | tok_sql_identifier
        vals = delimitedList(val)
        print(vals.parseString(src))
        self.assertEqual(len(vals.parseString(src)), 5, "error in greedy quote escaping")


class WordBoundaryExpressionsTest(ParseTestCase):
    def runTest(self):
        from pyparsing import WordEnd, WordStart, oneOf

        ws = WordStart()
        we = WordEnd()
        vowel = oneOf(list("AEIOUY"))
        consonant = oneOf(list("BCDFGHJKLMNPQRSTVWXZ"))

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
            [['D', 'G'], ['A'], ['C', 'F'], ['I'], ['E'], ['A', 'I']],
            [['J', 'M', 'P'], [], ['L', 'R'], ['O'], [], ['O']],
            [['S', 'V'], ['Y'], ['X', 'Z'], ['U'], [], ['U', 'Y']],
            [['D', 'G', 'J', 'M', 'P', 'S', 'V'],
             ['A', 'Y'],
             ['C', 'F', 'L', 'R', 'X', 'Z'],
             ['I', 'O', 'U'],
             ['E'],
             ['A', 'I', 'O', 'U', 'Y']],
            ]

        for t, expected in zip(tests, expectedResult):
            print(t)
            results = [flatten(e.searchString(t).asList()) for e in [
                leadingConsonant,
                leadingVowel,
                trailingConsonant,
                trailingVowel,
                internalVowel,
                bnf,
                ]]
            print(results)
            print()
            self.assertEqual(results, expected, "Failed WordBoundaryTest, expected %s, got %s" % (expected, results))

class RequiredEachTest(ParseTestCase):
    def runTest(self):
        from pyparsing import Keyword

        parser = Keyword('bam') & Keyword('boo')
        try:
            res1 = parser.parseString('bam boo')
            print(res1.asList())
            res2 = parser.parseString('boo bam')
            print(res2.asList())
        except ParseException:
            failed = True
        else:
            failed = False
            self.assertFalse(failed, "invalid logic in Each")

            self.assertEqual(set(res1), set(res2), "Failed RequiredEachTest, expected "
                             + str(res1.asList()) + " and " + str(res2.asList())
                             + "to contain same words in any order")

class OptionalEachTest(ParseTestCase):
    def runTest1(self):
        from pyparsing import Optional, Keyword

        the_input = "Major Tal Weiss"
        parser1 = (Optional('Tal') + Optional('Weiss')) & Keyword('Major')
        parser2 = Optional(Optional('Tal') + Optional('Weiss')) & Keyword('Major')
        p1res = parser1.parseString(the_input)
        p2res = parser2.parseString(the_input)
        self.assertEqual(p1res.asList(), p2res.asList(),
                         "Each failed to match with nested Optionals, "
                         + str(p1res.asList()) + " should match " + str(p2res.asList()))

    def runTest2(self):
        from pyparsing import Word, alphanums, OneOrMore, Group, Regex, Optional

        word = Word(alphanums + '_').setName("word")
        with_stmt = 'with' + OneOrMore(Group(word('key') + '=' + word('value')))('overrides')
        using_stmt = 'using' + Regex('id-[0-9a-f]{8}')('id')
        modifiers = Optional(with_stmt('with_stmt')) & Optional(using_stmt('using_stmt'))

        self.assertEqual(modifiers, "with foo=bar bing=baz using id-deadbeef")
        self.assertNotEqual(modifiers, "with foo=bar bing=baz using id-deadbeef using id-feedfeed")

    def runTest3(self):
        from pyparsing import Literal, Suppress

        foo = Literal('foo')
        bar = Literal('bar')

        openBrace = Suppress(Literal("{"))
        closeBrace = Suppress(Literal("}"))

        exp = openBrace + (foo[1, ...]("foo") & bar[...]("bar")) + closeBrace

        tests = """\
            {foo}
            {bar foo bar foo bar foo}
            """.splitlines()
        for test in tests:
            test = test.strip()
            if not test:
                continue
            result = exp.parseString(test)
            print(test, '->', result.asList())
            self.assertEqual(result.asList(), test.strip("{}").split(), "failed to parse Each expression %r" % test)
            print(result.dump())

        try:
            result = exp.parseString("{bar}")
            self.assertTrue(False, "failed to raise exception when required element is missing")
        except ParseException as pe:
            pass

    def runTest4(self):
        from pyparsing import pyparsing_common, Group

        expr = ((~pyparsing_common.iso8601_date + pyparsing_common.integer("id"))
                & (Group(pyparsing_common.iso8601_date)("date*")[...]))

        expr.runTests("""
            1999-12-31 100 2001-01-01
            42
            """)


    def runTest(self):
        self.runTest1()
        self.runTest2()
        self.runTest3()
        self.runTest4()

class EachWithParseFatalExceptionTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp
        ppc = pp.pyparsing_common

        option_expr = pp.Keyword('options') - '(' + ppc.integer + ')'
        step_expr1 = pp.Keyword('step') - '(' + ppc.integer + ")"
        step_expr2 = pp.Keyword('step') - '(' + ppc.integer + "Z" + ")"
        step_expr = step_expr1 ^ step_expr2

        parser = option_expr & step_expr[...]
        tests = [
            ("options(100) step(A)", "Expected integer, found 'A'  (at char 18), (line:1, col:19)"),
            ("step(A) options(100)", "Expected integer, found 'A'  (at char 5), (line:1, col:6)"),
            ("options(100) step(100A)", """Expected "Z", found 'A'  (at char 21), (line:1, col:22)"""),
            ("options(100) step(22) step(100ZA)",
             """Expected ")", found 'A'  (at char 31), (line:1, col:32)"""),
        ]
        test_lookup = dict(tests)

        success, output = parser.runTests((t[0] for t in tests), failureTests=True)
        for test_str, result in output:
            self.assertEqual(test_lookup[test_str], str(result),
                             "incorrect exception raised for test string {!r}".format(test_str))

class SumParseResultsTest(ParseTestCase):
    def runTest(self):

        samplestr1 = "garbage;DOB 10-10-2010;more garbage\nID PARI12345678;more garbage"
        samplestr2 = "garbage;ID PARI12345678;more garbage\nDOB 10-10-2010;more garbage"
        samplestr3 = "garbage;DOB 10-10-2010"
        samplestr4 = "garbage;ID PARI12345678;more garbage- I am cool"

        res1 = "ID:PARI12345678 DOB:10-10-2010 INFO:"
        res2 = "ID:PARI12345678 DOB:10-10-2010 INFO:"
        res3 = "ID: DOB:10-10-2010 INFO:"
        res4 = "ID:PARI12345678 DOB: INFO: I am cool"

        from pyparsing import Regex, Word, alphanums, restOfLine
        dob_ref = "DOB" + Regex(r"\d{2}-\d{2}-\d{4}")("dob")
        id_ref = "ID" + Word(alphanums, exact=12)("id")
        info_ref = "-" + restOfLine("info")

        person_data = dob_ref | id_ref | info_ref

        tests = (samplestr1, samplestr2, samplestr3, samplestr4,)
        results = (res1, res2, res3, res4,)
        for test, expected in zip(tests, results):
            person = sum(person_data.searchString(test))
            result = "ID:%s DOB:%s INFO:%s" % (person.id, person.dob, person.info)
            print(test)
            print(expected)
            print(result)
            for pd in person_data.searchString(test):
                print(pd.dump())
            print()
            self.assertEqual(expected, result,
                             "Failed to parse '%s' correctly, \nexpected '%s', got '%s'" % (test, expected, result))

class MarkInputLineTest(ParseTestCase):
    def runTest(self):

        samplestr1 = "DOB 100-10-2010;more garbage\nID PARI12345678;more garbage"

        from pyparsing import Regex
        dob_ref = "DOB" + Regex(r"\d{2}-\d{2}-\d{4}")("dob")

        try:
            res = dob_ref.parseString(samplestr1)
        except ParseException as pe:
            outstr = pe.markInputline()
            print(outstr)
            self.assertEqual(outstr, "DOB >!<100-10-2010;more garbage", "did not properly create marked input line")
        else:
            self.assertEqual(False, "test construction failed - should have raised an exception")

class LocatedExprTest(ParseTestCase):
    def runTest(self):

        #             012345678901234567890123456789012345678901234567890
        samplestr1 = "DOB 10-10-2010;more garbage;ID PARI12345678  ;more garbage"

        from pyparsing import Word, alphanums, locatedExpr
        id_ref = locatedExpr("ID" + Word(alphanums, exact=12)("id"))

        res = id_ref.searchString(samplestr1)[0][0]
        print(res.dump())
        self.assertEqual(samplestr1[res.locn_start:res.locn_end], 'ID PARI12345678', "incorrect location calculation")


class PopTest(ParseTestCase):
    def runTest(self):
        from pyparsing import Word, alphas, nums

        source = "AAA 123 456 789 234"
        patt = Word(alphas)("name") + Word(nums) * (1,)

        result = patt.parseString(source)
        tests = [
            (0, 'AAA', ['123', '456', '789', '234']),
            (None, '234', ['123', '456', '789']),
            ('name', 'AAA', ['123', '456', '789']),
            (-1, '789', ['123', '456']),
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
            self.assertEqual(ret, val, "wrong value returned, got %r, expected %r" % (ret, val))
            self.assertEqual(remaining, result.asList(),
                             "list is in wrong state after pop, got %r, expected %r" % (result.asList(), remaining))
            print()

        prevlist = result.asList()
        ret = result.pop('name', default="noname")
        print(ret)
        print(result.asList())
        self.assertEqual(ret, "noname",
                         "default value not successfully returned, got %r, expected %r" % (ret, "noname"))
        self.assertEqual(result.asList(), prevlist,
                         "list is in wrong state after pop, got %r, expected %r" % (result.asList(), remaining))


class AddConditionTest(ParseTestCase):
    def runTest(self):
        from pyparsing import Word, nums, Suppress, ParseFatalException

        numParser = Word(nums)
        numParser.addParseAction(lambda s, l, t: int(t[0]))
        numParser.addCondition(lambda s, l, t: t[0] % 2)
        numParser.addCondition(lambda s, l, t: t[0] >= 7)

        result = numParser.searchString("1 2 3 4 5 6 7 8 9 10")
        print(result.asList())
        self.assertEqual(result.asList(), [[7], [9]], "failed to properly process conditions")

        numParser = Word(nums)
        numParser.addParseAction(lambda s, l, t: int(t[0]))
        rangeParser = (numParser("from_") + Suppress('-') + numParser("to"))

        result = rangeParser.searchString("1-4 2-4 4-3 5 6 7 8 9 10")
        print(result.asList())
        self.assertEqual(result.asList(), [[1, 4], [2, 4], [4, 3]], "failed to properly process conditions")

        rangeParser.addCondition(lambda t: t.to > t.from_, message="from must be <= to", fatal=False)
        result = rangeParser.searchString("1-4 2-4 4-3 5 6 7 8 9 10")
        print(result.asList())
        self.assertEqual(result.asList(), [[1, 4], [2, 4]], "failed to properly process conditions")

        rangeParser = (numParser("from_") + Suppress('-') + numParser("to"))
        rangeParser.addCondition(lambda t: t.to > t.from_, message="from must be <= to", fatal=True)
        try:
            result = rangeParser.searchString("1-4 2-4 4-3 5 6 7 8 9 10")
            self.assertTrue(False, "failed to interrupt parsing on fatal condition failure")
        except ParseFatalException:
            print("detected fatal condition")

class PatientOrTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp

        # Two expressions and a input string which could - syntactically - be matched against
        # both expressions. The "Literal" expression is considered invalid though, so this PE
        # should always detect the "Word" expression.
        def validate(token):
            if token[0] == "def":
                raise pp.ParseException("signalling invalid token")
            return token

        a = pp.Word("de").setName("Word")#.setDebug()
        b = pp.Literal("def").setName("Literal").setParseAction(validate)#.setDebug()
        c = pp.Literal("d").setName("d")#.setDebug()

        # The "Literal" expressions's ParseAction is not executed directly after syntactically
        # detecting the "Literal" Expression but only after the Or-decision has been made
        # (which is too late)...
        try:
            result = (a ^ b ^ c).parseString("def")
            self.assertEqual(result.asList(), ['de'], "failed to select longest match, chose %s" % result)
        except ParseException:
            failed = True
        else:
            failed = False
        self.assertFalse(failed, "invalid logic in Or, fails on longest match with exception in parse action")

        # from issue #93
        word = pp.Word(pp.alphas).setName('word')
        word_1 = pp.Word(pp.alphas).setName('word_1').addCondition(lambda t: len(t[0]) == 1)

        a = word + (word_1 + word ^ word)
        b = word * 3
        c = a ^ b
        c.streamline()
        print(c)
        test_string = 'foo bar temp'
        result = c.parseString(test_string)
        print(test_string, '->', result.asList())

        self.assertEqual(result.asList(), test_string.split(), "failed to match longest choice")


class EachWithOptionalWithResultsNameTest(ParseTestCase):
    def runTest(self):
        from pyparsing import Optional

        result = (Optional('foo')('one') & Optional('bar')('two')).parseString('bar foo')
        print(result.dump())
        self.assertEqual(sorted(result.keys()), ['one', 'two'])

class UnicodeExpressionTest(ParseTestCase):
    def runTest(self):
        from pyparsing import Literal, ParseException

        z = 'a' | Literal('\u1111')
        z.streamline()
        try:
            z.parseString('b')
        except ParseException as pe:
            self.assertEqual(pe.msg, r'''Expected {"a" | "ᄑ"}''',
                             "Invalid error message raised, got %r" % pe.msg)

class SetNameTest(ParseTestCase):
    def runTest(self):
        from pyparsing import (oneOf, infixNotation, Word, nums, opAssoc, delimitedList, countedArray,
            nestedExpr, makeHTMLTags, anyOpenTag, anyCloseTag, commonHTMLEntity, replaceHTMLEntity,
            Forward)

        a = oneOf("a b c")
        b = oneOf("d e f")
        arith_expr = infixNotation(Word(nums),
                        [
                        (oneOf('* /'), 2, opAssoc.LEFT),
                        (oneOf('+ -'), 2, opAssoc.LEFT),
                        ])
        arith_expr2 = infixNotation(Word(nums),
                        [
                        (('?', ':'), 3, opAssoc.LEFT),
                        ])
        recursive = Forward()
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
            delimitedList(Word(nums).setName("int")),
            countedArray(Word(nums).setName("int")),
            nestedExpr(),
            makeHTMLTags('Z'),
            (anyOpenTag, anyCloseTag),
            commonHTMLEntity,
            commonHTMLEntity.setParseAction(replaceHTMLEntity).transformString("lsdjkf &lt;lsdjkf&gt;&amp;&apos;&quot;&xyzzy;"),
            ]

        expected = map(str.strip, """\
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
            lsdjkf <lsdjkf>&'"&xyzzy;""".splitlines())

        for t, e in zip(tests, expected):
            tname = str(t)
            print(tname)
            self.assertEqual(tname, e, "expression name mismatch, expected {} got {}".format(e, tname))

class TrimArityExceptionMaskingTest(ParseTestCase):
    def runTest(self):
        from pyparsing import Word

        invalid_message = "<lambda>() missing 1 required positional argument: 't'"
        try:
            Word('a').setParseAction(lambda t: t[0] + 1).parseString('aaa')
        except Exception as e:
            exc_msg = str(e)
            self.assertNotEqual(exc_msg, invalid_message, "failed to catch TypeError thrown in _trim_arity")

class TrimArityExceptionMaskingTest2(ParseTestCase):
    def runTest(self):
        # construct deep call tree
        def A():
            import traceback

            traceback.print_stack(limit=2)

            from pyparsing import Word

            invalid_message = "<lambda>() missing 1 required positional argument: 't'"
            try:
                Word('a').setParseAction(lambda t: t[0] + 1).parseString('aaa')
            except Exception as e:
                exc_msg = str(e)
                self.assertNotEqual(exc_msg, invalid_message, "failed to catch TypeError thrown in _trim_arity")


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


class ClearParseActionsTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp
        ppc = pp.pyparsing_common

        realnum = ppc.real()
        self.assertEqual(realnum.parseString("3.14159")[0], 3.14159, "failed basic real number parsing")

        # clear parse action that converts to float
        realnum.setParseAction(None)
        self.assertEqual(realnum.parseString("3.14159")[0], "3.14159", "failed clearing parse action")

        # add a new parse action that tests if a '.' is prsent
        realnum.addParseAction(lambda t: '.' in t[0])
        self.assertEqual(realnum.parseString("3.14159")[0], True,
                         "failed setting new parse action after clearing parse action")

class OneOrMoreStopTest(ParseTestCase):
    def runTest(self):
        from pyparsing import (Word, OneOrMore, alphas, Keyword, CaselessKeyword,
            nums, alphanums)

        test = "BEGIN aaa bbb ccc END"
        BEGIN, END = map(Keyword, "BEGIN,END".split(','))
        body_word = Word(alphas).setName("word")
        for ender in (END, "END", CaselessKeyword("END")):
            expr = BEGIN + OneOrMore(body_word, stopOn=ender) + END
            self.assertEqual(test, expr, "Did not successfully stop on ending expression %r" % ender)

            expr = BEGIN + body_word[...].stopOn(ender) + END
            self.assertEqual(test, expr, "Did not successfully stop on ending expression %r" % ender)

        number = Word(nums + ',.()').setName("number with optional commas")
        parser= (OneOrMore(Word(alphanums + '-/.'), stopOn=number)('id').setParseAction(' '.join)
                    + number('data'))
        result = parser.parseString('        XXX Y/123          1,234.567890')
        self.assertEqual(result.asList(), ['XXX Y/123', '1,234.567890'],
                         "Did not successfully stop on ending expression %r" % number)

class ZeroOrMoreStopTest(ParseTestCase):
    def runTest(self):
        from pyparsing import (Word, ZeroOrMore, alphas, Keyword, CaselessKeyword)

        test = "BEGIN END"
        BEGIN, END = map(Keyword, "BEGIN,END".split(','))
        body_word = Word(alphas).setName("word")
        for ender in (END, "END", CaselessKeyword("END")):
            expr = BEGIN + ZeroOrMore(body_word, stopOn=ender) + END
            self.assertEqual(test, expr, "Did not successfully stop on ending expression %r" % ender)

            expr = BEGIN + body_word[0, ...].stopOn(ender) + END
            self.assertEqual(test, expr, "Did not successfully stop on ending expression %r" % ender)

class NestedAsDictTest(ParseTestCase):
    def runTest(self):
        from pyparsing import Literal, Forward, alphanums, Group, delimitedList, Dict, Word, Optional

        equals = Literal("=").suppress()
        lbracket = Literal("[").suppress()
        rbracket = Literal("]").suppress()
        lbrace = Literal("{").suppress()
        rbrace = Literal("}").suppress()

        value_dict          = Forward()
        value_list          = Forward()
        value_string        = Word(alphanums + "@. ")

        value               = value_list ^ value_dict ^ value_string
        values              = Group(delimitedList(value, ","))
        #~ values              = delimitedList(value, ",").setParseAction(lambda toks: [toks.asList()])

        value_list          << lbracket + values + rbracket

        identifier          = Word(alphanums + "_.")

        assignment          = Group(identifier + equals + Optional(value))
        assignments         = Dict(delimitedList(assignment, ';'))
        value_dict          << lbrace + assignments + rbrace

        response = assignments

        rsp = 'username=goat; errors={username=[already taken, too short]}; empty_field='
        result_dict = response.parseString(rsp).asDict()
        print(result_dict)
        self.assertEqual(result_dict['username'], 'goat', "failed to process string in ParseResults correctly")
        self.assertEqual(result_dict['errors']['username'], ['already taken', 'too short'],
                         "failed to process nested ParseResults correctly")

class TraceParseActionDecoratorTest(ParseTestCase):
    def runTest(self):
        from pyparsing import traceParseAction, Word, nums

        @traceParseAction
        def convert_to_int(t):
            return int(t[0])

        class Z(object):
            def __call__(self, other):
                return other[0] * 1000

        integer = Word(nums).addParseAction(convert_to_int)
        integer.addParseAction(traceParseAction(lambda t: t[0] * 10))
        integer.addParseAction(traceParseAction(Z()))
        integer.parseString("132")

class RunTestsTest(ParseTestCase):
    def runTest(self):
        from pyparsing import Word, nums, delimitedList

        integer = Word(nums).setParseAction(lambda t : int(t[0]))
        intrange = integer("start") + '-' + integer("end")
        intrange.addCondition(lambda t: t.end > t.start, message="invalid range, start must be <= end", fatal=True)
        intrange.addParseAction(lambda t: list(range(t.start, t.end + 1)))

        indices = delimitedList(intrange | integer)
        indices.addParseAction(lambda t: sorted(set(t)))

        tests = """\
            # normal data
            1-3,2-4,6,8-10,16

            # lone integer
            11"""
        results = indices.runTests(tests, printResults=False)[1]

        expectedResults = [
            [1, 2, 3, 4, 6, 8, 9, 10, 16],
            [11],
            ]
        for res, expected in zip(results, expectedResults):
            print(res[1].asList())
            print(expected)
            self.assertEqual(res[1].asList(), expected, "failed test: " + str(expected))

        tests = """\
            # invalid range
            1-2, 3-1, 4-6, 7, 12
            """
        success = indices.runTests(tests, printResults=False, failureTests=True)[0]
        self.assertTrue(success, "failed to raise exception on improper range test")

class RunTestsPostParseTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp

        integer = pp.pyparsing_common.integer
        fraction = integer('numerator') + '/' + integer('denominator')

        accum = []
        def eval_fraction(test, result):
            accum.append((test, result.asList()))
            return "eval: {}".format(result.numerator / result.denominator)

        success = fraction.runTests("""\
            1/2
            1/0
        """, postParse=eval_fraction)[0]
        print(success)

        self.assertTrue(success, "failed to parse fractions in RunTestsPostParse")

        expected_accum = [('1/2', [1, '/', 2]), ('1/0', [1, '/', 0])]
        self.assertEqual(accum, expected_accum, "failed to call postParse method during runTests")

class CommonExpressionsTest(ParseTestCase):
    def runTest(self):
        from pyparsing import pyparsing_common
        import ast

        success = pyparsing_common.mac_address.runTests("""
            AA:BB:CC:DD:EE:FF
            AA.BB.CC.DD.EE.FF
            AA-BB-CC-DD-EE-FF
            """)[0]
        self.assertTrue(success, "error in parsing valid MAC address")

        success = pyparsing_common.mac_address.runTests("""
            # mixed delimiters
            AA.BB:CC:DD:EE:FF
            """, failureTests=True)[0]
        self.assertTrue(success, "error in detecting invalid mac address")

        success = pyparsing_common.ipv4_address.runTests("""
            0.0.0.0
            1.1.1.1
            127.0.0.1
            1.10.100.199
            255.255.255.255
            """)[0]
        self.assertTrue(success, "error in parsing valid IPv4 address")

        success = pyparsing_common.ipv4_address.runTests("""
            # out of range value
            256.255.255.255
            """, failureTests=True)[0]
        self.assertTrue(success, "error in detecting invalid IPv4 address")

        success = pyparsing_common.ipv6_address.runTests("""
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
            """)[0]
        self.assertTrue(success, "error in parsing valid IPv6 address")

        success = pyparsing_common.ipv6_address.runTests("""
            # too few values
            1080:0:0:0:8:800:200C

            # too many ::'s, only 1 allowed
            2134::1234:4567::2444:2106
            """, failureTests=True)[0]
        self.assertTrue(success, "error in detecting invalid IPv6 address")

        success = pyparsing_common.number.runTests("""
            100
            -100
            +100
            3.14159
            6.02e23
            1e-12
            """)[0]
        self.assertTrue(success, "error in parsing valid numerics")

        success = pyparsing_common.sci_real.runTests("""
            1e12
            -1e12
            3.14159
            6.02e23
            """)[0]
        self.assertTrue(success, "error in parsing valid scientific notation reals")

        # any int or real number, returned as float
        success = pyparsing_common.fnumber.runTests("""
            100
            -100
            +100
            3.14159
            6.02e23
            1e-12
            """)[0]
        self.assertTrue(success, "error in parsing valid numerics")

        success, results = pyparsing_common.iso8601_date.runTests("""
            1997
            1997-07
            1997-07-16
            """)
        self.assertTrue(success, "error in parsing valid iso8601_date")
        expected = [
            ('1997', None, None),
            ('1997', '07', None),
            ('1997', '07', '16'),
        ]
        for r, exp in zip(results, expected):
            self.assertTrue((r[1].year, r[1].month, r[1].day,) == exp, "failed to parse date into fields")

        success, results = pyparsing_common.iso8601_date().addParseAction(pyparsing_common.convertToDate()).runTests("""
            1997-07-16
            """)
        self.assertTrue(success, "error in parsing valid iso8601_date with parse action")
        self.assertTrue(results[0][1][0] == datetime.date(1997, 7, 16))

        success, results = pyparsing_common.iso8601_datetime.runTests("""
            1997-07-16T19:20+01:00
            1997-07-16T19:20:30+01:00
            1997-07-16T19:20:30.45Z
            1997-07-16 19:20:30.45
            """)
        self.assertTrue(success, "error in parsing valid iso8601_datetime")

        success, results = pyparsing_common.iso8601_datetime().addParseAction(pyparsing_common.convertToDatetime()).runTests("""
            1997-07-16T19:20:30.45
            """)
        self.assertTrue(success, "error in parsing valid iso8601_datetime")
        self.assertTrue(results[0][1][0] == datetime.datetime(1997, 7, 16, 19, 20, 30, 450000))

        success = pyparsing_common.uuid.runTests("""
            123e4567-e89b-12d3-a456-426655440000
            """)[0]
        self.assertTrue(success, "failed to parse valid uuid")

        success = pyparsing_common.fraction.runTests("""
            1/2
            -15/16
            -3/-4
            """)[0]
        self.assertTrue(success, "failed to parse valid fraction")

        success = pyparsing_common.mixed_integer.runTests("""
            1/2
            -15/16
            -3/-4
            1 1/2
            2 -15/16
            0 -3/-4
            12
            """)[0]
        self.assertTrue(success, "failed to parse valid mixed integer")

        success, results = pyparsing_common.number.runTests("""
            100
            -3
            1.732
            -3.14159
            6.02e23""")
        self.assertTrue(success, "failed to parse numerics")

        for test, result in results:
            expected = ast.literal_eval(test)
            self.assertEqual(result[0], expected, "numeric parse failed (wrong value) (%s should be %s)" % (result[0], expected))
            self.assertEqual(type(result[0]), type(expected), "numeric parse failed (wrong type) (%s should be %s)" % (type(result[0]), type(expected)))


class NumericExpressionsTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp
        ppc = pp.pyparsing_common

        # disable parse actions that do type conversion so we don't accidentally trigger
        # conversion exceptions when what we want to check is the parsing expression
        real = ppc.real().setParseAction(None)
        sci_real = ppc.sci_real().setParseAction(None)
        signed_integer = ppc.signed_integer().setParseAction(None)

        from itertools import product

        def make_tests():
            leading_sign = ['+', '-', '']
            leading_digit = ['0', '']
            dot = ['.', '']
            decimal_digit = ['1', '']
            e = ['e', 'E', '']
            e_sign = ['+', '-', '']
            e_int = ['22', '']
            stray = ['9', '.', '']

            seen = set()
            seen.add('')
            for parts in product(leading_sign, stray, leading_digit, dot, decimal_digit, stray, e, e_sign, e_int,
                                 stray):
                parts_str = ''.join(parts).strip()
                if parts_str in seen:
                    continue
                seen.add(parts_str)
                yield parts_str

            print(len(seen)-1, "tests produced")

        # collect tests into valid/invalid sets, depending on whether they evaluate to valid Python floats or ints
        valid_ints = set()
        valid_reals = set()
        valid_sci_reals = set()
        invalid_ints = set()
        invalid_reals = set()
        invalid_sci_reals = set()

        # check which strings parse as valid floats or ints, and store in related valid or invalid test sets
        for test_str in make_tests():
            if '.' in test_str or 'e' in test_str.lower():
                try:
                    float(test_str)
                except ValueError:
                    invalid_sci_reals.add(test_str)
                    if 'e' not in test_str.lower():
                        invalid_reals.add(test_str)
                else:
                    valid_sci_reals.add(test_str)
                    if 'e' not in test_str.lower():
                        valid_reals.add(test_str)

            try:
                int(test_str)
            except ValueError:
                invalid_ints.add(test_str)
            else:
                valid_ints.add(test_str)

        # now try all the test sets against their respective expressions
        all_pass = True
        suppress_results = {'printResults': False}
        for expr, tests, is_fail, fn in zip([real, sci_real, signed_integer] * 2,
                                            [valid_reals, valid_sci_reals, valid_ints,
                                             invalid_reals, invalid_sci_reals, invalid_ints],
                                            [False, False, False, True, True, True],
                                            [float, float, int] * 2):
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
            print(expr, ('FAIL', 'PASS')[success], "{}valid tests ({})".format('in' if is_fail else '',
                                                                                  len(tests),))
            all_pass = all_pass and success

        self.assertTrue(all_pass, "failed one or more numeric tests")

class TokenMapTest(ParseTestCase):
    def runTest(self):
        from pyparsing import tokenMap, Word, hexnums, OneOrMore

        parser = OneOrMore(Word(hexnums)).setParseAction(tokenMap(int, 16))
        success, report = parser.runTests("""
            00 11 22 aa FF 0a 0d 1a
            """)
        # WAS:
        # self.assertTrue(success, "failed to parse hex integers")
        # print(results)
        # self.assertEqual(results[0][-1].asList(), [0, 17, 34, 170, 255, 10, 13, 26], "tokenMap parse action failed")

        # USING JUST assertParseResultsEquals
        # results = [rpt[1] for rpt in report]
        # self.assertParseResultsEquals(results[0], [0, 17, 34, 170, 255, 10, 13, 26],
        #                               msg="tokenMap parse action failed")

        # if I hadn't unpacked the return from runTests, I could have just passed it directly,
        # instead of reconstituting as a tuple
        self.assertRunTestResults((success, report),
                                  [
                                      ([0, 17, 34, 170, 255, 10, 13, 26], "tokenMap parse action failed"),
                                  ],
                                  msg="failed to parse hex integers")


class ParseFileTest(ParseTestCase):
    def runTest(self):
        from pyparsing import pyparsing_common, OneOrMore
        s = """
        123 456 789
        """
        input_file = StringIO(s)
        integer = pyparsing_common.integer

        results = OneOrMore(integer).parseFile(input_file)
        print(results)

        results = OneOrMore(integer).parseFile('test/parsefiletest_input_file.txt')
        print(results)


class HTMLStripperTest(ParseTestCase):
    def runTest(self):
        from pyparsing import pyparsing_common, originalTextFor, OneOrMore, Word, printables

        sample = """
        <html>
        Here is some sample <i>HTML</i> text.
        </html>
        """
        read_everything = originalTextFor(OneOrMore(Word(printables)))
        read_everything.addParseAction(pyparsing_common.stripHTMLTags)

        result = read_everything.parseString(sample)
        self.assertEqual(result[0].strip(), 'Here is some sample HTML text.')

class ExprSplitterTest(ParseTestCase):
    def runTest(self):

        from pyparsing import Literal, quotedString, pythonStyleComment, Empty

        expr = Literal(';') + Empty()
        expr.ignore(quotedString)
        expr.ignore(pythonStyleComment)


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
            ['            this_semi_does_nothing()', ''],
            ['            neither_does_this_but_there_are_spaces_afterward()', ''],
            ['            a = "a;b"', 'return a # this is a comment; it has a semicolon!'],
            ['                z=1000', 'b("; in quotes")', 'c=200', 'return z'],
            ["            return ';'"],
            ["                '''a docstring; with a semicolon'''"],
            ['                a = 10', 'b = 11', 'c = 12'],
            ['                # this comment; has several; semicolons'],
            ['                    x = 12', 'return x # so; does; this; one'],
            ['                    x = 15', '', '', 'y += x', 'return y'],
            ]

        exp_iter = iter(expected)
        for line in filter(lambda ll: ';' in ll, sample.splitlines()):
            print(str(list(expr.split(line))) + ',')
            self.assertEqual(list(expr.split(line)), next(exp_iter), "invalid split on expression")

        print()

        expected = [
            ['            this_semi_does_nothing()', ';', ''],
            ['            neither_does_this_but_there_are_spaces_afterward()', ';', ''],
            ['            a = "a;b"', ';', 'return a # this is a comment; it has a semicolon!'],
            ['                z=1000', ';', 'b("; in quotes")', ';', 'c=200', ';', 'return z'],
            ["            return ';'"],
            ["                '''a docstring; with a semicolon'''"],
            ['                a = 10', ';', 'b = 11', ';', 'c = 12'],
            ['                # this comment; has several; semicolons'],
            ['                    x = 12', ';', 'return x # so; does; this; one'],
            ['                    x = 15', ';', '', ';', '', ';', 'y += x', ';', 'return y'],
            ]
        exp_iter = iter(expected)
        for line in filter(lambda ll: ';' in ll, sample.splitlines()):
            print(str(list(expr.split(line, includeSeparators=True))) + ',')
            self.assertEqual(list(expr.split(line, includeSeparators=True)), next(exp_iter),
                             "invalid split on expression")

        print()


        expected = [
            ['            this_semi_does_nothing()', ''],
            ['            neither_does_this_but_there_are_spaces_afterward()', ''],
            ['            a = "a;b"', 'return a # this is a comment; it has a semicolon!'],
            ['                z=1000', 'b("; in quotes");  c=200;return z'],
            ['                a = 10', 'b = 11; c = 12'],
            ['                    x = 12', 'return x # so; does; this; one'],
            ['                    x = 15', ';; y += x; return y'],
            ]
        exp_iter = iter(expected)
        for line in sample.splitlines():
            pieces = list(expr.split(line, maxsplit=1))
            print(str(pieces) + ',')
            if len(pieces) == 2:
                exp = next(exp_iter)
                self.assertEqual(pieces, exp, "invalid split on expression with maxSplits=1")
            elif len(pieces) == 1:
                self.assertEqual(len(expr.searchString(line)), 0, "invalid split with maxSplits=1 when expr not present")
            else:
                print("\n>>> " + line)
                self.assertTrue(False, "invalid split on expression with maxSplits=1, corner case")

class ParseFatalExceptionTest(ParseTestCase):
    def runTest(self):

        from pyparsing import Word, nums, ParseFatalException

        with self.assertRaisesParseException(exc_type=ParseFatalException,
                                             msg="failed to raise ErrorStop exception"):
            expr = "ZZZ" - Word(nums)
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

class InlineLiteralsUsingTest(ParseTestCase):
    def runTest(self):

        from pyparsing import ParserElement, Suppress, Literal, CaselessLiteral, Word, alphas, oneOf, CaselessKeyword, nums

        wd = Word(alphas)

        ParserElement.inlineLiteralsUsing(Suppress)
        result = (wd + ',' + wd + oneOf("! . ?")).parseString("Hello, World!")
        self.assertEqual(len(result), 3, "inlineLiteralsUsing(Suppress) failed!")

        ParserElement.inlineLiteralsUsing(Literal)
        result = (wd + ',' + wd + oneOf("! . ?")).parseString("Hello, World!")
        self.assertEqual(len(result), 4, "inlineLiteralsUsing(Literal) failed!")

        ParserElement.inlineLiteralsUsing(CaselessKeyword)
        # WAS:
        # result = ("SELECT" + wd + "FROM" + wd).parseString("select color from colors")
        # self.assertEqual(result.asList(), "SELECT color FROM colors".split(),
        #                  "inlineLiteralsUsing(CaselessKeyword) failed!")
        self.assertParseAndCheckList("SELECT" + wd + "FROM" + wd,
                                     "select color from colors",
                                     expected_list=['SELECT', 'color', 'FROM', 'colors'],
                                      msg="inlineLiteralsUsing(CaselessKeyword) failed!")

        ParserElement.inlineLiteralsUsing(CaselessLiteral)
        # result = ("SELECT" + wd + "FROM" + wd).parseString("select color from colors")
        # self.assertEqual(result.asList(), "SELECT color FROM colors".split(),
        #                  "inlineLiteralsUsing(CaselessLiteral) failed!")
        self.assertParseAndCheckList("SELECT" + wd + "FROM" + wd,
                                     "select color from colors",
                                     expected_list=['SELECT', 'color', 'FROM', 'colors'],
                                      msg="inlineLiteralsUsing(CaselessLiteral) failed!")

        integer = Word(nums)
        ParserElement.inlineLiteralsUsing(Literal)
        date_str = integer("year") + '/' + integer("month") + '/' + integer("day")
        # result = date_str.parseString("1999/12/31")
        # self.assertEqual(result.asList(), ['1999', '/', '12', '/', '31'], "inlineLiteralsUsing(example 1) failed!")
        self.assertParseAndCheckList(date_str, "1999/12/31", expected_list=['1999', '/', '12', '/', '31'],
                                      msg="inlineLiteralsUsing(example 1) failed!")

        # change to Suppress
        ParserElement.inlineLiteralsUsing(Suppress)
        date_str = integer("year") + '/' + integer("month") + '/' + integer("day")

        # result = date_str.parseString("1999/12/31")  # -> ['1999', '12', '31']
        # self.assertEqual(result.asList(), ['1999', '12', '31'], "inlineLiteralsUsing(example 2) failed!")
        self.assertParseAndCheckList(date_str, "1999/12/31", expected_list=['1999', '12', '31'],
                                      msg="inlineLiteralsUsing(example 2) failed!")

class CloseMatchTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp

        searchseq = pp.CloseMatch("ATCATCGAATGGA", 2)

        _, results = searchseq.runTests("""
            ATCATCGAATGGA
            XTCATCGAATGGX
            ATCATCGAAXGGA
            ATCAXXGAATGGA
            ATCAXXGAATGXA
            ATCAXXGAATGG
            """)
        expected = (
            [],
            [0, 12],
            [9],
            [4, 5],
            None,
            None
            )

        for r, exp in zip(results, expected):
            if exp is not None:
                self.assertEquals(r[1].mismatches, exp,
                                  "fail CloseMatch between %r and %r" % (searchseq.match_string, r[0]))
            print(r[0], 'exc: %s' % r[1] if exp is None and isinstance(r[1], Exception)
                                          else ("no match", "match")[r[1].mismatches == exp])

class DefaultKeywordCharsTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp

        with self.assertRaisesParseException(msg="failed to fail matching keyword using updated keyword chars"):
            pp.Keyword("start").parseString("start1000")

        try:
            pp.Keyword("start", identChars=pp.alphas).parseString("start1000")
        except pp.ParseException:
            self.assertTrue(False, "failed to match keyword using updated keyword chars")

        with resetting(pp.Keyword, "DEFAULT_KEYWORD_CHARS"):
            pp.Keyword.setDefaultKeywordChars(pp.alphas)
            try:
                pp.Keyword("start").parseString("start1000")
            except pp.ParseException:
                self.assertTrue(False, "failed to match keyword using updated keyword chars")

        with self.assertRaisesParseException(msg="failed to fail matching keyword using updated keyword chars"):
            pp.CaselessKeyword("START").parseString("start1000")

        try:
            pp.CaselessKeyword("START", identChars=pp.alphas).parseString("start1000")
        except pp.ParseException:
            self.assertTrue(False, "failed to match keyword using updated keyword chars")

        with resetting(pp.Keyword, "DEFAULT_KEYWORD_CHARS"):
            pp.Keyword.setDefaultKeywordChars(pp.alphas)
            try:
                pp.CaselessKeyword("START").parseString("start1000")
            except pp.ParseException:
                self.assertTrue(False, "failed to match keyword using updated keyword chars")

class ColTest(ParseTestCase):
    def runTest(self):

        test = "*\n* \n*   ALF\n*\n"
        initials = [c for i, c in enumerate(test) if pp.col(i, test) == 1]
        print(initials)
        self.assertTrue(len(initials) == 4 and all(c == '*' for c in initials), 'fail col test')

class LiteralExceptionTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp

        for cls in (pp.Literal, pp.CaselessLiteral, pp.Keyword, pp.CaselessKeyword,
             pp.Word, pp.Regex):
            expr = cls('xyz')#.setName('{}_expr'.format(cls.__name__.lower()))

            try:
                expr.parseString(' ')
            except Exception as e:
                print(cls.__name__, str(e))
                self.assertTrue(isinstance(e, pp.ParseBaseException),
                                "class {} raised wrong exception type {}".format(cls.__name__, type(e).__name__))

class ParseActionExceptionTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp
        import traceback

        number = pp.Word(pp.nums)
        def number_action():
            raise IndexError # this is the important line!

        number.setParseAction(number_action)
        symbol = pp.Word('abcd', max=1)
        expr = number | symbol

        try:
            expr.parseString('1 + 2')
        except Exception as e:
            print_traceback = True
            try:
                self.assertTrue(hasattr(e, '__cause__'), "no __cause__ attribute in the raised exception")
                self.assertTrue(e.__cause__ is not None, "__cause__ not propagated to outer exception")
                self.assertTrue(type(e.__cause__) == IndexError, "__cause__ references wrong exception")
                print_traceback = False
            finally:
                if print_traceback:
                    traceback.print_exc()
        else:
            self.assertTrue(False, "Expected ParseException not raised")

class ParseActionNestingTest(ParseTestCase):
    # tests Issue #22
    def runTest(self):

        vals = pp.OneOrMore(pp.pyparsing_common.integer)("int_values")
        def add_total(tokens):
            tokens['total'] = sum(tokens)
            return tokens
        vals.addParseAction(add_total)
        results = vals.parseString("244 23 13 2343")
        print(results.dump())
        self.assertParseResultsEquals(results, expected_dict={'int_values': [244, 23, 13, 2343], 'total': 2623},
                                      msg="noop parse action changed ParseResults structure")

        name = pp.Word(pp.alphas)('name')
        score = pp.Word(pp.nums + '.')('score')
        nameScore = pp.Group(name + score)
        line1 = nameScore('Rider')

        result1 = line1.parseString('Mauney 46.5')

        print("### before parse action is added ###")
        print("result1.dump():\n" + result1.dump() + "\n")
        before_pa_dict = result1.asDict()

        line1.setParseAction(lambda t: t)

        result1 = line1.parseString('Mauney 46.5')
        after_pa_dict = result1.asDict()

        print("### after parse action was added ###")
        print("result1.dump():\n" + result1.dump() + "\n")
        self.assertEqual(before_pa_dict, after_pa_dict, "noop parse action changed ParseResults structure")

class ParseResultsNameBelowUngroupedNameTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp

        rule_num = pp.Regex("[0-9]+")("LIT_NUM*")
        list_num = pp.Group(pp.Literal("[")("START_LIST")
                            + pp.delimitedList(rule_num)("LIST_VALUES")
                            + pp.Literal("]")("END_LIST"))("LIST")

        test_string = "[ 1,2,3,4,5,6 ]"
        list_num.runTests(test_string)

        U = list_num.parseString(test_string)
        self.assertTrue("LIT_NUM" not in U.LIST.LIST_VALUES, "results name retained as sub in ungrouped named result")

class ParseResultsNamesInGroupWithDictTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp
        from pyparsing import pyparsing_common as ppc

        key = ppc.identifier()
        value = ppc.integer()
        lat = ppc.real()
        long = ppc.real()
        EQ = pp.Suppress('=')

        data = lat("lat") + long("long") + pp.Dict(pp.OneOrMore(pp.Group(key + EQ + value)))
        site = pp.QuotedString('"')("name") + pp.Group(data)("data")

        test_string = '"Golden Gate Bridge" 37.819722 -122.478611 height=746 span=4200'
        site.runTests(test_string)

        a, aEnd = pp.makeHTMLTags('a')
        attrs = a.parseString("<a href='blah'>")
        print(attrs.dump())
        self.assertParseResultsEquals(attrs,
                                      expected_dict = {'startA': {'href': 'blah', 'tag': 'a', 'empty': False},
                                                      'href': 'blah', 'tag': 'a', 'empty': False})


class FollowedByTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp
        from pyparsing import pyparsing_common as ppc
        expr = pp.Word(pp.alphas)("item") + pp.FollowedBy(ppc.integer("qty"))
        result = expr.parseString("balloon 99")
        print(result.dump())
        self.assertTrue('qty' in result, "failed to capture results name in FollowedBy")
        self.assertEqual(result.asDict(), {'item': 'balloon', 'qty': 99},
                         "invalid results name structure from FollowedBy")

class SetBreakTest(ParseTestCase):
    """
    Test behavior of ParserElement.setBreak(), to invoke the debugger before parsing that element is attempted.

    Temporarily monkeypatches pdb.set_trace.
    """
    def runTest(self):
        was_called = False
        def mock_set_trace():
            nonlocal was_called
            was_called = True

        import pyparsing as pp
        wd = pp.Word(pp.alphas)
        wd.setBreak()

        print("Before parsing with setBreak:", was_called)
        import pdb
        with resetting(pdb, "set_trace"):
            pdb.set_trace = mock_set_trace
            wd.parseString("ABC")

        print("After parsing with setBreak:", was_called)
        self.assertTrue(was_called, "set_trace wasn't called by setBreak")

class UnicodeTests(ParseTestCase):
    def runTest(self):
        import pyparsing as pp
        ppu = pp.pyparsing_unicode
        ppc = pp.pyparsing_common

        # verify proper merging of ranges by addition
        kanji_printables = ppu.Japanese.Kanji.printables
        katakana_printables = ppu.Japanese.Katakana.printables
        hiragana_printables = ppu.Japanese.Hiragana.printables
        japanese_printables = ppu.Japanese.printables
        self.assertEqual(set(japanese_printables), set(kanji_printables
                                                       + katakana_printables
                                                       + hiragana_printables),
                         "failed to construct ranges by merging Japanese types")

        # verify proper merging of ranges using multiple inheritance
        cjk_printables = ppu.CJK.printables
        self.assertEqual(len(cjk_printables), len(set(cjk_printables)),
                         "CJK contains duplicate characters - all should be unique")

        chinese_printables = ppu.Chinese.printables
        korean_printables = ppu.Korean.printables
        print(len(cjk_printables), len(set(chinese_printables
                                           + korean_printables
                                           + japanese_printables)))

        self.assertEqual(len(cjk_printables), len(set(chinese_printables
                                                      + korean_printables
                                                      + japanese_printables)),
                         "failed to construct ranges by merging Chinese, Japanese and Korean")

        alphas = ppu.Greek.alphas
        greet = pp.Word(alphas) + ',' + pp.Word(alphas) + '!'

        # input string
        hello = "Καλημέρα, κόσμε!"
        result = greet.parseString(hello)
        print(result)
        self.assertParseResultsEquals(result,
                                      expected_list=['Καλημέρα', ',', 'κόσμε', '!'],
                                      msg="Failed to parse Greek 'Hello, World!' using "
                                         "pyparsing_unicode.Greek.alphas")

        # define a custom unicode range using multiple inheritance
        class Turkish_set(ppu.Latin1, ppu.LatinA):
            pass

        self.assertEqual(set(Turkish_set.printables),
                         set(ppu.Latin1.printables + ppu.LatinA.printables),
                         "failed to construct ranges by merging Latin1 and LatinA (printables)")

        self.assertEqual(set(Turkish_set.alphas),
                         set(ppu.Latin1.alphas + ppu.LatinA.alphas),
                         "failed to construct ranges by merging Latin1 and LatinA (alphas)")

        self.assertEqual(set(Turkish_set.nums),
                         set(ppu.Latin1.nums + ppu.LatinA.nums),
                         "failed to construct ranges by merging Latin1 and LatinA (nums)")

        key = pp.Word(Turkish_set.alphas)
        value = ppc.integer | pp.Word(Turkish_set.alphas, Turkish_set.alphanums)
        EQ = pp.Suppress('=')
        key_value = key + EQ + value

        sample = u"""\
            şehir=İzmir
            ülke=Türkiye
            nüfus=4279677"""
        result = pp.Dict(pp.OneOrMore(pp.Group(key_value))).parseString(sample)

        print(result.dump())
        self.assertParseResultsEquals(result,
                                      expected_dict={'şehir': 'İzmir', 'ülke': 'Türkiye', 'nüfus': 4279677},
                                      msg="Failed to parse Turkish key-value pairs")


class IndentedBlockExampleTest(ParseTestCase):
    # Make sure example in indentedBlock docstring actually works!
    def runTest(self):
        from textwrap import dedent
        from pyparsing import (Word, alphas, alphanums, indentedBlock, Optional, delimitedList, Group, Forward,
                               nums, OneOrMore)
        data = dedent('''
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
        ''')

        indentStack = [1]
        stmt = Forward()

        identifier = Word(alphas, alphanums)
        funcDecl = ("def" + identifier + Group("(" + Optional(delimitedList(identifier)) + ")") + ":")
        func_body = indentedBlock(stmt, indentStack)
        funcDef = Group(funcDecl + func_body)

        rvalue = Forward()
        funcCall = Group(identifier + "(" + Optional(delimitedList(rvalue)) + ")")
        rvalue << (funcCall | identifier | Word(nums))
        assignment = Group(identifier + "=" + rvalue)
        stmt << (funcDef | assignment | identifier)

        module_body = OneOrMore(stmt)

        parseTree = module_body.parseString(data)
        parseTree.pprint()
        self.assertEqual(parseTree.asList(),
                         [['def',
                           'A',
                           ['(', 'z', ')'],
                           ':',
                           [['A1'], [['B', '=', '100']], [['G', '=', 'A2']], ['A2'], ['A3']]],
                          'B',
                          ['def',
                           'BB',
                           ['(', 'a', 'b', 'c', ')'],
                           ':',
                           [['BB1'], [['def', 'BBA', ['(', ')'], ':', [['bba1'], ['bba2'], ['bba3']]]]]],
                          'C',
                          'D',
                          ['def',
                           'spam',
                           ['(', 'x', 'y', ')'],
                           ':',
                           [[['def', 'eggs', ['(', 'z', ')'], ':', [['pass']]]]]]],
                         "Failed indentedBlock example"
                         )


class IndentedBlockTest(ParseTestCase):
    # parse pseudo-yaml indented text
    def runTest(self):
        import textwrap

        EQ = pp.Suppress('=')
        stack = [1]
        key = pp.pyparsing_common.identifier
        value = pp.Forward()
        key_value = key + EQ + value
        compound_value = pp.Dict(pp.ungroup(pp.indentedBlock(key_value, stack)))
        value <<= pp.pyparsing_common.integer | pp.QuotedString("'") | compound_value
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
        text = textwrap.dedent(text)
        print(text)

        result = parser.parseString(text)
        print(result.dump())
        self.assertEqual(result.a,        100, "invalid indented block result")
        self.assertEqual(result.c.c1,     200, "invalid indented block result")
        self.assertEqual(result.c.c2.c21, 999, "invalid indented block result")


class IndentedBlockTest2(ParseTestCase):
    # exercise indentedBlock with example posted in issue #87
    def runTest(self):
        from textwrap import dedent
        from pyparsing import Word, alphas, alphanums, Suppress, Forward, indentedBlock, Literal, OneOrMore

        indent_stack = [1]

        key = Word(alphas, alphanums) + Suppress(":")
        stmt = Forward()

        suite = indentedBlock(stmt, indent_stack)
        body = key + suite

        pattern = (Word(alphas) + Suppress("(") + Word(alphas) + Suppress(")"))
        stmt << pattern

        def key_parse_action(toks):
            print("Parsing '%s'..." % toks[0])

        key.setParseAction(key_parse_action)
        header = Suppress("[") + Literal("test") + Suppress("]")
        content = (header - OneOrMore(indentedBlock(body, indent_stack, False)))

        contents = Forward()
        suites = indentedBlock(content, indent_stack)

        extra = Literal("extra") + Suppress(":") - suites
        contents << (content | extra)

        parser = OneOrMore(contents)

        sample = dedent("""
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
        """)

        success, _ = parser.runTests([sample])
        self.assertTrue(success, "Failed indentedBlock test for issue #87")

        sample2 = dedent("""
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
        """)

        del indent_stack[1:]
        success, _ = parser.runTests([sample2])
        self.assertTrue(success, "Failed indentedBlock multi-block test for issue #87")

class IndentedBlockScanTest(ParseTestCase):
    def get_parser(self):
        """
        A valid statement is the word "block:", followed by an indent, followed by the letter A only, or another block
        """
        stack = [1]
        block = pp.Forward()
        body = pp.indentedBlock(pp.Literal('A') ^ block, indentStack=stack, indent=True)
        block <<= pp.Literal('block:') + body
        return block

    def runTest(self):
        from textwrap import dedent

        # This input string is a perfect match for the parser, so a single match is found
        p1 = self.get_parser()
        r1 = list(p1.scanString(dedent("""\
        block:
            A
        """)))
        self.assertEqual(len(r1), 1)

        # This input string is a perfect match for the parser, except for the letter B instead of A, so this will fail (and should)
        p2 = self.get_parser()
        r2 = list(p2.scanString(dedent("""\
        block:
            B
        """)))
        self.assertEqual(len(r2), 0)

        # This input string contains both string A and string B, and it finds one match (as it should)
        p3 = self.get_parser()
        r3 = list(p3.scanString(dedent("""\
        block:
            A
        block:
            B
        """)))
        self.assertEqual(len(r3), 1)

        # This input string contains both string A and string B, but in a different order.
        p4 = self.get_parser()
        r4 = list(p4.scanString(dedent("""\
        block:
            B
        block:
            A
        """)))
        self.assertEqual(len(r4), 1)

        # This is the same as case 3, but with nesting
        p5 = self.get_parser()
        r5 = list(p5.scanString(dedent("""\
        block:
            block:
                A
        block:
            block:
                B
        """)))
        self.assertEqual(len(r5), 1)

        # This is the same as case 4, but with nesting
        p6 = self.get_parser()
        r6 = list(p6.scanString(dedent("""\
        block:
            block:
                B
        block:
            block:
                A
        """)))
        self.assertEqual(len(r6), 1)


class InvalidDiagSettingTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp

        with self.assertRaises(ValueError, msg="failed to raise exception when setting non-existent __diag__"):
            pp.__diag__.enable("xyzzy")

        with self.assertWarns(UserWarning, msg="failed to warn disabling 'collect_all_And_tokens"):
            pp.__compat__.disable("collect_all_And_tokens")


class ParseResultsWithNameMatchFirst(ParseTestCase):
    def runTest(self):
        import pyparsing as pp
        expr_a = pp.Literal('not') + pp.Literal('the') + pp.Literal('bird')
        expr_b = pp.Literal('the') + pp.Literal('bird')
        expr = (expr_a | expr_b)('rexp')

        success, report = expr.runTests("""\
            not the bird
            the bird
        """)
        results = [rpt[1] for rpt in report]
        self.assertParseResultsEquals(results[0],
                                      ['not', 'the', 'bird'],
                                      {'rexp': ['not', 'the', 'bird']})
        self.assertParseResultsEquals(results[1],
                                      ['the', 'bird'],
                                      {'rexp': ['the', 'bird']})

        # test compatibility mode, no longer restoring pre-2.3.1 behavior
        with resetting(pp.__compat__, "collect_all_And_tokens"), \
             resetting(pp.__diag__, "warn_multiple_tokens_in_named_alternation"):
            pp.__compat__.collect_all_And_tokens = False
            pp.__diag__.enable("warn_multiple_tokens_in_named_alternation")
            expr_a = pp.Literal('not') + pp.Literal('the') + pp.Literal('bird')
            expr_b = pp.Literal('the') + pp.Literal('bird')
            with self.assertWarns(UserWarning, msg="failed to warn of And within alternation"):
                expr = (expr_a | expr_b)('rexp')

            success, report = expr.runTests("""
                not the bird
                the bird
            """)
            results = [rpt[1] for rpt in report]
            self.assertParseResultsEquals(results[0],
                                          ['not', 'the', 'bird'],
                                          {'rexp': ['not', 'the', 'bird']})
            self.assertParseResultsEquals(results[1],
                                          ['the', 'bird'],
                                          {'rexp': ['the', 'bird']})


class ParseResultsWithNameOr(ParseTestCase):
    def runTest(self):
        import pyparsing as pp
        expr_a = pp.Literal('not') + pp.Literal('the') + pp.Literal('bird')
        expr_b = pp.Literal('the') + pp.Literal('bird')
        expr = (expr_a ^ expr_b)('rexp')
        expr.runTests("""\
            not the bird
            the bird
        """)
        result = expr.parseString('not the bird')
        self.assertParseResultsEquals(result,
                                      ['not', 'the', 'bird'],
                                      {'rexp': ['not', 'the', 'bird']})
        result = expr.parseString('the bird')
        self.assertParseResultsEquals(result,
                                      ['the', 'bird'],
                                      {'rexp': ['the', 'bird']})

        expr = (expr_a | expr_b)('rexp')
        expr.runTests("""\
            not the bird
            the bird
        """)
        result = expr.parseString('not the bird')
        self.assertParseResultsEquals(result,
                                      ['not', 'the', 'bird'],
                                      {'rexp':
                                    ['not', 'the', 'bird']})
        result = expr.parseString('the bird')
        self.assertParseResultsEquals(result,
                                      ['the', 'bird'],
                                      {'rexp': ['the', 'bird']})

        # test compatibility mode, no longer restoring pre-2.3.1 behavior
        with resetting(pp.__compat__, "collect_all_And_tokens"), \
             resetting(pp.__diag__, "warn_multiple_tokens_in_named_alternation"):
            pp.__compat__.collect_all_And_tokens = False
            pp.__diag__.enable("warn_multiple_tokens_in_named_alternation")
            expr_a = pp.Literal('not') + pp.Literal('the') + pp.Literal('bird')
            expr_b = pp.Literal('the') + pp.Literal('bird')

            with self.assertWarns(UserWarning, msg="failed to warn of And within alternation"):
                expr = (expr_a ^ expr_b)('rexp')

            expr.runTests("""\
                not the bird
                the bird
            """)
            self.assertEqual(list(expr.parseString('not the bird')['rexp']), 'not the bird'.split())
            self.assertEqual(list(expr.parseString('the bird')['rexp']), 'the bird'.split())


class EmptyDictDoesNotRaiseException(ParseTestCase):
    def runTest(self):
        import pyparsing as pp

        key = pp.Word(pp.alphas)
        value = pp.Word(pp.nums)
        EQ = pp.Suppress('=')
        key_value_dict = pp.dictOf(key, EQ + value)

        print(key_value_dict.parseString("""\
            a = 10
            b = 20
            """).dump())

        try:
            print(key_value_dict.parseString("").dump())
        except pp.ParseException as pe:
            print(pp.ParseException.explain(pe))
        else:
            self.assertTrue(False, "failed to raise exception when matching empty string")

class ExplainExceptionTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp

        expr = pp.Word(pp.nums).setName("int") + pp.Word(pp.alphas).setName("word")
        try:
            expr.parseString("123 355")
        except pp.ParseException as pe:
            print(pp.ParseException.explain(pe, depth=0))

        expr = pp.Word(pp.nums).setName("int") - pp.Word(pp.alphas).setName("word")
        try:
            expr.parseString("123 355 (test using ErrorStop)")
        except pp.ParseSyntaxException as pe:
            print(pp.ParseException.explain(pe))

        integer = pp.Word(pp.nums).setName("int").addParseAction(lambda t: int(t[0]))
        expr = integer + integer

        def divide_args(t):
            integer.parseString("A")
            return t[0] / t[1]

        expr.addParseAction(divide_args)
        pp.ParserElement.enablePackrat()
        print()

        try:
            expr.parseString("123 0")
        except pp.ParseException as pe:
            print(pp.ParseException.explain(pe))
        except Exception as exc:
            print(pp.ParseException.explain(exc))
            raise


class CaselessKeywordVsKeywordCaselessTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp

        frule = pp.Keyword('t', caseless=True) + pp.Keyword('yes', caseless=True)
        crule = pp.CaselessKeyword('t') + pp.CaselessKeyword('yes')

        flist = frule.searchString('not yes').asList()
        print(flist)
        clist = crule.searchString('not yes').asList()
        print(clist)
        self.assertEqual(flist, clist, "CaselessKeyword not working the same as Keyword(caseless=True)")


class OneOfKeywordsTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp

        literal_expr = pp.oneOf("a b c")
        success, _ = literal_expr[...].runTests("""
            # literal oneOf tests
            a b c
            a a a
            abc
        """)
        self.assertTrue(success, "failed literal oneOf matching")

        keyword_expr = pp.oneOf("a b c", asKeyword=True)
        success, _ = keyword_expr[...].runTests("""
            # keyword oneOf tests
            a b c
            a a a
        """)
        self.assertTrue(success, "failed keyword oneOf matching")

        success, _ = keyword_expr[...].runTests("""
            # keyword oneOf failure tests
            abc
        """, failureTests=True)
        self.assertTrue(success, "failed keyword oneOf failure tests")


class WarnUngroupedNamedTokensTest(ParseTestCase):
    """
     - warn_ungrouped_named_tokens_in_collection - flag to enable warnings when a results
       name is defined on a containing expression with ungrouped subexpressions that also
       have results names (default=True)
    """
    def runTest(self):
        import pyparsing as pp
        ppc = pp.pyparsing_common

        with resetting(pp.__diag__, "warn_ungrouped_named_tokens_in_collection"):
            pp.__diag__.enable("warn_ungrouped_named_tokens_in_collection")

            COMMA = pp.Suppress(',').setName("comma")
            coord = (ppc.integer('x') + COMMA + ppc.integer('y'))

            # this should emit a warning
            with self.assertWarns(UserWarning, msg="failed to warn with named repetition of"
                                                   " ungrouped named expressions"):
                path = coord[...].setResultsName('path')


class WarnNameSetOnEmptyForwardTest(ParseTestCase):
    """
     - warn_name_set_on_empty_Forward - flag to enable warnings whan a Forward is defined
       with a results name, but has no contents defined (default=False)
    """
    def runTest(self):
        import pyparsing as pp

        with resetting(pp.__diag__, "warn_name_set_on_empty_Forward"):
            pp.__diag__.enable("warn_name_set_on_empty_Forward")

            base = pp.Forward()

            with self.assertWarns(UserWarning, msg="failed to warn when naming an empty Forward expression"):
                base("x")


class WarnOnMultipleStringArgsToOneOfTest(ParseTestCase):
    """
     - warn_on_multiple_string_args_to_oneof - flag to enable warnings whan oneOf is
       incorrectly called with multiple str arguments (default=True)
    """
    def runTest(self):
        import pyparsing as pp

        with resetting(pp.__diag__, "warn_on_multiple_string_args_to_oneof"):
            pp.__diag__.enable("warn_on_multiple_string_args_to_oneof")

            with self.assertWarns(UserWarning, msg="failed to warn when incorrectly calling oneOf(string, string)"):
                a = pp.oneOf('A', 'B')


class EnableDebugOnNamedExpressionsTest(ParseTestCase):
    """
     - enable_debug_on_named_expressions - flag to auto-enable debug on all subsequent
       calls to ParserElement.setName() (default=False)
    """
    def runTest(self):
        import pyparsing as pp
        import textwrap

        with resetting(pp.__diag__, "enable_debug_on_named_expressions"):
            test_stdout = StringIO()

            with resetting(sys, 'stdout', 'stderr'):
                sys.stdout = test_stdout
                sys.stderr = test_stdout

                pp.__diag__.enable("enable_debug_on_named_expressions")
                integer = pp.Word(pp.nums).setName('integer')

                integer[...].parseString("1 2 3")

            expected_debug_output = textwrap.dedent("""\
                Match integer at loc 0(1,1)
                Matched integer -> ['1']
                Match integer at loc 1(1,2)
                Matched integer -> ['2']
                Match integer at loc 3(1,4)
                Matched integer -> ['3']
                Match integer at loc 5(1,6)
                Exception raised:Expected integer, found end of text  (at char 5), (line:1, col:6)
                """)
            output = test_stdout.getvalue()
            print(output)
            self.assertEquals(output,
                              expected_debug_output,
                              "failed to auto-enable debug on named expressions "
                              "using enable_debug_on_named_expressions")


class UndesirableButCommonPracticesTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp
        ppc = pp.pyparsing_common

        # While these are valid constructs, and they are not encouraged
        # there is apparently a lot of code out there using these
        # coding styles.
        #
        # Even though they are not encouraged, we shouldn't break them.

        # Create an And using a list of expressions instead of using '+' operator
        expr = pp.And([pp.Word('abc'), pp.Word('123')])
        expr.runTests("""
            aaa 333
            b 1
            ababab 32123
        """)

        # Passing a single expression to a ParseExpression, when it really wants a sequence
        expr = pp.Or(pp.Or(ppc.integer))
        expr.runTests("""
            123
            456
            abc
        """)

class EnableWarnDiagsTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp
        import pprint

        def filtered_vars(var_dict):
            dunders = [nm for nm in var_dict if nm.startswith('__')]
            return {k: v for k, v in var_dict.items()
                        if isinstance(v, bool) and k not in dunders}

        pprint.pprint(filtered_vars(vars(pp.__diag__)), width=30)

        warn_names = pp.__diag__._warning_names
        other_names = pp.__diag__._debug_names

        # make sure they are off by default
        for diag_name in warn_names:
            self.assertFalse(getattr(pp.__diag__, diag_name), "__diag__.{} not set to True".format(diag_name))

        with resetting(pp.__diag__, *warn_names):
            # enable all warn_* diag_names
            pp.__diag__.enable_all_warnings()
            pprint.pprint(filtered_vars(vars(pp.__diag__)), width=30)

            # make sure they are on after being enabled
            for diag_name in warn_names:
                self.assertTrue(getattr(pp.__diag__, diag_name), "__diag__.{} not set to True".format(diag_name))

            # non-warn diag_names must be enabled individually
            for diag_name in other_names:
                self.assertFalse(getattr(pp.__diag__, diag_name), "__diag__.{} not set to True".format(diag_name))

        # make sure they are off after AutoReset
        for diag_name in warn_names:
            self.assertFalse(getattr(pp.__diag__, diag_name), "__diag__.{} not set to True".format(diag_name))


class WordInternalReRangesTest(ParseTestCase):
    def runTest(self):
        import pyparsing as pp
        import random
        import re

        self.assertEqual(pp.Word(pp.printables).reString, "[!-~]+", "failed to generate correct internal re")
        self.assertEqual(pp.Word(pp.alphanums).reString, "[0-9A-Za-z]+", "failed to generate correct internal re")
        self.assertEqual(pp.Word(pp.pyparsing_unicode.Latin1.printables).reString, "[!-~¡-ÿ]+",
                         "failed to generate correct internal re")
        self.assertEqual(pp.Word(pp.alphas8bit).reString, "[À-ÖØ-öø-ÿ]+", "failed to generate correct internal re")

        esc_chars = r"\^-]"
        esc_chars2 = r"*+.?["
        for esc_char in esc_chars + esc_chars2:
            # test escape char as first character in range
            next_char = chr(ord(esc_char) + 1)
            prev_char = chr(ord(esc_char) - 1)
            esc_word = pp.Word(esc_char + next_char)
            expected = r"[{}{}-{}{}]+".format('\\' if esc_char in esc_chars else '', esc_char,
                                              '\\' if next_char in esc_chars else '', next_char)
            print("Testing escape char: {} -> {} re: '{}')".format(esc_char, esc_word, esc_word.reString))
            self.assertEqual(esc_word.reString, expected, "failed to generate correct internal re")
            test_string = ''.join(random.choice([esc_char, next_char]) for __ in range(16))
            print("Match '{}' -> {}".format(test_string, test_string == esc_word.parseString(test_string)[0]))
            self.assertEqual(esc_word.parseString(test_string)[0], test_string,
                             "Word using escaped range char failed to parse")

            # test escape char as last character in range
            esc_word = pp.Word(prev_char + esc_char)
            expected = r"[{}{}-{}{}]+".format('\\' if prev_char in esc_chars else '', prev_char,
                                              '\\' if esc_char in esc_chars else '', esc_char)
            print("Testing escape char: {} -> {} re: '{}')".format(esc_char, esc_word, esc_word.reString))
            self.assertEqual(esc_word.reString, expected, "failed to generate correct internal re")
            test_string = ''.join(random.choice([esc_char, prev_char]) for __ in range(16))
            print("Match '{}' -> {}".format(test_string, test_string == esc_word.parseString(test_string)[0]))
            self.assertEqual(esc_word.parseString(test_string)[0], test_string,
                             "Word using escaped range char failed to parse")

            # test escape char as first character in range
            next_char = chr(ord(esc_char) + 1)
            prev_char = chr(ord(esc_char) - 1)
            esc_word = pp.Word(esc_char + next_char)
            expected = r"[{}{}-{}{}]+".format('\\' if esc_char in esc_chars else '', esc_char,
                                              '\\' if next_char in esc_chars else '', next_char)
            print("Testing escape char: {} -> {} re: '{}')".format(esc_char, esc_word, esc_word.reString))
            self.assertEqual(esc_word.reString, expected, "failed to generate correct internal re")
            test_string = ''.join(random.choice([esc_char, next_char]) for __ in range(16))
            print("Match '{}' -> {}".format(test_string, test_string == esc_word.parseString(test_string)[0]))
            self.assertEqual(esc_word.parseString(test_string)[0], test_string,
                             "Word using escaped range char failed to parse")

            # test escape char as only character in range
            esc_word = pp.Word(esc_char + esc_char, pp.alphas.upper())
            expected = r"[{}{}][A-Z]*".format('\\' if esc_char in esc_chars else '', esc_char)
            print("Testing escape char: {} -> {} re: '{}')".format(esc_char, esc_word, esc_word.reString))
            self.assertEqual(esc_word.reString, expected, "failed to generate correct internal re")
            test_string = esc_char + ''.join(random.choice(pp.alphas.upper()) for __ in range(16))
            print("Match '{}' -> {}".format(test_string, test_string == esc_word.parseString(test_string)[0]))
            self.assertEqual(esc_word.parseString(test_string)[0], test_string,
                             "Word using escaped range char failed to parse")

            # test escape char as only character
            esc_word = pp.Word(esc_char, pp.alphas.upper())
            expected = r"{}[A-Z]*".format(re.escape(esc_char))
            print("Testing escape char: {} -> {} re: '{}')".format(esc_char, esc_word, esc_word.reString))
            self.assertEqual(esc_word.reString, expected, "failed to generate correct internal re")
            test_string = esc_char + ''.join(random.choice(pp.alphas.upper()) for __ in range(16))
            print("Match '{}' -> {}".format(test_string, test_string == esc_word.parseString(test_string)[0]))
            self.assertEqual(esc_word.parseString(test_string)[0], test_string,
                             "Word using escaped range char failed to parse")
            print()


class MiscellaneousParserTests(ParseTestCase):
    def runTest(self):

        runtests = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if IRON_PYTHON_ENV:
            runtests = "ABCDEGHIJKLMNOPQRSTUVWXYZ"

        # test making oneOf with duplicate symbols
        if "A" in runtests:
            print("verify oneOf handles duplicate symbols")
            try:
                test1 = pp.oneOf("a b c d a")
            except RuntimeError:
                self.assertTrue(False, "still have infinite loop in oneOf with duplicate symbols (string input)")

            print("verify oneOf handles generator input")
            try:
                test1 = pp.oneOf(c for c in "a b c d a" if not c.isspace())
            except RuntimeError:
                self.assertTrue(False, "still have infinite loop in oneOf with duplicate symbols (generator input)")

            print("verify oneOf handles list input")
            try:
                test1 = pp.oneOf("a b c d a".split())
            except RuntimeError:
                self.assertTrue(False, "still have infinite loop in oneOf with duplicate symbols (list input)")

            print("verify oneOf handles set input")
            try:
                test1 = pp.oneOf(set("a b c d a"))
            except RuntimeError:
                self.assertTrue(False, "still have infinite loop in oneOf with duplicate symbols (set input)")

        # test MatchFirst bugfix
        if "B" in runtests:
            print("verify MatchFirst iterates properly")
            results = pp.quotedString.parseString("'this is a single quoted string'")
            self.assertTrue(len(results) > 0, "MatchFirst error - not iterating over all choices")

        # verify streamline of subexpressions
        if "C" in runtests:
            print("verify proper streamline logic")
            compound = pp.Literal("A") + "B" + "C" + "D"
            self.assertEqual(len(compound.exprs), 2, "bad test setup")
            print(compound)
            compound.streamline()
            print(compound)
            self.assertEqual(len(compound.exprs), 4, "streamline not working")

        # test for Optional with results name and no match
        if "D" in runtests:
            print("verify Optional's do not cause match failure if have results name")
            testGrammar = pp.Literal("A") + pp.Optional("B")("gotB") + pp.Literal("C")
            try:
                testGrammar.parseString("ABC")
                testGrammar.parseString("AC")
            except pp.ParseException as pe:
                print(pe.pstr, "->", pe)
                self.assertTrue(False, "error in Optional matching of string %s" % pe.pstr)

        # test return of furthest exception
        if "E" in runtests:
            testGrammar = (pp.Literal("A") |
                            (pp.Optional("B") + pp.Literal("C")) |
                            pp.Literal("D"))
            try:
                testGrammar.parseString("BC")
                testGrammar.parseString("BD")
            except pp.ParseException as pe:
                print(pe.pstr, "->", pe)
                self.assertEqual(pe.pstr, "BD", "wrong test string failed to parse")
                self.assertEqual(pe.loc, 1, "error in Optional matching, pe.loc=" + str(pe.loc))

        # test validate
        if "F" in runtests:
            print("verify behavior of validate()")
            def testValidation(grmr, gnam, isValid):
                try:
                    grmr.streamline()
                    grmr.validate()
                    self.assertTrue(isValid, "validate() accepted invalid grammar " + gnam)
                except pp.RecursiveGrammarException as e:
                    print(grmr)
                    self.assertFalse(isValid, "validate() rejected valid grammar " + gnam)

            fwd = pp.Forward()
            g1 = pp.OneOrMore((pp.Literal("A") + "B" + "C") | fwd)
            g2 = ("C" + g1)[...]
            fwd << pp.Group(g2)
            testValidation(fwd, "fwd", isValid=True)

            fwd2 = pp.Forward()
            fwd2 << pp.Group("A" | fwd2)
            testValidation(fwd2, "fwd2", isValid=False)

            fwd3 = pp.Forward()
            fwd3 << pp.Optional("A") + fwd3
            testValidation(fwd3, "fwd3", isValid=False)

        # test getName
        if "G" in runtests:
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
            self.assertEqual(names, [None, 'B', 'B', 'A', 'B', 'B', 'A', 'B', None, 'B', 'A'],
                             "failure in getting names for tokens")

            from pyparsing import Keyword, Word, alphas, OneOrMore
            IF, AND, BUT = map(Keyword, "if and but".split())
            ident = ~(IF | AND | BUT) + Word(alphas)("non-key")
            scanner = OneOrMore(IF | AND | BUT | ident)
            def getNameTester(s, l, t):
                print(t, t.getName())
            ident.addParseAction(getNameTester)
            scanner.parseString("lsjd sldkjf IF Saslkj AND lsdjf")

        # test ParseResults.get() method
        if "H" in runtests:
            print("verify behavior of ParseResults.get()")
            # use sum() to merge separate groups into single ParseResults
            res = sum(g1.parseString(teststring)[1:])
            print(res.dump())
            print(res.get("A", "A not found"))
            print(res.get("D", "!D"))
            self.assertEqual(res.get("A", "A not found"), "aaa", "get on existing key failed")
            self.assertEqual(res.get("D", "!D"), "!D", "get on missing key failed")

        if "I" in runtests:
            print("verify handling of Optional's beyond the end of string")
            testGrammar = "A" + pp.Optional("B") + pp.Optional("C") + pp.Optional("D")
            testGrammar.parseString("A")
            testGrammar.parseString("AB")

        # test creating Literal with empty string
        if "J" in runtests:
            print('verify non-fatal usage of Literal("")')
            with self.assertWarns(SyntaxWarning, msg="failed to warn use of empty string for Literal"):
                e = pp.Literal("")
            try:
                e.parseString("SLJFD")
            except Exception as e:
                self.assertTrue(False, "Failed to handle empty Literal")

        # test line() behavior when starting at 0 and the opening line is an \n
        if "K" in runtests:
            print('verify correct line() behavior when first line is empty string')
            self.assertEqual(pp.line(0, "\nabc\ndef\n"), '', "Error in line() with empty first line in text")
            txt = "\nabc\ndef\n"
            results = [pp.line(i, txt) for i in range(len(txt))]
            self.assertEqual(results, ['', 'abc', 'abc', 'abc', 'abc', 'def', 'def', 'def', 'def'],
                             "Error in line() with empty first line in text")
            txt = "abc\ndef\n"
            results = [pp.line(i, txt) for i in range(len(txt))]
            self.assertEqual(results, ['abc', 'abc', 'abc', 'abc', 'def', 'def', 'def', 'def'],
                             "Error in line() with non-empty first line in text")

        # test bugfix with repeated tokens when packrat parsing enabled
        if "L" in runtests:
            print('verify behavior with repeated tokens when packrat parsing is enabled')
            a = pp.Literal("a")
            b = pp.Literal("b")
            c = pp.Literal("c")

            abb = a + b + b
            abc = a + b + c
            aba = a + b + a
            grammar = abb | abc | aba

            self.assertEqual(''.join(grammar.parseString("aba")), 'aba', "Packrat ABA failure!")

        if "M" in runtests:
            print('verify behavior of setResultsName with OneOrMore and ZeroOrMore')

            stmt = pp.Keyword('test')
            print(stmt[...]('tests').parseString('test test').tests)
            print(stmt[1, ...]('tests').parseString('test test').tests)
            print(pp.Optional(stmt[1, ...]('tests')).parseString('test test').tests)
            print(pp.Optional(stmt[1, ...])('tests').parseString('test test').tests)
            print(pp.Optional(pp.delimitedList(stmt))('tests').parseString('test,test').tests)
            self.assertEqual(len(stmt[...]('tests').parseString('test test').tests), 2, "ZeroOrMore failure with setResultsName")
            self.assertEqual(len(stmt[1, ...]('tests').parseString('test test').tests), 2, "OneOrMore failure with setResultsName")
            self.assertEqual(len(pp.Optional(stmt[1, ...]('tests')).parseString('test test').tests), 2, "OneOrMore failure with setResultsName")
            self.assertEqual(len(pp.Optional(pp.delimitedList(stmt))('tests').parseString('test,test').tests), 2, "delimitedList failure with setResultsName")
            self.assertEqual(len((stmt * 2)('tests').parseString('test test').tests), 2, "multiplied(1) failure with setResultsName")
            self.assertEqual(len(stmt[..., 2]('tests').parseString('test test').tests), 2, "multiplied(2) failure with setResultsName")
            self.assertEqual(len(stmt[1, ...]('tests').parseString('test test').tests), 2, "multipled(3) failure with setResultsName")
            self.assertEqual(len(stmt[2, ...]('tests').parseString('test test').tests), 2, "multipled(3) failure with setResultsName")

def makeTestSuite():
    import inspect
    suite = TestSuite()
    suite.addTest(PyparsingTestInit())

    test_case_classes = ParseTestCase.__subclasses__()
    # put classes in order as they are listed in the source code
    test_case_classes.sort(key=lambda cls: inspect.getsourcelines(cls)[1])

    test_case_classes.remove(PyparsingTestInit)
    # test_case_classes.remove(ParseASMLTest)
    if IRON_PYTHON_ENV:
        test_case_classes.remove(OriginalTextForTest)

    suite.addTests(T() for T in test_case_classes)

    if TEST_USING_PACKRAT:
        # retest using packrat parsing (disable those tests that aren't compatible)
        suite.addTest(EnablePackratParsing())

        unpackrattables = [PyparsingTestInit, EnablePackratParsing, RepeaterTest,]

        # add tests to test suite a second time, to run with packrat parsing
        # (leaving out those that we know wont work with packrat)
        packratTests = [t.__class__() for t in suite._tests
                            if t.__class__ not in unpackrattables]
        suite.addTests(packratTests)

    return suite

def makeTestSuiteTemp(classes):
    suite = TestSuite()
    suite.addTest(PyparsingTestInit())
    suite.addTests(cls() for cls in classes)
    return suite

# runnable from setup.py using "python setup.py test -s unitTests.suite"
suite = makeTestSuite()


if __name__ == '__main__':

    # run specific tests by including them in this list, otherwise
    # all tests will be run
    testclasses = [
        ]

    if not testclasses:
        testRunner = TextTestRunner()
        result = testRunner.run(suite)
    else:
        # disable chaser '.' display
        testRunner = TextTestRunner(verbosity=0)
        BUFFER_OUTPUT = False
        result = testRunner.run(makeTestSuiteTemp(testclasses))

    sys.stdout.flush()
    exit(0 if result.wasSuccessful() else 1)
