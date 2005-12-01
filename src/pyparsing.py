# module pyparsing.py
#
# Copyright (c) 2003,2004  Paul T. McGuire
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
#  Todo:
#  - add pprint() - pretty-print output of defined BNF
#
from __future__ import generators
"""
pyparsing module - Classes and methods to define and execute parsing grammars
"""
__version__ = "1.1.2"
__author__ = "Paul McGuire <ptmcg@users.sourceforge.net>"
#~ print "testing pyparsing module, version", __version__

import string
import copy,sys

class ParseException(Exception):
    "exception thrown when parse expressions don't match class"
    __slots__ = ( "loc","msg","pstr" )
    # Performance tuning: we construct a *lot* of these, so keep this
    # constructor as small and fast as possible
    def __init__( self, pstr, loc, msg ):
        self.loc = loc
        self.msg = msg
        self.pstr = pstr

    def __getattr__( self, aname ):
        """supported attributes by name are:
            - lineno - returns the line number of the exception text
            - col - returns the column number of the exception text
            - line - returns the line containing the exception text
        """
        if( aname == "lineno" ):
            return lineno( self.loc, self.pstr )
        elif( aname in ("col", "column") ):
            return col( self.loc, self.pstr )
        elif( aname == "line" ):
            return line( self.loc, self.pstr )
        else:
            raise AttributeError, aname

    def __str__( self ):
        return "%s (%d), (%d,%d)" % ( self.msg, self.loc, self.lineno, self.column )
    def __repr__( self ):
        return str(self)

class RecursiveGrammarException(Exception):
    "exception thrown by validate() if the grammar could be improperly recursive"
    def __init__( self, parseElementList ):
        self.parseElementTrace = parseElementList
    
    def __str__( self ):
        return "RecursiveGrammarException: %s" % self.parseElementTrace

class ParseResults(object):
    """Structured parse results, to provide multiple means of access to the parsed data:
       - as a list (len(results))
       - by list index (results[0], results[1], etc.)
       - by attribute (results.<resultsName>)
       """
    __slots__ = ( "list", "dict" )
    # Performance tuning: we construct a *lot* of these, so keep this
    # constructor as small and fast as possible
    def __init__( self, toklist, name=None, asList=True ):
        toklistType = type(toklist)
        if toklistType is ParseResults:
            self.list = toklist.list[:]
            self.dict = toklist.dict.copy()
        elif toklistType is list:
            self.list = toklist[:]
            self.dict = {}
        else:
            self.list = [toklist]
            self.dict = {}
            
        if name:
            if toklist:
                if asList:
                    self.dict[name] = ParseResults(toklist[0])
                else:
                    try:
                        self.dict[name] = toklist[0]
                    except TypeError:
                        self.dict[name] = toklist

    def __getitem__( self, i ):
        if isinstance( i, int ):
            return self.list[i]
        else:
            return self.dict[i]

    def __delitem__( self, i ):
        del self.list[i]

    def __len__( self ): return len( self.list )
    def __iter__( self ): return iter( self.list )
    def keys( self ): return self.dict.keys()
    def items( self ): return self.dict.items()

    def __getattr__( self, name ):
        if self.dict.has_key( name ):
            return self.dict[name]
        else:
            return ""

    def __iadd__( self, other ):
        self.list += other.list
        self.dict.update( other.dict )
        return self
       
    def __repr__( self ):
        return "(%s, %s)" % ( repr( self.list ), repr( self.dict ) )

    def __str__( self ):
        out = "["
        sep = ""
        for i in self.list:
            if isinstance(i, ParseResults):
                out += sep + str(i)
            else:
                out += sep + repr(i)
            sep = ", "
        out += "]"
        return out

    def _asStringList( self ):
        out = []
        for item in self.list:
            if isinstance( item, ParseResults ):
                out += item._asStringList()
            else:
                out += item
        return out

    def asList( self ):
        "Returns the parse results as a nested list of matching tokens, all converted to strings."
        out = []
        for res in self.list:
            if isinstance(res,ParseResults):
                out.append( res.asList() )
            else:
                out.append( res )
        return out

col = lambda loc,strg: loc - strg.rfind("\n", 0, loc)
col.__doc__ = """Returns current column within a string, counting newlines as line separators
   The first column is number 1.
   """

lineno = lambda loc,strg: strg.count("\n",0,loc) + 1
lineno.__doc__ = """Returns current line number within a string, counting newlines as line separators
   The first line is number 1.
   """

def line( loc, strg ):
    """Returns the line of text containing loc within a string, counting newlines as line separators
       The first line is number 1.
       """
    lastCR = strg.rfind("\n", 0, loc)
    nextCR = strg.find("\n", loc)
    if nextCR > 0:
        return strg[lastCR+1:nextCR]
    else:
        return strg[lastCR+1:]


