"""
Interactive REPL for the TINY language.

Features
- Starts with an empty TinyEngine and a single empty TinyFrame (locals scope).
- Executes entered TINY statements in the context of the current frame.
- Supports commands:
  - `quit` — exit the REPL
  - `import <file>` — parse a TINY source file and load all defined functions,
    ignoring any `main()` function present. Existing functions are left intact.
  - `reimport <file>` — same as `import`, but overwrites previously defined functions.
  - `clear vars` — clear all locally defined variables (reset current frame).
  - `clear all` — clear all variables and functions (engine reset).

Usage:
    python -m examples.tiny.tiny_repl
"""
from __future__ import annotations

from pathlib import Path
import sys
import traceback
from typing import Iterable

import pyparsing as pp

from .tiny_parser import parse_tiny, stmt_seq, Function_Definition, comment as TINY_COMMENT
from .tiny_ast import TinyNode
from .tiny_engine import TinyEngine, TinyFrame, __version__ as TINY_VERSION


PROMPT = ">>> "
CONT_PROMPT = "... "


def _explain_parse_error(src: str, err: pp.ParseBaseException) -> str:
    """Return a helpful, context-rich parse error string."""
    src_lines = src.splitlines()
    # Guard against last-line errors
    if err.lineno - 1 >= len(src_lines):
        src_lines.append("")
    pre_idx = max(err.lineno - 3, 0)
    frag_lines: list[str] = []
    width = len(str(err.lineno + 1))
    for i in range(pre_idx, err.lineno - 1):
        frag_lines.append(f"{i+1:>{width}}:  {src_lines[i]}")
    current = src_lines[err.lineno - 1]
    frag_lines.append(f"{err.lineno:>{width}}: >{current}")
    next_line = src_lines[err.lineno] if err.lineno < len(src_lines) else ""
    frag_lines.append(f"{err.lineno+1:>{width}}:  {next_line}")
    return "\n".join(frag_lines) + "\n\n" + err.explain(depth=0)


def _build_nodes_from_stmt_seq(parsed_seq: pp.ParseResults) -> list[TinyNode]:
    """Convert a parsed `stmt_seq` group into prebuilt `TinyNode` instances."""
    nodes: list[TinyNode] = []
    for st in parsed_seq:
        stype = st.get("type")
        cls = TinyNode.from_statement_type(stype)
        if not cls:
            # Skip unknown or unimplemented statements gracefully
            continue
        nodes.append(cls.from_parsed(st))
    return nodes


def _load_functions_from_file(
    engine: TinyEngine,
    filepath: str | Path,
    *,
    overwrite: bool,
    debug: bool = False,
) -> None:
    """Parse a .tiny file and register its function definitions into the engine.

    - Ignores any `main()` function present.
    - If `overwrite` is False, existing functions with the same name are preserved.
    """
    p = Path(filepath)
    try:
        with p.open("r", encoding="utf-8") as f:
            source_text = f.read()
        try:
            parsed = parse_tiny(source_text)
        except pp.ParseBaseException as exc:
            msg = _explain_parse_error(source_text, exc)
            print(msg, file=sys.stderr)
            return
    except OSError as exc:
        # File-related problems
        if debug:
            traceback.print_exc()
        else:
            print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return
    except Exception as exc:
        # Unexpected importer exception
        if debug:
            traceback.print_exc()
        else:
            print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return

    program = parsed.program
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

            # Skip if not overwriting and function already exists
            if not overwrite and engine.get_function(fname) is not None:
                continue

            # Build function node and register signature and node
            fn_node_class = TinyNode.from_statement_type(fdef.type)
            if fn_node_class is None:
                continue
            fn_node = fn_node_class.from_parsed(fdef)
            engine.register_function_signature(fname, return_type, params)
            engine.register_function(fname, fn_node)


