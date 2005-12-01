#
# verilogParse.py
#
# an example of using the pyparsing module to be able to process Verilog files
# uses BNF defined at http://www.verilog.com/VerilogBNF.html
#
#    Copyright (c) 2004,2005 Paul T. McGuire.  All rights reserved.
#    
#    Redistribution and use in source and binary forms, with or without
#    modification, are permitted provided that the following conditions
#    are met:
#    1. Commercial use of this software and that derived from it is EXPRESSLY
#    PROHIBITED without specific prior written permission.  "Commercial uses"
#    include, but are not limited to:
#     - inclusion in a product for sale
#     - inclusion with a product as a "gratis" or "no charge" item
#     - use in providing a paid consulting or data processing service
#    2. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#    3. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#    4. Neither the name of the author nor the names of any co-contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#    
#    DISCLAIMER: 
#    THIS SOFTWARE IS PROVIDED BY PAUL T. McGUIRE ``AS IS'' AND ANY EXPRESS OR
#    IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
#    MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO
#    EVENT SHALL PAUL T. McGUIRE OR CO-CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
#    INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
#    BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OFUSE,
#    DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
#    OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#    NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
#    EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#     
#    For questions or inquiries regarding this license, or commercial use of 
#    this software, contact the author via e-mail: ptmcg@users.sourceforge.net
#
# Todo:
#  - add pre-process pass to implement compilerDirectives (ifdef, include, etc.)
#
# Revision History:
#
#   1.0   - Initial release
#   1.0.1 - Fixed grammar errors:
#           . real declaration was incorrect
#           . tolerant of '=>' for '*>' operator
#           . tolerant of '?' as hex character
#           . proper handling of mintypmax_expr within path delays
#   1.0.2 - Performance tuning (requires pyparsing 1.3)
#
import pdb
import time
import pprint

__version__ = "1.0.2"

try:
    import psyco
    psyco.full()
except:
    print "failed to import psyco Python optimizer"
    
from pyparsing import Literal, CaselessLiteral, Word, Upcase, OneOrMore, ZeroOrMore, \
        Forward, NotAny, delimitedList, Group, Optional, Combine, alphas, nums, restOfLine, cStyleComment, \
        alphanums, printables, dblQuotedString, empty, ParseException, ParseResults, MatchFirst, oneOf, GoToColumn, \
        ParseResults,StringEnd, FollowedBy, ParserElement, And

def dumpTokens(s,l,t):
    import pprint
    pprint.pprint( t.asList() )
    
def mergeBasedNumber(s, l, t):
    return l, [ " ".join(t) ]
    
