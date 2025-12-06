"""
Interactive REPL for the TINY language.

Features
- Starts with an empty TinyEngine and a single empty TinyFrame (locals scope).
- Executes entered TINY statements in the context of the current frame.
- Supports commands:
  - `help` — display commands help
  - `quit` — exit the REPL
  - `import <file>` — parse a TINY source file and load all defined functions,
    ignoring any `main()` function present.
  - `clear vars` — clear all locally defined variables (reset current frame).
  - `clear all` — clear all variables and functions (engine reset).
  - `list`, `list vars`, `list functions` — list defined vars and/or functions

Usage:
    python -m examples.tiny.tiny_repl
"""
from __future__ import annotations

from pathlib import Path
import sys
import traceback
from typing import Generic, TypeVar

import pyparsing as pp

from .tiny_parser import parse_tiny, stmt_seq, Function_Definition, comment as TINY_COMMENT
from .tiny_ast import TinyNode
from .tiny_engine import TinyEngine, TinyFrame, __version__ as TINY_VERSION
from .tiny_run import explain_parse_error


PROMPT = ">>> "
CONTINUE_PROMPT = "... "

T = TypeVar("T")

class byref(Generic[T]):
    """Class to pass scalar values by reference"""
    def __init__(self, /, value: T):
        self._value = value

    def get(self) -> T:
        return self._value

    def set(self, value: T):
        self._value = value


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
            msg = explain_parse_error(source_text, exc)
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
            except Exception:
                # Skip malformed definitions
                continue

            # Build function node and register signature and node
            fn_node_class = TinyNode.from_statement_type(fdef.type)
            if fn_node_class is None:
                continue
            fn_node = fn_node_class.from_parsed(fdef)
            engine.register_function(fname, fn_node)


def handle_meta_command(engine: TinyEngine, cmd: str, debug_ref: byref[bool]) -> bool:
    # normalize to lowercase, and collapse whitespace
    lower = " ".join(cmd.lower().split())
    line = cmd.strip()

    if lower == "help":
        print(f"TINY REPL v{TINY_VERSION}")
        print("Commands:")
        print("  help            - list commands and descriptions")
        print("  quit            - exit the REPL")
        print("  import <file>   - load functions from a .tiny file")
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
                    print(f"  {name}({', '.join(' '.join(p) for p in fn_params)}) : {fn_ret_type}")

        if lower in ("list", "list vars"):
            _print_vars()
        if lower in ("list", "list functions"):
            _print_functions()
        return True

    # Debug mode commands
    if lower == "debug on":
        debug_ref.set(True)
        print("[debug: on]")
        return True
    if lower == "debug off":
        debug_ref.set(False)
        print("[debug: off]")
        return True

    # import commands
    if cmd.startswith("import "):
        try:
            _, rest = line.split(None, 1)
        except ValueError:
            print("usage: import <file>")
            return True
        _load_functions_from_file(engine, rest.strip(), debug=debug_ref.get())
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
    print(
        f"TINY REPL v{TINY_VERSION} — enter statements on one or more lines."
        " Ctrl-C to cancel current input; `quit` to exit."
    )
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
            line = input(PROMPT if not buffer_lines else CONTINUE_PROMPT)
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

            debug_ref = byref(debug)
            if handle_meta_command(engine, cmd, debug_ref):
                debug = debug_ref.get()
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
                fdef = fdef_parsed[0]

                # Build node and register (overwrite if already exists)
                try:
                    fn_node_class = TinyNode.from_statement_type(fdef.type)
                    if fn_node_class is None:
                        raise TypeError(f"Unsupported function node type: {getattr(fdef, 'type', None)!r}")
                    fn_node = fn_node_class.from_parsed(fdef)
                    engine.register_function(fn_node.name, fn_node)
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
        echoed_any = False
        try:
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