class ParserElement(object):
    "Abstract base level parser element class."
    def __init__( self, savelist=False ):
        self.parseAction = None
        #~ self.name = "<unknown>"  # don't define self.name, let subclasses try/except upcall
        self.strRepr = None
        self.resultsName = None
        self.saveList = savelist
        self.skipWhitespace = True
        self.whiteChars = " \n\t\r"
        self.mayReturnEmpty = False
        self.ignoreExprs = []
        self.debug = False
        self.streamlined = False
        
    def setName( self, name ):
        "Define name for this expression, for use in debugging."
        self.name = name
        self.errmsg = "Expected " + self.name
        return self

    def setResultsName( self, name ):
        """Define name for referencing matching tokens as a nested attribute 
           of the returned parse results.
           NOTE: this returns a *copy* of the original ParseElement object;
           this is so that the client can define a basic element, such as an
           integer, and reference it in multiple places with different names.
        """
        newself = copy.copy( self )
        newself.resultsName = name
        return newself

    def getResultsName( self ):
        return self.resultsName

    def setParseAction( self, fn ):
        """Define action to perform when successfully matching parse element definition.
           Parse action fn is a callable method with the arguments (s, loc, toks) where:
            - s   = the original string being parsed
            - loc = the location of the matching substring
            - toks = a list of the matched tokens
           fn must return toks (although fn may modify the list passed in as an argument) 
        """
        self.parseAction = fn
        return self

    def skipIgnorables( self, instring, loc ):
        exprsFound = True
        while exprsFound:
            exprsFound = False
            for e in self.ignoreExprs:
                try:
                    while 1:
                        loc,dummy = e.parse( instring, loc )
                        exprsFound = True
                except ParseException:
                    pass
        return loc

    def preParse( self, instring, loc ):
        if self.ignoreExprs:
            loc = self.skipIgnorables( instring, loc )
        
        if self.skipWhitespace:
            wt = self.whiteChars
            instrlen = len(instring)
            while loc < instrlen and instring[loc] in wt:
                loc += 1
                
        return loc

    def parseImpl( self, instring, loc, doActions=True ):
        return loc,[]

    def postParse( self, instring, loc, tokenlist ):
        return loc,tokenlist

    def parse( self, instring, loc, doActions=True ):
        debugging = ( self.debug and doActions )

        if debugging:
            print "Match",self,"at loc",loc,"(%d,%d)" % ( lineno(loc,instring), col(loc,instring) )
            loc = self.preParse( instring, loc )
            tokensStart = loc
            try:
                loc,tokens = self.parseImpl( instring, loc, doActions )
            except IndexError:
                raise ParseException, ( instring, len(instring), "Expected "+str(self) )
            except ParseException, err:
                print "Exception raised:", err
                raise
        else:
            loc = self.preParse( instring, loc )
            tokensStart = loc
            try:
                loc,tokens = self.parseImpl( instring, loc, doActions )
            except IndexError:
                raise ParseException, ( instring, len(instring), "Expected "+str(self) )
        
        loc,tokens = self.postParse( instring, loc, tokens )

        retTokens = ParseResults( tokens, self.getResultsName(), asList=self.saveList )
        if self.parseAction and doActions:
            if debugging:
                try:
                    tokens = self.parseAction( instring, tokensStart, retTokens )
                    if isinstance(tokens,tuple):
                        tokens = tokens[1]
                    retTokens = ParseResults( tokens, self.getResultsName(), asList=self.saveList )
                except ParseException, err:
                    print "Exception raised in user parse action:", err
                    raise
            else:
                tokens = self.parseAction( instring, tokensStart, retTokens )
                if isinstance(tokens,tuple):
                    tokens = tokens[1]
                retTokens = ParseResults( tokens, self.getResultsName(), asList=self.saveList )

        if debugging:
            print "Matched",self,"->",retTokens.asList()

        return loc, retTokens

    def tryParse( self, instring, loc ):
        return self.parse( instring, loc, doActions=False )

    def parseString( self, instring ):
        """Execute the parse expression with the given string.
           This is the main interface to the client code, once the complete 
           expression has been built.
        """
        if not self.streamlined:
            self.streamline()
        for e in self.ignoreExprs:
            e.streamline()
        loc, tokens = self.parse( instring.expandtabs(), 0 )
        return tokens

    def scanString( self, instring ):
        if not self.streamlined:
            self.streamline()
        for e in self.ignoreExprs:
            e.streamline()
        
        instring = instring.expandtabs()
        instrlen = len(instring)
        loc = 0
        preparseFn = self.preParse
        parseFn = self.parse
        while loc < instrlen:
            try:
                loc = preparseFn( instring, loc )
                nextLoc,tokens = parseFn( instring, loc )
            except ParseException:
                loc += 1
            else:
                yield tokens, loc, nextLoc
                loc = nextLoc
        
    def __add__(self, other ):
        if isinstance( other, str ):
            other = Literal( other )
        return And( [ self, other ] )

    def __radd__(self, other ):
        if isinstance( other, str ):
            other = Literal( other )
        return other + self

    def __or__(self, other ):
        if isinstance( other, str ):
            other = Literal( other )
        return MatchFirst( [ self, other ] )

    def __ror__(self, other ):
        if isinstance( other, str ):
            other = Literal( other )
        return other | self

    def __xor__(self, other ):
        if isinstance( other, str ):
            other = Literal( other )
        return Or( [ self, other ] )

    def __rxor__(self, other ):
        if isinstance( other, str ):
            other = Literal( other )
        return other ^ self

    def __invert__( self ):
        return NotAny( self )

    def suppress( self ):
        """Suppresses the output of this ParseElement; useful to keep punctuation from
           cluttering up returned output.
        """
        return Suppress( self )

    def leaveWhitespace( self ):
        self.skipWhitespace = False
        return self

    def ignore( self, other ):
        """Define expression to be ignored (e.g., comments) while doing pattern 
           matching; may be called repeatedly, to define multiple comment or other
           ignorable patterns.
        """
        if isinstance( other, Suppress ):
            if other not in self.ignoreExprs:
                self.ignoreExprs.append( other )
        else:
            self.ignoreExprs.append( Suppress( other ) )

    def setDebug( self, flag=True ):
        "Enable display of debugging messages while doing pattern matching."
        self.debug = flag
        return self

    def __str__( self ):
        return self.name

    def __repr__( self ):
        return str(self)
        
    def streamline( self ):
        self.streamlined = True
        self.strRepr = None
        return self
        
    def checkRecursion( self, parseElementList ):
        pass
        
    def validate( self, validateTrace=[] ):
        self.checkRecursion( [] )


