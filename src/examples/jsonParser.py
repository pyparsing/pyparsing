# jsonParser.py
#
# Implementation of a simple JSON parser, returning a hierarchical
# ParseResults object support both list- and dict-style data access.
#
# Copyright 2006, by Paul McGuire
#
# Updated 8 Jan 2007 - fixed dict grouping bug, and made elements and
#   members optional in array and object collections
#
json_bnf = """
object 
    { members } 
    {} 
members 
    string : value 
    members , string : value 
array 
    [ elements ]
    [] 
elements 
    value 
    elements , value 
value 
    string
    number
    object
    array
    true
    false
    null
"""

from pyparsing import *

TRUE = Keyword("true").setParseAction( replaceWith(True) )
FALSE = Keyword("false").setParseAction( replaceWith(False) )
NULL = Keyword("null").setParseAction( replaceWith(None) )

jsonString = dblQuotedString.setParseAction( removeQuotes )
jsonNumber = Combine( Optional('-') + ( '0' | Word('123456789',nums) ) +
                    Optional( '.' + Word(nums) ) +
                    Optional( Word('eE',exact=1) + Word(nums+'+-',nums) ) )

jsonObject = Forward()
jsonValue = Forward()
jsonElements = delimitedList( jsonValue )
jsonArray = Group(Suppress('[') + Optional(jsonElements) + Suppress(']') )
jsonValue << ( jsonString | jsonNumber | Group(jsonObject)  | jsonArray | TRUE | FALSE | NULL )
memberDef = Group( jsonString + Suppress(':') + jsonValue )
jsonMembers = delimitedList( memberDef )
jsonObject << Dict( Suppress('{') + Optional(jsonMembers) + Suppress('}') )

jsonComment = cppStyleComment 
jsonObject.ignore( jsonComment )

def convertNumbers(s,l,toks):
    n = toks[0]
    try:
        return int(n)
    except ValueError, ve:
        return float(n)
        
jsonNumber.setParseAction( convertNumbers )
    
if __name__ == "__main__":
    testdata = """
    {
        "glossary": {
            "title": "example glossary",
            "GlossDiv": {
                "title": "S",
                "GlossList": 
                    {
                    "ID": "SGML",
                    "SortAs": "SGML",
                    "GlossTerm": "Standard Generalized Markup Language",
                    "TrueValue": true,
                    "FalseValue": false,
                    "Gravity": -9.8,
                    "LargestPrimeLessThan100": 97,
                    "AvogadroNumber": 6.02E23,
                    "EvenPrimesGreaterThan2": null,
                    "PrimesLessThan10" : [2,3,5,7],
                    "Acronym": "SGML",
                    "Abbrev": "ISO 8879:1986",
                    "GlossDef": "A meta-markup language, used to create markup languages such as DocBook.",
                    "GlossSeeAlso": ["GML", "XML", "markup"],
                    "EmptyDict" : {},
                    "EmptyList" : []
                    }
            }
        }
    }
    """

    import pprint
    results = jsonObject.parseString(testdata)
    pprint.pprint( results.asList() )
    print
    def testPrint(x):
        print type(x),repr(x)
    print results.glossary.GlossDiv.GlossList.keys()
    testPrint( results.glossary.title )
    testPrint( results.glossary.GlossDiv.GlossList.ID )
    testPrint( results.glossary.GlossDiv.GlossList.FalseValue )
    testPrint( results.glossary.GlossDiv.GlossList.Acronym )
    testPrint( results.glossary.GlossDiv.GlossList.EvenPrimesGreaterThan2 )
    testPrint( results.glossary.GlossDiv.GlossList.PrimesLessThan10 )


