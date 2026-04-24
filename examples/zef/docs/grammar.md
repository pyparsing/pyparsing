# ZEF Language Grammar

## EBNF Definition

```ebnf
program = { statement } ;

statement = variable_declaration
          | function_definition
          | class_definition
          | package_definition
          | if_statement
          | while_loop
          | expression_statement ;

variable_declaration = [ "static" ] "my" identifier_list [ "=" expression ] ;
identifier_list = identifier { "," identifier } ;

function_definition = "fn" [ identifier ] [ parameters ] ( block | expression ) ;
parameters = "(" [ identifier { "," identifier } ] ")" ;

class_definition = "class" identifier [ ":" expression ] "{" { class_member } "}" ;
class_member = variable_declaration
             | accessor_declaration
             | function_definition ;

accessor_declaration = ( "readable" | "accessible" ) identifier ;

package_definition = "package" identifier "{" { statement } "}" ;

if_statement = "if" "(" expression ")" ( block | statement ) 
               { "else" "if" "(" expression ")" ( block | statement ) }
               [ "else" ( block | statement ) ] ;

while_loop = "while" "(" expression ")" ( block | statement ) ;

block = "{" { statement } "}" ;

expression_statement = expression ;

expression = assignment ;

assignment = [ primary "." ] identifier ( "=" | "+=" | "-=" ) expression
           | primary "[" expression "]" "=" expression
           | logical_or ;

logical_or = logical_and { "||" logical_and } ;
logical_and = equality { "&&" equality } ;
equality = relational { ( "==" | "!=" ) relational } ;
relational = additive { ( "<" | ">" | "<=" | ">=" ) additive } ;
additive = multiplicative { ( "+" | "-" ) multiplicative } ;
multiplicative = unary { ( "*" | "/" | "%" ) unary } ;

unary = [ "-" | "!" ] primary ;

primary = literal
        | identifier
        | "(" expression ")"
        | array_literal
        | function_call
        | member_access
        | index_access
        | anonymous_function
        | if_expression ;

literal = integer | float | string ;
integer = [ "-" ] digit { digit } ;
float = [ "-" ] digit { digit } "." digit { digit } ;
string = '"' { any_character_except_quote } '"' ;

array_literal = "[" [ expression { "," expression } ] "]" ;

function_call = primary "(" [ expression { "," expression } ] ")" ;
member_access = primary "." identifier ;
index_access = primary "[" expression "]" ;

anonymous_function = "fn" [ parameters ] ( block | expression ) ;

if_expression = "if" "(" expression ")" expression "else" expression ;

identifier = letter { letter | digit | "_" } ;
```

## Observations
- **Function Return**: The last expression in a function/block is its return value.
- **Anonymous Functions**: Can be assigned to variables or returned.
- **Dynamic Inheritance**: The base class in `class : base` can be any expression (e.g., an `if` expression or a function call).
- **Accessors**: `readable` (getter) and `accessible` (getter + setter) simplify property management.
- **Static Members**: `static my` defines class-level variables.
- **Packages**: Namespaced containers that can be nested and reopened.
- **Semicolons**: Not explicitly used in examples, implying newline or structural termination.
- **Comments**: Started with `#`.
