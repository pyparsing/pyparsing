# TINY language grammar (current parser outline)

This document reflects the current definitions in `examples/tiny/tiny_parser.py`.

Notes
- Terminals appear in single quotes.
- Whitespace is insignificant except inside quoted strings.
- Comments use C-style block comments `/* ... */` and are ignored globally.
- Simple statements are terminated with a trailing semicolon `;`. Control-flow
  statements (`if ... end`, `repeat ... until ...`) do not end with a semicolon.

Lexical tokens
- punctuation: `'(' ')' '{' '}' ',' ';' ':='`
- keywords (reserved): `if then else elseif end repeat until read write return endl int float string main`
- identifier: a letter followed by letters, digits, or `_`, but not a reserved word
- number: integer or floating point
- string: double-quoted with `\` as escape, for example: `"hello"`

Program structure
- Program := { FunctionDefinition } MainFunction
- MainFunction := Datatype 'main' '(' ')' FunctionBody
- FunctionDefinition := FunctionDeclaration FunctionBody
- FunctionDeclaration := Datatype FunctionName '(' [ Parameter { ',' Parameter } ] ')'
- FunctionBody := '{' StmtSeq '}'
- Datatype := 'int' | 'float' | 'string'

Statements
- StmtSeq := one-or-more Statement
- Statement :=
  - DeclarationStatement
  - AssignmentStatement
  - ReadStatement
  - WriteStatement
  - ReturnStatement
  - FunctionCallStatement
  - IfStatement
  - RepeatStatement

Simple statements (each ends with `;`)
- DeclarationStatement := Datatype VarDecl { ',' VarDecl } ';'
  - VarDecl := identifier [ ':=' Expr ]
- AssignmentStatement := identifier ':=' Expr ';'
- ReadStatement := 'read' identifier ';'
- WriteStatement := 'write' ( 'endl' | Expr ) ';'
- ReturnStatement := 'return' Expr ';'
- FunctionCallStatement := FunctionCall ';'

Control flow (no trailing semicolon)
- IfStatement := 'if' Condition 'then' StmtSeq { ElseIfBlock } [ 'else' StmtSeq ] 'end'
  - ElseIfBlock := 'elseif' Condition 'then' StmtSeq
- RepeatStatement := 'repeat' StmtSeq 'until' Condition

Expressions
- Expr := RelExpr
- RelExpr := Arith { RelOp Arith }
- RelOp := '<' | '>' | '=' | '<>'
- Condition := RelExpr { '&&' RelExpr | '||' RelExpr }
- Arith :=
  - Right-assoc prefix `+` on a single operand
  - Then left-assoc `*` `/`
  - Then left-assoc `+` `-`
  (This mirrors the `infix_notation` levels in the parser.)
- Term := number | string | FunctionCall | identifier
- FunctionCall := FunctionName '(' [ Expr { ',' Expr } ] ')'

Additional notes
- The special literal `endl` may be used only in `write` statements (as modeled by the parser), or a general expression can be written instead.
- Comments `/* ... */` may appear between tokens anywhere a statement or expression is allowed; they are ignored by the parser.

Examples
- Declaration and assignment
  - `int x; float y := 2.5, z; string s := "Hello";`
- If/elseif/else (no semicolons after blocks)
  - `if x < 10 then y := y + 1; write y; elseif x = 0 then write 0; else read x; end`
- Repeat/until (no semicolon after `until` line)
  - `repeat x := x - 1; write x; until x = 0`
- Functions and main
  - `int sum(int a, int b){ write a; return a + b; } int main(){ int r; r := sum(2,3); write r; return 0; }`
