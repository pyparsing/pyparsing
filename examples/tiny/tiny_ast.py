"""
Executable Tiny AST types (skeletal).

This module defines the abstract base class `TinyNode` and skeletal subclasses
for the statement types produced by `examples.tiny.tiny_parser`.

Each subclass sets a class-level `statement_type` that matches the value used
by the parser's `pp.Tag("type", ...)` for that construct. Implementations are
skeletal on purpose and currently just wrap the original `ParseResults`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, ClassVar
import pyparsing as pp


class TinyNode(ABC):
    """Abstract base for all executable TINY AST node classes.

    Subclasses must define a class-level `statement_type` that matches the
    `type` tag emitted by the parser for that statement.
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

        Iterates over direct subclasses. If deeper hierarchies are created,
        this could be expanded to recurse.
        """
        for sub in cls.__subclasses__():
            if sub.statement_type == type_name:
                return sub
        return None

    # Execution interface (must be overridden by subclasses)
    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        """Execute this node against the given engine.

        TinyNode is an abstract base; subclasses must implement this method.
        """
        raise NotImplementedError(f"execute() not implemented for {type(self).__name__}")

    # All subclasses must provide a uniform factory for construction
    @classmethod
    @abstractmethod
    def from_parsed(cls, parsed: pp.ParseResults) -> "TinyNode":
        """Construct an instance from a parser `ParseResults` group."""
        raise NotImplementedError


# --- Skeletal TinyNode subclasses for statements ---

@dataclass(init=False)
class MainDeclNode(TinyNode):
    # Keep as class variable; not a dataclass field
    statement_type: ClassVar[str] = "main_decl"

    # Prebuilt main-body statements
    statements: list[TinyNode] = field(default_factory=list)

    def __init__(self, parsed: pp.ParseResults):
        super().__init__(parsed)
        # Pre-build contained statement nodes for the main body
        self.statements = []
        self.build_contained_statements()

    @classmethod
    def from_parsed(cls, parsed: pp.ParseResults) -> "MainDeclNode":
        # Maintain compatibility with engine/builders expecting factory constructors
        return cls(parsed)

    def build_contained_statements(self) -> None:
        """Convert parsed body statements to TinyNode instances.

        This runs once at construction so that execute() only iterates nodes.
        """
        body = self.parsed.body
        stmts = body.stmts if hasattr(body, "stmts") else []
        built: list[TinyNode] = []
        for stmt in stmts:
            if isinstance(stmt, pp.ParseResults) and "type" in stmt:
                node_cls = TinyNode.from_statement_type(stmt["type"])  # type: ignore[index]
                if node_cls is not None:
                    # All subclasses are guaranteed to implement from_parsed
                    built.append(node_cls.from_parsed(stmt))  # type: ignore[arg-type]
        self.statements = built

    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        # Main body: push a new frame for main's locals
        engine.push_frame()
        try:
            for node in self.statements:
                # Return statements propagate via exception
                node.execute(engine)
            return None
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

    Note: `statement_type` remains a class variable and is not a dataclass
    instance field.
    """

    # Keep as class variable; do not include as dataclass field
    statement_type: ClassVar[str] = "func_decl"

    # Prebuilt function body statements (if a body was provided)
    name: str
    statements: list[TinyNode] = field(default_factory=list)

    @classmethod
    def from_parsed(cls, parsed: pp.ParseResults) -> "FunctionDeclStmtNode":
        fn_name = parsed.decl.name

        # Locate a function body group in common shapes
        body_group: pp.ParseResults = parsed.body

        built: list[TinyNode] = []
        if body_group:
            raw_stmts = body_group.stmts or []
            for stmt in raw_stmts:
                node_cls = TinyNode.from_statement_type(stmt["type"])  # type: ignore[index]
                if node_cls is not None:
                    built.append(node_cls.from_parsed(stmt))  # type: ignore[arg-type]
        return cls(name=fn_name, statements=built)

    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        # Execute the function body in a new local frame. If no body is present,
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
    # ClassVar so dataclass does not treat this as a field
    statement_type: ClassVar[str] = "decl_stmt"

    dtype: str = "int"
    # list of (name, init_expr | None)
    decls: List[Tuple[str, Optional[object]]] = field(default_factory=list)

    @classmethod
    def from_parsed(cls, parsed: pp.ParseResults) -> "DeclStmtNode":
        dtype = parsed.datatype or "int"
        items: List[Tuple[str, Optional[object]]] = []
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
    # ClassVar so dataclass does not treat this as a field
    statement_type: ClassVar[str] = "assign_stmt"

    target: str = ""
    expr: object = None

    @classmethod
    def from_parsed(cls, parsed: pp.ParseResults) -> "AssignStmtNode":
        return cls(target=parsed.target, expr=parsed.value)

    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        value = engine.eval_expr(self.expr)
        engine.assign_var(self.target, value)
        return None


