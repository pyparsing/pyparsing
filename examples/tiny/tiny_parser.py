"""
TINY language parser (initial scaffold)

This module defines a pyparsing grammar for a classic instructional subset of the
TINY language. It follows pyparsing best practices (see `python -m pyparsing.ai.show_best_practices`).

Usage
- Programmatic: from tiny_parser import parse_tiny; parse_tiny(source)
- CLI tests: python -m examples.tiny.tiny_parser

The grammar is defined to be independent of any evaluation/model logic. Results
are structured using names and Groups to support later processing.
"""
from __future__ import annotations

import pyparsing as pp

# Best practice for recursive grammars: enable packrat for performance
pp.ParserElement.enable_packrat()



# For TINY, whitespace is not line-significant; keep default whitespace
# Define comment syntax: { ... }
LBRACE, RBRACE, LPAREN, RPAREN, SEMI = pp.Suppress.using_each("{}();")
ASSIGN = pp.Suppress(":=")

comment = pp.nested_expr(opener="{", closer="}")
comment.set_name("comment")

# We'll ignore comments everywhere

# Keywords and identifiers
ppc = pp.common

IF, THEN, ELSE, END, REPEAT, UNTIL, READ, WRITE = pp.Keyword.using_each(
    ["if", "then", "else", "end", "repeat", "until", "read", "write"]
)

ident_start = pp.alphas + "_"
ident_body = pp.alphanums + "_"
ident_word = pp.Word(ident_start, ident_body)("id").set_name("identifier")

# Prevent keywords from being matched as identifiers, and wrap as named Group
identifier = pp.Group(~pp.MatchFirst([IF, THEN, ELSE, END, REPEAT, UNTIL, READ, WRITE]) + ident_word)("Identifier")

number = ppc.integer("int").set_name("Integer")

# Forward declarations for recursive parts
expr = pp.Forward().set_name("expr")
statement = pp.Forward().set_name("statement")
stmt_seq = pp.Forward().set_name("stmt_seq")

# Operators and expressions (using infix_notation)
multop = pp.one_of("* /").set_name("mulop")
addop = pp.one_of("+ -").set_name("addop")
relop = pp.one_of("< <= = >= > <>").set_name("relop")

expr <<= pp.infix_notation(
    (number | identifier),
    [
        (addop, 1, pp.OpAssoc.RIGHT),  # unary +/-
        (multop, 2, pp.OpAssoc.LEFT),  # * /
        (addop, 2, pp.OpAssoc.LEFT),   # + -
        (relop, 2, pp.OpAssoc.LEFT),   # relational operators
    ],
).set_name("expr")

# Statements
assign_stmt = (
    pp.Group(
        pp.Tag("type", "assign_stmt")
        + identifier("target")
        + ASSIGN
        + expr("value")
    )
    .set_name("assign_stmt")
)

# Explicit Forwards for blocks used in control-flow statements
then_block = pp.Forward().set_name("then_block")
else_block = pp.Forward().set_name("else_block")
body_block = pp.Forward().set_name("body_block")

if_stmt = (
    pp.Group(
        pp.Tag("type", "if_stmt")
        + pp.Suppress(IF)
        + expr("cond")
        + pp.Suppress(THEN)
        + then_block("then")
        + pp.Optional(pp.Suppress(ELSE) + else_block("else"))
        + pp.Suppress(END)
    )
    .set_name("if_stmt")
)
repeat_stmt = (
    pp.Group(
        pp.Tag("type", "repeat_stmt")
        + pp.Suppress(REPEAT)
        + body_block("body")
        + pp.Suppress(UNTIL)
        + expr("cond")
    )
    .set_name("repeat_stmt")
)

read_stmt = (
    pp.Group(pp.Tag("type", "read_stmt") + pp.Suppress(READ) + identifier("var"))
    .set_name("read_stmt")
)
write_stmt = (
    pp.Group(pp.Tag("type", "write_stmt") + pp.Suppress(WRITE) + expr("expr"))
    .set_name("write_stmt")
)

# Now that we used placeholders inside if/repeat, define stmt and stmt_seq
statement <<= pp.MatchFirst([assign_stmt, if_stmt, repeat_stmt, read_stmt, write_stmt])

stmt_list = pp.DelimitedList(statement, delim=SEMI, allow_trailing_delim=True)
stmt_seq_def = pp.Group(stmt_list)("stmts").set_name("stmt_seq")

# Assign the blocks
then_block <<= stmt_seq_def
else_block <<= stmt_seq_def
body_block <<= stmt_seq_def

stmt_seq <<= stmt_seq_def

# Top-level program
# Wrap stmt_list in an inner Group named 'stmts', then wrap with outer Group named 'program'
program = pp.Group(pp.Group(stmt_list)("stmts"))("program")

# Ignore comments at the program level
program.ignore(comment)

# Create railroad diagram for the TINY grammar
program.create_diagram('tiny_parser_diagram.html')


def parse_tiny(text: str, parse_all: bool = True) -> pp.ParseResults:
    """Parse a TINY source string and return structured ParseResults.

    Args:
        text: Source code to parse.
        parse_all: If True, require full string to be consumed.
    """
    return program.parse_string(text, parse_all=parse_all)


def _mini_tests() -> None:
    # Pass a list of test strings to run_tests so that multi-line cases (like
    # the repeat-until block) are treated as a single test case.
    tests = [
        # Assignment, read, write
        "read x; y := 42; write y",
        # if/else
        "if x < 10 then y := y + 1; write y else read x; write x end",
        # repeat until (multi-line test case)
        r"""
repeat {loop}
    x := x - 1; write x
until x = 0
""",
    ]
    program.run_tests(tests, parse_all=True)


if __name__ == "__main__":
    _mini_tests()
