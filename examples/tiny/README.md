# TINY parser and interpreter (pyparsing)

This folder contains a complete pyparsing parser/interpreter for the educational TINY language.

## Running the interpreter

After cloning the repo and establishing a virtual environment, cd to the project top-level
directory and run `python -m examples.tiny.tiny_run samples/hello.tiny` to run the basic 
"Hello, World!" program. The `samples` directory contains several other
illustrative scripts, using the TINY language.

## Running the REPL

The TINY project includes an interactive Read–Eval–Print Loop (REPL) for quickly
trying out statements and functions.

- Start the REPL:

  ```
  python -m examples.tiny.tiny_repl
  ```

- Enter TINY statements directly at the `>>> ` prompt. The REPL incrementally parses your
  input and executes as soon as the current input forms a complete statement sequence.

- Useful keys/behavior:
  - Press Ctrl-C while typing to cancel the current partial input and return to a fresh prompt.
  - Press Ctrl-C during a long-running execution to interrupt it and return to the prompt.

- Built-in REPL commands (typed at an empty prompt):
  - `quit` — exit the REPL
  - `import <file>` — load function definitions from a `.tiny` file (ignores any `main()`)
  - `reimport <file>` — same as `import`, but overwrites any previously defined functions
  - `clear vars` — clear locally defined variables in the current frame
  - `clear all` — reset engine state (variables and functions)
  - `list` — show current variables and all defined function names
  - `list vars` — show only current variables
  - `list functions` — show only function names
  - `help` — list all REPL commands with brief descriptions
  - `debug on` — enable debug mode (show full Python exception tracebacks during execution)
  - `debug off` — disable debug mode (default; suppress tracebacks and print only `Type: message`)

- Example session:

  ```
  >>> list
  [variables] (none)
  [functions] (none)
  >>> import examples/tiny/samples/math_functions.tiny
  >>> int x := 5;
  >>> write factorial(x);
  120
  >>> list
  [variables]
    x = 5 : int
  [functions]
    abs(float a) : float
    cos(float rad_) : float
    deg(float rad) : float
    div(int a, int b) : int
    exp(float x) : float
    factorial(int n) : int
    hypot(float x, float y) : float
    mod(int a, int b) : int
    pi() : float
    pow(float x, int y) : float
    rad(float deg) : float
    round(float a, int n) : float
    sgn(float x) : int
    sin(float rad_) : float
    sqrt(float a) : float
    tan(float rad_) : float
  >>> quit
  ```

- Errors and debugging:
  - By default, exceptions raised while executing TINY statements are shown concisely as 
    `ExceptionType: message` without a traceback.
  - The same concise behavior applies when importing files with `import`/`reimport` (I/O and other errors
    print `ExceptionType: message`).
  - Turn on verbose debugging with `debug on` to display full Python tracebacks for exceptions during execution.
    Use `debug off` to return to concise error messages.
  - In debug mode, file import errors will also show full Python tracebacks.

For a fuller walkthrough of REPL features and development notes, see
`examples/tiny/docs/tiny_repl_transcript.md`.

## Project Structure

- tiny_parser.py
  - Defines the TINY language grammar using pyparsing and exposes `parse_tiny(text)` to parse source into internal
    parser results.
  - The parser tags each statement group with a `type` tag (for example: `main_decl`, `decl_stmt`, `assign_stmt`,
    `if_stmt`, `repeat_stmt`, `read_stmt`, `write_stmt`, `return_stmt`, `call_stmt`), which is used in `tiny_ast.py` 
    to instantiate the appropriate executable AST node subclass.
  - Independent of execution; focused purely on syntax and result structuring.
  - Allows for testing the parser in isolation from any integration or implementation components.

- tiny_ast.py
  - Declares the abstract base `TinyNode` and node subclasses for each TINY statement type.
  - Nodes wrap parser results and implement `execute(engine)`; nodes that contain bodies pre-build their child nodes.

- tiny_engine.py
  - Implements `TinyEngine`, the runtime responsible for variable scopes (stack frames plus globals), text I/O, 
    expression evaluation, and function invocation.
  - Provides APIs used by AST nodes: declare/assign variables, evaluate expressions, read/write output, call functions.

- tiny_run.py
  - CLI entry point to parse and run a `.tiny` program.
  - Registers top-level functions/globals, builds the `main` function node, and executes it using `TinyEngine`.
  - Converts the parser's internal results into an executable hierarchy of `TinyNode` objects, using each statement 
    group's `type` tag to instantiate the correct `TinyNode` subclass.

- tiny_repl.py
  - CLI entry point to start the interactive TINY REPL.
  - Implements the REPL's command-line interface and REPL-specific logic.
  - Uses `tiny_parser.py`, `tiny_ast.py`, and `tiny_engine.py` to parse and execute TINY statements.

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

Pyparsing best practices were used to prompt the AI on preferred usages of pyparsing. Accessible using the command 
`python -m pyparsing.ai.show_best_practices`

## Reference
- TINY language definition: https://a7medayman6.github.io/Tiny-Compiler/Language-Description.html