def _try_execute(engine: TinyEngine, source: str) -> None:
    """Parse and execute a TINY statement sequence against the engine.

    Ctrl-C (KeyboardInterrupt) during execution interrupts the current run
    and returns to the prompt. Any buffered output is flushed and a newline
    is printed in all cases.
    """
    if not source.strip():
        return
    try:
        parsed = stmt_seq.parse_string(source, parse_all=True)
    except pp.ParseBaseException as exc:
        print(_explain_parse_error(source, exc), file=sys.stderr)
        return

    nodes = _build_nodes_from_stmt_seq(parsed)
    try:
        for node in nodes:
            node.execute(engine)
    except KeyboardInterrupt:
        # Interrupt execution and return to prompt
        pass
    finally:
        # Always flush any buffered output and print a newline after executing
        engine.output_text()
        print()

def handle_meta_command(engine: TinyEngine, cmd: str, debug:list[bool]) -> bool:
    # normalize to lowercase, and collapse whitespace
    lower = " ".join(cmd.lower().split())
    line = cmd.strip()

    if lower == "help":
        print(f"TINY REPL v{TINY_VERSION}")
        print("Commands:")
        print("  help            - list commands and descriptions")
        print("  quit            - exit the REPL")
        print("  import <file>   - load functions from a .tiny file")
        print("  reimport <file> - load functions, overwriting existing")
        print("  clear vars      - clear current local variables")
        print("  clear all       - reset engine state (all vars, funcs)")
        print("  list            - list variables and functions")
        print("  list vars       - list only current variables")
        print("  list functions  - list defined function names")
        print("  debug on        - show full Python tracebacks")
        print("  debug off       - concise errors; hide tracebacks")
        return True

    if lower == "quit":
        return True

    if lower in ("list", "list vars", "list functions"):
        # Listing helpers
        def _print_vars() -> None:
            frame = engine.current_frame
            vars_dict = getattr(frame, "_vars", {})  # type: ignore[attr-defined]
            names = sorted(vars_dict.keys())
            if not names:
                print("[variables] (none)")
            else:
                print("[variables]")
                for name in names:
                    dtype, value = vars_dict[name]
                    print(f"  {name} = {value!r} : {dtype}")

        def _print_functions() -> None:
            funcs = engine.get_functions()
            names = sorted(funcs.keys())
            if not names:
                print("[functions] (none)")
            else:
                print("[functions]")
                sigs = engine.get_function_signatures()
                for name in names:
                    fn_ret_type, fn_params = sigs[name]
                    print(f"  {fn_ret_type} {name}({', '.join(' '.join(p) for p in fn_params)})")

        if lower in ("list", "list vars"):
            _print_vars()
        if lower in ("list", "list functions"):
            _print_functions()
        return True

    # Debug mode commands
    if lower == "debug on":
        debug[0] = True
        print("[debug: on]")
        return True
    if lower == "debug off":
        debug[0] = False
        print("[debug: off]")
        return True

    # import commands
    if cmd.startswith("import "):
        try:
            _, rest = line.split(None, 1)
        except ValueError:
            print("usage: import <file>")
            return True
        _load_functions_from_file(engine, rest.strip(), overwrite=False, debug=debug[0])
        return True
    if line.lower().startswith("reimport "):
        try:
            _, rest = line.split(None, 1)
        except ValueError:
            print("usage: reimport <file>")
            return True
        _load_functions_from_file(engine, rest.strip(), overwrite=True, debug=debug[0])
        return True

    # clear/reset commands
    if lower == "clear vars":
        if engine._frames:  # type: ignore[attr-defined]
            engine._frames[-1] = TinyFrame()  # type: ignore[attr-defined]
        else:
            engine.push_frame()
        print("[locals cleared]")
        return True

    if lower == "clear all":
        engine = TinyEngine()
        engine.push_frame()
        print("[engine reset]")
        return True

    return False

