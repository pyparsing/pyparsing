"""
TinyEngine: runtime support for executing TINY AST nodes.

This module exposes the `TinyEngine` class, moved out of `tiny_run.py` to keep
runtime concerns separate from the CLI and parsing scaffold.

It also defines `TinyFrame`, which represents a single stack frame for local
variables. `TinyEngine` maintains a stack (list) of frames, with the current
frame being the last element.
"""
from __future__ import annotations

import pyparsing as pp


class TinyFrame:
    """A single stack frame holding local variables and their types.

    Variables in TINY are stored per-frame; lookups search from the top frame
    downward to the bottom (global) frame.
    """

    def __init__(self) -> None:
        self._vars: dict[str, object] = {}
        self._types: dict[str, str] = {}  # 'int' | 'float' | 'string'

    def __contains__(self, name: str) -> bool:  # allow `name in frame`
        return name in self._vars

    def has(self, name: str) -> bool:
        return name in self._vars

    def declare(self, name: str, dtype: str, value: object) -> None:
        if name in self._vars:
            raise NameError(f"Variable already declared in frame: {name}")
        self._vars[name] = value
        self._types[name] = dtype

    def set(self, name: str, value: object) -> None:
        if name not in self._vars:
            raise NameError(f"Variable not declared in this frame: {name}")
        self._vars[name] = value

    def get(self, name: str) -> object:
        return self._vars[name]

    def get_type(self, name: str) -> str:
        return self._types[name]


