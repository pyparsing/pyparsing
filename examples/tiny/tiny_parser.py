"""
TINY language parser (expanded grammar with types, functions, and control flow)

This module defines a pyparsing grammar for an expanded instructional subset of the
TINY language, including declarations, functions, and boolean conditions.

Usage
- Programmatic:

    from examples.tiny.tiny_parser import parse_tiny
    parse_tiny(source)

- CLI tests:

    python -m examples.tiny.tiny_parser

The grammar is defined to be independent of any evaluation/model logic. Results
are structured using names and Groups to support later processing.
"""
from __future__ import annotations

import pyparsing as pp

# Best practice for recursive grammars: enable packrat for performance
pp.ParserElement.enable_packrat()

# Shorthand
ppc = pp.common

# Punctuation
LPAREN, RPAREN, LBRACE, RBRACE, COMMA, SEMI = pp.Suppress.using_each("(){},;")
ASSIGN = pp.Suppress(":=")

# Comments (C-style /* ... */)
comment = pp.c_style_comment

# Keywords
(
    IF, THEN, ELSE, ELSEIF, END, REPEAT, UNTIL, READ, WRITE, RETURN, ENDL,
    INT, FLOAT, STRING, MAIN,
) = pp.Keyword.using_each(
    """
    if then else elseif end repeat until read write return endl
    int float string main
    """.split()
)

RESERVED = pp.MatchFirst(
    [
        IF, THEN, ELSE, ELSEIF, END, REPEAT, UNTIL, READ, WRITE, RETURN, ENDL,
        INT, FLOAT, STRING, MAIN,
    ]
).set_name("RESERVED")

# Identifiers
ident = pp.Word(pp.alphas, pp.alphanums + "_")
Identifier = pp.Combine(~RESERVED + ident).set_name("identifier")
FunctionName = Identifier

# Literals
# Use ppc.number to auto-convert to Python int/float during parsing
number = ppc.number.set_name("Number")
string_lit = pp.QuotedString('"', esc_char="\\", unquote_results=True).set_name("String")

# Forward declarations
expr = pp.Forward().set_name("expr")
term = pp.Forward().set_name("term")
statement = pp.Forward().set_name("statement")
stmt_seq = pp.Forward().set_name("stmt_seq")
condition_stmt = pp.Forward().set_name("condition_stmt")

# Function call: name '(' [Identifier (',' Identifier)*] ')'
function_call = pp.Group(
    pp.Tag("type", "func_call")
    + FunctionName("name")
    + LPAREN
    + pp.Optional(pp.DelimitedList(expr, COMMA))("args")
    + RPAREN
).set_name("function_call")

# Term: number | Identifier | func_call | '(' expr ')'
term <<= (
        number | string_lit | function_call | Identifier #| pp.Group(LPAREN + expr + RPAREN)
).set_name("term")

# Operators
mulop = pp.one_of("* /")
addop = pp.one_of("+ -")
relop = pp.one_of("< > = <> >= <=")
andop = pp.Literal("&&")
orop = pp.Literal("||")

# Arithmetic and relational expression (Equation/Expression)
# Build arithmetic first, then allow relational comparisons
arith = pp.infix_notation(
    term,
    [
        (addop, 1, pp.OpAssoc.RIGHT),
        (mulop, 2, pp.OpAssoc.LEFT),
        (addop, 2, pp.OpAssoc.LEFT),
    ],
)
rel_expr = pp.infix_notation(
    arith,
    [
        (relop, 2, pp.OpAssoc.LEFT),
    ],
)

# Condition statement with boolean operators
condition_stmt <<= pp.infix_notation(
    rel_expr,
    [
        (andop, 2, pp.OpAssoc.LEFT),
        (orop, 2, pp.OpAssoc.LEFT),
    ],
)

# Expression may be string, number, term/equation, or function call
expr <<= rel_expr

# Datatypes
Datatype = pp.MatchFirst([INT, FLOAT, STRING]).set_name("Datatype")

# Declarations: Datatype id (:= expr)? (',' id (:= expr)?)*
init_opt = pp.Optional(ASSIGN + expr("init"))
var_decl = pp.Group(Identifier("name") + init_opt)
Declaration_Statement = pp.Group(
    pp.Tag("type", "decl_stmt")
    + Datatype("datatype")
    + pp.DelimitedList(var_decl, COMMA)("decls")
    + SEMI
).set_name("Declaration_Statement")

# Assignment
Assignment_Statement = pp.Group(
    pp.Tag("type", "assign_stmt")
    + Identifier("target")
    + ASSIGN
    + expr("value")
    + SEMI
).set_name("Assignment_Statement")

