# chemicalFormulas.py
#
# Copyright (c) 2003, Paul McGuire
#

from pyparsing import Word, Optional, OneOrMore, Group, ParseException, Regex
from pyparsing import alphas

atomicWeight = {
    "O"  : 15.9994,
    "H"  : 1.00794,
    "Na" : 22.9897,
    "Cl" : 35.4527,
    "C"  : 12.0107
    }
    
def test( bnf, strg, fn=None ):
    try:
        print(strg,"->", bnf.parseString( strg ), end=' ')
    except ParseException as pe:
        print(pe)
    else:
        if fn != None:
            print(fn( bnf.parseString( strg ) ))
        else:
            print()

digits = "0123456789"

# Version 1
element = Regex("A[cglmrstu]|B[aehikr]?|C[adeflmorsu]?|D[bsy]|"
                "E[rsu]|F[emr]?|G[ade]|H[efgos]?|I[nr]?|Kr?|L[airu]|"
                "M[dgnot]|N[abdeiop]?|Os?|P[abdmortu]?|R[abefghnu]|"
                "S[bcegimnr]?|T[abcehilm]|U(u[bhopqst])?|V|W|Xe|Yb?|Z[nr]")

element = Word( alphas.upper(), alphas.lower(), max=2)
elementRef = Group( element + Optional( Word( digits ), default="1" ) )
formula = OneOrMore( elementRef )

fn = lambda elemList : sum(atomicWeight[elem]*int(qty) for elem,qty in elemList)
test( formula, "H2O", fn )
test( formula, "C6H5OH", fn )
test( formula, "NaCl", fn )
print()

# Version 2 - access parsed items by field name
elementRef = Group( element("symbol") + Optional( Word( digits ), default="1" )("qty") )
formula = OneOrMore( elementRef )

fn = lambda elemList : sum(atomicWeight[elem.symbol]*int(elem.qty) for elem in elemList)
test( formula, "H2O", fn )
test( formula, "C6H5OH", fn )
test( formula, "NaCl", fn )
print()

# Version 3 - convert integers during parsing process
integer = Word( digits ).setParseAction(lambda t:int(t[0]))
elementRef = Group( element("symbol") + Optional( integer, default=1 )("qty") )
formula = OneOrMore( elementRef )

fn = lambda elemList : sum(atomicWeight[elem.symbol]*elem.qty for elem in elemList)
test( formula, "H2O", fn )
test( formula, "C6H5OH", fn )
test( formula, "NaCl", fn )
    


