# excelExpr.py
#
# Copyright 2010, Paul McGuire
#
# A partial implementation of a parser of Excel formula expressions.
#
import pyparsing as pp
ppc = pp.common

pp.ParserElement.enablePackrat()

EQ, LPAR, RPAR, COLON, COMMA = pp.Suppress.using_each("=():,")
EXCL, DOLLAR = pp.Literal.using_each("!$")
sheetRef = pp.Word(pp.alphas, pp.alphanums) | pp.QuotedString("'", escQuote="''")
colRef = pp.Opt(DOLLAR) + pp.Word(pp.alphas, max=2)
rowRef = pp.Opt(DOLLAR) + pp.Word(pp.nums)
cellRef = pp.Combine(
    pp.Group(pp.Opt(sheetRef + EXCL)("sheet") + colRef("col") + rowRef("row"))
)

cellRange = (
    pp.Group(cellRef("start") + COLON + cellRef("end"))("range")
    | cellRef
    | pp.Word(pp.alphas, pp.alphanums)
)

expr = pp.Forward()

COMPARISON_OP = pp.one_of("< = > >= <= != <>")
condExpr = expr + COMPARISON_OP + expr

ifFunc = (
    pp.CaselessKeyword("if")
    - LPAR
    + pp.Group(condExpr)("condition")
    + COMMA
    + pp.Group(expr)("if_true")
    + COMMA
    + pp.Group(expr)("if_false")
    + RPAR
)


def stat_function(name):
    return pp.Group(pp.CaselessKeyword(name) + pp.Group(LPAR + pp.DelimitedList(expr) + RPAR))


sumFunc = stat_function("sum")
minFunc = stat_function("min")
maxFunc = stat_function("max")
aveFunc = stat_function("ave")
funcCall = ifFunc | sumFunc | minFunc | maxFunc | aveFunc

multOp = pp.one_of("* /")
addOp = pp.one_of("+ -")
numericLiteral = ppc.number
operand = numericLiteral | funcCall | cellRange | cellRef
arithExpr = pp.infix_notation(
    operand,
    [
        (multOp, 2, pp.OpAssoc.LEFT),
        (addOp, 2, pp.OpAssoc.LEFT),
    ],
)

textOperand = pp.dblQuotedString | cellRef
textExpr = pp.infix_notation(
    textOperand,
    [
        ("&", 2, pp.OpAssoc.LEFT),
    ],
)

expr <<= arithExpr | textExpr


def main():
    success, report = (EQ + expr).run_tests(
        """\
        =3*A7+5
        =3*Sheet1!$A$7+5
        =3*'Sheet 1'!$A$7+5
        =3*'O''Reilly''s sheet'!$A$7+5
        =if(Sum(A1:A25)>42,Min(B1:B25),if(Sum(C1:C25)>3.14, (Min(C1:C25)+3)*18,Max(B1:B25)))
        =sum(a1:a25,10,min(b1,c2,d3))
        =if("T"&a2="TTime", "Ready", "Not ready")
    """
    )
    assert success


if __name__ == '__main__':
    main()