"""
TINY interpreter scaffold built using:
- parser defined in tiny_parser.py
- executable statement AST classes defined in tiny_ast.py
- execution engine defined in tiny_engine.py

This module currently provides:
- main(): CLI entry point that reads a .tiny source file, parses it using the
  TINY grammar, and prepares for conversion to TinyNode-based AST.

Usage:
    python -m examples.tiny.tiny_run path/to/program.tiny [--dump]
"""
from __future__ import annotations

import argparse
import sys

import pyparsing as pp

from .tiny_parser import parse_tiny
from .tiny_ast import TinyNode
from .tiny_engine import TinyEngine


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a TINY program using the TINY interpreter scaffold.")
    parser.add_argument("source", help="Path to the .tiny source file")
    parser.add_argument("--dump", action="store_true", help="Dump parsed structure (debug)")
    args = parser.parse_args(argv)

    try:
        with open(args.source, "r", encoding="utf-8") as f:
            source_text = f.read()
    except OSError as exc:
        print(f"Error reading {args.source}: {exc}", file=sys.stderr)
        return 2

    try:
        parsed = parse_tiny(source_text)
    except pp.ParseBaseException as exc:
        # Print helpful location info
        error_lineno = exc.lineno
        lineno_len = len(str(error_lineno + 1))
        # add an extra line to guard against failing to unpack if the error is on the last line
        source_lines = source_text.splitlines() + [""]
        *prelude, error_line, postlude = source_lines[max(error_lineno - 3, 0) : error_lineno + 1]
        fragment = "\n".join(
            [
            *(f"{prelineno:>{lineno_len}}:  {line}" for prelineno, line in enumerate(prelude, start = error_lineno - len(prelude))),
            f"{error_lineno:>{lineno_len}}: >{error_line}",
            f"{error_lineno + 1:>{lineno_len}}:  {postlude}",
            ]
        )
        print(fragment)
        print()
        print(exc.explain(depth=0))
        return 3

    if args.dump:
        # Pretty-print the primary structure for inspection
        print(parsed.dump())
        exit()

    # Instantiate the engine that will hold globals, functions, and frames
    engine = TinyEngine()

    # initialize engine with parsed globals
    initialize_engine(engine, parsed.program)

    # Execute scripts "main" function
    main_node = engine.get_function("main")
    main_node.execute(engine)


def initialize_engine(engine: TinyEngine, program: pp.ParseResults):
    # Register all top-level function definitions: build function nodes and signatures
    if "functions" in program:
        for fdef in program.functions:
            try:
                decl = fdef.decl
                fname = decl.name
                return_type = decl.return_type or "int"
                params_group = decl.parameters
                param_list = list(params_group[0]) if params_group else []
                params: list[tuple[str, str]] = []
                for p in param_list:
                    ptype = p.type or "int"
                    pname = p.name
                    params.append((ptype, pname))
            except Exception:
                # Skip malformed definitions
                continue

            # Build a function node with a prebuilt body
            fn_node_class = TinyNode.from_statement_type(fdef.type)
            fn_node = fn_node_class.from_parsed(fdef)

            # Register function node for runtime use
            engine.register_function(fname, fn_node)

    # Register any top-level globals if they exist (grammar may not provide these)
    if "globals" in program:
        for g in program.globals:
            try:
                dtype = str(g.datatype)
                # Handle one or more variable declarations in a decl stmt
                decls = g.decls if hasattr(g, "decls") else []
                for d in decls:
                    name = d.name
                    init_val = d.get("init") if isinstance(d, pp.ParseResults) else None
                    engine.declare_global_var(name, dtype, init_val)
            except Exception:
                # Best-effort: skip malformed/unsupported global forms
                continue

    # Build AST node for main() and register it as a function
    main_group = program.main
    main_node_class = TinyNode.from_statement_type(main_group["type"])
    main_node = main_node_class.from_parsed(main_group)
    engine.register_function("main", main_node)


if __name__ == "__main__":
    raise SystemExit(main())