class Token(ParserElement):
    "Abstract ParserElement subclass, for defining atomic matching patterns."
    def __init__( self ):
        super(Token,self).__init__( savelist=False )


class Empty(Token):
    "An empty token, will always match."
    def __init__( self ):
        super(Empty,self).__init__()
        self.name = "Empty"
        self.mayReturnEmpty = True


class Literal(Token):
    "Token to exactly match a specified string."
    def __init__( self, matchString ):
        super(Literal,self).__init__()
        self.match = matchString
        self.matchLen = len(matchString)
        self.firstMatchChar = matchString[0]
        self.name = '"%s"' % self.match
        self.errmsg = "Expected " + self.name
        self.mayReturnEmpty = ( self.matchLen == 0 )

    # Performance tuning: this routine gets called a *lot*
    # if this is a single character match string  and the first character matches,
    # short-circuit as quickly as possible, and avoid constructing string slice
    def parseImpl( self, instring, loc, doActions=True ):
        if not(instring[loc] == self.firstMatchChar) or \
           (self.matchLen > 1 and instring[ loc:loc+self.matchLen ] != self.match ):
            raise ParseException, ( instring, loc, self.errmsg )
        return loc+self.matchLen, [ self.match ]


class CaselessLiteral(Literal):
    """Token to match a specified string, ignoring case of letters.
       Note: the matched results will always be in the case of the given
       match string, NOT the case of the input text.
    """
    def __init__( self, matchString ):
        super(CaselessLiteral,self).__init__( matchString.upper() )
        self.name = "'%s'" % self.match
        self.errmsg = "Expected " + self.name

    def parseImpl( self, instring, loc, doActions=True ):
        if instring[ loc:loc+self.matchLen ].upper() != self.match:
            raise ParseException, ( instring, loc, self.errmsg )
        return loc+self.matchLen, [ self.match ]


class Word(Token):
    """Token for matching words composed of allowed character sets
       Defined with string containing all allowed initial characters,
       an optional string containing allowed body characters (if omitted,
       defaults to the initial character set), and an optional minimum,
       maximum, and/or exact length.
    """
    def __init__( self, initChars, bodyChars=None, min=1, max=0, exact=0 ):
        super(Word,self).__init__()
        self.initChars = initChars
        if bodyChars :
            self.bodyChars = bodyChars
        else:
            self.bodyChars = initChars

        self.minLen = min

        if max > 0:
            self.maxLen = max
        else:
            self.maxLen = sys.maxint

        if exact > 0:
            self.maxLen = exact
            self.minLen = exact

        self.name = str(self)
        self.errmsg = "Expected " + self.name

    def parseImpl( self, instring, loc, doActions=True ):
        if not(instring[ loc ] in self.initChars):
            raise ParseException, ( instring, loc, self.errmsg )
        start = loc
        loc += 1
        bodychars = self.bodyChars
        maxloc = start + self.maxLen
        maxloc = min( maxloc, len(instring) )
        while loc < maxloc and instring[loc] in bodychars:
            loc += 1

        if loc - start < self.minLen:
            raise ParseException, ( instring, loc, self.errmsg )

        return loc, [ instring[start:loc] ]

    def __str__( self ):
        try:
            return super(Word,self).__str__()
        except:
            pass

            
        if self.strRepr is None:
            
            def charsAsStr(s):
                if len(s)>4:
                    return s[:4]+"..."
                else:
                    return s
            
            if ( self.initChars != self.bodyChars ):
                self.strRepr = "W:(%s,%s)" % ( charsAsStr(self.initChars), charsAsStr(self.bodyChars) )
            else:
                self.strRepr = "W:(%s)" % charsAsStr(self.initChars)

        return self.strRepr