class TinyEngine:
    """Runtime engine to execute TINY AST nodes.

    Responsibilities:
    - Manage I/O buffers (text-based input and output)
    - Maintain a simple variable environment (name -> value, with optional type)
    - Provide helpers for declaring and assigning variables
    - Evaluate parser expression trees produced by `tiny_parser`

    Notes:
    - Types supported: int, float, string. Numeric operations promote to float when needed.
    - Boolean context: 0 or empty string is False; anything else is True.
    - Function calls (`func_call`) are recognized but not implemented yet.
    """

    def __init__(self) -> None:
        # Stack of frames (last is current), and I/O buffers
        self._frames: list[TinyFrame] = [TinyFrame()]
        self._in: list[str] = []
        self._out: list[str] = []

    # ----- Frame management -----
    @property
    def current_frame(self) -> TinyFrame:
        return self._frames[-1]

    def push_frame(self) -> None:
        self._frames.append(TinyFrame())

    def pop_frame(self) -> None:
        if len(self._frames) == 1:
            raise RuntimeError("Cannot pop the global frame")
        self._frames.pop()

    # ----- I/O API -----
    def input_text(self, data: str) -> None:
        """Load whitespace-delimited tokens into the input buffer.

        Example: engine.input_text("10 20 hello")
        """
        # split on any whitespace; preserve order for FIFO consumption
        if data:
            self._in.extend(data.split())

    def output_text(self) -> str:
        """Return the current output as a single string."""
        return "".join(self._out)

    # Optional helpers for potential node use
    def _write(self, s: str) -> None:
        self._out.append(s)

    def _writeln(self) -> None:
        self._out.append("\n")

    def _read_token(self) -> str | None:
        return self._in.pop(0) if self._in else None

    # ----- Variables API -----
    def declare_var(self, name: str, dtype: str, init_value: object | None = None) -> None:
        """Declare a variable with an optional initial value.

        dtype: 'int' | 'float' | 'string'
        """
        # Declare in the current frame only
        if dtype not in {"int", "float", "string"}:
            raise TypeError(f"Unsupported datatype: {dtype}")
        if name in self.current_frame:
            raise NameError(f"Variable already declared: {name}")
        value = self._coerce(init_value, dtype) if init_value is not None else self._default_for(dtype)
        self.current_frame.declare(name, dtype, value)

    def assign_var(self, name: str, value: object) -> None:
        """Assign to an existing variable; if undeclared, declare using inferred type."""
        if isinstance(value, (list, tuple)) or hasattr(value, "__class__") and value.__class__.__name__ == "ParseResults":
            # Late evaluation if a parse tree is passed accidentally
            value = self.eval_expr(value)  # type: ignore[arg-type]

        # Find the nearest frame containing the variable; otherwise declare in current frame
        frame = self._find_frame_for_var(name)
        if frame is None:
            inferred = self._infer_type_from_value(value)
            self.declare_var(name, inferred, value)
            return
        dtype = frame.get_type(name)
        frame.set(name, self._coerce(value, dtype))

    def get_var(self, name: str) -> object:
        frame = self._find_frame_for_var(name)
        if frame is None:
            raise NameError(f"Variable not declared: {name}")
        return frame.get(name)

    def _find_frame_for_var(self, name: str) -> TinyFrame | None:
        for fr in reversed(self._frames):
            if name in fr:
                return fr
        return None

    # ----- Expression Evaluation -----
    def eval_expr(self, expr: object) -> object:
        """Evaluate an expression built by pyparsing's infix_notation and tokens.

        Accepts primitives (int/float/str), identifiers (str that is a declared var),
        pyparsing ParseResults for infix trees, and function call groups with
        tag type 'func_call'.
        """
        # Primitive values
        if isinstance(expr, (int, float, str)):
            # Identifier lookup: if a bare string matches a var name, read its value
            if isinstance(expr, str):
                fr = self._find_frame_for_var(expr)
                if fr is not None:
                    return fr.get(expr)
            return expr

        # ParseResults cases
        if isinstance(expr, pp.ParseResults):
            # Function call group
            if "type" in expr and expr["type"] == "func_call":  # type: ignore[index]
                name = expr["name"]
                args = [self.eval_expr(arg) for arg in (expr.get("args", []) or [])]
                raise NotImplementedError(f"Function calls not implemented: {name}({', '.join(map(str, args))})")

            # Infix notation yields list-like tokens
            tokens = list(expr)
            if not tokens:
                return None
            # Unary + or - : [op, operand]
            if len(tokens) == 2 and tokens[0] in {"+", "-"}:
                op, rhs = tokens
                rv = self.eval_expr(rhs)
                return +self._to_number(rv) if op == "+" else -self._to_number(rv)

            # Binary or n-ary left-assoc: [lhs, op, rhs, op, rhs, ...]
            # We fold left-to-right respecting the original parsed precedence.
            acc = self.eval_expr(tokens[0])
            i = 1
            while i < len(tokens):
                op = tokens[i]
                rhs = self.eval_expr(tokens[i + 1])
                acc = self._apply_op(acc, op, rhs)
                i += 2
            return acc

        # Lists/tuples could be token sequences
        if isinstance(expr, (list, tuple)):
            acc: object | None = None
            for part in expr:
                acc = self.eval_expr(part)
            return acc

        # Fallback
        return expr

    # ----- Helpers -----
    def _default_for(self, dtype: str) -> object:
        return 0 if dtype == "int" else 0.0 if dtype == "float" else ""

    def _infer_type_from_value(self, value: object) -> str:
        if isinstance(value, bool):
            return "int"  # treat bool as int
        if isinstance(value, int):
            return "int"
        if isinstance(value, float):
            return "float"
        if isinstance(value, str):
            return "string"
        # Unknown types default to string via str()
        return "string"

    def _coerce(self, value: object, dtype: str) -> object:
        if dtype == "int":
            if isinstance(value, str) and value.strip().isdigit():
                return int(value)
            if isinstance(value, (int, float)):
                return int(value)
            raise TypeError(f"Cannot coerce {value!r} to int")
        if dtype == "float":
            if isinstance(value, (int, float)):
                return float(value)
            try:
                return float(str(value))
            except Exception as exc:
                raise TypeError(f"Cannot coerce {value!r} to float") from exc
        if dtype == "string":
            return str(value)
        raise TypeError(f"Unsupported datatype: {dtype}")

    def _truthy(self, v: object) -> bool:
        if isinstance(v, (int, float)):
            return v != 0
        if isinstance(v, str):
            return v != ""
        return bool(v)

    def _to_number(self, v: object) -> float:
        if isinstance(v, (int, float)):
            return float(v)
        try:
            return float(str(v))
        except Exception as exc:
            raise TypeError(f"Expected numeric, got {v!r}") from exc

    def _apply_op(self, lhs: object, op: str, rhs: object) -> object:
        # Boolean ops
        if op in {"&&", "||"}:
            lv = self._truthy(lhs)
            rv = self._truthy(rhs)
            return lv and rv if op == "&&" else lv or rv

        # Relational ops
        if op in {"<", ">", "=", "<>"}:
            # Numeric compare if both numeric-like; else string compare
            if isinstance(lhs, (int, float)) or isinstance(rhs, (int, float)):
                lnum = self._to_number(lhs)
                rnum = self._to_number(rhs)
                if op == "<":
                    return lnum < rnum
                if op == ">":
                    return lnum > rnum
                if op == "=":
                    return lnum == rnum
                return lnum != rnum  # "<>"
            else:
                lstr = str(lhs)
                rstr = str(rhs)
                if op == "<":
                    return lstr < rstr
                if op == ">":
                    return lstr > rstr
                if op == "=":
                    return lstr == rstr
                return lstr != rstr

        # Arithmetic ops
        if op in {"+", "-", "*", "/"}:
            # String concatenation when both are strings and op '+'
            if op == "+" and isinstance(lhs, str) and isinstance(rhs, str):
                return lhs + rhs
            # Numeric operations
            lnum = self._to_number(lhs)
            rnum = self._to_number(rhs)
            if op == "+":
                return lnum + rnum
            if op == "-":
                return lnum - rnum
            if op == "*":
                return lnum * rnum
            # '/'
            return lnum / rnum

        raise NotImplementedError(f"Operator not implemented: {op}")
