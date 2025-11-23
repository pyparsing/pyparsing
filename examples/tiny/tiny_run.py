"""
TINY interpreter scaffold built on top of the TINY parser.

This module currently provides:
- main(): CLI entry point that reads a .tiny source file, parses it using the
  TINY grammar, and prepares for conversion to TinyNode-based AST.

Note: Subclasses of TinyNode for concrete statement types are intentionally
not implemented yet. The conversion logic is scaffolded and will activate once
those subclasses are added, using each subclass's `statement_type` marker.

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




def _build_nodes(parsed: pp.ParseResults):
    """Scaffold for converting ParseResults to TinyNode instances.

    Since concrete TinyNode subclasses are not implemented yet, this function
    currently returns the original ParseResults. Once subclasses are added,
    this function will detect `type` tags on statement groups and instantiate
    the appropriate TinyNode subclass via `TinyNode.from_statement_type`.
    """
    # Minimal activation: wrap known statement groups into TinyNode subclasses
    if isinstance(parsed, pp.ParseResults) and "type" in parsed:
        node_cls = TinyNode.from_statement_type(parsed["type"])  # type: ignore[index]
        if node_cls is not None:
            return node_cls(parsed)
        # Fall through if no subclass yet
    return parsed


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

    # Register all top-level function definitions (store raw definitions for now)
    if "functions" in program:
        for fdef in program.functions:
            try:
                fname = fdef.decl.name
            except Exception:
                continue
            engine.register_function(fname, fdef)

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
    main_node = _build_nodes(main_group)
    engine.register_function("main", main_node)

    # Execute main if it is a TinyNode with an execute() method
    if isinstance(main_node, TinyNode):
        _ = main_node.execute(engine)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
