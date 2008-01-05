# -*- coding: UTF-8 -*-
from unittest import TestCase, TestSuite, TextTestRunner
from pyparsing import ParseException
import HTMLTestRunner

import sys
import pprint
import pdb

TEST_USING_PACKRAT = True

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
        assert 1==1, "we've got bigger problems..."
        
    def tearDown(self):
        pass
"""

class ParseTestCase(TestCase):
    def setUp(self):
        print ">>>> Starting test",str(self)
    
    def runTest(self):
        pass
        
    def tearDown(self):
        print "<<<< End of test",str(self)
        print  
        
    def __str__(self):
        return self.__class__.__name__
        
class PyparsingTestInit(ParseTestCase):
    def setUp(self):
        from pyparsing import __version__ as pyparsingVersion
        print "Beginning test of pyparsing, version", pyparsingVersion
        print "Python version", sys.version
    def tearDown(self):
        pass
        
class ParseASMLTest(ParseTestCase):
    def runTest(self):
        import parseASML
        files = [ ("A52759.txt", 2150, True, True, 0.38, 25, "21:47:17", "22:07:32", 235),
                  ("24141506_P5107RM59_399A1457N1_PHS04", 373,True, True, 0.5, 1, "11:35:25", "11:37:05", 183),
                  ("24141506_P5107RM59_399A1457N1_PHS04B", 373, True, True, 0.5, 1, "01:02:54", "01:04:49", 186),
                  ("24157800_P5107RM74_399A1828M1_PHS04", 1141, True, False, 0.5, 13, "00:00:54", "23:59:48", 154) ]
        for testFile,numToks,trkInpUsed,trkOutpUsed,maxDelta,numWafers,minProcBeg,maxProcEnd,maxLevStatsIV in files:
            print "Parsing",testFile,"...",
            #~ text = "\n".join( [ line for line in file(testFile) ] )
            #~ results = parseASML.BNF().parseString( text )
            results = parseASML.BNF().parseFile( testFile )
            #~ pprint.pprint( results.asList() )
            #~ pprint.pprint( results.batchData.asList() )
            #~ print results.batchData.keys()
                    
            allToks = flatten( results.asList() )
            assert len(allToks) == numToks, \
                "wrong number of tokens parsed (%s), got %d, expected %d" % (testFile, len(allToks),numToks)
            assert results.batchData.trackInputUsed == trkInpUsed, "error evaluating results.batchData.trackInputUsed"
            assert results.batchData.trackOutputUsed == trkOutpUsed, "error evaluating results.batchData.trackOutputUsed"
            assert results.batchData.maxDelta == maxDelta,"error evaluating results.batchData.maxDelta"
            assert len(results.waferData) == numWafers, "did not read correct number of wafers"
            assert min([wd.procBegin for wd in results.waferData]) == minProcBeg, "error reading waferData.procBegin"
            assert max([results.waferData[k].procEnd for k in range(len(results.waferData))]) == maxProcEnd, "error reading waferData.procEnd"
            assert sum(results.levelStatsIV['MAX']) == maxLevStatsIV, "error reading levelStatsIV"
            assert sum(results.levelStatsIV.MAX) == maxLevStatsIV, "error reading levelStatsIV"
            print "OK"
            print testFile,len(allToks)
            #~ print "results.batchData.trackInputUsed =",results.batchData.trackInputUsed
            #~ print "results.batchData.trackOutputUsed =",results.batchData.trackOutputUsed
            #~ print "results.batchData.maxDelta =",results.batchData.maxDelta
            #~ print len(results.waferData)," wafers"
            #~ print min([wd.procBegin for wd in results.waferData])
            #~ print max([results.waferData[k].procEnd for k in range(len(results.waferData))])
            #~ print sum(results.levelStatsIV['MAX.'])
        

class ParseFourFnTest(ParseTestCase):
    def runTest(self):
        import fourFn
        def test(s,ans):
            fourFn.exprStack = []
            results = fourFn.BNF().parseString( s )
            resultValue = fourFn.evaluateStack( fourFn.exprStack )
            assert resultValue == ans, "failed to evaluate %s, got %f" % ( s, resultValue )
            print s, "->", resultValue
            
        test( "9", 9 )
        test( "9 + 3 + 6", 18 )
        test( "9 + 3 / 11", 9.0+3.0/11.0)
        test( "(9 + 3)", 12 )
        test( "(9+3) / 11", (9.0+3.0)/11.0 )
        test( "9 - (12 - 6)", 3)
        test( "2*3.14159", 6.28318)
        test( "3.1415926535*3.1415926535 / 10", 3.1415926535*3.1415926535/10.0 )
        test( "PI * PI / 10", 3.1415926535*3.1415926535/10.0 )
        test( "PI*PI/10", 3.1415926535*3.1415926535/10.0 )
        test( "6.02E23 * 8.048", 6.02E23 * 8.048 )
        test( "e / 3", 2.718281828/3.0 )
        test( "sin(PI/2)", 1.0 )
        test( "trunc(E)", 2.0 )
        test( "E^PI", 2.718281828**3.1415926535 )
        test( "2^3^2", 2**3**2)
        test( "2^3+2", 2**3+2)
        test( "2^9", 2**9 )
        test( "sgn(-2)", -1 )
        test( "sgn(0)", 0 )
        test( "sgn(0.1)", 1 )

class ParseSQLTest(ParseTestCase):
    def runTest(self):
        import simpleSQL
        
        def test(s, numToks, errloc=-1 ):
            try:
                sqlToks = flatten( simpleSQL.simpleSQL.parseString(s).asList() )
                print s,sqlToks,len(sqlToks)
                assert len(sqlToks) == numToks
            except ParseException, e:
                if errloc >= 0:
                    assert e.loc == errloc
                    
            
        test( "SELECT * from XYZZY, ABC", 6 )
        test( "select * from SYS.XYZZY", 5 )
        test( "Select A from Sys.dual", 5 )
        test( "Select A,B,C from Sys.dual", 7 )
        test( "Select A, B, C from Sys.dual", 7 )
        test( "Select A, B, C from Sys.dual, Table2   ", 8 )
        test( "Xelect A, B, C from Sys.dual", 0, 0 )
        test( "Select A, B, C frox Sys.dual", 0, 15 )
        test( "Select", 0, 6 )
        test( "Select &&& frox Sys.dual", 0, 7 )
        test( "Select A from Sys.dual where a in ('RED','GREEN','BLUE')", 12 )
        test( "Select A from Sys.dual where a in ('RED','GREEN','BLUE') and b in (10,20,30)", 20 )
        test( "Select A,b from table1,table2 where table1.id eq table2.id -- test out comparison operators", 10 )

class ParseConfigFileTest(ParseTestCase):
    def runTest(self):
        import configParse
        
        def test(fnam,numToks,resCheckList):
            print "Parsing",fnam,"...",
            iniFileLines = "\n".join([ lin for lin in file(fnam) ])
            iniData = configParse.inifile_BNF().parseString( iniFileLines )
            print len(flatten(iniData.asList()))
            #~ pprint.pprint( iniData.asList() )
            #~ pprint.pprint( repr(iniData) )
            #~ print len(iniData), len(flatten(iniData.asList()))
            print iniData.keys()
            #~ print iniData.users.keys()
            #~ print
            assert len(flatten(iniData.asList())) == numToks, "file %s not parsed correctly" % fnam
            for chk in resCheckList:
                print chk[0], eval("iniData."+chk[0]), chk[1]
                assert eval("iniData."+chk[0]) == chk[1]
            print "OK"
            
        test("karthik.ini", 23, 
                [ ("users.K","8"), 
                  ("users.mod_scheme","'QPSK'"),
                  ("users.Na", "K+2") ]
                  )
        test("setup.ini", 125, 
                [ ("Startup.audioinf", "M3i"),
                  ("Languages.key1", "0x0003"),
                  ("test.foo","bar") ] )

class ParseJSONDataTest(ParseTestCase):
    def runTest(self):
        from jsonParser import jsonObject
        from jsonParserFull import test1,test2,test3,test4,test5
        
        expected = [
            [],
            [],
            [],
            [],
            [],
            ]
            
        import pprint
        for t,exp in zip((test1,test2,test3,test4,test5),expected):
            result = jsonObject.parseString(t)
##            print result.dump()
            pprint.pprint(result.asList())
            print
##            if result.asList() != exp:
##                print "Expected %s, parsed results as %s" % (exp, result.asList())

class ParseCommaSeparatedValuesTest(ParseTestCase):
    def runTest(self):
        from pyparsing import commaSeparatedList
        import string
        
        testData = [
            "a,b,c,100.2,,3",
            "d, e, j k , m  ",
            "'Hello, World', f, g , , 5.1,x",
            "John Doe, 123 Main St., Cleveland, Ohio",
            "Jane Doe, 456 St. James St., Los Angeles , California   ",
            "",
            ]
        testVals = [
            [ (3,'100.2'), (4,''), (5, '3') ],
            [ (2, 'j k'), (3, 'm') ],
            [ (0, "'Hello, World'"), (2, 'g'), (3, '') ],
            [ (0,'John Doe'), (1, '123 Main St.'), (2, 'Cleveland'), (3, 'Ohio') ], 
            [ (0,'Jane Doe'), (1, '456 St. James St.'), (2, 'Los Angeles'), (3, 'California') ]
            ]
        for line,tests in zip(testData, testVals):
            print "Parsing: \""+line+"\" ->",
            results = commaSeparatedList.parseString(line)
            print results.asList()
            for t in tests:
                if not(len(results)>t[0] and results[t[0]] == t[1]):
                    print "$$$", results.dump()
                    print "$$$", results[0]
                assert len(results)>t[0] and results[t[0]] == t[1],"failed on %s, item %d s/b '%s', got '%s'" % ( line, t[0], t[1], str(results.asList()) )

class ParseEBNFTest(ParseTestCase):
    def runTest(self):
        import ebnf
        from pyparsing import Word, quotedString, alphas, nums,ParserElement
        
        print 'Constructing EBNF parser with pyparsing...'
        
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
        table['meta_identifier'] = Word(alphas+"_", alphas+"_"+nums)
        table['integer'] = Word(nums)
        
        print 'Parsing EBNF grammar with EBNF parser...'
        parsers = ebnf.parse(grammar, table)
        ebnf_parser = parsers['syntax']
        #~ print ",\n ".join( str(parsers.keys()).split(", ") )
        print "-","\n- ".join( parsers.keys() )
        assert len(parsers.keys()) == 13, "failed to construct syntax grammar"

        print 'Parsing EBNF grammar with generated EBNF parser...'
        parsed_chars = ebnf_parser.parseString(grammar)
        parsed_char_len = len(parsed_chars)
        
        print "],\n".join(str( parsed_chars.asList() ).split("],"))
        assert len(flatten(parsed_chars.asList())) == 98, "failed to tokenize grammar correctly"
        

class ParseIDLTest(ParseTestCase):
    def runTest(self):
        import idlParse

        def test( strng, numToks, errloc=0 ):
            #~ print strng
            try:
                bnf = idlParse.CORBA_IDL_BNF()
                tokens = flatten( bnf.parseString( strng ).asList() )
                #~ print "tokens = "
                #~ pprint.pprint( tokens.asList() )
                #~ print len(tokens)
                assert len(tokens) == numToks, "error matching IDL string, %s -> %s" % (strng, str(tokens) )
            except ParseException, err:
                #~ print err.line
                #~ print " "*(err.column-1) + "^"
                #~ print err
                assert numToks == 0, "unexpected ParseException while parsing %s, %s" % (strng, str(err) )
                assert err.loc == errloc, "expected ParseException at %d, found exception at %d" % (errloc, err.loc)
            
        test(
            """
            /*
             * a block comment *
             */
            typedef string[10] tenStrings;
            typedef sequence<string> stringSeq;
            typedef sequence< sequence<string> > stringSeqSeq;
            
            interface QoSAdmin {
                stringSeq method1( in string arg1, inout long arg2 );
                stringSeqSeq method2( in string arg1, inout long arg2, inout long arg3);
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
                stringSeq method1( in string arg1, inout long arg2 );
                stringSeqSeq method2( in string arg1, inout long arg2, inout long arg3);
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
                void method1( in string arg1, inout long arg2 );
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
                void method1( in string arg1, inout long arg2 ) 
                  raises ( TestException );
                };
              };
            """, 0, 57
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

class RunExamplesTest(ParseTestCase):
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
        ipAddress = Combine( integer + "." + integer + "." + integer + "." + integer )
        tdStart = Suppress("<td>")
        tdEnd = Suppress("</td>")
        timeServerPattern =  tdStart + ipAddress.setResultsName("ipAddr") + tdEnd + \
                tdStart + CharsNotIn("<").setResultsName("loc") + tdEnd
        servers = \
            [ srvr.ipAddr for srvr,startloc,endloc in timeServerPattern.scanString( testdata ) ]
            
        print servers
        assert servers == ['129.6.15.28', '129.6.15.29', '132.163.4.101', '132.163.4.102', '132.163.4.103'], \
            "failed scanString()"
        
        # test for stringEnd detection in scanString
        foundStringEnds = [ r for r in StringEnd().scanString("xyzzy") ]
        print foundStringEnds
        assert foundStringEnds, "Failed to find StringEnd in scanString"
            
class QuotedStringsTest(ParseTestCase):
    def runTest(self):
        from pyparsing import sglQuotedString,dblQuotedString,quotedString
        testData = \
            """
                'a valid single quoted string'
                'an invalid single quoted string
                 because it spans lines'
                "a valid double quoted string"
                "an invalid double quoted string
                 because it spans lines"
            """
        print testData
        sglStrings = [ (t[0],b,e) for (t,b,e) in sglQuotedString.scanString(testData) ]
        print sglStrings
        assert len(sglStrings) == 1 and (sglStrings[0][1]==17 and sglStrings[0][2]==47), \
            "single quoted string failure"
        dblStrings = [ (t[0],b,e) for (t,b,e) in dblQuotedString.scanString(testData) ]
        print dblStrings
        assert len(dblStrings) == 1 and (dblStrings[0][1]==154 and dblStrings[0][2]==184), \
            "double quoted string failure"
        allStrings = [ (t[0],b,e) for (t,b,e) in quotedString.scanString(testData) ]
        print allStrings
        assert len(allStrings) == 2 and (allStrings[0][1]==17 and allStrings[0][2]==47) and \
                                         (allStrings[1][1]==154 and allStrings[1][2]==184), \
            "quoted string failure"
        
        escapedQuoteTest = \
            r"""
                'This string has an escaped (\') quote character'
                "This string has an escaped (\") quote character"
            """
        sglStrings = [ (t[0],b,e) for (t,b,e) in sglQuotedString.scanString(escapedQuoteTest) ]
        print sglStrings
        assert len(sglStrings) == 1 and (sglStrings[0][1]==17 and sglStrings[0][2]==66), \
            "single quoted string escaped quote failure (%s)" % str(sglStrings[0])
        dblStrings = [ (t[0],b,e) for (t,b,e) in dblQuotedString.scanString(escapedQuoteTest) ]
        print dblStrings
        assert len(dblStrings) == 1 and (dblStrings[0][1]==83 and dblStrings[0][2]==132), \
            "double quoted string escaped quote failure (%s)" % str(dblStrings[0])
        allStrings = [ (t[0],b,e) for (t,b,e) in quotedString.scanString(escapedQuoteTest) ]
        print allStrings
        assert len(allStrings) == 2 and (allStrings[0][1]==17 and allStrings[0][2]==66 and
                                          allStrings[1][1]==83 and allStrings[1][2]==132), \
            "quoted string escaped quote failure (%s)" % ([str(s[0]) for s in allStrings])
        
        dblQuoteTest = \
            r"""
                'This string has an doubled ('') quote character'
                "This string has an doubled ("") quote character"
            """
        sglStrings = [ (t[0],b,e) for (t,b,e) in sglQuotedString.scanString(dblQuoteTest) ]
        print sglStrings
        assert len(sglStrings) == 1 and (sglStrings[0][1]==17 and sglStrings[0][2]==66), \
            "single quoted string escaped quote failure (%s)" % str(sglStrings[0])
        dblStrings = [ (t[0],b,e) for (t,b,e) in dblQuotedString.scanString(dblQuoteTest) ]
        print dblStrings
        assert len(dblStrings) == 1 and (dblStrings[0][1]==83 and dblStrings[0][2]==132), \
            "double quoted string escaped quote failure (%s)" % str(dblStrings[0])
        allStrings = [ (t[0],b,e) for (t,b,e) in quotedString.scanString(dblQuoteTest) ]
        print allStrings
        assert len(allStrings) == 2 and (allStrings[0][1]==17 and allStrings[0][2]==66 and
                                          allStrings[1][1]==83 and allStrings[1][2]==132), \
            "quoted string escaped quote failure (%s)" % ([str(s[0]) for s in allStrings])
        
class CaselessOneOfTest(ParseTestCase):
    def runTest(self):
        from pyparsing import oneOf,ZeroOrMore
        
        caseless1 = oneOf("d a b c aA B A C", caseless=True)
        caseless1str = str( caseless1 )
        print caseless1str
        caseless2 = oneOf("d a b c Aa B A C", caseless=True)
        caseless2str = str( caseless2 )
        print caseless2str
        assert caseless1str.upper() == caseless2str.upper(), "oneOf not handling caseless option properly"
        assert caseless1str != caseless2str, "Caseless option properly sorted"
        
        res = ZeroOrMore(caseless1).parseString("AAaaAaaA")
        print res
        assert len(res) == 4, "caseless1 oneOf failed"
        assert "".join(res) == "aA"*4,"caseless1 CaselessLiteral return failed"
        
        res = ZeroOrMore(caseless2).parseString("AAaaAaaA")
        print res
        assert len(res) == 4, "caseless2 oneOf failed"
        assert "".join(res) == "Aa"*4,"caseless1 CaselessLiteral return failed"
        

class AsXMLTest(ParseTestCase):
    def runTest(self):
        
        import pyparsing
        # test asXML()
        
        aaa = pyparsing.Word("a").setResultsName("A")
        bbb = pyparsing.Group(pyparsing.Word("b")).setResultsName("B")
        ccc = pyparsing.Combine(":" + pyparsing.Word("c")).setResultsName("C")
        g1 = "XXX>&<" + pyparsing.ZeroOrMore( aaa | bbb | ccc )
        teststring = "XXX>&< b b a b b a b :c b a"
        #~ print teststring
        print "test including all items"
        xml = g1.parseString(teststring).asXML("TEST",namedItemsOnly=False)
        assert xml=="\n".join(["",
                                "<TEST>",
                                "  <ITEM>XXX&gt;&amp;&lt;</ITEM>",
                                "  <B>",
                                "    <ITEM>b</ITEM>",
                                "  </B>",
                                "  <B>",
                                "    <ITEM>b</ITEM>",
                                "  </B>",
                                "  <A>a</A>",
                                "  <B>",
                                "    <ITEM>b</ITEM>",
                                "  </B>",
                                "  <B>",
                                "    <ITEM>b</ITEM>",
                                "  </B>",
                                "  <A>a</A>",
                                "  <B>",
                                "    <ITEM>b</ITEM>",
                                "  </B>",
                                "  <C>:c</C>",
                                "  <B>",
                                "    <ITEM>b</ITEM>",
                                "  </B>",
                                "  <A>a</A>",
                                "</TEST>",
                                ] ), \
            "failed to generate XML correctly showing all items: \n[" + xml + "]"
        print "test filtering unnamed items"
        xml = g1.parseString(teststring).asXML("TEST",namedItemsOnly=True)
        assert xml=="\n".join(["",
                                "<TEST>",
                                "  <B>",
                                "    <ITEM>b</ITEM>",
                                "  </B>",
                                "  <B>",
                                "    <ITEM>b</ITEM>",
                                "  </B>",
                                "  <A>a</A>",
                                "  <B>",
                                "    <ITEM>b</ITEM>",
                                "  </B>",
                                "  <B>",
                                "    <ITEM>b</ITEM>",
                                "  </B>",
                                "  <A>a</A>",
                                "  <B>",
                                "    <ITEM>b</ITEM>",
                                "  </B>",
                                "  <C>:c</C>",
                                "  <B>",
                                "    <ITEM>b</ITEM>",
                                "  </B>",
                                "  <A>a</A>",
                                "</TEST>", 
                                ] ), \
            "failed to generate XML correctly, filtering unnamed items: " + xml

class AsXMLTest2(ParseTestCase):
    def runTest(self):
        from pyparsing import Suppress,Optional,CharsNotIn,Combine,ZeroOrMore,Word,Group
        
        EndOfLine = Word("\n").setParseAction(lambda s,l,t: [' '])
        whiteSpace=Word('\t ')
        Mexpr = Suppress(Optional(whiteSpace)) + CharsNotIn('\\"\t \n') + Optional(" ") + \
                Suppress(Optional(whiteSpace))
        reducedString = Combine(Mexpr + ZeroOrMore(EndOfLine + Mexpr))
        
        QuotedReducedString = Combine( Suppress(_dblQuote) + ZeroOrMore( reducedString |
                                                                         _escapedChar ) + \
                                       Suppress(_dblQuote )).streamline()
        
        Manifest_string = QuotedReducedString.setResultsName('manifest_string')
        
        Identifier  = Word( alphas, alphanums+ '_$' ).setResultsName("identifier")
        Index_string = CharsNotIn('\\";\n')
        Index_string.setName('index_string')
        Index_term_list = (
                Group(delimitedList(Manifest_string, delim=',')) | \
                Index_string
                ).setResultsName('value')
        
        IndexKey = Identifier.setResultsName('key')
        IndexKey.setName('key')
        Index_clause = Group(IndexKey + Suppress(':') + Optional(Index_term_list))
        Index_clause.setName('index_clause')
        Index_list = Index_clause.setResultsName('index') 
        Index_list.setName('index_list')
        Index_block = Group('indexing' + Group(OneOrMore(Index_list + Suppress(';')))).setResultsName('indexes')
        

class CommentParserTest(ParseTestCase):
    def runTest(self):
        import pyparsing
        print "verify processing of C and HTML comments"
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
        foundLines = [ pyparsing.lineno(s,testdata)
            for t,s,e in pyparsing.cStyleComment.scanString(testdata) ]
        assert foundLines == range(11)[2:],"only found C comments on lines "+str(foundLines)
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
        foundLines = [ pyparsing.lineno(s,testdata)
            for t,s,e in pyparsing.htmlComment.scanString(testdata) ]
        assert foundLines == range(11)[2:],"only found HTML comments on lines "+str(foundLines)

        # test C++ single line comments that have line terminated with '\' (should continue comment to following line)
        testSource = r"""
            // comment1
            // comment2 \
            still comment 2
            // comment 3
            """
        assert len(pyparsing.cppStyleComment.searchString(testSource)[1][0]) == 41, r"failed to match single-line comment with '\' at EOL"

class ParseExpressionResultsTest(ParseTestCase):
    def runTest(self):
        from pyparsing import Word,alphas,OneOrMore,Optional,Group

        a = Word("a",alphas).setName("A")
        b = Word("b",alphas).setName("B")
        c = Word("c",alphas).setName("C")
        ab = (a + b).setName("AB")
        abc = (ab + c).setName("ABC")
        word = Word(alphas).setName("word")
        
        #~ words = OneOrMore(word).setName("words")
        words = Group(OneOrMore(~a + word)).setName("words")
        
        #~ phrase = words.setResultsName("Head") + \
                    #~ ( abc ^ ab ^ a ).setResultsName("ABC") + \
                    #~ words.setResultsName("Tail")
        #~ phrase = words.setResultsName("Head") + \
                    #~ ( abc | ab | a ).setResultsName("ABC") + \
                    #~ words.setResultsName("Tail")
        phrase = words.setResultsName("Head") + \
                    Group( a + Optional(b + Optional(c)) ).setResultsName("ABC") + \
                    words.setResultsName("Tail")
        
        results = phrase.parseString("xavier yeti alpha beta charlie will beaver")
        print results,results.Head, results.ABC,results.Tail
        for key,ln in [("Head",2), ("ABC",3), ("Tail",2)]:
            #~ assert len(results[key]) == ln,"expected %d elements in %s, found %s" % (ln, key, str(results[key].asList()))
            assert len(results[key]) == ln,"expected %d elements in %s, found %s" % (ln, key, str(results[key]))
        

class ParseKeywordTest(ParseTestCase):
    def runTest(self):
        from pyparsing import Literal,Keyword
        
        kw = Keyword("if")
        lit = Literal("if")
        
        def test(s,litShouldPass,kwShouldPass):
            print "Test",s
            print "Match Literal",
            try:
                print lit.parseString(s)
            except:
                print "failed"
                if litShouldPass: assert False, "Literal failed to match %s, should have" % s
            else:
                if not litShouldPass: assert False, "Literal matched %s, should not have" % s
        
            print "Match Keyword",
            try:
                print kw.parseString(s)
            except:
                print "failed"
                if kwShouldPass: assert False, "Keyword failed to match %s, should have" % s
            else:
                if not kwShouldPass: assert False, "Keyword matched %s, should not have" % s
        
        test("ifOnlyIfOnly", True, False)
        test("if(OnlyIfOnly)", True, True)
        test("if (OnlyIf Only)", True, True)
        
        kw = Keyword("if",caseless=True)
        
        test("IFOnlyIfOnly", False, False)
        test("If(OnlyIfOnly)", False, True)
        test("iF (OnlyIf Only)", False, True)



class ParseExpressionResultsAccumulateTest(ParseTestCase):
    def runTest(self):
        from pyparsing import Word,delimitedList,Combine,alphas,nums

        num=Word(nums).setName("num").setResultsName("base10", listAllMatches=True)
        hexnum=Combine("0x"+ Word(nums)).setName("hexnum").setResultsName("hex", listAllMatches=True)
        name = Word(alphas).setName("word").setResultsName("word", listAllMatches=True)
        list_of_num=delimitedList( hexnum | num | name, "," )
        
        tokens = list_of_num.parseString('1, 0x2, 3, 0x4, aaa')
        for k,llen,lst in ( ("base10",2,['1','3']),
                             ("hex",2,['0x2','0x4']),
                             ("word",1,['aaa']) ):
            print k,tokens[k]
            assert len(tokens[k]) == llen, "Wrong length for key %s, %s" % (k,str(tokens[k].asList()))
            assert lst == tokens[k].asList(), "Incorrect list returned for key %s, %s" % (k,str(tokens[k].asList()))
        assert tokens.base10.asList() == ['1','3'], "Incorrect list for attribute base10, %s" % str(tokens.base10.asList())
        assert tokens.hex.asList() == ['0x2','0x4'], "Incorrect list for attribute hex, %s" % str(tokens.hex.asList())
        assert tokens.word.asList() == ['aaa'], "Incorrect list for attribute word, %s" % str(tokens.word.asList())

        from pyparsing import Literal, Word, nums, Group, Dict, alphas, \
            quotedString, oneOf, delimitedList, removeQuotes, alphanums

        lbrack = Literal("(").suppress()
        rbrack = Literal(")").suppress()
        integer = Word( nums ).setName("int")
        variable = Word( alphas, max=1 ).setName("variable")
        relation_body_item = variable | integer | quotedString.copy().setParseAction(removeQuotes)
        relation_name = Word( alphas+"_", alphanums+"_" )
        relation_body = lbrack + Group(delimitedList(relation_body_item)) + rbrack
        Goal = Dict(Group( relation_name + relation_body ))
        Comparison_Predicate = Group(variable + oneOf("< >") + integer).setResultsName("pred",listAllMatches=True)
        Query = Goal.setResultsName("head") + ":-" + delimitedList(Goal | Comparison_Predicate)

        test="""Q(x,y,z):-Bloo(x,"Mitsis",y),Foo(y,z,1243),y>28,x<12,x>3"""
        
        queryRes = Query.parseString(test)
        print "pred",queryRes.pred
        assert queryRes.pred.asList() == [['y', '>', '28'], ['x', '<', '12'], ['x', '>', '3']], "Incorrect list for attribute pred, %s" % str(queryRes.pred.asList())
        print queryRes.dump()

class ReStringRangeTest(ParseTestCase):
    def runTest(self):
        import pyparsing
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
            )
        expectedResults = (
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "A",
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz",
            " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~",
            " !\"#$%&'()*+,-./0",
            "!\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~",
            #~ "¡¢£¤¥¦§¨©ª«¬­®¯°±²³´µ¶·¸¹º»¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþ",
            u'\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe',
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
            )
        for test in zip( testCases, expectedResults ):
            t,exp = test
            res = pyparsing.srange(t)
            #~ print t,"->",res
            assert res == exp, "srange error, srange(%s)->'%s', expected '%s'" % (t, res, exp)

class SkipToParserTests(ParseTestCase):
    def runTest(self):
        
        from pyparsing import Literal, SkipTo, NotAny, cStyleComment
        
        thingToFind = Literal('working')
        testExpr = SkipTo(Literal(';'), True, cStyleComment) + thingToFind
        
        def tryToParse (someText):
            try:
                print testExpr.parseString(someText)
            except Exception, e:
                print "Exception %s while parsing string %s" % (e,repr(someText))
                assert False, "Exception %s while parsing string %s" % (e,repr(someText))
    
        # This first test works, as the SkipTo expression is immediately following the ignore expression (cStyleComment)
        tryToParse('some text /* comment with ; in */; working')
        # This second test fails, as there is text following the ignore expression, and before the SkipTo expression.
        tryToParse('some text /* comment with ; in */some other stuff; working')


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
        colonQuotes = QuotedString(':','\\','::')
        dashQuotes  = QuotedString('-','\\', '--')
        hatQuotes   = QuotedString('^','\\')
        hatQuotes1  = QuotedString('^','\\','^^')
        dblEqQuotes = QuotedString('==','\\')
        
        def test(quoteExpr, expected):
            print quoteExpr.pattern
            print quoteExpr.searchString(testString)
            print quoteExpr.searchString(testString)[0][0]
            assert quoteExpr.searchString(testString)[0][0] == expected, \
                    "failed to match %s, expected '%s', got '%s'" % \
                    (quoteExpr,expected,quoteExpr.searchString(testString)[0])
        
        test(colonQuotes, r"sdf:jls:djf")
        test(dashQuotes,  r"sdf:jls::-djf: sl")
        test(hatQuotes,   r"sdf:jls")
        test(hatQuotes1,  r"sdf:jls^--djf")
        test(dblEqQuotes, r"sdf:j=ls::--djf: sl")
        test( QuotedString(':::'), 'jls::--djf: sl')
        test( QuotedString('==',endQuoteChar='--'), 'sdf\:j=lz::')
        test( QuotedString('^^^',multiline=True), """==sdf\:j=lz::--djf: sl=^^=kfsjf
            sdlfjs ==sdf\:j=ls::--djf: sl==kfsjf""")
        try:
            bad1 = QuotedString('','\\')
        except SyntaxError,se:
            pass
        else:
            assert False,"failed to raise SyntaxError with empty quote string"

class RepeaterTest(ParseTestCase):
    def runTest(self):
        from pyparsing import matchPreviousLiteral,matchPreviousExpr, Forward, Literal, Word, alphas, nums

        first = Word("abcdef").setName("word1")
        bridge = Word(nums).setName("number")
        second = matchPreviousLiteral(first).setName("repeat(word1)")

        seq = first + bridge + second

        tests = [
            ( "abc12abc", True ),
            ( "abc12aabc", False ),
            ( "abc12cba", True ),
            ( "abc12bca", True ),
        ]

        for tst,result in tests:
            found = False
            for tokens,start,end in seq.scanString(tst):
                f,b,s = tokens
                print f,b,s
                found = True
            if not found:
                print "No literal match in", tst
            assert found == result, "Failed repeater for test: %s, matching %s" % (tst, str(seq))
        print
        seq = first + bridge + second
        csFirst = seq.setName("word-num-word")
        csSecond = matchPreviousLiteral(csFirst)
        compoundSeq = csFirst + ":" + csSecond
        
        first = Word("abcdef").setName("word1")
        bridge = Word(nums).setName("number")
        second = matchPreviousExpr(first).setName("repeat(word1)")
        seq = first + bridge + second
        
        tests = [
            ( "abc12abc", True ),
            ( "abc12cba", False ),
            ( "abc12abcdef", False ),
            ]

        for tst,result in tests:
            found = False
            for tokens,start,end in seq.scanString(tst):
                print tokens.asList()
                found = True
            if not found:
                print "No expression match in", tst
            assert found == result, "Failed repeater for test: %s, matching %s" % (tst, str(seq))
            
        print
        seq = first + bridge + second
        csFirst = seq.setName("word-num-word")
        csSecond = matchPreviousExpr(csFirst)
        compoundSeq = csFirst + ":" + csSecond
        compoundSeq.streamline()
        print compoundSeq
        
        tests = [
            ( "abc12abc:abc12abc", True ),
            ( "abc12cba:abc12abc", False ),
            ( "abc12abc:abc12abcdef", False ),
            ]

        for tst,result in tests:
            found = False
            for tokens,start,end in compoundSeq.scanString(tst):
                print tokens.asList()
                found = True
            if not found:
                print "No expression match in", tst
            assert found == result, "Failed repeater for test: %s, matching %s" % (tst, str(seq))
            
        print
        eFirst = Word(nums)
        eSecond = matchPreviousExpr(eFirst)
        eSeq = eFirst + ":" + eSecond
        
        tests = [
            ( "1:1A", True ),
            ( "1:10", False ),
            ]
        
        for tst,result in tests:
            found = False
            for tokens,start,end in eSeq.scanString(tst):
                #~ f,b,s = tokens
                #~ print f,b,s
                print tokens.asList()
                found = True
            if not found:
                print "No match in", tst
            assert found == result, "Failed repeater for test: %s, matching %s" % (tst, str(seq))

class RecursiveCombineTest(ParseTestCase):
    def runTest(self):
        from pyparsing import Forward,Word,alphas,nums,Optional,Combine
        
        testInput = "myc(114)r(11)dd"
        Stream=Forward()
        Stream << Optional(Word(alphas))+Optional("("+Word(nums)+")"+Stream)
        expected = Stream.parseString(testInput).asList()
        print ["".join(expected)]

        Stream=Forward()
        Stream << Combine(Optional(Word(alphas))+Optional("("+Word(nums)+")"+Stream))
        testVal = Stream.parseString(testInput).asList()
        print testVal
        
        assert "".join(testVal) == "".join(expected), "Failed to process Combine with recursive content"

class OperatorPrecedenceGrammarTest1(ParseTestCase):
    def runTest(self):
        from pyparsing import Word,nums,alphas,Literal,oneOf,operatorPrecedence,opAssoc
        
        integer = Word(nums).setParseAction(lambda t:int(t[0]))
        variable = Word(alphas,exact=1)
        operand = integer | variable

        expop = Literal('^')
        signop = oneOf('+ -')
        multop = oneOf('* /')
        plusop = oneOf('+ -')
        factop = Literal('!')

        expr = operatorPrecedence( operand,
            [("!", 1, opAssoc.LEFT),
             ("^", 2, opAssoc.RIGHT),
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
        expected = map(lambda x:eval(x),expected)
        for t,e in zip(test,expected):
            print t,"->",e, "got", expr.parseString(t).asList()
            assert expr.parseString(t).asList() == e,"mismatched results for operatorPrecedence: got %s, expected %s" % (expr.parseString(t).asList(),e)

class OperatorPrecedenceGrammarTest2(ParseTestCase):
    def runTest(self):

        from pyparsing import operatorPrecedence, Word, alphas, oneOf, opAssoc
        
        boolVars = { "True":True, "False":False }
        class BoolOperand(object):
            def __init__(self,t):
                self.args = t[0][0::2]
            def __str__(self):
                sep = " %s " % self.reprsymbol
                return "(" + sep.join(map(str,self.args)) + ")"
            
        class BoolAnd(BoolOperand):
            reprsymbol = '&'
            def __nonzero__(self):
                for a in self.args:
                    if isinstance(a,basestring):
                        v = boolVars[a]
                    else:
                        v = bool(a)
                    if not v:
                        return False
                return True

        class BoolOr(BoolOperand):
            reprsymbol = '|'    
            def __nonzero__(self):
                for a in self.args:
                    if isinstance(a,basestring):
                        v = boolVars[a]
                    else:
                        v = bool(a)
                    if v:
                        return True
                return False

        class BoolNot(BoolOperand):
            def __init__(self,t):
                self.arg = t[0][1]
            def __str__(self):
                return "~" + str(self.arg)
            def __nonzero__(self):
                if isinstance(self.arg,basestring):
                    v = boolVars[self.arg]
                else:
                    v = bool(self.arg)
                return not v

        boolOperand = Word(alphas,max=1) | oneOf("True False")
        boolExpr = operatorPrecedence( boolOperand,
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
        print "p =", boolVars["p"]
        print "q =", boolVars["q"]
        print "r =", boolVars["r"]
        print
        for t in test:
            res = boolExpr.parseString(t)[0]
            print t,'\n', res, '=', bool(res),'\n'

        
class OperatorPrecedenceGrammarTest3(ParseTestCase):
    def runTest(self):

        from pyparsing import operatorPrecedence, Word, alphas, oneOf, opAssoc, nums, Literal
        
        global count
        count = 0
        
        def evaluate_int(t):
            global count
            value = int(t[0])
            print "evaluate_int", value
            count += 1
            return value

        integer = Word(nums).setParseAction(evaluate_int)
        variable = Word(alphas,exact=1)
        operand = integer | variable

        expop = Literal('^')
        signop = oneOf('+ -')
        multop = oneOf('* /')
        plusop = oneOf('+ -')
        factop = Literal('!')

        expr = operatorPrecedence( operand,
            [
            ("!", 1, opAssoc.LEFT),
            ("^", 2, opAssoc.RIGHT),
            (signop, 1, opAssoc.RIGHT),
            (multop, 2, opAssoc.LEFT),
            (plusop, 2, opAssoc.LEFT),
            ])

        test = ["9"]
        for t in test:
            count = 0
            print "%s => %s" % (t, expr.parseString(t))
            assert count == 1, "count evaluated too many times!"

class OperatorPrecedenceGrammarTest4(ParseTestCase):
    def runTest(self):

        import pyparsing

        word = pyparsing.Word(pyparsing.alphas)

        def supLiteral(s):
            """Returns the suppressed literal s"""
            return pyparsing.Literal(s).suppress()

        def booleanExpr(atom):
            ops = [
                (supLiteral(u"!"), 1, pyparsing.opAssoc.RIGHT, lambda s, l, t: ["!", t[0][0]]),
                (pyparsing.oneOf(u"= !="), 2, pyparsing.opAssoc.LEFT, ),
                (supLiteral(u"&"), 2, pyparsing.opAssoc.LEFT,  lambda s, l, t: ["&", t[0]]),
                (supLiteral(u"|"), 2, pyparsing.opAssoc.LEFT,  lambda s, l, t: ["|", t[0]])]
            return pyparsing.operatorPrecedence(atom, ops)

        f = booleanExpr(word) + pyparsing.StringEnd()

        tests = [
            ("bar = foo", "[['bar', '=', 'foo']]"),
            ("bar = foo & baz = fee", "['&', [['bar', '=', 'foo'], ['baz', '=', 'fee']]]"),
            ]
        for test,expected in tests:
            print test
            results = f.parseString(test)
            print results
            assert str(results) == expected, "failed to match expected results, got '%s'" % str(results)
            print
        

class ParseResultsPickleTest(ParseTestCase):
    def runTest(self):
        from pyparsing import makeHTMLTags
        import pickle
        
        body = makeHTMLTags("BODY")[0]
        result = body.parseString("<BODY BGCOLOR='#00FFBB' FGCOLOR=black>")
        print result.dump()
        print
        
        pickleString = pickle.dumps(result)
        newresult = pickle.loads(pickleString)
        print newresult.dump()
        
        assert result.dump() == newresult.dump(), "Error pickling ParseResults object"

class ParseResultsWithNamedTupleTest(ParseTestCase):
    def runTest(self):

        from pyparsing import Literal,replaceWith

        expr = Literal("A")
        expr.setParseAction(replaceWith(tuple(["A","Z"])))
        expr = expr.setResultsName("Achar")

        res = expr.parseString("A")
        print repr(res)
        print res.Achar
        assert res.Achar == ("A","Z"), "Failed accessing named results containing a tuple, got " + res.Achar


class MiscellaneousParserTests(ParseTestCase):
    def runTest(self):
        import pyparsing
        
        # test making oneOf with duplicate symbols
        print "verify oneOf handles duplicate symbols"
        try:
            test1 = pyparsing.oneOf("a b c d a")
        except RuntimeError:
            assert False,"still have infinite loop in oneOf with duplicate symbols"
        
        # test MatchFirst bugfix
        print "verify MatchFirst iterates properly"
        results = pyparsing.quotedString.parseString("'this is a single quoted string'")
        assert len(results) > 0, "MatchFirst error - not iterating over all choices"
            
        # verify streamline of subexpressions
        print "verify proper streamline logic"
        compound = pyparsing.Literal("A") + "B" + "C" + "D"
        assert len(compound.exprs) == 2,"bad test setup"
        print compound
        compound.streamline()
        print compound
        assert len(compound.exprs) == 4,"streamline not working"
        
        # test for Optional with results name and no match
        print "verify Optional's do not cause match failure if have results name"
        testGrammar = pyparsing.Literal("A") + pyparsing.Optional("B").setResultsName("gotB") + pyparsing.Literal("C")
        try:
            testGrammar.parseString("ABC")
            testGrammar.parseString("AC")
        except pyparsing.ParseException, pe:
            print pe.pstr,"->",pe
            assert False, "error in Optional matching of string %s" % pe.pstr
        
        # test return of furthest exception
        testGrammar = ( pyparsing.Literal("A") |
                        ( pyparsing.Optional("B") + pyparsing.Literal("C") ) |
                        pyparsing.Literal("D") )
        try:
            testGrammar.parseString("BC")
            testGrammar.parseString("BD")
        except pyparsing.ParseException, pe:
            #~ print pe.pstr,"->",pe
            assert pe.pstr == "BD", "wrong test string failed to parse"
            assert pe.loc == 1, "error in Optional matching"

        # test validate
        print "verify behavior of validate()"
        def testValidation( grmr, gnam, isValid ):
            try:
                grmr.validate()
                assert isValid,"validate() accepted invalid grammar " + gnam
            except pyparsing.RecursiveGrammarException,e:
                assert not isValid, "validate() rejected valid grammar " + gnam
            
        fwd = pyparsing.Forward()
        g1 = pyparsing.OneOrMore( ( pyparsing.Literal("A") + "B" + "C" ) | fwd )
        g2 = pyparsing.ZeroOrMore("C" + g1)
        fwd << pyparsing.Group(g2)
        testValidation( fwd, "fwd", isValid=True )
                    
        fwd2 = pyparsing.Forward()
        fwd2 << pyparsing.Group("A" | fwd2)
        testValidation( fwd2, "fwd2", isValid=False )
                
        fwd3 = pyparsing.Forward()
        fwd3 << pyparsing.Optional("A") + fwd3
        testValidation( fwd3, "fwd3", isValid=False )

        # test getName
        print "verify behavior of getName()"
        aaa = pyparsing.Group(pyparsing.Word("a")).setResultsName("A")
        bbb = pyparsing.Group(pyparsing.Word("b")).setResultsName("B")
        ccc = pyparsing.Group(":" + pyparsing.Word("c")).setResultsName("C")
        g1 = "XXX" + pyparsing.ZeroOrMore( aaa | bbb | ccc )
        teststring = "XXX b b a b b a b :c b a"
        names = []
        for t in g1.parseString(teststring):
            #~ print t, repr(t)
            try:
                names.append( t[0].getName() )
            except:
                try:
                    names.append( t.getName() )
                except:
                    names.append( None )
        print teststring
        print names
        assert names==[None, 'B', 'B', 'A', 'B', 'B', 'A', 'B', 'C', 'B', 'A'], \
            "failure in getting names for tokens"
        
        # test Optional beyond end of string
        print "verify handling of Optional's beyond the end of string"
        testGrammar = "A" + pyparsing.Optional("B") + pyparsing.Optional("C") + pyparsing.Optional("D")
        testGrammar.parseString("A")
        testGrammar.parseString("AB")
        
        # test creating Literal with empty string
        print 'verify non-fatal usage of Literal("")'
        e = pyparsing.Literal("")
        try:
            e.parseString("SLJFD")
        except Exception,e:
            assert False, "Failed to handle empty Literal"

            
class ParseHTMLTagsTest(ParseTestCase):
    def runTest(self):
        import pyparsing
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
        
        bodyStart, bodyEnd = pyparsing.makeHTMLTags("BODY")
        resIter = iter(results)
        for t,s,e in (bodyStart | bodyEnd).scanString( test ):
            print test[s:e], "->", t.asList()
            (expectedType, expectedEmpty, expectedBG, expectedFG) = resIter.next()
            
            tType = t.getName() 
            #~ print tType,"==",expectedType,"?"
            assert tType in "startBody endBody".split(), "parsed token of unknown type '%s'" % tType
            assert tType == expectedType, "expected token of type %s, got %s" % (expectedType, tType) 
            if tType == "startBody":
                assert bool(t.empty) == expectedEmpty, "expected %s token, got %s" % ( expectedEmpty and "empty" or "not empty", 
                                                                                                t.empty and "empty" or "not empty" )
                assert t.bgcolor == expectedBG, "failed to match BGCOLOR, expected %s, got %s" % ( expectedBG, t.bgcolor )
                assert t.fgcolor == expectedFG, "failed to match FGCOLOR, expected %s, got %s" % ( expectedFG, t.bgcolor )
            elif tType == "endBody":
                #~ print "end tag"
                pass
            else:
                print "BAD!!!"

class UpcaseDowncaseUnicode(ParseTestCase):
    def runTest(self):
    
        import pyparsing as pp
        import sys

        a = u'\u00bfC\u00f3mo esta usted?'
        ualphas = u"".join( [ unichr(i) for i in range(sys.maxunicode)
                            if unichr(i).isalpha() ] )
        uword = pp.Word(ualphas).setParseAction(pp.upcaseTokens)

        print uword.searchString(a)

        uword = pp.Word(ualphas).setParseAction(pp.downcaseTokens)

        print uword.searchString(a)


        #test html data
        html = "<TR class=maintxt bgColor=#ffffff> \
            <TD vAlign=top>Производитель, модель</TD> \
            <TD vAlign=top><STRONG>BenQ-Siemens CF61</STRONG></TD> \
        ".decode('utf-8')

        # u'Manufacturer, model
        text_manuf = u'Производитель, модель'
        manufacturer = pp.Literal(text_manuf)

        td_start, td_end = pp.makeHTMLTags("td")
        manuf_body =  td_start.suppress() + manufacturer + pp.SkipTo(td_end).setResultsName("cells", True) + td_end.suppress()

        #~ manuf_body.setDebug()

        for tokens in manuf_body.scanString(html):
            print tokens

class ParseUsingRegex(ParseTestCase):
    def runTest(self):
    
        import re
        import pyparsing
        
        signedInt = pyparsing.Regex('[-+][0-9]+')
        unsignedInt = pyparsing.Regex('[0-9]+')
        simpleString = pyparsing.Regex('("[^\"]*")|(\'[^\']*\')')
        namedGrouping = pyparsing.Regex('("(?P<content>[^\"]*)")')
        
        def testMatch (expression, instring, shouldPass, expectedString=None):
            if shouldPass:
                try:
                    result = expression.parseString(instring)
                    print '%s correctly matched %s' % (repr(expression), repr(instring))
                    if expectedString != result[0]:
                        print '\tbut failed to match the pattern as expected:'
                        print '\tproduced %s instead of %s' % \
                            (repr(result[0]), repr(expectedString))
                    return True
                except pyparsing.ParseException:
                    print '%s incorrectly failed to match %s' % \
                        (repr(expression), repr(instring))
            else:
                try:
                    result = expression.parseString(instring)
                    print '%s incorrectly matched %s' % (repr(expression), repr(instring))
                    print '\tproduced %s as a result' % repr(result[0])
                except pyparsing.ParseException:
                    print '%s correctly failed to match %s' % \
                        (repr(expression), repr(instring))
                    return True
            return False
        
        # These should fail
        assert testMatch(signedInt, '1234 foo', False), "Re: (1) passed, expected fail"
        assert testMatch(signedInt, '    +foo', False), "Re: (2) passed, expected fail"
        assert testMatch(unsignedInt, 'abc', False), "Re: (3) passed, expected fail"
        assert testMatch(unsignedInt, '+123 foo', False), "Re: (4) passed, expected fail"
        assert testMatch(simpleString, 'foo', False), "Re: (5) passed, expected fail"
        assert testMatch(simpleString, '"foo bar\'', False), "Re: (6) passed, expected fail"
        assert testMatch(simpleString, '\'foo bar"', False), "Re: (7) passed, expected fail"

        # These should pass
        assert testMatch(signedInt, '   +123', True, '+123'), "Re: (8) failed, expected pass"
        assert testMatch(signedInt, '+123', True, '+123'), "Re: (9) failed, expected pass"
        assert testMatch(signedInt, '+123 foo', True, '+123'), "Re: (10) failed, expected pass"
        assert testMatch(signedInt, '-0 foo', True, '-0'), "Re: (11) failed, expected pass"
        assert testMatch(unsignedInt, '123 foo', True, '123'), "Re: (12) failed, expected pass"
        assert testMatch(unsignedInt, '0 foo', True, '0'), "Re: (13) failed, expected pass"
        assert testMatch(simpleString, '"foo"', True, '"foo"'), "Re: (14) failed, expected pass"
        assert testMatch(simpleString, "'foo bar' baz", True, "'foo bar'"), "Re: (15) failed, expected pass"
        
        # This one is going to match correctly, but fail to pull out the correct result
        #  (for now), as there is no actual handling for extracted named groups
        assert testMatch(namedGrouping, '"foo bar" baz', True, '"foo bar"'), "Re: (16) failed, expected pass"
        ret = namedGrouping.parseString('"zork" blah')
        print ret.asList()
        print ret.items()
        print ret.content
        assert ret.content == 'zork', "named group lookup failed"
        assert ret[0] == simpleString.parseString('"zork" blah')[0], "Regex not properly returning ParseResults for named vs. unnamed groups"
        
        try:
            #~ print "lets try an invalid RE"
            invRe = pyparsing.Regex('("[^\"]*")|(\'[^\']*\'')
        except Exception,e:
            print "successfully rejected an invalid RE:",
            print e
        else:
            assert False, "failed to reject invalid RE"
            
        invRe = pyparsing.Regex('')

class CountedArrayTest(ParseTestCase):
    def runTest(self):
        from pyparsing import Word,nums,OneOrMore,countedArray
        
        testString = "2 5 7 6 0 1 2 3 4 5 0 3 5 4 3"

        integer = Word(nums).setParseAction(lambda t: int(t[0]))
        countedField = countedArray(integer)
        
        r = OneOrMore(countedField).parseString( testString )
        print testString
        print r.asList()
        
        assert r.asList() == [[5,7],[0,1,2,3,4,5],[],[5,4,3]], \
                "Failed matching countedArray, got " + str(r.asList())

class CountedArrayTest2(ParseTestCase):
    # addresses bug raised by Ralf Vosseler
    def runTest(self):
        from pyparsing import Word,nums,OneOrMore,countedArray
        
        testString = "2 5 7 6 0 1 2 3 4 5 0 3 5 4 3"

        integer = Word(nums).setParseAction(lambda t: int(t[0]))
        countedField = countedArray(integer)
        
        dummy = Word("A")
        r = OneOrMore(dummy ^ countedField).parseString( testString )
        print testString
        print r.asList()
        
        assert r.asList() == [[5,7],[0,1,2,3,4,5],[],[5,4,3]], \
                "Failed matching countedArray, got " + str(r.asList())

class LineAndStringEndTest(ParseTestCase):
    def runTest(self):
        from pyparsing import OneOrMore,lineEnd,alphanums,Word,stringEnd,delimitedList,SkipTo

        les = OneOrMore(lineEnd)
        bnf1 = delimitedList(Word(alphanums).leaveWhitespace(),les)
        bnf2 = Word(alphanums) + stringEnd
        bnf3 = Word(alphanums) + SkipTo(stringEnd)
        tests = [
            ("testA\ntestB\ntestC\n", ['testA', 'testB', 'testC']),
            ("testD\ntestE\ntestF", ['testD', 'testE', 'testF']),
            ("a", ['a']),
             ]

        for t in tests:
            res1 = bnf1.parseString(t[0])
            print res1,'=?',t[1]
            assert res1.asList() == t[1], "Failed lineEnd/stringEnd test (1): "+repr(t[0])+ " -> "+str(res1.asList())
            res2 = bnf2.searchString(t[0])
            print res2[0].asList(),'=?',t[1][-1:]
            assert res2[0].asList() == t[1][-1:], "Failed lineEnd/stringEnd test (2): "+repr(t[0])+ " -> "+str(res2[0].asList())
            res3 = bnf3.parseString(t[0])
            print repr(res3[1]),'=?',repr(t[0][len(res3[0])+1:])
            assert res3[1] == t[0][len(res3[0])+1:], "Failed lineEnd/stringEnd test (3): " +repr(t[0])+ " -> "+str(res3[1].asList())

class VariableParseActionArgsTest(ParseTestCase):
    def runTest(self):
        
        pa3 = lambda s,l,t: t
        pa2 = lambda l,t: t
        pa1 = lambda t: t
        def pa0(): return
        class Callable3(object):
            def __call__(self,s,l,t):
                return t
        class Callable2(object):
            def __call__(self,l,t):
                return t
        class Callable1(object):
            def __call__(self,t):
                return t
        class Callable0(object):
            def __call__(self):
                return 
        class CallableS3(object):
            @staticmethod
            def __call__(s,l,t):
                return t
        class CallableS2(object):
            @staticmethod
            def __call__(l,t):
                return t
        class CallableS1(object):
            @staticmethod
            def __call__(t):
                return t
        class CallableS0(object):
            @staticmethod
            def __call__():
                return
        class CallableC3(object):
            @classmethod
            def __call__(cls,s,l,t):
                return t
        class CallableC2(object):
            @classmethod
            def __call__(cls,l,t):
                return t
        class CallableC1(object):
            @classmethod
            def __call__(cls,t):
                return t
        class CallableC0(object):
            @classmethod
            def __call__(cls):
                return
        
        class parseActionHolder(object):
            @staticmethod
            def pa3(s,l,t):
                return t
            @staticmethod
            def pa2(l,t):
                return t
            @staticmethod
            def pa1(t):
                return t
            @staticmethod
            def pa0():
                return
                
        def paArgs(*args):
            print args
            return args[2]

        def ClassAsPA0(object):
            def __init__(self):
                pass
            def __str__(self):
                return "*"
                
        def ClassAsPA1(object):
            def __init__(self,t):
                self.t = t
            def __str__(self):
                return self.t
                
        def ClassAsPA2(object):
            def __init__(self,l,t):
                self.t = t
            def __str__(self):
                return self.t
                
        def ClassAsPA3(object):
            def __init__(self,s,l,t):
                self.t = t
            def __str__(self):
                return self.t
                

        from pyparsing import Literal,OneOrMore
        
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
        
        gg = OneOrMore( A | B | C | D | E | F | G | H |
                        I | J | K | L | M | N | O | P | Q | R | S | T | U | V)
        testString = "VUTSRQPONMLKJIHGFEDCBA"
        res = gg.parseString(testString)
        print res.asList()
        assert res.asList()==list(testString), "Failed to parse using variable length parse actions"
        
        A = Literal("A").setParseAction(ClassAsPA0)
        B = Literal("B").setParseAction(ClassAsPA1)
        C = Literal("C").setParseAction(ClassAsPA2)
        D = Literal("D").setParseAction(ClassAsPA3)
        
        gg = OneOrMore( A | B | C | D | E | F | G | H |
                        I | J | K | L | M | N | O | P | Q | R | S | T | U | V)
        testString = "VUTSRQPONMLKJIHGFEDCBA"
        res = gg.parseString(testString)
        print map(str,res)
        assert map(str,res)==list(testString), "Failed to parse using variable length parse actions using class constructors as parse actions"
        
class EnablePackratParsing(ParseTestCase):
    def runTest(self):
        from pyparsing import ParserElement
        ParserElement.enablePackrat()

class SingleArgExceptionTest(ParseTestCase):
    def runTest(self):
        from pyparsing import ParseBaseException,ParseFatalException
        
        msg = ""
        raisedMsg = ""
        testMessage = "just one arg"
        try:
            raise ParseFatalException, testMessage
        except ParseBaseException,pbe:
            print "Received expected exception:", pbe
            raisedMsg = pbe.msg
        assert raisedMsg == testMessage, "Failed to get correct exception message"


class KeepOriginalTextTest(ParseTestCase):
    def runTest(self):
        from pyparsing import makeHTMLTags, keepOriginalText
        
        def rfn(t):
            return "%s:%d" % (t.src, len("".join(t)))

        makeHTMLStartTag = lambda tag: makeHTMLTags(tag)[0].setParseAction(keepOriginalText)
            
        # use the lambda, Luke
        #~ start, imge = makeHTMLTags('IMG')  
        start = makeHTMLStartTag('IMG')

        # don't replace our fancy parse action with rfn, 
        # append rfn to the list of parse actions
        #~ start.setParseAction(rfn)
        start.addParseAction(rfn)

        #start.setParseAction(lambda s,l,t:t.src)
        text = '''_<img src="images/cal.png"
            alt="cal image" width="16" height="15">_'''
        s = start.transformString(text)
        print s
        assert s.startswith("_images/cal.png:"), "failed to preserve input s properly"
        assert s.endswith("77_"),"failed to return full original text properly"

class PackratParsingCacheCopyTest(ParseTestCase):
    def runTest(self):
        from pyparsing import Word,nums,ParserElement,delimitedList,Literal,Optional,alphas,alphanums,ZeroOrMore,empty

        integer = Word(nums).setName("integer")
        id = Word(alphas+'_',alphanums+'_')
        simpleType = Literal('int');
        arrayType= simpleType+ZeroOrMore('['+delimitedList(integer)+']')
        varType = arrayType | simpleType
        varDec  = varType + delimitedList(id + Optional('='+integer))+';'
         
        codeBlock = Literal('{}')
         
        funcDef = Optional(varType | 'void')+id+'('+(delimitedList(varType+id)|'void'|empty)+')'+codeBlock
         
        program = varDec | funcDef
        input = 'int f(){}'
        results = program.parseString(input)
        print "Parsed '%s' as %s" % (input, results.asList())
        assert results.asList() == ['int', 'f', '(', ')', '{}'], "Error in packrat parsing"

class ParseResultsDelTest(ParseTestCase):
    def runTest(self):
        from pyparsing import OneOrMore, Word, alphas, nums
        
        grammar = OneOrMore(Word(nums))("ints") + OneOrMore(Word(alphas))("words")
        res = grammar.parseString("123 456 ABC DEF")
        print res
        
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
        
        from pyparsing import makeHTMLTags, Word, withAttribute, nums
        
        data = """
        <a>1</a>
        <a b="x">2</a>
        <a B="x">3</a>
        <a b="X">4</a>
        <a b="y">5</a>
        """
        tagStart, tagEnd = makeHTMLTags("a")
        
        expr = tagStart + Word(nums).setResultsName("value") + tagEnd
          
        expected = [['a', ['b', 'x'], False, '2', '</a>'], ['a', ['b', 'x'], False, '3', '</a>']]
        
        for attrib in [
            withAttribute(b="x"),
            withAttribute(B="x"),
            withAttribute(("b","x")),
            withAttribute(("B","x"))
            ]:
          
          tagStart.setParseAction(attrib)
          result = expr.searchString(data)
          
          print result.dump()
          assert result.asList() == expected, "Failed test, expected %s, got %s" % (expected, result.asList())

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
        print "Test defaults:"
        teststring = "(( ax + by)*C) (Z | (E^F) & D)"

        expr = nestedExpr()

        expected = [[['ax', '+', 'by'], '*C']]
        result = expr.parseString(teststring)
        print result.dump()
        assert result.asList() == expected, "Defaults didn't work. That's a bad sign. Expected: %s, got: %s" % (expected, result)

        #Going through non-defaults, one by one; trying to think of anything
        #odd that might not be properly handled.

        #Change opener
        print "\nNon-default opener"
        opener = "["
        teststring = test_string = "[[ ax + by)*C)"
        expected = [[['ax', '+', 'by'], '*C']]
        expr = nestedExpr("[")
        result = expr.parseString(teststring)
        print result.dump()
        assert result.asList() == expected, "Non-default opener didn't work. Expected: %s, got: %s" % (expected, result)

        #Change closer
        print "\nNon-default closer"

        teststring = test_string = "(( ax + by]*C]"
        expected = [[['ax', '+', 'by'], '*C']]
        expr = nestedExpr(closer="]")
        result = expr.parseString(teststring)
        print result.dump()
        assert result.asList() == expected, "Non-default closer didn't work. Expected: %s, got: %s" % (expected, result)

        # #Multicharacter opener, closer
        # opener = "bar"
        # closer = "baz"
        print "\nLiteral expressions for opener and closer"

        opener,closer = map(Literal, "bar baz".split())
        expr = nestedExpr(opener, closer, 
                    content=Regex(r"([^b ]|b(?!a)|ba(?![rz]))+")) 
                    
        teststring = "barbar ax + bybaz*Cbaz"
        expected = [[['ax', '+', 'by'], '*C']]
        # expr = nestedExpr(opener, closer)
        result = expr.parseString(teststring)
        print result.dump()
        assert result.asList() == expected, "Multicharacter opener and closer didn't work. Expected: %s, got: %s" % (expected, result)

        #Lisp-ish comments
        print "\nUse ignore expression (1)"
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
        print result.dump()
        assert result.asList() == expected , "Lisp-ish comments (\";; <...> $\") didn't work. Expected: %s, got: %s" % (expected, result)


        #Lisp-ish comments, using a standard bit of pyparsing, and an Or.
        print "\nUse ignore expression (2)"
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
        print result.dump()
        assert result.asList() == expected , "Lisp-ish comments (\";; <...> $\") and quoted strings didn't work. Expected: %s, got: %s" % (expected, result)



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
        tests.append( "\n".join(tests) )

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
            
        for t,expected in zip(tests, expectedResult):
            print t
            results = map(lambda e: flatten(e.searchString(t).asList()), 
                [
                leadingConsonant,
                leadingVowel,
                trailingConsonant,
                trailingVowel,
                internalVowel,
                bnf,
                ]
                )
            print results
            assert results==expected,"Failed WordBoundaryTest, expected %s, got %s" % (expected,results)
            print


def makeTestSuite():
    suite = TestSuite()
    suite.addTest( PyparsingTestInit() )
    suite.addTest( ParseIDLTest() )
    suite.addTest( ParseASMLTest() )
    suite.addTest( ParseFourFnTest() )
    suite.addTest( ParseSQLTest() )
    suite.addTest( ParseConfigFileTest() )
    suite.addTest( ParseJSONDataTest() )
    suite.addTest( ParseCommaSeparatedValuesTest() )
    suite.addTest( ParseEBNFTest() )
    suite.addTest( ScanStringTest() )
    suite.addTest( QuotedStringsTest() )
    suite.addTest( CustomQuotesTest() )
    suite.addTest( CaselessOneOfTest() )
    suite.addTest( AsXMLTest() )
    suite.addTest( CommentParserTest() )
    suite.addTest( ParseExpressionResultsTest() )
    suite.addTest( ParseExpressionResultsAccumulateTest() )
    suite.addTest( ReStringRangeTest() )
    suite.addTest( ParseKeywordTest() )
    suite.addTest( ParseHTMLTagsTest() )
    suite.addTest( ParseUsingRegex() )
    suite.addTest( SkipToParserTests() )
    suite.addTest( CountedArrayTest() )
    suite.addTest( CountedArrayTest2() )
    suite.addTest( LineAndStringEndTest() )
    suite.addTest( VariableParseActionArgsTest() )
    suite.addTest( RepeaterTest() )
    suite.addTest( RecursiveCombineTest() )
    suite.addTest( OperatorPrecedenceGrammarTest1() )
    suite.addTest( OperatorPrecedenceGrammarTest2() )
    suite.addTest( OperatorPrecedenceGrammarTest3() )
    suite.addTest( OperatorPrecedenceGrammarTest4() )
    suite.addTest( ParseResultsPickleTest() )
    suite.addTest( ParseResultsWithNamedTupleTest() )
    suite.addTest( SingleArgExceptionTest() )
    suite.addTest( UpcaseDowncaseUnicode() )
    suite.addTest( KeepOriginalTextTest() )
    suite.addTest( PackratParsingCacheCopyTest() )
    suite.addTest( WithAttributeParseActionTest() )
    suite.addTest( NestedExpressionsTest() )
    suite.addTest( WordBoundaryExpressionsTest() )
    suite.addTest( MiscellaneousParserTests() )

    if TEST_USING_PACKRAT:
        # retest using packrat parsing (disable those tests that aren't compatible)
        suite.addTest( EnablePackratParsing() )
        
        unpackrattables = [ EnablePackratParsing, ParseIDLTest, RepeaterTest, ]
        
        # add tests to test suite a second time, to run with packrat parsing
        # (leaving out those that we know wont work with packrat)
        packratTests = [t.__class__() for t in suite._tests
                            if t.__class__ not in unpackrattables]
        suite.addTests( packratTests )
        
    return suite
    

console = False
#~ console = True
if console:
    #~ # console mode
    testRunner = TextTestRunner()
    testRunner.run( makeTestSuite() )
else:
    # HTML mode
    outfile = "testResults.html"
    outstream = file(outfile,"w")
    testRunner = HTMLTestRunner.HTMLTestRunner( stream=outstream )
    testRunner.run( makeTestSuite() )
    outstream.close()

    import os
    os.system(outfile)
