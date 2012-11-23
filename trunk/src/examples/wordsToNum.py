# wordsToNum.py
# Copyright 2006, Paul McGuire
#
# Sample parser grammar to read a number given in words, and return the numeric value.
#
from pyparsing import *
from operator import mul
from functools import reduce

def makeLit(s,val):
    ret = CaselessLiteral(s).setName(s)
    return ret.setParseAction( replaceWith(val) )

unitDefinitions = [
    ("zero",       0),
    ("oh",         0),
    ("zip",        0),
    ("zilch",      0),
    ("nada",       0),
    ("bupkis",     0),
    ("one",        1),
    ("two",        2),
    ("three",      3),
    ("four",       4),
    ("five",       5),
    ("six",        6),
    ("seven",      7),
    ("eight",      8),
    ("nine",       9),
    ("ten",       10),
    ("eleven",    11),
    ("twelve",    12),
    ("thirteen",  13),
    ("fourteen",  14),
    ("fifteen",   15),
    ("sixteen",   16),
    ("seventeen", 17),
    ("eighteen",  18),
    ("nineteen",  19),
    ]
units = Or( [ makeLit(s,v) for s,v in unitDefinitions ] )

tensDefinitions = [
    ("ten",     10),
    ("twenty",  20),
    ("thirty",  30),
    ("forty",   40),
    ("fourty",  40), # for the spelling-challenged...
    ("fifty",   50),
    ("sixty",   60),
    ("seventy", 70),
    ("eighty",  80),
    ("ninety",  90),
    ]
tens = Or( [ makeLit(s,v) for s,v in tensDefinitions ] )

hundreds = makeLit("hundred", 100)

majorDefinitions = [
    ("thousand",    int(1e3)),
    ("million",     int(1e6)),
    ("billion",     int(1e9)),
    ("trillion",    int(1e12)),
    ("quadrillion", int(1e15)),
    ("quintillion", int(1e18)),
    ]
mag = Or( [ makeLit(s,v) for s,v in majorDefinitions ] )

wordprod = lambda t: reduce(mul,t)
wordsum = lambda t: sum(t)
numPart = (((( units + Optional(hundreds) ).setParseAction(wordprod) + 
               Optional(tens)).setParseAction(wordsum) 
               ^ tens )
               + Optional(units) ).setParseAction(wordsum)
numWords = OneOrMore( (numPart + Optional(mag)).setParseAction(wordprod) 
                    ).setParseAction(wordsum) + StringEnd()
numWords.ignore("-")
numWords.ignore(CaselessLiteral("and"))

def test(s,expected):
    try:
        val = numWords.parseString(s)[0]
    except ParseException as pe:
        print("Parsing failed:")
        print(s)
        print("%s^" % (' '*(pe.col-1)))
        print(pe.msg)
    else:
        print("'%s' -> %d" % (s, val), end=' ')
        if val == expected:
            print("CORRECT")
        else:
            print("***WRONG***, expected %d" % expected)

test("one hundred twenty hundred", 120)
test("one hundred and twennty", 120)
test("one hundred and twenty", 120)
test("one hundred and three", 103)
test("one hundred twenty-three", 123)
test("one hundred and twenty three", 123)
test("one hundred twenty three million", 123000000)
test("one hundred and twenty three million", 123000000)
test("one hundred twenty three million and three", 123000003)
test("fifteen hundred and sixty five", 1565)
test("seventy-seven thousand eight hundred and nineteen", 77819)
test("seven hundred seventy-seven thousand seven hundred and seventy-seven", 777777)
test("zero", 0)
test("forty two", 42)
test("fourty two", 42)