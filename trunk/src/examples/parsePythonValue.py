# parsePythonValue.py
#
# Copyright, 2006, by Paul McGuire
#

from pyparsing import *

cvtBool = lambda t:t[0]=='True'
cvtInt = lambda toks: int(toks[0])
cvtReal = lambda toks: float(toks[0])
cvtTuple = lambda toks : tuple(toks.asList())
cvtDict = lambda toks: dict(toks.asList())

# define punctuation as suppressed literals
lparen,rparen,lbrack,rbrack,lbrace,rbrace,colon = \
    map(Suppress,"()[]{}:")

integer = Regex(r"[+-]?\d+")\
    .setName("integer")\
    .setParseAction( cvtInt )
real = Regex(r"[+-]?\d+\.\d*([Ee][+-]?\d+)?")\
    .setName("real")\
    .setParseAction( cvtReal )
tupleStr = Forward()
listStr = Forward()
dictStr = Forward()

unicodeString.setParseAction(lambda t:t[0][2:-1].decode('unicode-escape'))
quotedString.setParseAction(lambda t:t[0][1:-1].decode('string-escape'))
boolLiteral = oneOf("True False").setParseAction(cvtBool)
noneLiteral = Literal("None").setParseAction(replaceWith(None))

listItem = real|integer|quotedString|unicodeString|boolLiteral|noneLiteral| \
            Group(listStr) | tupleStr | dictStr

tupleStr << ( Suppress("(") + Optional(delimitedList(listItem)) + 
            Optional(Suppress(",")) + Suppress(")") )
tupleStr.setParseAction( cvtTuple )

listStr << (lbrack + Optional(delimitedList(listItem) + 
            Optional(Suppress(","))) + rbrack)

dictEntry = Group( listItem + colon + listItem )
dictStr << (lbrace + Optional(delimitedList(dictEntry) + \
    Optional(Suppress(","))) + rbrace)
dictStr.setParseAction( cvtDict )

tests = """['a', 100, ('A', [101,102]), 3.14, [ +2.718, 'xyzzy', -1.414] ]
           [{0: [2], 1: []}, {0: [], 1: [], 2: []}, {0: [1, 2]}]
           { 'A':1, 'B':2, 'C': {'a': 1.2, 'b': 3.4} }
           3.14159
           42
           6.02E23
           6.02e+023
           1.0e-7
           'a quoted string'""".split("\n")

for test in tests:
    print("Test:", test.strip())
    result = listItem.parseString(test)[0]
    print("Result:", result)
    try:
        for dd in result:
            if isinstance(dd,dict): print(list(dd.items()))
    except TypeError as te:
        pass
    print()
