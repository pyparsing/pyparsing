# TINY parser and interpreter (pyparsing)

This folder contains a complete pyparsing parser/interpreter for the educational TINY language.

## Running the interpreter

After cloning the repo and establishing a virtual environment, cd to the project top-level
directory and run `python -m examples.tiny.tiny_run samples/hello.tiny` to run the basic 
"Hello, World!" program. The `samples` directory contains several other
illustrative scripts, using the TINY language.

## Project Structure

- tiny_parser.py
  - Defines the TINY language grammar using pyparsing and exposes `parse_tiny(text)` to parse source into `ParseResults`.
  - Independent of execution; focused purely on syntax and result structuring.
  - Allows for testing the parser in isolation from any integration or implementation
    components.

- tiny_ast.py
  - Declares the abstract base `TinyNode` and node subclasses for each TINY statement type (for example: `main_decl`, `decl_stmt`, `assign_stmt`, `if_stmt`, `repeat_stmt`, `read_stmt`, `write_stmt`, `return_stmt`, `call_stmt`).
  - Nodes wrap parser results and implement `execute(engine)`; nodes that contain bodies pre-build their child nodes.

- tiny_engine.py
  - Implements `TinyEngine`, the runtime responsible for variable scopes (stack frames plus globals), text I/O, expression evaluation, and function invocation.
  - Provides APIs used by AST nodes: declare/assign variables, evaluate expressions, read/write output, call functions.

- tiny_run.py
  - CLI entry point to parse and run a `.tiny` program.
  - Registers top-level functions/globals, builds the `main` function node, and executes it using `TinyEngine`.
  - Converts the parser's `ParseResults` into an executable hierarchy of `TinyNode` objects, using each statement group's `type` tag to instantiate the correct `TinyNode` subclass.

- samples/
  - Sample TINY programs (for example: `hello.tiny`, `hello_5.tiny`, `factorial.tiny`).

- tests/ and examples/tiny/tests/
  - Pytest-based tests that exercise the parser and AST/engine execution.

## How to run quick self-tests of the parser itself

- Run simple tests of the parser using `python -m examples.tiny.tiny_parser`

## How to use from Python

    from examples.tiny.tiny_parser import parse_tiny
    src = "read x; y := 1 + 2; write y"
    result = parse_tiny(src)
    print(result.dump())

Grammar outline: see `docs/grammar.md` and `docs/tiny_parser_diagram.html`

Pyparsing best practices were used to prompt the AI on preferred usages of pyparsing. Accessible using the command `python -m pyparsing.ai.show_best_practices`

## Reference
- TINY language definition: https://a7medayman6.github.io/Tiny-Compiler/Language-Description.html