verilogbnf = None
def Verilog_BNF():
    global verilogbnf
    
    if verilogbnf is None:

        # compiler directives
        compilerDirective = Combine( "`" + \
            oneOf("define undef ifdef else endif default_nettype "
                  "include resetall timescale unconnected_drive "
                  "nounconnected_drive celldefine endcelldefine") + \
            restOfLine ).setName("compilerDirective")
        
        # primitives
        semi = Literal(";")
        lpar = Literal("(")
        rpar = Literal(")")
        equals = Literal("=")

        identifier = Combine( Optional(".") + 
                              delimitedList( Word(alphas+"$_", alphanums+"$_"), ".", combine=True ) 
                            ).setName("baseIdent")
        #~ e = CaselessLiteral( "E" )
        e = Word( "Ee",exact=1 )
        spacedNums = nums + "_"
        hexnums = nums + "abcdefABCDEF" + "_?"
        base = Word( "'","bBoOdDhH", exact=2 ).setName("base")
        basedNumber = Combine( Optional( Word(spacedNums) ) + base + Word(hexnums+"xXzZ"), 
                               adjacent=False ).setName("basedNumber").setParseAction(mergeBasedNumber)
        number = ( basedNumber | Combine( Word( "+-"+spacedNums, spacedNums ) + 
                           Optional( "." + Optional( Word( spacedNums ) ) ) +
                           Optional( e + Word( "+-"+spacedNums, spacedNums ) ) ).setName("numeric") )
        #~ decnums = nums + "_"
        #~ octnums = "01234567" + "_"
        expr = Forward().setName("expr")
        concat = Group( "{" + delimitedList( expr ) + "}" )
        multiConcat = Group("{" + expr + concat + "}").setName("multiConcat")
        funcCall = Group(identifier + "(" + Optional( delimitedList( expr ) ) + ")").setName("funcCall")
        
        subscrIdentifier = Group( identifier + Optional( "[" + delimitedList( expr, ":" ) + "]" ) )
        scalarConst = ( FollowedBy('1') + oneOf("1'b0 1'b1 1'bx 1'bX 1'B0 1'B1 1'Bx 1'BX 1") ) | "0"
        mintypmaxExpr = Group( expr + ":" + expr + ":" + expr ).setName("mintypmax")
        primary = (
                  number | 
                  ("(" + mintypmaxExpr + ")" ) | 
                  ( "(" + Group(expr) + ")" ).setName("nestedExpr") | #.setDebug() | 
                  multiConcat | 
                  concat | 
                  dblQuotedString | 
                  funcCall |
                  subscrIdentifier 
                  )
                  
        unop  = oneOf( "+  -  !  ~  &  ~&  |  ^|  ^  ~^" ).setName("unop")
        binop = oneOf( "+  -  *  /  %  ==  !=  ===  !==  &&  "
                       "||  <  <=  >  >=  &  |  ^  ^~  >>  << ** <<< >>>" ).setName("binop")
        
        expr << (
                ( unop + expr ) |  # must be first!
                ( primary + "?" + expr + ":" + expr ) |
                ( primary + Optional( binop + expr ) ) 
                )

        lvalue = subscrIdentifier | concat

        # keywords
        if_        = Literal("if")
        else_      = Literal("else")
        edge       = Literal("edge")
        posedge    = Literal("posedge")
        negedge    = Literal("negedge")
        specify    = Literal("specify")
        endspecify = Literal("endspecify")
        fork       = Literal("fork")
        join       = Literal("join")
        begin      = Literal("begin")
        end        = Literal("end")
        default    = Literal("default")
        forever    = Literal("forever")
        repeat     = Literal("repeat")
        while_     = Literal("while")
        for_       = Literal("for")
        case       = oneOf( "case casez casex" )
        endcase    = Literal("endcase")
        wait       = Literal("wait")
        disable    = Literal("disable")
        deassign   = Literal("deassign")
        force      = Literal("force")
        release    = Literal("release")
        assign     = Literal("assign")
        
        eventExpr = Forward()
        eventTerm = ( posedge + expr ) | ( negedge + expr ) | expr | ( "(" + eventExpr + ")" )
        eventExpr << ( 
            Group( delimitedList( eventTerm, "or" ) )
            )
        eventControl = Group( "@" + ( ( "(" + eventExpr + ")" ) | identifier | "*" ) ).setName("eventCtrl")

        delayArg = ( number | 
                     Word(alphanums+"$_") | #identifier | 
                     ( "(" + Group( delimitedList( mintypmaxExpr | expr ) ) + ")" ) 
                   ).setName("delayArg")#.setDebug()
        delay = Group( "#" + delayArg ).setName("delay")#.setDebug()
        delayOrEventControl = delay | eventControl

        assgnmt   = Group( lvalue + "=" + Optional( delayOrEventControl ) + expr ).setName( "assgnmt" )
        nbAssgnmt = Group(( lvalue + "<=" + Optional( delay ) + expr ) |
                     ( lvalue + "<=" + Optional( eventControl ) + expr )).setName( "nbassgnmt" )
        
        range = "[" + expr + ":" + expr + "]"
        
        paramAssgnmt = Group( identifier + "=" + expr ).setName("paramAssgnmt")
        parameterDecl = Group( "parameter" + Optional( range ) + delimitedList( paramAssgnmt ) + semi).setName("paramDecl")
        
        inputDecl = Group( "input" + Optional( range ) + delimitedList( identifier ) + semi )
        outputDecl = Group( "output" + Optional( range ) + delimitedList( identifier ) + semi )
        inoutDecl = Group( "inout" + Optional( range ) + delimitedList( identifier ) + semi )
        
        regIdentifier = Group( identifier + Optional( "[" + expr + ":" + expr + "]" ) )
        regDecl = Group( "reg" + Optional("signed") + Optional( range ) + delimitedList( regIdentifier ) + semi ).setName("regDecl")
        timeDecl = Group( "time" + delimitedList( regIdentifier ) + semi )
        integerDecl = Group( "integer" + delimitedList( regIdentifier ) + semi )
        
        strength0 = oneOf("supply0  strong0  pull0  weak0  highz0")        
        strength1 = oneOf("supply1  strong1  pull1  weak1  highz1") 
        driveStrength = Group( "(" + ( ( strength0 + "," + strength1 ) | 
                                       ( strength1 + "," + strength0 ) ) + ")" )
        nettype = oneOf("wire  tri  tri1  supply0  wand  triand  tri0  supply1  wor  trior  trireg")
        expandRange = Optional( oneOf("scalared vectored") ) + range
        realDecl = Group( "real" + delimitedList( identifier ) + semi )
        
        eventDecl = Group( "event" + delimitedList( identifier ) + semi )

        blockDecl = ( 
            parameterDecl |
            regDecl |
            integerDecl |
            realDecl |
            timeDecl |
            eventDecl
            )

        stmt = Forward().setName("stmt")#.setDebug()
        stmtOrNull = stmt | semi
        caseItem = ( delimitedList( expr ) + ":" + stmtOrNull ) | \
                   ( default + Optional(":") + stmtOrNull )
        stmt << Group(
            ( begin + ZeroOrMore( stmt ) + end ).setName("begin-end") |
            ( if_ + "(" + expr + ")" + stmtOrNull + Optional( else_ + stmtOrNull ) ).setName("if") |
            ( delayOrEventControl + stmtOrNull ) | #.setDebug() |
            ( case + "(" + expr + ")" + OneOrMore( caseItem ) + endcase ) |
            ( forever + stmt ) |
            ( repeat + "(" + expr + ")" + stmt ) |
            ( while_ + "(" + expr + ")" + stmt ) |
            ( for_ + "(" + assgnmt + semi + Group( expr ) + semi + assgnmt + ")" + stmt ) |
            ( fork + ZeroOrMore( stmt ) + join ) |
            ( fork + ":" + identifier + ZeroOrMore( blockDecl ) + ZeroOrMore( stmt ) + end ) |
            ( wait + "(" + expr + ")" + stmtOrNull ) |
            ( "->" + identifier + semi ) |
            ( disable + identifier + semi ) |
            ( assign + assgnmt + semi ) |
            ( deassign + lvalue + semi ) |
            ( force + assgnmt + semi ) |
            ( release + lvalue + semi ) |
            ( begin + ":" + identifier + ZeroOrMore( blockDecl ) + ZeroOrMore( stmt ) + end ).setName("begin:label-end") |
            # these  *have* to go at the end of the list!!!
            ( assgnmt + semi ) |  
            ( nbAssgnmt + semi ) |
            ( Combine( Optional("$") + identifier ) + Optional( "(" + delimitedList(expr|empty) + ")" ) + semi ) 
            ).setName("stmtBody")
        """
        x::=<blocking_assignment> ;
        x||= <non_blocking_assignment> ;
        x||= if ( <expression> ) <statement_or_null>
        x||= if ( <expression> ) <statement_or_null> else <statement_or_null>
        x||= case ( <expression> ) <case_item>+ endcase
        x||= casez ( <expression> ) <case_item>+ endcase
        x||= casex ( <expression> ) <case_item>+ endcase
        x||= forever <statement>
        x||= repeat ( <expression> ) <statement>
        x||= while ( <expression> ) <statement>
        x||= for ( <assignment> ; <expression> ; <assignment> ) <statement>
        x||= <delay_or_event_control> <statement_or_null>
        x||= wait ( <expression> ) <statement_or_null>
        x||= -> <name_of_event> ;
        x||= <seq_block>
        x||= <par_block>
        x||= <task_enable>
        x||= <system_task_enable>
        x||= disable <name_of_task> ;
        x||= disable <name_of_block> ;
        x||= assign <assignment> ;
        x||= deassign <lvalue> ;
        x||= force <assignment> ;
        x||= release <lvalue> ;
        """
        alwaysStmt = Group( "always" + Optional(eventControl) + stmt ).setName("alwaysStmt")
        initialStmt = Group( "initial" + stmt ).setName("initialStmt")
        
        chargeStrength = Group( "(" + oneOf( "small medium large" ) + ")" )
        
        continuousAssign = Group(
            assign + Optional( driveStrength ) + Optional( delay ) + delimitedList( assgnmt ) + semi
            ).setName("continuousAssign")
            
        
        tfDecl = (
            parameterDecl |
            inputDecl |
            outputDecl |
            inoutDecl |
            regDecl |
            timeDecl |
            integerDecl |
            realDecl
            )
            
        functionDecl = Group( 
            "function" + Optional( range | "integer" | "real" ) + identifier + semi + 
            OneOrMore( tfDecl ) + 
            ZeroOrMore( stmt ) + 
            "endfunction"
            )
        
        netDecl1 = Group( nettype +
            Optional( expandRange ) +
            Optional( delay ) +
            delimitedList( identifier ) +
            semi )
        netDecl2 = Group( "trireg" +
            Optional( chargeStrength ) +
            Optional( expandRange ) +
            Optional( delay ) +
            delimitedList( identifier ) + 
            semi )
        netDecl3 = Group( nettype +
            Optional( driveStrength ) +
            Optional( expandRange ) +
            Optional( delay ) +
            delimitedList( assgnmt ) +
            semi )
        
        gateType = oneOf("and  nand  or  nor xor  xnor buf  bufif0 bufif1 "
                         "not  notif0 notif1  pulldown pullup nmos  rnmos "
                         "pmos rpmos cmos rcmos   tran rtran  tranif0  "
                         "rtranif0  tranif1 rtranif1"  )
        gateInstance = Optional( Group( identifier + Optional( range ) ) ) + \
                        "(" + Group( delimitedList( expr ) ) + ")"
        gateDecl = Group( gateType +
            Optional( driveStrength ) + 
            Optional( delay ) +
            delimitedList( gateInstance) +
            semi )
        
        udpInstance = Group( Group( identifier + Optional(range) ) +
            "(" + Group( delimitedList( expr ) ) + ")" )
        udpInstantiation = Group( identifier +
            Optional( driveStrength ) +
            Optional( delay ) +
            delimitedList( udpInstance ) +
            semi )#.setParseAction(dumpTokens)

        parameterValueAssignment = Group( Literal("#") + "(" + Group( delimitedList( expr ) ) + ")" )
        namedPortConnection = Group( "." + identifier + "(" + expr + ")" )
        modulePortConnection = expr | empty
        #~ moduleInstance = Group( Group ( identifier + Optional(range) ) +
            #~ ( delimitedList( modulePortConnection ) |
              #~ delimitedList( namedPortConnection ) ) )
        inst_args = Group( "(" + (delimitedList( modulePortConnection ) | 
                    delimitedList( namedPortConnection )) + ")").setName("inst_args")#.setDebug()
        moduleInstance = Group( Group ( identifier + Optional(range) ) + inst_args )

        moduleInstantiation = Group( identifier + 
            Optional( parameterValueAssignment ) +
            delimitedList( moduleInstance ).setName("moduleInstanceList") +
            semi ).setName("moduleInstantiation")
        
        parameterOverride = Group( "defparam" + delimitedList( paramAssgnmt ) + semi )
        task = Group( "task" + identifier + semi +
            ZeroOrMore( tfDecl ) +
            stmtOrNull +
            "endtask" )
        
        specparamDecl = Group( "specparam" + delimitedList( paramAssgnmt ) + semi )

        pathDescr1 = Group( "(" + subscrIdentifier + "=>" + subscrIdentifier + ")" )
        pathDescr2 = Group( "(" + Group( delimitedList( subscrIdentifier ) ) + "*>" + 
                                  Group( delimitedList( subscrIdentifier ) ) + ")" )
        pathDescr3 = Group( "(" + Group( delimitedList( subscrIdentifier ) ) + "=>" + 
                                  Group( delimitedList( subscrIdentifier ) ) + ")" )
        pathDelayValue = Group( ( "(" + Group( delimitedList( mintypmaxExpr | expr ) ) + ")" ) | 
                                 mintypmaxExpr | 
                                 expr )
        pathDecl = Group( ( pathDescr1 | pathDescr2 | pathDescr3 ) + "=" + pathDelayValue + semi ).setName("pathDecl")
        
        portConditionExpr = Forward()
        portConditionTerm = Optional(unop) + subscrIdentifier
        portConditionExpr << portConditionTerm + Optional( binop + portConditionExpr )
        polarityOp = Word("+-",exact=1)
        levelSensitivePathDecl1 = Group(
            if_ + "(" + portConditionExpr + ")" +
            subscrIdentifier + Optional( polarityOp ) + "=>" + subscrIdentifier + "=" + 
            pathDelayValue +
            semi )
        levelSensitivePathDecl2 = Group(
            if_ + "(" + portConditionExpr + ")" +
            lpar + Group( delimitedList( subscrIdentifier ) ) + Optional( polarityOp ) + "*>" +
                Group( delimitedList( subscrIdentifier ) ) + rpar + "=" + 
            pathDelayValue +
            semi )
        levelSensitivePathDecl = levelSensitivePathDecl1 | levelSensitivePathDecl2
        
        edgeIdentifier = posedge | negedge
        edgeSensitivePathDecl1 = Group(
            Optional( if_ + "(" + expr + ")" ) +
            lpar + Optional( edgeIdentifier ) +
            subscrIdentifier + "=>" + 
            lpar + subscrIdentifier + Optional( polarityOp ) + ":" + expr + rpar + rpar +
            "=" + 
            pathDelayValue +
            semi )
        edgeSensitivePathDecl2 = Group(
            Optional( if_ + "(" + expr + ")" ) +
            lpar + Optional( edgeIdentifier ) +
            subscrIdentifier + "*>" + 
            lpar + delimitedList( subscrIdentifier ) + Optional( polarityOp ) + ":" + expr + rpar + rpar +
            "=" + 
            pathDelayValue +
            semi )
        edgeSensitivePathDecl = edgeSensitivePathDecl1 | edgeSensitivePathDecl2
        
        edgeDescr = oneOf("01 10 0x x1 1x x0")
        
        timCheckEventControl = Group( posedge | negedge | (edge + "[" + delimitedList( edgeDescr ) + "]" ))
        timCheckCond = Forward()
        timCondBinop = oneOf("== === != !==")
        timCheckCondTerm = ( expr + timCondBinop + scalarConst ) | ( Optional("~") + expr )
        timCheckCond << ( "(" + timCheckCond + ")" ) | timCheckCondTerm
        timCheckEvent = Group( Optional( timCheckEventControl ) + 
                                subscrIdentifier + 
                                Optional( "&&&" + timCheckCond ) )
        timCheckLimit = expr
        controlledTimingCheckEvent = Group( timCheckEventControl + subscrIdentifier + 
                                            Optional( "&&&" + timCheckCond ) )
        notifyRegister = identifier
        
        systemTimingCheck1 = Group( "$setup" + 
            lpar + timCheckEvent + "," + timCheckEvent + "," + timCheckLimit + 
            Optional( "," + notifyRegister ) + rpar +
            semi )
        systemTimingCheck2 = Group( "$hold" + 
            lpar + timCheckEvent + "," + timCheckEvent + "," + timCheckLimit + 
            Optional( "," + notifyRegister ) + rpar +
            semi )
        systemTimingCheck3 = Group( "$period" + 
            lpar + controlledTimingCheckEvent + "," + timCheckLimit +  
            Optional( "," + notifyRegister ) + rpar +
            semi )
        systemTimingCheck4 = Group( "$width" + 
            lpar + controlledTimingCheckEvent + "," + timCheckLimit +  
            Optional( "," + expr + "," + notifyRegister ) + rpar +
            semi )
        systemTimingCheck5 = Group( "$skew" + 
            lpar + timCheckEvent + "," + timCheckEvent + "," + timCheckLimit + 
            Optional( "," + notifyRegister ) + rpar +
            semi )
        systemTimingCheck6 = Group( "$recovery" + 
            lpar + controlledTimingCheckEvent + "," + timCheckEvent + "," + timCheckLimit +  
            Optional( "," + notifyRegister ) + rpar +
            semi )
        systemTimingCheck7 = Group( "$setuphold" + 
            lpar + timCheckEvent + "," + timCheckEvent + "," + timCheckLimit + "," + timCheckLimit + 
            Optional( "," + notifyRegister ) + rpar +
            semi )
        systemTimingCheck = (FollowedBy('$') + ( systemTimingCheck1 | systemTimingCheck2 | systemTimingCheck3 | 
            systemTimingCheck4 | systemTimingCheck5 | systemTimingCheck6 | systemTimingCheck7 )).setName("systemTimingCheck")
        sdpd = if_ + "(" + expr + ")" + \
            ( pathDescr1 | pathDescr2 ) + "=" + pathDelayValue + semi
        
        specifyItem = ~Literal("endspecify") +(
            specparamDecl |
            pathDecl |
            levelSensitivePathDecl |
            edgeSensitivePathDecl |
            systemTimingCheck |
            sdpd
            )
        """
        x::= <specparam_declaration>
        x||= <path_declaration>
        x||= <level_sensitive_path_declaration>
        x||= <edge_sensitive_path_declaration>
        x||= <system_timing_check>
        x||= <sdpd>
        """
        specifyBlock = Group( "specify" + ZeroOrMore( specifyItem ) + "endspecify" )
            
        moduleItem = ~Literal("endmodule") + (
            parameterDecl |
            inputDecl |
            outputDecl |
            inoutDecl |
            regDecl |
            netDecl3 |
            netDecl1 |
            netDecl2 |
            timeDecl |
            integerDecl |
            realDecl |
            eventDecl |
            gateDecl | 
            parameterOverride |
            continuousAssign |
            specifyBlock |
            initialStmt |
            alwaysStmt |
            task |
            functionDecl |
            # these have to be at the end - they start with identifiers
            moduleInstantiation |
            udpInstantiation
            )
        """  All possible moduleItems, from Verilog grammar spec
        x::= <parameter_declaration>
        x||= <input_declaration>
        x||= <output_declaration>
        x||= <inout_declaration>
        ?||= <net_declaration>  (spec does not seem consistent for this item)
        x||= <reg_declaration>
        x||= <time_declaration>
        x||= <integer_declaration>
        x||= <real_declaration>
        x||= <event_declaration>
        x||= <gate_declaration>
        x||= <UDP_instantiation>
        x||= <module_instantiation>
        x||= <parameter_override>
        x||= <continuous_assign>
        x||= <specify_block>
        x||= <initial_statement>
        x||= <always_statement>
        x||= <task>
        x||= <function>
        """
        portRef = subscrIdentifier
        portExpr = portRef | Group( "{" + delimitedList( portRef ) + "}" )
        port = portExpr | Group( ( "." + identifier + "(" + portExpr + ")" ) )
        
        moduleHdr = Group ( oneOf("module macromodule") + identifier + 
                 Optional( "(" + Group( delimitedList( port ) ) + ")" ) + semi ).setName("moduleHdr")#.setDebug()
        module = Group(  moduleHdr + 
                 Group( ZeroOrMore( moduleItem ) ) + 
                 "endmodule" ).setName("module")#.setDebug()
                 
        udpDecl = outputDecl | inputDecl | regDecl
        udpInitVal = oneOf("1'b0 1'b1 1'bx 1'bX 1'B0 1'B1 1'Bx 1'BX 1 0 x X")
        udpInitialStmt = Group( "initial" + 
            identifier + "=" + udpInitVal + semi ).setName("udpInitialStmt")
        
        levelSymbol = oneOf("0   1   x   X   ?   b   B")
        levelInputList = Group( OneOrMore( levelSymbol ).setName("levelInpList") )
        outputSymbol = oneOf("0   1   x   X")
        combEntry = Group( levelInputList + ":" + outputSymbol + semi )
        edgeSymbol = oneOf("r   R   f   F   p   P   n   N   *")
        edge = Group( "(" + levelSymbol + levelSymbol + ")" ) | \
               Group( edgeSymbol )
        edgeInputList = Group( ZeroOrMore( levelSymbol ) + edge + ZeroOrMore( levelSymbol ) )
        inputList = levelInputList | edgeInputList
        seqEntry = Group( inputList + ":" + levelSymbol + ":" + ( outputSymbol | "-" ) + semi ).setName("seqEntry")
        udpTableDefn = Group( "table" + 
            OneOrMore( combEntry | seqEntry ) + 
            "endtable" ).setName("table")
        
        """
        <UDP>
        ::= primitive <name_of_UDP> ( <name_of_variable> <,<name_of_variable>>* ) ;
                <UDP_declaration>+
                <UDP_initial_statement>?
                <table_definition>
                endprimitive
        """
        udp = Group( "primitive" + identifier +
            "(" + Group( delimitedList( identifier ) ) + ")" + semi +
            OneOrMore( udpDecl ) +
            Optional( udpInitialStmt ) +
            udpTableDefn +
            "endprimitive" )
            
        verilogbnf = OneOrMore( module | udp ) + StringEnd()

        singleLineComment = ( "//" + restOfLine ).setName("singleLineComment")
        #~ verilogbnf.ignore( singleLineComment )
        #~ verilogbnf.ignore( cStyleComment )
        allCcomments = FollowedBy("/") + ( cStyleComment | singleLineComment )
        verilogbnf.ignore( allCcomments )
        verilogbnf.ignore( compilerDirective )
        
    return verilogbnf


