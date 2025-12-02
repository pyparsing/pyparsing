"""
Executable Tiny AST types.

This module defines the abstract base class `TinyNode` and statement-type-specific
subclasses for the statement types produced by `examples.tiny.tiny_parser`.

Each subclass sets a class-level `statement_type` that matches the value used
by the parser's `pp.Tag("type", ...)` for that construct. This associates the
parsed results for a statement to the corresponding `TinyNode` subclass.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, ClassVar, Any
import pyparsing as pp


class TinyNode(ABC):
    """Abstract base for all executable TINY AST node classes.

    Purpose
    - Each concrete subclass represents one statement form produced by
      `examples.tiny.tiny_parser`.
    - Subclasses must define a class-level `statement_type` whose value matches
      the parser's `pp.Tag("type", ...)` for that construct.

    Lifecycle and required methods
    - `from_parsed(parsed: pp.ParseResults) -> TinyNode`
      Factory that constructs an instance from a parser group. Implementations
      should normalize the raw `ParseResults` into explicit dataclass fields and
      eagerly prebuild any child statement nodes. After construction, runtime
      execution should not need to reach back into `self.parsed` except for
      debugging. This separation keeps execution independent of the parser's
      internal token structure and avoids pervasive `hasattr`/`in` checks.

    - `execute(engine: TinyEngine) -> object | None`
      Execute this node against the provided runtime engine. Implementations
      perform side effects via the engine (variable declaration/assignment,
      I/O writes, control flow) and return a value when appropriate:
        * Most statement nodes return `None`.
        * `ReturnStmtNode` signals control flow by raising `ReturnPropagate`;
          callers (such as function or main bodies) catch this to retrieve the
          value. Other nodes should rely on this mechanism and not special-case
          return handling.

    Notes
    - Keep `statement_type` as a class variable (see below) so it is not treated
      as a dataclass field in subclasses.
    - Subclasses may keep a reference to the original `parsed` group for
      diagnostics, but business logic should use their explicit fields.
    """

    # Note: keep `statement_type` as a class variable. For dataclass subclasses,
    # this must not become an instance field. Use ClassVar to make intent explicit.
    statement_type: ClassVar[str] = ""

    def __init__(self, parsed: pp.ParseResults):
        self.parsed: pp.ParseResults = parsed

    def __repr__(self) -> str:
        cls = type(self).__name__
        stype = getattr(self, "statement_type", None)
        return f"<{cls} statement_type={stype!r}>"

    @classmethod
    def from_statement_type(cls, type_name: str) -> type[TinyNode] | None:
        """Return the TinyNode subclass matching `type_name`.

        Iterates over direct subclasses. If deeper inheritance hierarchies are created,
        this needs to be expanded to recurse.
        """
        for sub in cls.__subclasses__():
            if sub.statement_type == type_name:
                return sub
        return None

    # All subclasses must provide a uniform factory for construction
    @classmethod
    @abstractmethod
    def from_parsed(cls, parsed: pp.ParseResults) -> TinyNode:
        """Construct an instance from a parser `ParseResults` group."""
        raise NotImplementedError

    @staticmethod
    def body_statements(stmts: list[Any] | Any) -> list[TinyNode]:
        """Convert a sequence of parsed body statements to TinyNode instances.

        Used in statements with a contained body (e.g. function, repeat, if-then-else).
        """
        built: list[TinyNode] = []
        for stmt in stmts:
            if isinstance(stmt, pp.ParseResults) and "type" in stmt:
                node_cls = TinyNode.from_statement_type(stmt["type"])  # type: ignore[index]
                if node_cls is not None:
                    # All subclasses are guaranteed to implement from_parsed
                    built.append(node_cls.from_parsed(stmt))  # type: ignore[arg-type]
        return built

    # Execution interface (must be overridden by subclasses)
    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        """Execute this node against the given engine.

        Subclasses must implement this method.
        """
        raise NotImplementedError(f"execute() not implemented for {type(self).__name__}")


# --- Skeletal TinyNode subclasses for statements ---

@dataclass(init=False)
class MainDeclNode(TinyNode):
    """Dataclass node representing the `main` function body.

    - Prebuilds and stores the list of child statement nodes under
      `statements` at construction time.
    - Execution pushes a new frame, executes each statement in order, and
      returns the value propagated by a `return` (via `ReturnPropagate`),
      or `None` if no return occurs.
    - Construct using `from_parsed(parsed)` or the legacy `__init__(parsed)`.
    """
    statement_type: ClassVar[str] = "main_decl"

    # Prebuilt main-body statements
    return_type: str = "int"
    parameters: list[tuple[str, str]] = field(default_factory=list)
    statements: list[TinyNode] = field(default_factory=list)

    def __init__(self, parsed: pp.ParseResults):
        super().__init__(parsed)
        # Pre-build contained statement nodes for the main body
        self.statements = []
        self.parameters = []
        self.build_contained_statements()

    @classmethod
    def from_parsed(cls, parsed: pp.ParseResults) -> MainDeclNode:
        # Maintain compatibility with engine/builders expecting factory constructors
        return cls(parsed)

    def build_contained_statements(self) -> None:
        """Convert parsed body statements to TinyNode instances.

        This runs once at construction so that execute() only iterates nodes.
        """
        body = self.parsed.body
        stmts = body.stmts if hasattr(body, "stmts") else []
        self.statements = self.body_statements(stmts)

    def execute(self, engine: "TinyEngine") -> int:  # noqa: F821 - forward ref
        # Main body: push a new frame for main's locals
        engine.push_frame()
        try:
            for node in self.statements:
                # Return statements propagate via exception
                node.execute(engine)
            return 0
        except ReturnPropagate as rp:
            return rp.value
        finally:
            engine.pop_frame()


@dataclass
class FunctionDeclStmtNode(TinyNode):
    """Node representing a function declaration/definition.

    This node accepts parser groups tagged with type 'func_decl'. It will
    initialize its `statements` from an associated function body group if
    available. The body is expected under either `parsed.Function_Body.stmts`
    or `parsed.body.stmts`, depending on how the upstream parser groups were
    provided by the caller.
    """
    statement_type: ClassVar[str] = "func_decl"

    # Prebuilt function body statements (if a body was provided)
    name: str
    return_type: str = ""
    parameters: list[tuple[str, str]] = field(default_factory=list)
    statements: list[TinyNode] = field(default_factory=list)

    @classmethod
    def from_parsed(cls, parsed: pp.ParseResults) -> FunctionDeclStmtNode:
        fn_name = parsed.decl.name
        return_type = parsed.decl.return_type
        if parsed.decl.parameters:
            params = [(p.type, p.name) for p in parsed.decl.parameters[0]]
        else:
            params = []

        # Locate a function body group in common shapes
        body_group: pp.ParseResults = parsed.body

        statement_nodes: list[TinyNode] = []
        if body_group:
            raw_stmts = body_group.stmts or []
            statement_nodes.extend(cls.body_statements(raw_stmts))

        return cls(name=fn_name, return_type=return_type, parameters=params, statements=statement_nodes)

    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        # Execute the function body in a new local frame. If body is absent,
        # this is effectively a no-op that returns None.

        # Caller should have already created a frame and populated parameters as vars
        try:
            for node in self.statements:
                node.execute(engine)
            return None
        except ReturnPropagate as rp:
            return rp.value


@dataclass
class DeclStmtNode(TinyNode):
    """Declaration statement node.

    Represents one declaration statement possibly declaring multiple
    identifiers with optional initializers, for example:

        int x := 1, y, z := 2;

    Fields:
    - dtype: declared datatype ("int", "float", or "string").
    - decls: list of (name, init_expr | None).
    """
    statement_type: ClassVar[str] = "decl_stmt"

    dtype: str = "int"
    # list of (name, init_expr | None)
    decls: list[tuple[str, Optional[object]]] = field(default_factory=list)

    @classmethod
    def from_parsed(cls, parsed: pp.ParseResults) -> DeclStmtNode:
        dtype = parsed.datatype or "int"
        items: list[tuple[str, Optional[object]]] = []
        for d in (parsed.decls or []):
            if not isinstance(d, pp.ParseResults):
                continue
            name = d.get("name")
            init_expr = d.init if "init" in d else None  # type: ignore[attr-defined]
            items.append((name, init_expr))
        return cls(dtype=dtype, decls=items)

    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        for name, init_expr in self.decls:
            init_val = engine.eval_expr(init_expr) if init_expr is not None else None
            engine.declare_var(name, self.dtype, init_val)
        return None


@dataclass
class AssignStmtNode(TinyNode):
    """Assignment statement node.

    Holds a target variable name and an expression to evaluate and assign.
    Example: `x := x + 1;`.
    """
    statement_type: ClassVar[str] = "assign_stmt"

    target: str = ""
    expr: object = None

    @classmethod
    def from_parsed(cls, parsed: pp.ParseResults) -> AssignStmtNode:
        return cls(target=parsed.target, expr=parsed.value)

    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        value = engine.eval_expr(self.expr)
        engine.assign_var(self.target, value)
        return None


@dataclass
class IfStmtNode(TinyNode):
    """If/ElseIf/Else control-flow node.

    Captures the main condition, then-branch statements, zero or more
    `elseif` branches as (condition, statements) pairs, and an optional
    `else` statements list. Execution evaluates conditions in order and
    executes the first matching branch.
    """
    statement_type: ClassVar[str] = "if_stmt"

    # Explicit fields for condition and branches
    cond: object | None = None
    then_statements: list[TinyNode] = field(default_factory=list)
    elseif_branches: list[tuple[object, list[TinyNode]]] = field(default_factory=list)
    else_statements: list[TinyNode] = field(default_factory=list)

    @classmethod
    def from_parsed(cls, parsed: pp.ParseResults) -> IfStmtNode:
        # Initial condition (defined by the parser for if-statements)
        cond_expr = parsed.cond if "cond" in parsed else None

        # Build THEN branch nodes
        built_then: list[TinyNode] = []
        then_seq = parsed.then if "then" in parsed else []
        built_then.extend(cls.body_statements(then_seq))

        # Build ELSEIF branches
        built_elseif: list[tuple[object, list[TinyNode]]] = []
        if "elseif" in parsed:
            for br in parsed["elseif"]:
                if not isinstance(br, pp.ParseResults):
                    continue
                branch_nodes = cls.body_statements(br.then)
                built_elseif.append((br.cond, branch_nodes))

        # Build ELSE branch
        built_else: list[TinyNode] = []
        if "else" in parsed:
            built_else = cls.body_statements(parsed["else"])

        return cls(cond=cond_expr, then_statements=built_then, elseif_branches=built_elseif, else_statements=built_else)

    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        # Evaluate main condition
        if self.cond is not None and bool(engine.eval_expr(self.cond)):
            for node in self.then_statements:
                node.execute(engine)
            return None

        # Elseif branches in order
        for cond, nodes in self.elseif_branches:
            if bool(engine.eval_expr(cond)):
                for node in nodes:
                    node.execute(engine)
                return None

        # Else branch if present
        for node in self.else_statements:
            node.execute(engine)
        return None


@dataclass
class RepeatStmtNode(TinyNode):
    """Repeat-Until loop node (do-while semantics).

    Executes the body statements at least once, then evaluates the `cond`
    expression after each iteration, terminating when it evaluates to true.
    """
    statement_type: ClassVar[str] = "repeat_stmt"

    # Body statements for the repeat block
    statements: list[TinyNode] = field(default_factory=list)
    # Until condition expression evaluated after each iteration
    cond: object | None = None

    @classmethod
    def from_parsed(cls, parsed: pp.ParseResults) -> RepeatStmtNode:
        # Build child statement nodes from the parsed body sequence
        statement_nodes: list[TinyNode] = []
        if parsed.body:
            stmts = parsed.body
            statement_nodes.extend(cls.body_statements(stmts))

        cond_expr = parsed.cond
        return cls(statements=statement_nodes, cond=cond_expr)

    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        # Repeat-Until is a do-while: execute body, then check condition; stop when condition is true
        while True:
            for node in self.statements:
                # Return statements now propagate via exception; no need to inspect results
                node.execute(engine)
            # Evaluate loop condition after executing the body
            cond_val = engine.eval_expr(self.cond) if self.cond is not None else False
            if bool(cond_val):
                break
        return None


@dataclass
class ReadStmtNode(TinyNode):
    """Read (input) statement node.

    Prompts for a token and assigns it (as a string) to the given variable
    name in the current frame.
    """
    statement_type: ClassVar[str] = "read_stmt"

    var_name: str = ""

    @classmethod
    def from_parsed(cls, parsed: pp.ParseResults) -> ReadStmtNode:
        return cls(var_name=getattr(parsed, "var", ""))

    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        user_in = input(f"{self.var_name}? ")
        engine.assign_var(self.var_name, user_in)
        return None


@dataclass
class WriteStmtNode(TinyNode):
    """Write (output) statement node.

    Writes the evaluated expression value, or a newline if `is_endl` is true
    or `expr` is None. Output is buffered in the engine and flushed per call.
    """
    statement_type: ClassVar[str] = "write_stmt"

    expr: Optional[object] = None
    is_endl: bool = False

    @classmethod
    def from_parsed(cls, parsed: pp.ParseResults) -> WriteStmtNode:
        if "expr" in parsed:
            return cls(expr=parsed.expr, is_endl=False)
        # expect literal endl otherwise
        return cls(expr=None, is_endl=True)

    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        if self.is_endl or self.expr is None:
            engine._writeln()
        else:
            val = engine.eval_expr(self.expr)
            engine._write(str(val))
        engine.output_text()
        return None

class ReturnPropagate(Exception):
    """Using exception mechanism to propagate return value from within
    nested statements within a function.
    """
    def __init__(self, value):
        self.value = value

@dataclass
class ReturnStmtNode(TinyNode):
    """Return statement node.

    Evaluates the optional expression and raises `ReturnPropagate` to unwind
    to the nearest function/main boundary with the computed value (or None).
    """
    statement_type: ClassVar[str] = "return_stmt"

    expr: Optional[object] = None

    @classmethod
    def from_parsed(cls, parsed: pp.ParseResults) -> ReturnStmtNode:
        return cls(expr=parsed.expr if "expr" in parsed else None)

    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        value = engine.eval_expr(self.expr) if self.expr is not None else None
        raise ReturnPropagate(value)


@dataclass
class CallStmtNode(TinyNode):
    """Statement form of a function call.

    Holds the function name and argument expressions; on execution the
    arguments are evaluated and `TinyEngine.call_function` is invoked. The
    return value (if any) is ignored in statement context.
    """
    statement_type: ClassVar[str] = "call_stmt"

    name: str = ""
    args: list[object] = field(default_factory=list)

    @classmethod
    def from_parsed(cls, parsed: pp.ParseResults) -> CallStmtNode:
        func_group: pp.ParseResults | None = None
        for item in parsed:
            if isinstance(item, pp.ParseResults) and "type" in item and item["type"] == "func_call":  # type: ignore[index]
                func_group = item
                break
        if func_group is None:
            return cls(name="", args=[])
        name = func_group.name
        raw_args = func_group.args or []
        return cls(name=name, args=list(raw_args))

    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        arg_values = [engine.eval_expr(arg) for arg in self.args]
        _ = engine.call_function(self.name, arg_values)
        return None


__all__ = [
    "TinyNode",
    "MainDeclNode",
    "FunctionDeclStmtNode",
    "DeclStmtNode",
    "AssignStmtNode",
    "IfStmtNode",
    "RepeatStmtNode",
    "ReadStmtNode",
    "WriteStmtNode",
    "ReturnStmtNode",
    "CallStmtNode",
]
