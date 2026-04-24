"""
ZEF language parser

This module defines a pyparsing grammar for the ZEF language,
including variables, functions, classes, and packages.

Usage:
    from examples.zef.zef_parser import parse_zef
    parse_zef(source)

Ref: https://zef-lang.dev/implementation
"""

from __future__ import annotations
import pyparsing as pp

# Best practice for recursive grammars: enable packrat for performance
pp.ParserElement.enable_packrat()

# Shorthand
ppc = pp.common

# Punctuation
LPAREN, RPAREN, LBRACE, RBRACE, LBRACK, RBRACK, COMMA, DOT, SEMI, COLON = pp.Suppress.using_each("(){}[],.;:")
EQ, PLUS_EQ, MINUS_EQ = pp.Literal.using_each("= += -=".split())

# Comments (started with #)
comment = pp.python_style_comment
pp.ParserElement.set_default_whitespace_chars(" \t\n\r")

# Keywords
(
    MY, FN, CLASS, PACKAGE, IF, ELSE, WHILE, READABLE, ACCESSIBLE, STATIC, SUPER
) = pp.Keyword.using_each(
    "my fn class package if else while readable accessible static super".split()
)

RESERVED = pp.MatchFirst(
    [MY, FN, CLASS, PACKAGE, IF, ELSE, WHILE, READABLE, ACCESSIBLE, STATIC, SUPER]
).set_name("RESERVED")

# Identifiers
ident = pp.Word(pp.alphas + "_", pp.alphanums + "_")
Identifier = pp.Combine(~RESERVED + ident).set_name("identifier")

# Literals
integer = ppc.signed_integer.set_name("integer")
real = ppc.real.set_name("float")
string_lit = pp.QuotedString('"', esc_char="\\", unquote_results=True).set_name("string")
literal = real | integer | string_lit

# Forward declarations
expr = pp.Forward().set_name("expression")
statement = pp.Forward().set_name("statement")
block = pp.Forward().set_name("block")

# Array Literal: '[' [expression (',' expression)*] ']'
array_literal = pp.Group(
    pp.Tag("type", "array_lit")
    + LBRACK + pp.Optional(pp.DelimitedList(expr))("elements") + RBRACK
).set_name("array_literal")

# Function Parameters
parameters = pp.Group(LPAREN + pp.Optional(pp.DelimitedList(Identifier)) + RPAREN).set_name("parameters")

# Function Definition
# "fn" [identifier] [parameters] (block | expr)
function_definition = pp.Group(
    pp.Tag("type", "fn_def")
    + FN 
    + ( (Identifier("name") + pp.Optional(parameters("params"))) | parameters("params") | pp.Empty() )
    + (block | expr)("body")
).set_name("function_definition")

# Anonymous function / Lambda
# fn [parameters] (block | expr)
anonymous_function = pp.Group(
    pp.Tag("type", "lambda")
    + FN + pp.Optional(parameters)("params") + (block | expr)("body")
).set_name("anonymous_function")

# If expression (for dynamic inheritance or ternary-like use)
# if (expression) expression else expression
if_expression = pp.Group(
    pp.Tag("type", "if_expr")
    + IF + LPAREN + expr("condition") + RPAREN + expr("then_expr") + ELSE + expr("else_expr")
).set_name("if_expression")

# Primary
# literal | function_call | identifier | array_literal | anonymous_function | if_expression
primary = pp.Forward().set_name("primary")

# Function Call: identifier '(' [args] ')'
function_call = pp.Group(
    pp.Tag("type", "func_call")
    + Identifier("name")
    + LPAREN
    + pp.Optional(pp.DelimitedList(expr))("args")
    + RPAREN
).set_name("function_call")

# Member Access: primary ('.' identifier | '(' args ')' | '[' index ']')*
# We'll define a helper for the trailing parts.
member_access = pp.Group(DOT + Identifier).set_name("member_access")
method_call = pp.Group(LPAREN + pp.Optional(pp.DelimitedList(expr))("args") + RPAREN).set_name("method_call")
index_access = pp.Group(LBRACK + expr + RBRACK).set_name("index_access")

primary << (
    literal
    | function_call
    | Identifier
    | array_literal
    | anonymous_function
    | if_expression
    | SUPER
)

# Postfix operators for member access and calls
primary_postfix = pp.Forward().set_name("primary_postfix")
primary_postfix << primary + pp.ZeroOrMore(member_access | method_call | index_access)

# Expressions using infix_notation
# We'll put assignment at a higher level than infix_notation
arith_expr = pp.infix_notation(
    primary_postfix,
    [
        (pp.one_of("! -"), 1, pp.opAssoc.RIGHT),
        (pp.one_of("* / %"), 2, pp.opAssoc.LEFT),
        (pp.one_of("+ -"), 2, pp.opAssoc.LEFT),
        (pp.one_of("< > <= >="), 2, pp.opAssoc.LEFT),
        (pp.one_of("== !="), 2, pp.opAssoc.LEFT),
        (pp.Literal("&&"), 2, pp.opAssoc.LEFT),
        (pp.Literal("||"), 2, pp.opAssoc.LEFT),
    ]
)

