"""
TINY interpreter scaffold built on top of the TINY parser.

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
        parsed = parse_tiny(source_text, parse_all=True)
    except pp.ParseBaseException as exc:
        # Print helpful location info
        print(f"Parse error at line {exc.lineno}, col {exc.column}: {exc}", file=sys.stderr)
        return 3

    if args.dump:
        # Pretty-print the primary structure for inspection
        print(parsed.dump())

    # Instantiate the engine that will hold globals, functions, and frames
    engine = TinyEngine()

    # Build nodes where applicable and register top-level items
    program = parsed.program

    initialize_engine(engine, program)

    # Execute scripts "main" function
    main_node = engine.get_function("main")

    try:
        main_node.execute(engine)
    finally:
        if sys.exc_info()[0] is not None:
            return 1
        return 0


def initialize_engine(engine: TinyEngine, program: ParseResults | str | Any) -> TinyNode:
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

            # Register signature and node for runtime use
            engine.register_function_signature(fname, return_type, params)
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

    return main_node


if __name__ == "__main__":
    raise SystemExit(main())