class CharsNotIn(Token):
    """Token for matching words composed of characters *not* in a given set.
       Defined with string containing all disallowed characters, and an optional 
       minimum, maximum, and/or exact length.
    """
    def __init__( self, notChars, min=1, max=0, exact=0 ):
        super(CharsNotIn,self).__init__()
        self.skipWhitespace = False
        self.notChars = notChars
        
        self.minLen = min

        if max > 0:
            self.maxLen = max
        else:
            self.maxLen = sys.maxint

        if exact > 0:
            self.maxLen = exact
            self.minLen = exact
        
        self.name = str(self)
        self.errmsg = "Expected " + self.name
        self.mayReturnEmpty = ( self.minLen == 0 )

    def parseImpl( self, instring, loc, doActions=True ):
        if instring[loc] in self.notChars:
            raise ParseException, ( instring, loc, self.errmsg )
            
        start = loc
        loc += 1
        notchars = self.notChars
        maxlen = min( start+self.maxLen, len(instring) )
        while loc < maxlen and \
              (instring[loc] not in notchars):
            loc += 1

        if loc - start < self.minLen:
            raise ParseException, ( instring, loc, self.errmsg )

        return loc, [ instring[start:loc] ]

    def __str__( self ):
        try:
            return super(CharsNotIn, self).__str__()
        except:
            pass

        if self.strRepr is None:
            if len(self.notChars) > 4:
                self.strRepr = "!W:(%s...)" % self.notChars[:4]
            else:
                self.strRepr = "!W:(%s)" % self.notChars
        
        return self.strRepr


class PositionToken(Token):
    def __init__( self ):
        super(PositionToken,self).__init__()
        self.name=self.__class__.__name__
        self.mayReturnEmpty = True

class GoToColumn(PositionToken):
    "Token to advance to a specific column of input text; useful for tabular report scraping."
    def __init__( self, colno ):
        super(GoToColumn,self).__init__()
        self.col = colno

    def preParse( self, instring, loc ):
        if col(loc,instring) != self.col:
            instrlen = len(instring)
            if self.ignoreExprs:
                loc = self.skipIgnorables( instring, loc )
            while loc < instrlen and instring[loc].isspace() and col( loc, instring ) != self.col :
                loc += 1
        return loc

    def parseImpl( self, instring, loc, doActions=True ):
        thiscol = col( loc, instring )
        if thiscol > self.col:
            raise ParseException, ( instring, loc, "Text not in expected column" )
        newloc = loc + self.col - thiscol
        ret = instring[ loc: newloc ]
        return newloc, [ ret ]

class LineStart(PositionToken):
    "Matches if current position is at the beginning of a line within the parse string"
    def __init__( self ):
        super(LineStart,self).__init__()
        self.whiteChars = " \t"

    def preParse( self, instring, loc ):
        loc = super(LineStart,self).preParse(instring,loc)
        if instring[loc] == "\n":
            loc += 1
        return loc

    def parseImpl( self, instring, loc, doActions=True ):
        if not( loc==0 or ( loc<len(instring) and instring[loc-1] == "\n" ) ): #col(loc, instring) != 1:
            raise ParseException, ( instring, loc, "Expected start of line" )
        return loc, []

class LineEnd(PositionToken):
    "Matches if current position is at the end of a line within the parse string"
    def __init__( self ):
        super(LineEnd,self).__init__()
        self.whiteChars = " \t"
    
    def parseImpl( self, instring, loc, doActions=True ):
        if loc<len(instring) and instring[loc] != "\n":
            raise ParseException, ( instring, loc, "Expected end of line" )
        return loc, []

class StringStart(PositionToken):
    "Matches if current position is at the beginning of the parse string"
    def __init__( self ):
        super(StringStart,self).__init__()
    
    def parseImpl( self, instring, loc, doActions=True ):
        if loc != 0:
            # see if entire string up to here is just whitespace and ignoreables
            if loc != self.preParse( instring, 0 ):
                raise ParseException, ( instring, loc, "Expected start of text" )
        return loc, []

class StringEnd(PositionToken):
    "Matches if current position is at the end of the parse string"
    def __init__( self ):
        super(StringEnd,self).__init__()
    
    def parseImpl( self, instring, loc, doActions=True ):
        if loc < len(instring):
            raise ParseException, ( instring, loc, "Expected end of text" )
        return loc, []