@dataclass
class IfStmtNode(TinyNode):
    # Keep as class variable; not a dataclass field
    statement_type: ClassVar[str] = "if_stmt"

    # Explicit fields for condition and branches
    cond: object | None = None
    then_statements: list[TinyNode] = field(default_factory=list)
    elseif_branches: list[tuple[object, list[TinyNode]]] = field(default_factory=list)
    else_statements: list[TinyNode] = field(default_factory=list)

    @classmethod
    def from_parsed(cls, parsed: pp.ParseResults) -> "IfStmtNode":
        # Initial condition (defined by the parser for if-statements)
        cond_expr = parsed.cond if "cond" in parsed else None

        # Build THEN branch nodes
        built_then: list[TinyNode] = []
        then_seq = parsed.then if "then" in parsed else []
        for stmt in then_seq:
            if isinstance(stmt, pp.ParseResults) and "type" in stmt:
                node_cls = TinyNode.from_statement_type(stmt["type"])  # type: ignore[index]
                if node_cls is not None:
                    built_then.append(node_cls.from_parsed(stmt))  # type: ignore[arg-type]

        # Build ELSEIF branches
        built_elseif: list[tuple[object, list[TinyNode]]] = []
        if "elseif" in parsed:
            for br in parsed["elseif"]:
                if not isinstance(br, pp.ParseResults):
                    continue
                branch_nodes: list[TinyNode] = []
                for stmt in br.then:
                    if isinstance(stmt, pp.ParseResults) and "type" in stmt:
                        node_cls = TinyNode.from_statement_type(stmt["type"])  # type: ignore[index]
                        if node_cls is not None:
                            branch_nodes.append(node_cls.from_parsed(stmt))  # type: ignore[arg-type]
                built_elseif.append((br.cond, branch_nodes))

        # Build ELSE branch
        built_else: list[TinyNode] = []
        if "else" in parsed:
            for stmt in parsed["else"]:
                if isinstance(stmt, pp.ParseResults) and "type" in stmt:
                    node_cls = TinyNode.from_statement_type(stmt["type"])  # type: ignore[index]
                    if node_cls is not None:
                        built_else.append(node_cls.from_parsed(stmt))  # type: ignore[arg-type]

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
    # ClassVar so dataclass does not treat this as a field
    statement_type: ClassVar[str] = "repeat_stmt"

    # Body statements for the repeat block
    statements: list[TinyNode] = field(default_factory=list)
    # Until condition expression evaluated after each iteration
    cond: object | None = None

    @classmethod
    def from_parsed(cls, parsed: pp.ParseResults) -> "RepeatStmtNode":
        # Build child statement nodes from the parsed body sequence
        built: list[TinyNode] = []
        for stmt in parsed:
            if isinstance(stmt, pp.ParseResults) and "type" in stmt:
                node_cls = TinyNode.from_statement_type(stmt["type"])  # type: ignore[index]
                if node_cls is not None:
                    built.append(node_cls.from_parsed(stmt))  # type: ignore[arg-type]
        # Condition is mandatory in the parser's definition of repeat-until
        cond_expr = parsed.cond
        return cls(statements=built, cond=cond_expr)

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
    # ClassVar so dataclass does not treat this as a field
    statement_type: ClassVar[str] = "read_stmt"

    var_name: str = ""

    @classmethod
    def from_parsed(cls, parsed: pp.ParseResults) -> "ReadStmtNode":
        return cls(var_name=getattr(parsed, "var", ""))

    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        user_in = input(f"{self.var_name}? ")
        engine.assign_var(self.var_name, user_in)
        return None


@dataclass
class WriteStmtNode(TinyNode):
    # ClassVar so dataclass does not treat this as a field
    statement_type: ClassVar[str] = "write_stmt"

    expr: Optional[object] = None
    is_endl: bool = False

    @classmethod
    def from_parsed(cls, parsed: pp.ParseResults) -> "WriteStmtNode":
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
    # ClassVar so dataclass does not treat this as a field
    statement_type: ClassVar[str] = "return_stmt"

    expr: Optional[object] = None

    @classmethod
    def from_parsed(cls, parsed: pp.ParseResults) -> "ReturnStmtNode":
        return cls(expr=parsed.expr if "expr" in parsed else None)

    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        value = engine.eval_expr(self.expr) if self.expr is not None else None
        raise ReturnPropagate(value)


@dataclass
class CallStmtNode(TinyNode):
    # ClassVar so dataclass does not treat this as a field
    statement_type: ClassVar[str] = "call_stmt"

    name: str = ""
    args: List[object] = field(default_factory=list)

    @classmethod
    def from_parsed(cls, parsed: pp.ParseResults) -> "CallStmtNode":
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
