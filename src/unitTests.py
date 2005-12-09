# -*- coding: UTF-8 -*-
from unittest import TestCase, TestSuite, TextTestRunner
from pyparsing import ParseException

import pprint
import pdb

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
            [ (3, 'Ohio') ], 
            [ (2, 'Los Angeles'), (3, 'California') ]
            ]
        for line,tests in zip(testData, testVals):
            print "Parsing: \""+line+"\" ->",
            results = commaSeparatedList.parseString(line)
            print results.asList()
            for t in tests:
                assert results[t[0]] == t[1],"failed on %s, item %d s/b '%s', got '%s'" % ( line, t[0], t[1], results[t[0]] )

class ParseEBNFTest(ParseTestCase):
    def runTest(self):
        import ebnf
        from pyparsing import Word, quotedString, alphas, nums
        
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
        from pyparsing import Word, Combine, Suppress, CharsNotIn, nums
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
        
        
class CaselessOneOfTest(ParseTestCase):
    def runTest(self):
        from pyparsing import oneOf
        
        caseless1 = str( oneOf("d a b c aA B A C", caseless=True) )
        print caseless1
        caseless2 = str( oneOf("d a b c Aa B A C", caseless=True) )
        print caseless2
        assert caseless1.upper() == caseless2.upper(), "oneOf not handling caseless option properly"
        assert caseless1 != caseless2, "Caseless option properly"
        

class AsXMLTest(ParseTestCase):
    def runTest(self):
        
        import pyparsing
        # test asXML()
        
        aaa = pyparsing.Word("a").setResultsName("A")
        bbb = pyparsing.Group(pyparsing.Word("b")).setResultsName("B")
        ccc = pyparsing.Combine(":" + pyparsing.Word("c")).setResultsName("C")
        g1 = "XXX" + pyparsing.ZeroOrMore( aaa | bbb | ccc )
        teststring = "XXX b b a b b a b :c b a"
        #~ print teststring
        print "test including all items"
        xml = g1.parseString(teststring).asXML("TEST",namedItemsOnly=False)
        assert xml=="\n".join(["",
                                "<TEST>",
                                "  <ITEM>XXX</ITEM>",
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

class ParseExpressionResultsTest(ParseTestCase):
    def runTest(self):
        from pyparsing import Word,alphas,OneOrMore,Optional

        a = Word("a",alphas).setName("A")
        b = Word("b",alphas).setName("B")
        c = Word("c",alphas).setName("C")
        ab = (a + b).setName("AB")
        abc = (ab + c).setName("ABC")
        word = Word(alphas).setName("word")
        
        #~ words = OneOrMore(word).setName("words")
        words = OneOrMore(~a + word).setName("words")
        
        #~ phrase = words.setResultsName("Head") + \
                    #~ ( abc ^ ab ^ a ).setResultsName("ABC") + \
                    #~ words.setResultsName("Tail")
        #~ phrase = words.setResultsName("Head") + \
                    #~ ( abc | ab | a ).setResultsName("ABC") + \
                    #~ words.setResultsName("Tail")
        phrase = words.setResultsName("Head") + \
                    ( a + Optional(b + Optional(c)) ).setResultsName("ABC") + \
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
        compound.streamline()
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
        assert namedGrouping.parseString('"zork" blah').content == 'zork', "named group lookup failed"
        
        try:
            #~ print "lets try an invalid RE"
            invRe = pyparsing.Regex('("[^\"]*")|(\'[^\']*\'')
        except Exception,e:
            print "successfully rejected an invalid RE:",
            print e
        else:
            assert False, "failed to reject invalid RE"
            
        invRe = pyparsing.Regex('')

def makeTestSuite():
    suite = TestSuite()
    suite.addTest( PyparsingTestInit() )
    suite.addTest( ParseIDLTest() )
    suite.addTest( ParseASMLTest() )
    suite.addTest( ParseFourFnTest() )
    suite.addTest( ParseSQLTest() )
    suite.addTest( ParseConfigFileTest() )
    suite.addTest( ParseCommaSeparatedValuesTest() )
    suite.addTest( ParseEBNFTest() )
    suite.addTest( ScanStringTest() )
    suite.addTest( QuotedStringsTest() )
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
    suite.addTest( MiscellaneousParserTests() )
    return suite
    

testRunner = TextTestRunner()
testRunner.run( makeTestSuite() )