class ParseExpression(ParserElement):
    "Abstract subclass of ParserElement, for combining and post-processing parsed tokens."
    def __init__( self, exprs, savelist = False ):
        super(ParseExpression,self).__init__(savelist)
        if isinstance( exprs, list ):
            self.exprs = exprs
        elif isinstance( exprs, str ):
            self.exprs = [ Literal( exprs ) ]
        else:
            self.exprs = [ exprs ]

    def append( self, other ):
        self.exprs.append( other )
        self.strRepr = None
        return self

    def leaveWhitespace( self ):
        self.skipWhitespace = False
        self.exprs = [ copy.copy(e) for e in self.exprs ]
        for e in self.exprs:
            e.leaveWhitespace()
        return self

    def ignore( self, other ):
        if isinstance( other, Suppress ):
            if other not in self.ignoreExprs:
                super( ParseExpression, self).ignore( other )
                for e in self.exprs:
                    e.ignore( self.ignoreExprs[-1] )
        else:
            super( ParseExpression, self).ignore( other )
            for e in self.exprs:
                e.ignore( self.ignoreExprs[-1] )

    def __str__( self ):
        try:
            return super(ParseExpression,self).__str__()
        except:
            pass
            
        if self.strRepr is None:
            self.strRepr = "%s:(%s)" % ( self.__class__.__name__, str(self.exprs) )
        return self.strRepr

    def streamline( self ):
        super(ParseExpression,self).streamline()

        for e in self.exprs:
            e.streamline()

        if ( len(self.exprs) == 2 and
              not ( self.parseAction or self.resultsName ) ):
            other = self.exprs[0]
            if ( isinstance( other, self.__class__ ) ):
                if not ( other.parseAction or other.resultsName ):
                    self.exprs = other.exprs[:] + [ self.exprs[1] ]
                    self.strRepr = None
                
            other = self.exprs[1]
            if ( isinstance( other, self.__class__ ) ):
                if not ( other.parseAction or other.resultsName ):
                    self.exprs = [ self.exprs[0] ] + other.exprs[:]
                    self.strRepr = None
        
        return self

    def validate( self, validateTrace=[] ):
        tmp = validateTrace[:]+[self]
        for e in self.exprs:
            e.validate(tmp)
        self.checkRecursion( [] )


class And(ParseExpression):
    """Requires all given ParseExpressions to be found in the given order.
       Expressions may be separated by whitespace.
       May be constructed using the '+' operator.
    """
    def __init__( self, exprs, savelist = False ):
        super(And,self).__init__(exprs, savelist)
        self.mayReturnEmpty = True
        for e in exprs:
            if not e.mayReturnEmpty:
                self.mayReturnEmpty = False
                break
 
    def parseImpl( self, instring, loc, doActions=True ):
        loc, resultlist = self.exprs[0].parse( instring, loc, doActions )
        for e in self.exprs[1:]:
            loc, exprtokens = e.parse( instring, loc, doActions )
            resultlist += exprtokens

        return loc, resultlist

    def __iadd__(self, other ):
        if isinstance( other, str ):
            other = Literal( other )
        return self.append( other ) #And( [ self, other ] )
        
    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )
            if not e.mayReturnEmpty:
                break

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name
            
        if self.strRepr is None:
            self.strRepr = "{" + " ".join( [ str(e) for e in self.exprs ] ) + "}"
        
        return self.strRepr

class Or(ParseExpression):
    """Requires that at least one ParseExpression is found.
       If two expressions match, the expression that matches the longest string will be used.
       May be constructed using the '^' operator.
    """
    def __init__( self, exprs, savelist = False ):
        super(Or,self).__init__(exprs, savelist)
        self.mayReturnEmpty = False
        for e in exprs:
            if e.mayReturnEmpty:
                self.mayReturnEmpty = True
                break
    
    def parseImpl( self, instring, loc, doActions=True ):
        exceptions = []
        matches = []
        for e in self.exprs:
            try:
                loc2, tokenlist = e.tryParse( instring, loc )
                matches.append( ( loc2, e ) )
            except ParseException, err:
                exceptions.append( copy.copy(err) )

        if len( matches ) == 0:
            sortDescendingLoc = ( lambda a,b: b.loc - a.loc )
            exceptions.sort( sortDescendingLoc )
            raise exceptions[0]

        matches.sort( lambda a,b: b[0]-a[0] )
        e = matches[0][1]
        return e.parse( instring, loc, doActions )

    def __ixor__(self, other ):
        if isinstance( other, str ):
            other = Literal( other )
        return self.append( other ) #Or( [ self, other ] )

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name
            
        if self.strRepr is None:
            self.strRepr = "{" + " ^ ".join( [ str(e) for e in self.exprs ] ) + "}"
        
        return self.strRepr
    
    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )


