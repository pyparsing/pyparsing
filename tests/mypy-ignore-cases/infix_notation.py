import pyparsing as pp

# infix_notation should be annotated to return a ParserElement
operand = pp.pyparsing_common.integer
arith_expr: pp.ParserElement = pp.infix_notation(
    operand,
    [
        ("-", 1, pp.OpAssoc.RIGHT),
        (pp.one_of("* /"), 2, pp.OpAssoc.LEFT),
        (pp.one_of("+ -"), 2, pp.OpAssoc.LEFT),
    ],
)
# confirm that it isn't returning Any because it cannot be assigned to an int
x: int = pp.infix_notation(  # type: ignore[assignment]
    operand, [("+", 2, pp.OpAssoc.LEFT)]
)

# the legacy synonym should carry the same annotations
y: int = pp.infixNotation(  # type: ignore[assignment]
    operand, [("+", 2, pp.OpAssoc.LEFT)]
)

# op_list entries are type-checked against InfixNotationOperatorSpec
pp.infix_notation(operand, [(1, 2, 3)])  # type: ignore[list-item]