def repl() -> int:
    print(f"TINY REPL v{TINY_VERSION} — enter statements on one or more lines. Ctrl-C to cancel current input; `quit` to exit.")
    engine = TinyEngine()
    # Initialize with a single empty frame for locals
    engine.push_frame()

    # Incremental input buffer
    buffer_lines: list[str] = []
    # Debug mode flag: when True, show full tracebacks for exceptions during execution
    debug: bool = False
    while True:
        try:
            # Choose prompt based on whether we're in the middle of a statement
            line = input(PROMPT if not buffer_lines else CONT_PROMPT)
        except EOFError:
            # On EOF: discard any partial input and exit
            print()
            break
        except KeyboardInterrupt:
            # Ctrl-C while prompting: clear current buffer and show fresh prompt
            print()  # move to a new line
            buffer_lines.clear()
            continue

        # If starting fresh, allow immediate REPL commands
        if not buffer_lines:
            cmd = line.strip()
            if not cmd:
                # ignore empty input
                continue

            if handle_meta_command(engine, cmd, [debug]):
                if cmd.strip().lower() == "quit":
                    break

                continue

        # Treat as part of TINY input
        buffer_lines.append(line)
        source = "\n".join(buffer_lines)
        # Try to parse after each line; if it parses, execute immediately
        try:
            parsed = stmt_seq.parse_string(source, parse_all=True)
        except pp.ParseBaseException:
            # Try parsing a single function definition instead
            try:
                fdef_parsed = Function_Definition.parse_string(source, parse_all=True)
            except pp.ParseBaseException:
                # If the buffer contains only comments, accept and clear it
                try:
                    pp.OneOrMore(TINY_COMMENT).parse_string(source, parse_all=True)
                except pp.ParseBaseException:
                    # Keep collecting lines until parse succeeds or user presses Ctrl-C
                    continue
                else:
                    buffer_lines.clear()
                    continue
            else:
                # Successfully parsed a function declaration/definition typed at the prompt
                try:
                    fdef = fdef_parsed[0] if isinstance(fdef_parsed[0], pp.ParseResults) else fdef_parsed
                except Exception:
                    fdef = fdef_parsed

                # Extract signature
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
                except Exception as exc:
                    # Malformed function declaration; report concisely unless in debug
                    if debug:
                        traceback.print_exc()
                    else:
                        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
                    buffer_lines.clear()
                    continue

                # Build node and register (overwrite if already exists)
                try:
                    fn_node_class = TinyNode.from_statement_type(fdef.type)
                    if fn_node_class is None:
                        raise TypeError(f"Unsupported function node type: {getattr(fdef, 'type', None)!r}")
                    fn_node = fn_node_class.from_parsed(fdef)
                    engine.register_function_signature(fname, return_type, params)
                    engine.register_function(fname, fn_node)
                except Exception as exc:
                    if debug:
                        traceback.print_exc()
                    else:
                        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
                finally:
                    # Clear buffer and continue to next prompt
                    buffer_lines.clear()
                continue

        # Parsed successfully: execute and reset buffer
        nodes = _build_nodes_from_stmt_seq(parsed)
        try:
            echoed_any = False
            for node in nodes:
                ret = node.execute(engine)
                stype = getattr(node, "statement_type", None)
                if stype in ("expr_stmt", "call_stmt"):
                    # Echo the resulting value using Python repr()
                    if ret is not None:
                        print(repr(ret))
                    echoed_any = True
        except KeyboardInterrupt:
            # Interrupt current execution; fall through to flush output
            pass
        except Exception as exc:  # Non-runtime exceptions during execution
            if debug:
                # In debug mode, show full traceback but keep REPL alive
                traceback.print_exc()
            else:
                # Suppress traceback: show only exception type and message
                print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        finally:
            engine.output_text()
            if not echoed_any:
                # Preserve the invariant: ensure at least one newline after execution
                print()
        buffer_lines.clear()

    return 0


def main(argv: list[str] | None = None) -> int:
    # No CLI options at this time; reserved for future enhancements
    return repl()


if __name__ == "__main__":
    raise SystemExit(main())