class MatchFirst(ParseExpression):
    """Requires that at least one ParseExpression is found.
       If two expressions match, the first one listed is the one that will match.
       May be constructed using the '|' operator.
    """
    def __init__( self, exprs, savelist = False ):
        super(MatchFirst,self).__init__(exprs, savelist)
        self.mayReturnEmpty = False
        for e in exprs:
            if e.mayReturnEmpty:
                self.mayReturnEmpty = True
                break
    
    def parseImpl( self, instring, loc, doActions=True ):
        maxExcLoc = -1
        for e in self.exprs:
            try:
                return e.parse( instring, loc )
            except ParseException, err:
                if err.loc > maxExcLoc:
                    maxException = err
                    maxExcLoc = err.loc

        # only got here if no expression matched, raise exception for match that made it the furthest
        raise maxException

        #~ return loc2, tokenlist

    def __ior__(self, other ):
        if isinstance( other, str ):
            other = Literal( other )
        return self.append( other ) #MatchFirst( [ self, other ] )

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name
            
        if self.strRepr is None:
            self.strRepr = "{" + " | ".join( [ str(e) for e in self.exprs ] ) + "}"
        
        return self.strRepr
    
    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )


class ParseElementEnhance(ParserElement):
    "Abstract subclass of ParserElement, for combining and post-processing parsed tokens."
    def __init__( self, expr, savelist=False ):
        super(ParseElementEnhance,self).__init__(savelist)
        if isinstance( expr, str ):
            expr = Literal(expr)
        self.expr = expr
        self.strRepr = None
        
    def parseImpl( self, instring, loc, doActions=True ):
        return self.expr.parse( instring, loc, doActions )

    def leaveWhitespace( self ):
        self.skipWhitespace = False
        self.expr = copy.copy(self.expr)
        self.expr.leaveWhitespace()
        return self

    def ignore( self, other ):
        if isinstance( other, Suppress ):
            if other not in self.ignoreExprs:
                super( ParseElementEnhance, self).ignore( other )
                self.expr.ignore( self.ignoreExprs[-1] )
        else:
            super( ParseElementEnhance, self).ignore( other )
            self.expr.ignore( self.ignoreExprs[-1] )

    def streamline( self ):
        super(ParseElementEnhance,self).streamline()
        self.expr.streamline()
        return self

    def checkRecursion( self, parseElementList ):
        if self in parseElementList:
            raise RecursiveGrammarException( parseElementList+[self] )
        subRecCheckList = parseElementList[:] + [ self ]
        self.expr.checkRecursion( subRecCheckList )
        
    def validate( self, validateTrace=[] ):
        tmp = validateTrace[:]+[self]
        self.expr.validate(tmp)
        self.checkRecursion( [] )
    
    def __str__( self ):
        try:
            return super(ParseElementEnhance,self).__str__()
        except:
            pass
            
        if self.strRepr is None:
            self.strRepr = "%s:(%s)" % ( self.__class__.__name__, str(self.expr) )
        return self.strRepr


class NotAny(ParseElementEnhance):
    "Lookahead to disallow matching with the given parse expression."
    def __init__( self, expr ):
        super(NotAny,self).__init__(expr)
        #~ self.leaveWhitespace()
        self.skipWhitespace = False  # do NOT use self.leaveWhitespace(), don't want to propagate to exprs
        self.mayReturnEmpty = True
        self.errmsg = "Found unexpected token, "+str(self.expr)
        
    def parseImpl( self, instring, loc, doActions=True ):
        try:
            loc2, tokenlist = self.expr.tryParse( instring, loc )
        except ParseException:
            pass
        else:
            raise ParseException, (instring, loc, self.errmsg )

        return loc, []

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name
            
        if self.strRepr is None:
            self.strRepr = "~{" + str(self.expr) + "}"
        
        return self.strRepr


class ZeroOrMore(ParseElementEnhance):
    "Optional repetition of zero or more of the given expression."
    def __init__( self, expr ):
        super(ZeroOrMore,self).__init__(expr)
        self.mayReturnEmpty = True
    
    def parseImpl( self, instring, loc, doActions=True ):
        tokens = []
        try:
            loc, tokens = self.expr.parse( instring, loc, doActions )
            hasIgnoreExprs = ( len(self.ignoreExprs) > 0 )
            while 1:
                if hasIgnoreExprs:
                    loc = self.skipIgnorables( instring, loc )
                loc, tmptokens = self.expr.parse( instring, loc, doActions )
                tokens += tmptokens
        except ParseException:
            pass

        return loc, tokens

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name
            
        if self.strRepr is None:
            self.strRepr = "[" + str(self.expr) + "]..."
        
        return self.strRepr
    

class OneOrMore(ParseElementEnhance):
    "Repetition of one or more of the given expression."
    def parseImpl( self, instring, loc, doActions=True ):
        # must be at least one
        loc, tokens = self.expr.parse( instring, loc, doActions )
        try:
            hasIgnoreExprs = ( len(self.ignoreExprs) > 0 )
            while 1:
                if hasIgnoreExprs:
                    loc = self.skipIgnorables( instring, loc )
                loc, tmptokens = self.expr.parse( instring, loc, doActions )
                tokens += tmptokens
        except ParseException:
            pass

        return loc, tokens

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name
            
        if self.strRepr is None:
            self.strRepr = "{" + str(self.expr) + "}..."
        
        return self.strRepr
    

