# TINY language grammar (initial BNF outline)

This file captures the evolving BNF for the TINY language parser we are building with pyparsing.
We start with a classic educational subset of TINY often used in compiler courses.

Notes
- Terminals in single quotes.
- Whitespace is insignificant except inside quoted strings; comments are in braces `{ ... }`.
- Statements are separated by semicolons `;`. Newlines are not significant.

Program
- program := stmt_seq

Statements
- stmt_seq := statement { ';' statement }
- statement := assign_stmt | if_stmt | repeat_stmt | read_stmt | write_stmt
- assign_stmt := identifier ':=' expr
- if_stmt := 'if' expr 'then' stmt_seq [ 'else' stmt_seq ] 'end'
- repeat_stmt := 'repeat' stmt_seq 'until' expr
- read_stmt := 'read' identifier
- write_stmt := 'write' expr

Expressions
- expr := simple_expr [ relop simple_expr ]
- relop := '<' | '=' | '>' | '<=' | '>=' | '<>'
- simple_expr := term { addop term }
- addop := '+' | '-'
- term := factor { mulop factor }
- mulop := '*' | '/'
- factor := '(' expr ')' | number | identifier

Lexical
- identifier := letter { letter | digit }
- number := digit { digit }
- comment := '{' ... '}'  (may span multiple characters, not nested)
- keywords := 'if' | 'then' | 'else' | 'end' | 'repeat' | 'until' | 'read' | 'write'

This BNF is a starting point; refine as the implementation details evolve.