def test( strng ):
    tokens = []
    try:
        tokens = Verilog_BNF().parseString( strng )
    except ParseException, err:
        print err.line
        print " "*(err.column-1) + "^"
        print err
    return tokens


#~ if __name__ == "__main__":
if 0:
    import pprint
    toptest = """
        module TOP( in, out );
        input [7:0] in;
        output [5:0] out;
        COUNT_BITS8 count_bits( .IN( in ), .C( out ) );
        endmodule"""
    pprint.pprint( test(toptest).asList() )
    
else:
    #~ import make_constants
    #~ map(make_constants.bind_all, (Word, OneOrMore, ZeroOrMore,ParserElement, Literal, And, MatchFirst ) )
    def main():
        import os
        failCount = 0
        Verilog_BNF()
        numlines = 0
        startTime = time.clock()
        #~ fileDir = "verilog/new"
        fileDir = "verilog"
        allFiles = filter( lambda f : f.endswith(".v"), os.listdir(fileDir) )
        #~ allFiles = [ "list_path_delays_test.v" ]
        #~ allFiles = filter( lambda f : f.startswith("a") and f.endswith(".v"), os.listdir(fileDir) )
        pp = pprint.PrettyPrinter( indent=2 )
        totalTime = 0
        for vfile in allFiles:
            fnam = fileDir + "/"+vfile
            infile = file(fnam) 
            filelines = infile.readlines()
            infile.close()
            print fnam, len(filelines),
            numlines += len(filelines)
            teststr = "".join(filelines)
            time1 = time.clock()
            tokens = test( teststr )
            time2 = time.clock()
            elapsed = time2-time1
            totalTime += elapsed
            if ( len( tokens ) ):
                print "OK", elapsed
                #~ print "tokens="
                #~ pp.pprint( tokens.asList() )
                #~ print
            else:
                print "failed", elapsed
                failCount += 1
        endTime = time.clock()
        print "Total parse time:", totalTime
        print "Total source lines:", numlines
        print "Average lines/sec:", ( "%.1f" % (float(numlines)/(totalTime+.05 ) ) )
        if failCount:
            print "FAIL - %d files failed to parse" % failCount
        else:
            print "SUCCESS - all files parsed"
            
        return 0
    
    main()
    #~ import hotshot
    #~ p = hotshot.Profile("vparse.prof",1,1)
    #~ p.start()
    #~ main()
    #~ p.stop()
    #~ p.close()