class Optional(ParseElementEnhance):
    """Optional matching of the given expression.
       A default return string can also be specified, if the optional expression
       is not found.
    """
    def __init__( self, exprs, default=None ):
        super(Optional,self).__init__( exprs, savelist=False )
        self.defaultValue = default
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        try:
            loc, tokens = self.expr.parse( instring, loc, doActions )
        except ParseException:
            if self.defaultValue is not None:
                tokens = [ self.defaultValue ]
            else:
                tokens = []

        return loc, tokens

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name
            
        if self.strRepr is None:
            self.strRepr = "[" + str(self.expr) + "]"
        
        return self.strRepr
    

class Forward(ParseElementEnhance):
    """Forward declaration of an expression to be defined later -
       used for recursive grammars, such as algebraic infix notation.
       When the expression is known, it is assigned to the Forward variable using the '<<' operator.
    """
    def __init__( self, other=None ):
        super(Forward,self).__init__( other, savelist=False )

    def __lshift__( self, other ):
        self.expr = other
        self.mayReturnEmpty = other.mayReturnEmpty
        self.strRepr = None
        return self

    def leaveWhitespace( self ):
        self.skipWhitespace = False
        return self

    def streamline( self ):
        if not self.streamlined:
            self.streamlined = True
            self.expr.streamline()
        return self

    def validate( self, validateTrace=[] ):
        if self not in validateTrace:
            tmp = validateTrace[:]+[self]
            self.expr.validate(tmp)
        self.checkRecursion([])        
        
    def __str__( self ):
        if hasattr(self,"name"):
            return self.name
            
        strmethod = self.__str__
        self.__class__ = _ForwardNoRecurse
        retString = str(self.expr)
        self.__class__ = Forward
        return "Forward:"+retString

class _ForwardNoRecurse(Forward):
    def __str__( self ):
        return "..."
        
class TokenConverter(ParseElementEnhance):
    "Abstract subclass of ParseExpression, for converting parsed results."
    def __init__( self, expr, savelist=False ):
        super(TokenConverter,self).__init__( expr )#, savelist )


class Upcase(TokenConverter):
    "Converter to upper case all matching tokens."
    def postParse( self, instring, loc, tokenlist ):
        return loc, map( string.upper, tokenlist )


class Combine(TokenConverter):
    """Converter to concatenate all matching tokens to a single string.
       By default, the matching patterns must also be contiguous in the input string;
       this can be disabled by specifying 'adjacent=False' in the constructor.
    """
    def __init__( self, expr, joinString="", adjacent=True ):
        super(Combine,self).__init__( expr )
        # suppress whitespace-stripping in contained parse expressions, but re-enable it on the Combine itself
        if adjacent:
            self.leaveWhitespace()
        self.skipWhitespace = True
        self.joinString = joinString

    def postParse( self, instring, loc, tokenlist ):
        retToks = ParseResults( tokenlist )
        retToks.list = [ self.joinString.join(tokenlist._asStringList()) ]

        if self.getResultsName() and len(retToks.keys())>0:
            return loc, [ retToks ]
        else:
            return loc, retToks


class Group(TokenConverter):
    "Converter to return the matched tokens as a list - useful for returning tokens of ZeroOrMore and OneOrMore expressions."
    def __init__( self, exprs ):
        super(Group,self).__init__( exprs )
        self.saveList = True

    def postParse( self, instring, loc, tokenlist ):
        return loc, [ tokenlist ]

class Dict(TokenConverter):
    """Converter to return a repetitive expression as a list, but also as a dictionary.
       Each element can also be referenced using the first token in the expression as its key.
       Useful for tabular report scraping when the first column can be used as a item key.
    """
    def __init__( self, exprs ):
        super(Dict,self).__init__( exprs )
        self.saveList = True

    def postParse( self, instring, loc, tokenlist ):
        for i in tokenlist:
            ikey = str(i[0]).strip()
            if len(i)==1:
                tokenlist.dict[ ikey ] = ""
            elif len(i)==2:
                tokenlist.dict[ ikey ] = i[1]
            else:
                dictvalue = ParseResults(i)
                del dictvalue[0]
                tokenlist.dict[ ikey ] = dictvalue

        if self.getResultsName():
            return loc, [ tokenlist ]
        else:
            return loc, tokenlist


class Suppress(TokenConverter):
    "Converter for ignoring the results of a parsed expression."
    def postParse( self, instring, loc, tokenlist ):
        return loc, []
    
    def suppress( self ):
        return self