# Read/Write
Read_Statement = pp.Group(
    pp.Tag("type", "read_stmt") + READ.suppress() + Identifier("var") + SEMI
).set_name("Read_Statement")
Write_Statement = pp.Group(
    pp.Tag("type", "write_stmt")
    + WRITE.suppress()
    + (ENDL.copy().set_parse_action(lambda: "endl") | expr("expr"))
    + SEMI
).set_name("Write_Statement")

# Return
Return_Statement = pp.Group(
    pp.Tag("type", "return_stmt") + RETURN.suppress() + expr("expr") + SEMI
).set_name("Return_Statement")

# If / ElseIf / Else
If_Statement = pp.Group(
    pp.Tag("type", "if_stmt")
    + IF.suppress()
    + condition_stmt("cond")
    + THEN.suppress()
    + pp.Group(stmt_seq)("then")
    + pp.ZeroOrMore(
        pp.Group(
            ELSEIF.suppress()
            + condition_stmt("cond")
            + THEN.suppress()
            + pp.Group(stmt_seq)("then"))
    )("elseif")
    + pp.Optional(ELSE.suppress() + pp.Group(stmt_seq)("else"))
    + END.suppress()
).set_name("If_Statement")

# Repeat Until
Repeat_Statement = pp.Group(
    pp.Tag("type", "repeat_stmt")
    + REPEAT.suppress()
    + stmt_seq("body")
    + UNTIL.suppress()
    + condition_stmt("cond")
).set_name("Repeat_Statement")

# Statement list and statement choices
Function_Call_Statement = (
    pp.Group(
        pp.Tag("type", "call_stmt")
        + function_call
        + SEMI
    ).set_name("Function_Call_Statement")
)

statement <<= pp.MatchFirst(
    [
        Declaration_Statement,
        Assignment_Statement,
        If_Statement,
        Repeat_Statement,
        Read_Statement,
        Write_Statement,
        Return_Statement,
        Function_Call_Statement,
    ]
)

stmt_list = pp.OneOrMore(statement)
stmt_seq <<= stmt_list("stmts")

# Parameters and functions
Parameter = pp.Group(Datatype("type") + Identifier("name"))
Param_List = pp.Optional(pp.Group(pp.DelimitedList(Parameter, COMMA)))
Function_Declaration = pp.Group(
    pp.Tag("type", "func_decl") +
    Datatype("return_type") + FunctionName("name") + LPAREN + Param_List("parameters") + RPAREN
).set_name("Function_Declaration")
Function_Body = pp.Group(
    LBRACE + stmt_seq("stmts") + RBRACE
).set_name("Function_Body")
Function_Definition = pp.Group(Function_Declaration("decl") + Function_Body("body")).set_name("Function_Definition")

Main_Function = pp.Group(
    pp.Tag("type", "main_decl") +
    Datatype("return_type") + MAIN.suppress() + LPAREN + RPAREN + Function_Body("body")
)

# Program: {Function_Statement} Main_Function
Program = pp.Group(
    pp.Group(pp.ZeroOrMore(Function_Definition))("functions") + Main_Function("main")
)("program").set_name("program")

# Ignore comments globally
Program.ignore(comment)

# Optional: generate diagram
# Program.create_diagram('tiny_parser_diagram.html')


def parse_tiny(text: str, parse_all: bool = True) -> pp.ParseResults:
    """Parse a TINY source string and return structured ParseResults.

    Args:
        text: Source code to parse.
        parse_all: If True, require full string to be consumed.
    """
    return Program.parse_string(text, parse_all=parse_all)


def _mini_tests() -> None:
    statement_tests = """\
        # Declarations with assignments
        int x; float y:=2.5, z; string s:="Hello";

        # Assignment, read, write with endl
        read x; x := 42; write endl; write x;

        # If / elseif / else with boolean conditions
        if x < 10 && x > 1 then y := y + 1; write y; elseif x = 0 then write 0; else read x; end
        
        if x < 10 then y := y + 1; write y; elseif x = 0 then write 0; else read x; end

        # Repeat until
        repeat x := x - 1; write x; until x = 0
    """
    stmt_list.run_tests(statement_tests, parse_all=True, full_dump=False)

    program_tests = [
        # Function with params and return, and main
        'int sum(int a, int b){ write a; return a + b; } int main(){ int r; r := sum(2,3); write r; return 0; }',
        'int main(){ write "Hello, World!"; return 0; }',
    ]
    Program.run_tests(program_tests, parse_all=True, full_dump=True)


if __name__ == "__main__":
    _mini_tests()