# Assignment: target (= | += | -=) expression
# Since primary_postfix can be quite complex, we use it as the target.
# To avoid ambiguity with expression_statement, assignment should be checked first or be part of expr.
assignment_expr = pp.Group(
    pp.Tag("type", "assignment")
    + primary_postfix("target")
    + (EQ | PLUS_EQ | MINUS_EQ)("op")
    + expr("value")
)

expr << (assignment_expr | arith_expr)

# Statements
# variable_declaration = ["static"] "my" identifier {"," identifier} ["=" expression]
variable_declaration = pp.Group(
    pp.Tag("type", "var_decl")
    + pp.Optional(STATIC)("static")
    + MY
    + pp.DelimitedList(Identifier)("names")
    + pp.Optional(EQ + expr("value"))
).set_name("variable_declaration")

# Assignment
# primary_postfix ( "=" | "+=" | "-=" ) expression
# (Removed assignment statement since it is now part of expression_statement)

# Expression statement
expression_statement = pp.Group(
    pp.Tag("type", "expr_stmt")
    + expr
).set_name("expression_statement")

# Block
block << pp.Group(
    LBRACE + pp.ZeroOrMore(statement + pp.Optional(SEMI)) + RBRACE
).set_name("block")

# If statement
# if (expression) (block | statement) {else if (expression) (block | statement)} [else (block | statement)]
if_statement = pp.Group(
    pp.Tag("type", "if_stmt")
    + IF + LPAREN + expr("condition") + RPAREN + (block | statement)("then_block")
    + pp.ZeroOrMore(pp.Group(ELSE + IF + LPAREN + expr("condition") + RPAREN + (block | statement)("then_block")))("else_ifs")
    + pp.Optional(pp.Group(ELSE + (block | statement))("else_block"))
).set_name("if_statement")

# While loop
# while (expression) (block | statement)
while_loop = pp.Group(
    pp.Tag("type", "while_loop")
    + WHILE + LPAREN + expr("condition") + RPAREN + (block | statement)("body")
).set_name("while_loop")

# Function Definition
# (Already defined above for anonymous functions use)
accessor_declaration = pp.Group(
    pp.Tag("type", "accessor")
    + (READABLE | ACCESSIBLE)("access_type") + Identifier("name")
).set_name("accessor_declaration")

# Class Member
class_member = variable_declaration | accessor_declaration | function_definition

# Class Definition
# "class" identifier [":" expression] "{" {class_member} "}"
class_definition = pp.Group(
    pp.Tag("type", "class_def")
    + CLASS + Identifier("name") + pp.Optional(COLON + expr("base")) + LBRACE + pp.ZeroOrMore(class_member)("members") + RBRACE
).set_name("class_definition")

# Package Definition
# "package" identifier "{" {statement} "}"
package_definition = pp.Group(
    pp.Tag("type", "package_def")
    + PACKAGE + Identifier("name") + LBRACE + pp.ZeroOrMore(statement) + RBRACE
).set_name("package_definition")

statement << (
    variable_declaration
    | function_definition
    | class_definition
    | package_definition
    | if_statement
    | while_loop
    | expression_statement
).set_name("statement")

program = pp.OneOrMore(statement).ignore(comment).set_name("program")

def parse_zef(text: str):
    return program.parse_string(text, parse_all=True)

Program = program # Alias for diagram generation if needed
Program.create_diagram("examples/zef/docs/zef_parser_diagram.html")

def _mini_tests():
    # Test with some examples
    test_cases = [
        """
        my x = 42
        fn greet(name) {
            println("Hello, " + name)
        }
        class Point {
            my x, y
            fn (inX, inY) {
                x = inX
                y = inY
            }
        }
        """,
        """
        # Inheritance
        class Circle : Shape {
            my radius
            fn (r) radius = r
            fn area 3.14159 * radius * radius
        }
        """,
        """
        # Accessors
        class Person {
            readable name
            accessible age
            static my count = 0
        }

        # Packages
        package math {
            fn add(a, b) a + b
        }

        # Control flow
        if (x > 50) { println("big") } else { println("small") }

        # Dynamic inheritance
        class MyClass : if (x == 42) Base1 else Base2 {
            fn () super()
        }
        """,
        """
        # Closures and nested classes
        fn makeCounter {
            my count = 0
            class Counter {
                fn increment { count += 1; count }
            }
            Counter()
        }
        """,
    ]

    success, _ = Program.run_tests(test_cases, comment=None, parse_all=True)

    assert success, "One or more tests failed"
    print("\nAll tests passed!")

if __name__ == "__main__":
    _mini_tests()
