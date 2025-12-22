"""
TINY language parser (expanded grammar with types, functions, and control flow)

This module defines a pyparsing grammar for the instructional TINY language,
including declarations, functions, and boolean conditions.

Usage
- Programmatic:

    from examples.tiny.tiny_parser import parse_tiny
    parse_tiny(source)

- CLI tests:

    python -m examples.tiny.tiny_parser

The grammar is defined to be independent of any evaluation/model logic. Results
are structured using names and Groups to support later processing.

Grammar definitions are based on the Tiny Language Reference:
https://github.com/a7medayman6/Tiny-Compiler/blob/master/Language-Description.md
"""

from __future__ import annotations

# disable black reformatting
# fmt: off

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
string_lit = pp.QuotedString('"', esc_char="\\", unquote_results=True).set_name(
    "String"
)

# Forward declarations
expr = pp.Forward().set_name("expr")
statement = pp.Forward().set_name("statement")
stmt_seq = pp.Forward().set_name("stmt_seq")
bool_expr = pp.Forward().set_name("bool_expr")

# Function call: name '(' [Identifier (',' Identifier)*] ')'
function_call = pp.Group(
    pp.Tag("type", "func_call")
    + FunctionName("name")
    + LPAREN
    + (
        # fast evaluation of empty arg list, since it is common, and the recursive expr
        # parser can be expensive
        RPAREN
        | pp.DelimitedList(expr)("args") + RPAREN
    )
).set_name("function_call")

# Term: number | Identifier | func_call | '(' expr ')'
term = (
    number
    | string_lit
    | function_call
    | Identifier
    # infix_notation will implement this internally
    # | pp.Group(LPAREN + expr + RPAREN)
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
bool_expr <<= pp.infix_notation(
    rel_expr,
    [
        (andop, 2, pp.OpAssoc.LEFT),
        (orop, 2, pp.OpAssoc.LEFT),
    ],
)

# Expression may be string, number, term/equation, or function call
expr <<= bool_expr


# Datatypes
Datatype = (INT | FLOAT | STRING).set_name("Datatype")

# Declarations: Datatype id (:= expr)? (',' id (:= expr)?)*
var_init = (ASSIGN + expr("init")).set_name("var_initialization")
var_decl = pp.Group(Identifier("name") + pp.Optional(var_init)).set_name("var_decl")
Declaration_Statement = pp.Group(
    pp.Tag("type", "decl_stmt")
    + Datatype("datatype")
    - pp.DelimitedList(var_decl, COMMA)("decls")
    + SEMI
).set_name("Declaration_Statement")

# Assignment
Assignment_Statement = pp.Group(
    pp.Tag("type", "assign_stmt")
    + Identifier("target")
    + ASSIGN
    - expr("value")
    + SEMI
).set_name("Assignment_Statement")

# Read/Write
Read_Statement = pp.Group(
    pp.Tag("type", "read_stmt") + READ - Identifier("var") + SEMI
).set_name("Read_Statement")
Write_Statement = pp.Group(
    pp.Tag("type", "write_stmt")
    + WRITE
    - (ENDL.copy().set_parse_action(lambda: "endl") | expr("expr"))
    + SEMI
).set_name("Write_Statement")

# Return
Return_Statement = pp.Group(
    pp.Tag("type", "return_stmt") + RETURN - expr("expr") - SEMI
).set_name("Return_Statement")

# If / ElseIf / Else
If_Statement = pp.Group(
    pp.Tag("type", "if_stmt")
    + IF
    + bool_expr("cond")
    + THEN
    - pp.Group(stmt_seq)("then")
    + pp.ZeroOrMore(
        pp.Group(
            ELSEIF
            - bool_expr("cond")
            + THEN
            + pp.Group(stmt_seq)("then")
        )
    )("elseif")
    + pp.Optional(ELSE - pp.Group(stmt_seq)("else"))
    + END
).set_name("If_Statement")

# Repeat Until
Repeat_Statement = pp.Group(
    pp.Tag("type", "repeat_stmt")
    + REPEAT
    - pp.Group(stmt_seq)("body")
    + UNTIL
    + bool_expr("cond")
).set_name("Repeat_Statement")

# Statement list and statement choices
Function_Call_Statement = (
    pp.Group(
        pp.Tag("type", "call_stmt")
        + function_call
        + SEMI
    ).set_name("Function_Call_Statement")
)

statement <<= (
    Declaration_Statement
    | Assignment_Statement
    | If_Statement
    | Repeat_Statement
    | Read_Statement
    | Write_Statement
    | Return_Statement
    | Function_Call_Statement
)

stmt_seq <<= pp.OneOrMore(statement)

# Parameters and functions
Parameter = pp.Group(Datatype("type") + Identifier("name"))
Param_List = pp.Group(pp.DelimitedList(Parameter, COMMA))
Function_Declaration = pp.Group(
    Datatype("return_type")
    + FunctionName("name")
    + LPAREN
    - pp.Optional(Param_List, default=[])("parameters")
    + RPAREN
).set_name("Function_Declaration")
Function_Body = pp.Group(LBRACE + pp.Group(stmt_seq)("stmts") + RBRACE).set_name(
    "Function_Body"
)
Function_Definition = pp.Group(
    pp.Tag("type", "func_decl")
    + Function_Declaration("decl")
    - Function_Body("body")
).set_name("Function_Definition")

Main_Function = pp.Group(
    pp.Tag("type", "main_decl")
    + Datatype("return_type")
    + MAIN
    + LPAREN
    + RPAREN
    - Function_Body("body")
).set_name("Main_Function")

# Program: {Function_Statement} Main_Function
Program = pp.Group(
    pp.Group(pp.ZeroOrMore(Function_Definition))("functions") + Main_Function("main")
)("program").set_name("Program")

# Ignore comments
Program.ignore(comment)


def parse_tiny(text: str) -> pp.ParseResults:
    """Parse a TINY source string and return structured ParseResults.

    Args:
        text: Source code to parse.
    """
    try:
        return Program.parse_string(text, parse_all=True)
    except pp.ParseException as err:
        print(err.explain())
        raise


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
        
        write x > 2 && x < 10;
    """
    stmt_seq.run_tests(statement_tests, parse_all=True, full_dump=False)

    program_tests = [
        # Function with params and return, and main
        "int sum(int a, int b){ write a; return a + b; } int main(){ int r; r := sum(2,3); write r; return 0; }",
        'int main(){ write "Hello, World!"; return 0; }',
    ]
    Program.run_tests(program_tests, parse_all=True, full_dump=True)


if __name__ == "__main__":

    # Optional: generate diagram
    # Program.create_diagram("tiny_parser_diagram.html", show_results_names=True)

    _mini_tests()
