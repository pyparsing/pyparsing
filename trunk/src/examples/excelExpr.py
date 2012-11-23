# excelExpr.py
#
# Copyright 2010, Paul McGuire
# 
# A partial implementation of a parser of Excel formula expressions.
#
from pyparsing import (CaselessKeyword, Suppress, Word, alphas, 
    alphanums, nums, Optional, Group, oneOf, Forward, Regex, 
    operatorPrecedence, opAssoc, dblQuotedString, delimitedList, 
    Combine, Literal, QuotedString)

EQ,EXCL,LPAR,RPAR,COLON,COMMA = map(Suppress, '=!():,')
EXCL, DOLLAR = map(Literal,"!$")
sheetRef = Word(alphas, alphanums) | QuotedString("'",escQuote="''")
colRef = Optional(DOLLAR) + Word(alphas,max=2)
rowRef = Optional(DOLLAR) + Word(nums)
cellRef = Combine(Group(Optional(sheetRef + EXCL)("sheet") + colRef("col") + 
                    rowRef("row")))

cellRange = (Group(cellRef("start") + COLON + cellRef("end"))("range") 
                | cellRef | Word(alphas,alphanums))

expr = Forward()

COMPARISON_OP = oneOf("< = > >= <= != <>")
condExpr = expr + COMPARISON_OP + expr

ifFunc = (CaselessKeyword("if") + 
          LPAR + 
          Group(condExpr)("condition") + 
          COMMA + expr("if_true") + 
          COMMA + expr("if_false") + RPAR)

statFunc = lambda name : CaselessKeyword(name) + LPAR + delimitedList(expr) + RPAR
sumFunc = statFunc("sum")
minFunc = statFunc("min")
maxFunc = statFunc("max")
aveFunc = statFunc("ave")
funcCall = ifFunc | sumFunc | minFunc | maxFunc | aveFunc

multOp = oneOf("* /")
addOp = oneOf("+ -")
numericLiteral = Regex(r"\-?\d+(\.\d+)?")
operand = numericLiteral | funcCall | cellRange | cellRef 
arithExpr = operatorPrecedence(operand,
    [
    (multOp, 2, opAssoc.LEFT),
    (addOp, 2, opAssoc.LEFT),
    ])

textOperand = dblQuotedString | cellRef
textExpr = operatorPrecedence(textOperand,
    [
    ('&', 2, opAssoc.LEFT),
    ])
expr << (arithExpr | textExpr)


test1 = "=3*A7+5"
test2 = "=3*Sheet1!$A$7+5"
test2a ="=3*'Sheet 1'!$A$7+5" 
test2b ="=3*'O''Reilly''s sheet'!$A$7+5" 
test3 = "=if(Sum(A1:A25)>42,Min(B1:B25), " \
     "if(Sum(C1:C25)>3.14, (Min(C1:C25)+3)*18,Max(B1:B25)))"
test3a = "=sum(a1:a25,10,min(b1,c2,d3))"

import pprint
tests = [locals()[t] for t in list(locals().keys()) if t.startswith("test")]
for test in tests:
    print(test)
    pprint.pprint( (EQ + expr).parseString(test,parseAll=True).asList() )
    print() 
