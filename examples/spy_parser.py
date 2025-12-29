#
# spy_parser.py
#
# SPy (Simplified Python) - SPY is a strongly typed, easy to use language inspired by
# features from Python and functional languages like OCaml and SML.
#
# Language definition submitted by Sanil Shah as part of the coursework for
# COMS W4115 - Programming Languages and Translators, at Columbia University,
# New York, NY. Lecturer: Prof. Stephen A. Edwards.
#
# See SPy language definition: https://www.cs.columbia.edu/~sedwards/classes/2016/4115-summer-cvn/lrms/SPY.pdf
#
import sys
import pyparsing as pp

sys.setrecursionlimit(3000)
# pp.ParserElement.enable_packrat()
pp.ParserElement.enable_left_recursion()
pp.ParserElement.set_default_whitespace_chars(" \t")
NL = pp.LineEnd()
TERM = NL | pp.StringEnd()

(
    DEF,
    LAMBDA,
    END,
    PRINT,
    IF,
    ELIF,
    ELSE,
    HD,
    TL,
    KEYS,
    AND,
    OR,
    NOT,
    TRUE,
    FALSE,
    KEYS,
) = pp.Keyword.using_each(
    "def,lambda,end,print,if,elif,else,hd,tl,keys,and,or,not,true,false,keys".split(",")
)

# general punctuation - can be suppressed, used just as delimiters
LPAR, RPAR, LBRACE, RBRACE, LSQUARE, RSQUARE, COMMA, DOT, COLON = (
    pp.Suppress.using_each("(){}[],.:")
)

# operators - can not be suppressed, needed to distinguish among operations at same precedence level
ADD, SUB, DIV, MUL, MOD, CONCAT = pp.Literal.using_each("+-/*%^")
LT, GT, LE, GE, EQ, NE = pp.Literal.using_each("< > <= >= == !=".split())
MINUS = SUB
LIST_CONS, LIST_APP = pp.Literal.using_each(":: @".split())
DICT_SET = pp.Literal("<-")

integer = pp.Regex(r"0|[1-9][0-9]*").set_name("integer")
float_ = pp.Regex(r"(0|[1-9]\d*)\.\d*").set_name("float")
string = pp.Regex(r'"([^\\"]|\\[\\nrt])*"').set_name("string")
identifier = pp.Regex(r"[a-z][a-zA-Z0-9_]*").set_name("identifier")
bool_literal = TRUE | FALSE

list_literal = pp.Forward()
dict_literal = pp.Forward()

string_expr = pp.infix_notation(
    string,
    [
        (CONCAT, 2, pp.OpAssoc.LEFT),
    ],
).set_name("string_expr")

arith_expr = pp.infix_notation(
    (float_ | integer).set_name("arith_operand"),
    [
        (MINUS().set_name("unary_minus"), 1, pp.OpAssoc.RIGHT),
        ((MUL | DIV | MOD).set_name("mul_op"), 2, pp.OpAssoc.LEFT),
        ((ADD | SUB).set_name("add_op"), 2, pp.OpAssoc.LEFT),
    ],
).set_name("arith_expr")

expr = pp.Forward().set_name("expr")

conditional_expr = pp.infix_notation(
    expr,
    [((LE | GE | LT | GT | EQ | NE).set_name("comparison_op"), 2, pp.OpAssoc.LEFT)],
).set_name("conditional_expr")

bool_expr = pp.infix_notation(
    (bool_literal | conditional_expr).set_name("bool_operand"),
    [
        (NOT, 1, pp.OpAssoc.RIGHT),
        (AND, 2, pp.OpAssoc.LEFT),
        (OR, 2, pp.OpAssoc.LEFT),
    ],
).set_name("bool_expr")

expr <<= string_expr | bool_expr | arith_expr

list_literal <<= LSQUARE + pp.DelimitedList(expr)[0, 1] + RSQUARE
dict_literal <<= LBRACE + pp.DelimitedList(expr)[0, 1] + RBRACE

statement = pp.Forward().set_name("statement")
block = (statement + NL)[1, ...].set_name("block")

arg_list = pp.DelimitedList(identifier)[0, 1]
lambda_def = LAMBDA + LPAR + arg_list("args") + RPAR + COLON + expr

function_def = pp.Group(
    DEF
    + identifier("name")
    + LPAR
    + arg_list("args")
    + RPAR
    + COLON
    + NL
    + block("body")
    + END
)

lhs = identifier
assignment_stmt = lhs("lhs") + "=" + expr("rhs")

if_stmt = pp.Group(
    IF
    + conditional_expr("condition")
    + COLON
    + NL
    + block("if_block")
    + NL
    + pp.Group(ELIF + conditional_expr("condition") + COLON + NL + block + NL)[0, ...](
        "elif_blocks"
    )
    + ELSE
    + COLON
    + NL
    + block("else_block")
)

dict_set_stmt = pp.Group(
    identifier("dest") + LSQUARE + expr("key") + RSQUARE + DICT_SET + expr("rhs")
)

statement <<= pp.Group(
    (if_stmt | function_def | assignment_stmt | dict_set_stmt) + TERM
)


spy_program = statement[1, ...].set_name("program")
pp.autoname_elements()

if __name__ == "__main__":
    import contextlib

    with contextlib.suppress(Exception):
        spy_program.create_diagram("spy_grammar.html")

    statement.run_tests(
        """\
        a = 100
        b = 0.100
        c = true and false
        d["blah"] <- 1000
    """
    )
