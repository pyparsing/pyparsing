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
from .tiny_ast import TinyNode, ReturnStmtNode, ReturnPropagate

import operator

_op_map = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
    "=": operator.eq,
    "<>": operator.ne,
    "<": operator.lt,
    ">": operator.gt,
    "<=": operator.le,
    ">=": operator.ge,
}

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
    """

    def __init__(self) -> None:
        # Dedicated program-level globals and function registry
        self._globals: TinyFrame = TinyFrame()
        self._functions: dict[str, TinyNode] = {}

        # Function signatures: name -> (return_type, [(ptype, pname), ...])
        # Used when functions are registered as AST nodes to bind parameters
        self._function_sigs: dict[str, tuple[str, list[tuple[str, str]]]] = {}

        # Stack of frames (last is current); empty until main/function entry
        self._frames: list[TinyFrame] = []
        self._in: list[str] = []
        self._out: list[str] = []

    # ----- Program-level registry (globals/functions) -----
    def register_function(self, name: str, fn: TinyNode) -> None:
        """Register a program-level function definition by name.
        """
        self._functions[name] = fn

    def get_function(self, name: str) -> TinyNode | None:
        return self._functions.get(name)

    def register_function_signature(self, name: str, return_type: str, params: list[tuple[str, str]]) -> None:
        """Register or update a function's signature metadata.

        params: list of (ptype, pname)
        """
        self._function_sigs[name] = (return_type, params)

    # ----- Frame management -----
    @property
    def current_frame(self) -> TinyFrame:
        if not self._frames:
            raise RuntimeError("No current frame: push_frame() must be called before using locals")
        return self._frames[-1]

    def push_frame(self) -> None:
        self._frames.append(TinyFrame())

    def pop_frame(self) -> None:
        if not self._frames:
            raise RuntimeError("No frame to pop")
        self._frames.pop()

    # ----- I/O API -----
    def input_text(self, data: str) -> None:
        """Load whitespace-delimited tokens into the input buffer.

        Example: engine.input_text("10 20 hello")
        """
        # split on any whitespace; preserve order for FIFO consumption
        if data:
            self._in.extend(data.split())

    def output_text(self) -> None:
        """Print the current buffered output and clear the buffer."""
        print("".join(self._out), end="")
        self._out.clear()

    # Optional helpers for potential node use
    def _write(self, s: str) -> None:
        self._out.append(s)

    def _writeln(self) -> None:
        self._out.append("\n")

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

    # Globals API
    def declare_global_var(self, name: str, dtype: str, init_value: object | None = None) -> None:
        if dtype not in {"int", "float", "string"}:
            raise TypeError(f"Unsupported datatype: {dtype}")
        if name in self._globals:
            raise NameError(f"Global already declared: {name}")
        value = self._coerce(init_value, dtype) if init_value is not None else self._default_for(dtype)
        self._globals.declare(name, dtype, value)

    def assign_global_var(self, name: str, value: object) -> None:
        if name not in self._globals:
            # If not declared, infer type and declare
            inferred = self._infer_type_from_value(value)
            self.declare_global_var(name, inferred, value)
            return
        dtype = self._globals.get_type(name)
        self._globals.set(name, self._coerce(value, dtype))

    def assign_var(self, name: str, value: object) -> None:
        """Assign to an existing variable; if undeclared, declare using inferred type."""
        if isinstance(value, (list, tuple)) or hasattr(value, "__class__") and value.__class__.__name__ == "ParseResults":
            # Late evaluation if a parse tree is passed accidentally
            value = self.eval_expr(value)  # type: ignore[arg-type]

        # Find the nearest frame containing the variable; fall back to globals; otherwise declare local
        frame = self.current_frame
        if name in frame:
            dtype = frame.get_type(name)
            frame.set(name, self._coerce(value, dtype))
            return
        if name in self._globals:
            dtype = self._globals.get_type(name)
            self._globals.set(name, self._coerce(value, dtype))
            return
        # Not found anywhere; declare locally with inferred type
        inferred = self._infer_type_from_value(value)
        self.declare_var(name, inferred, value)

    def get_var(self, name: str) -> object:
        frame = self.current_frame
        if name in frame:
            return frame.get(name)
        if name in self._globals:
            return self._globals.get(name)
        raise NameError(f"Variable not declared: {name}")

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
                fr = self.current_frame
                if expr in fr:
                    return fr.get(expr)
                if expr in self._globals:
                    return self._globals.get(expr)
            return expr

        # ParseResults cases
        if isinstance(expr, pp.ParseResults):
            # Function call group
            if "type" in expr and expr["type"] == "func_call":  # type: ignore[index]
                name = expr.name
                arg_values = [self.eval_expr(arg) for arg in (expr.get("args", []) or [])]
                return self.call_function(name, arg_values)

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

    # ----- Functions API (execution helper to share with CallStmtNode) -----
    def call_function(self, name: str, args: list[object]) -> object | None:
        """Call a user-defined function by name with already-evaluated arguments.

        This method is used by expression evaluation (for `func_call` terms) and
        can be reused by `CallStmtNode.execute` to perform statement-style calls.
        """
        fn = self.get_function(name)
        if fn is None:
            raise NameError(f"Undefined function: {name}")

        if name not in self._function_sigs:
            raise TypeError(f"Missing signature for function {name!r}")
        return_type, params = self._function_sigs[name]
        if len(args) != len(params):
            raise TypeError(f"Function {name} expects {len(params)} args, got {len(args)}")

        self.push_frame()
        try:
            # Bind parameters in order
            for (ptype, pname), value in zip(params, args):
                self.declare_var(pname, ptype or "int", value)

            # Execute body node; catch return propagation
            return fn.execute(self)
        finally:
            self.pop_frame()

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
            try:
                return int(value)
            except ValueError:
                raise TypeError(f"Cannot coerce {value!r} to int") from None

        if dtype == "float":
            try:
                return float(value)
            except ValueError:
                raise TypeError(f"Cannot coerce {value!r} to float") from None

        if dtype == "string":
            return str(value)
        raise TypeError(f"Unsupported datatype: {dtype}")

    def _truthy(self, v: object) -> bool:
        if isinstance(v, (int, float)):
            return v != 0
        if isinstance(v, str):
            return v != ""
        return bool(v)

    def _to_number(self, v: object) -> int | float:
        """Return a numeric value for v following Tiny semantics.

        Rules:
        - If v is already an int or float, return it unchanged (no float coercion).
        - If v is a string, treat it as a variable name; fetch its current value
          from the environment. If that value is int or float, return it; otherwise
          raise TypeError.
        - For all other types, raise TypeError.
        """
        # Already numeric: return as-is (do not coerce int->float)
        if isinstance(v, (int, float)):
            return v

        # If it's a string, interpret as variable name and resolve
        if isinstance(v, str):
            try:
                val = self.get_var(v)
            except NameError as exc:
                raise TypeError(f"Expected numeric variable name, got undefined identifier {v!r}") from exc
            if isinstance(val, (int, float)):
                return val
            raise TypeError(f"Variable {v!r} is not numeric: {val!r}")

        # Anything else is not acceptable as a numeric
        raise TypeError(f"Expected numeric, got {v!r}")

    def _apply_op(self, lhs: object, op: str, rhs: object) -> object:
        # Boolean ops
        if op in {"&&", "||"}:
            lv = self._truthy(lhs)
            rv = self._truthy(rhs)
            return lv and rv if op == "&&" else lv or rv

        # Relational ops
        if op in {"<", ">", "=", "<>", ">=", "<="}:
            # Numeric compare if both numeric-like; else string compare
            if isinstance(lhs, (int, float)) or isinstance(rhs, (int, float)):
                lnum = self._to_number(lhs)
                rnum = self._to_number(rhs)
                return _op_map[op](lnum, rnum)
            else:
                lstr = str(lhs)
                rstr = str(rhs)
                return _op_map[op](lstr, rstr)

        # Arithmetic ops
        if op in {"+", "-", "*", "/"}:
            # String concatenation when both are strings and op '+'
            if op == "+" and isinstance(lhs, str) and isinstance(rhs, str):
                return lhs + rhs
            # Numeric operations
            lnum = self._to_number(lhs)
            rnum = self._to_number(rhs)
            return _op_map[op](lnum, rnum)

        raise NotImplementedError(f"Operator not implemented: {op}")