#
# global helpers
#
def delimitedList( expr, delim=",", combine=False ):
    """Helper to define a delimited list of expressions - the delimiter defaults to ','.
       By default, the list elements and delimiters can have intervening whitespace, and 
       comments, but this can be overridden by passing 'combine=True' in the constructor.
       If combine is set to True, the matching tokens are returned as a single token
       string, with the delimiters included; otherwise, the matching tokens are returned
       as a list of tokens, with the delimiters suppressed.
    """
    if combine:
        return Combine( expr + ZeroOrMore( Literal(delim) + expr ) ).setName(str(expr)+delim+"...")
    else:
        return ( expr + ZeroOrMore( Suppress( Literal(delim) ) + expr ) ).setName(str(expr)+delim+"...")

def oneOf( strs, caseless=False ):
    """Helper to quickly define a set of alternative Literals, and makes sure to do 
       longest-first testing when there is a conflict, regardless of the input order, 
       but returns a MatchFirst for best performance.
    """
    symbols = strs.split()
    i = 0
    while i < len(symbols)-1:
        cur = symbols[i]
        for j,other in enumerate(symbols[i+1:]):
            if ( other == cur ):
                del symbols[i+j+1]
                break
            elif ( other.startswith(cur) ):
                del symbols[i+j+1]
                symbols.insert(i,other)
                cur = other
                break
        else:
            i += 1
    if caseless:
        return MatchFirst( [ CaselessLiteral(sym) for sym in symbols ] )
    else:
        return MatchFirst( [ Literal(sym) for sym in symbols ] )
    
alphas     = string.letters
nums       = string.digits
alphanums  = alphas + nums
printables = "".join( [ c for c in string.printable if c not in string.whitespace ] )
empty      = Empty().setName("empty")

_bslash = "\\"
_escapables = "tnrfbacdeghijklmopqsuvwxyz" + _bslash
_octDigits = "01234567"
_escapedChar = ( Word( _bslash, _escapables, exact=2 ) |
                 Word( _bslash, _octDigits, min=2, max=4 ) )
_sglQuote = Literal("'")
_dblQuote = Literal('"')
dblQuotedString = Combine( _dblQuote + ZeroOrMore( CharsNotIn('\\"\n\r') | _escapedChar ) + _dblQuote ).streamline().setName("string enclosed in double quotes")
sglQuotedString = Combine( _sglQuote + ZeroOrMore( CharsNotIn("\\'\n\r") | _escapedChar ) + _sglQuote ).streamline().setName("string enclosed in single quotes")
quotedString = ( dblQuotedString | sglQuotedString ).setName("quotedString using single or double quotes")

# it's easy to get these comment structures wrong - they're very common, so may as well make them available
cStyleComment = Combine( Literal("/*") +
                         ZeroOrMore( CharsNotIn("*") | ( "*" + ~Literal("/") ) ) +
                         Literal("*/") ).streamline().setName("cStyleComment enclosed in /* ... */")
restOfLine = Optional( CharsNotIn( "\n\r" ), default="" ).setName("rest of line up to \\n").leaveWhitespace()
_noncomma = "".join( [ c for c in printables if c != "," ] )
_commasepitem = Combine(OneOrMore(Word(_noncomma) + 
                                  Optional( Word(" \t") + 
                                            ~Literal(",") + ~LineEnd() ) ) ).streamline().setName("commaItem")
commaSeparatedList = delimitedList( Optional( quotedString | _commasepitem, default="") ).setName("commaSeparatedList")


if __name__ == "__main__":

    def test( teststring ):
        print teststring,"->"
        try:
            tokens = simpleSQL.parseString( teststring )
            print tokens
            tokenlist = tokens.asList()
            print tokenlist
            print "tokens = ",        tokens
            print "tokens.columns =", tokens.columns
            print "tokens.tables =",  tokens.tables
        except ParseException, err:
            print err.line
            print " "*(err.column-1) + "^"
            print err
        print

    selectToken    = CaselessLiteral( "select" )
    fromToken      = CaselessLiteral( "from" )

    ident          = Word( alphas, alphanums + "_$" )
    columnName     = Upcase( ident )
    columnNameList = Group( delimitedList( columnName ) )
    tableName      = Upcase( delimitedList( ident, ".", combine=True ) )
    tableNameList  = Group( delimitedList( tableName ) )
    simpleSQL      = selectToken + \
                     ( '*' | columnNameList ).setResultsName( "columns" ) + \
                     fromToken + \
                     tableNameList.setResultsName( "tables" )

    test( "SELECT * from XYZZY, ABC" )
    test( "select * from SYS.XYZZY" )
    test( "Select A from Sys.dual" )
    test( "Select AA,BB,CC from Sys.dual" )
    test( "Select A, B, C from Sys.dual" )
    test( "Select A, B, C from Sys.dual" )
    test( "Xelect A, B, C from Sys.dual" )
    test( "Select A, B, C frox Sys.dual" )
    test( "Select" )
    test( "Select ^^^ frox Sys.dual" )
    test( "Select A, B, C from Sys.dual, Table2   " )
