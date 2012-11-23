# parseListString.py
#
# Copyright, 2006, by Paul McGuire
#

from pyparsing import *

# first pass
lbrack = Literal("[")
rbrack = Literal("]")
integer = Word(nums).setName("integer")
real = Combine(Optional(oneOf("+ -")) + Word(nums) + "." +
               Optional(Word(nums))).setName("real")

listItem = real | integer | quotedString

listStr = lbrack + delimitedList(listItem) + rbrack

test = "['a', 100, 3.14]"

print(listStr.parseString(test))


# second pass, cleanup and add converters
lbrack = Literal("[").suppress()
rbrack = Literal("]").suppress()
cvtInt = lambda s,l,toks: int(toks[0])
integer = Word(nums).setName("integer").setParseAction( cvtInt )
cvtReal = lambda s,l,toks: float(toks[0])
real = Combine(Optional(oneOf("+ -")) + Word(nums) + "." +
               Optional(Word(nums))).setName("real").setParseAction( cvtReal )
listItem = real | integer | quotedString.setParseAction( removeQuotes )

listStr = lbrack + delimitedList(listItem) + rbrack

test = "['a', 100, 3.14]"

print(listStr.parseString(test))

# third pass, add nested list support, and tuples, too!
cvtInt = lambda s,l,toks: int(toks[0])
cvtReal = lambda s,l,toks: float(toks[0])

lbrack = Literal("[").suppress()
rbrack = Literal("]").suppress()
integer = Word(nums).setName("integer").setParseAction( cvtInt )
real = Combine(Optional(oneOf("+ -")) + Word(nums) + "." +
               Optional(Word(nums))).setName("real").setParseAction( cvtReal )
tupleStr = Forward()
listStr = Forward()
listItem = real | integer | quotedString.setParseAction(removeQuotes) | Group(listStr) | tupleStr
tupleStr << ( Suppress("(") + delimitedList(listItem) + Optional(Suppress(",")) + Suppress(")") )
tupleStr.setParseAction( lambda t:tuple(t.asList()) )
listStr << lbrack + delimitedList(listItem) + Optional(Suppress(",")) + rbrack

test = "['a', 100, ('A', [101,102]), 3.14, [ +2.718, 'xyzzy', -1.414] ]"
print(listStr.parseString(test))

# fourth pass, just parsing tuples of numbers
#~ from pyparsing import *

#~ integer = (Word(nums)|Word('-+',nums)).setName("integer")
#~ real = Combine(integer + "." + Optional(Word(nums))).setName("real")
#~ tupleStr = Forward().setName("tuple")
#~ tupleItem = real | integer | tupleStr
#~ tupleStr << ( Suppress("(") + delimitedList(tupleItem) + 
               #~ Optional(Suppress(",")) + Suppress(")") )

#~ # add parse actions to do conversion during parsing
#~ integer.setParseAction( lambda toks: int(toks[0]) )
#~ real.setParseAction( lambda toks: float(toks[0]) )
#~ tupleStr.setParseAction( lambda toks: tuple(toks) )

#~ s = '((1,2), (3,4), (-5,9.2),)'
#~ print tupleStr.parseString(s)[0]


cvtInt = lambda s,l,toks: int(toks[0])
cvtReal = lambda s,l,toks: float(toks[0])
cvtDict = lambda s,l,toks: dict(toks[0])

lbrack = Literal("[").suppress()
rbrack = Literal("]").suppress()
lbrace = Literal("{").suppress()
rbrace = Literal("}").suppress()
colon = Literal(":").suppress()
integer = Word(nums).setName("integer").setParseAction( cvtInt )
real = Combine(Optional(oneOf("+ -")) + Word(nums) + "." +
               Optional(Word(nums))).setName("real").setParseAction( cvtReal )
tupleStr = Forward()
listStr = Forward()
dictStr = Forward()
listItem = real | integer | quotedString.setParseAction(removeQuotes) | Group(listStr) | tupleStr | dictStr
tupleStr << ( Suppress("(") + delimitedList(listItem) + Optional(Suppress(",")) + Suppress(")") )
tupleStr.setParseAction( lambda t:tuple(t.asList()) )
listStr << lbrack + delimitedList(listItem) + Optional(Suppress(",")) + rbrack
dictStr << rbrace + delimitedList( Group( listItem + colon + listItem ) ) + rbrace
test = "['a', 100, ('A', [101,102]), 3.14, [ +2.718, 'xyzzy', -1.414] ]"
test = '[{0: [2], 1: []}, {0: [], 1: [], 2: []}, {0: [1, 2]}]'
print(listStr.parseString(test))
