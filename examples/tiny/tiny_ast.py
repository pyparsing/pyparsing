"""
Executable Tiny AST types (skeletal).

This module defines the abstract base class `TinyNode` and skeletal subclasses
for the statement types produced by `examples.tiny.tiny_parser`.

Each subclass sets a class-level `statement_type` that matches the value used
by the parser's `pp.Tag("type", ...)` for that construct. Implementations are
skeletal on purpose and currently just wrap the original `ParseResults`.
"""
from __future__ import annotations

import pyparsing as pp


class TinyNode:
    """Abstract base for all executable TINY AST node classes.

    Subclasses must define a class-level `statement_type` that matches the
    `type` tag emitted by the parser for that statement.
    """

    statement_type: str | None = None

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
            if getattr(sub, "statement_type", None) == type_name:
                return sub
        return None

    @classmethod
    def is_implemented(cls) -> bool:
        """Return True if this class overrides TinyNode.execute.

        A node class is considered implemented when it defines its own
        execute() method. If the execute attribute on the class is the same
        function object as TinyNode.execute, then it is not yet implemented.
        """
        return cls.execute is not TinyNode.execute

    # Execution interface (default: do nothing)
    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        """Execute this node against the given engine.

        Base implementation does nothing and returns None. Subclasses override
        to provide behavior.
        """
        return None


# --- Skeletal TinyNode subclasses for statements ---

class MainDeclNode(TinyNode):
    statement_type = "main_decl"
    
    def __init__(self, parsed: pp.ParseResults):
        super().__init__(parsed)
        # Pre-build contained statement nodes for the main body
        self.statements: list[TinyNode] = []
        self.build_contained_statements()

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
                    built.append(node_cls(stmt))
        self.statements = built

    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        # Main body: push a new frame for main's locals
        engine.push_frame()
        try:
            for node in self.statements:
                result = node.execute(engine)
                # Stop execution on explicit return (signaled by ReturnStmtNode or non-None)
                if isinstance(node, ReturnStmtNode) or result is not None:
                    return result
            return None
        finally:
            engine.pop_frame()


class DeclStmtNode(TinyNode):
    statement_type = "decl_stmt"

    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        """Declare one or more variables, with optional initializers.

        Grammar provides:
          - `datatype`: one of 'int' | 'float' | 'string'
          - `decls`: a list of groups each with `name` and optional `init` expression
        """
        dtype = str(self.parsed.datatype) if "datatype" in self.parsed else "int"
        decls = self.parsed.decls if "decls" in self.parsed else []
        for d in decls:
            if not isinstance(d, pp.ParseResults):
                continue
            name = d.get("name")
            init_val = engine.eval_expr(d.init) if "init" in d else None  # type: ignore[attr-defined]
            engine.declare_var(name, dtype, init_val)
        return None


class AssignStmtNode(TinyNode):
    statement_type = "assign_stmt"

    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        # Evaluate RHS expression and assign to the target identifier
        target = self.parsed.target
        value = engine.eval_expr(self.parsed.value)
        engine.assign_var(target, value)
        return None


class IfStmtNode(TinyNode):
    statement_type = "if_stmt"


class RepeatStmtNode(TinyNode):
    statement_type = "repeat_stmt"

    def __init__(self, parsed: pp.ParseResults):
        super().__init__(parsed)
        self.statements: list[TinyNode] = []
        self.build_contained_statements()

    def build_contained_statements(self) -> None:
        """Pre-build TinyNode children for the repeat body statements."""
        stmts = self.parsed
        built: list[TinyNode] = []
        for stmt in stmts:
            if isinstance(stmt, pp.ParseResults) and "type" in stmt:
                node_cls = TinyNode.from_statement_type(stmt["type"])  # type: ignore[index]
                if node_cls is not None:
                    built.append(node_cls(stmt))
        self.statements = built

    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        # Repeat-Until is a do-while: execute body, then check condition; stop when condition is true
        while True:
            for node in self.statements:
                result = node.execute(engine)
                if isinstance(node, ReturnStmtNode) or result is not None:
                    return result
            # Evaluate loop condition after executing the body
            cond_val = engine.eval_expr(self.parsed.cond) if "cond" in self.parsed else False
            if bool(cond_val):
                break
        return None


class ReadStmtNode(TinyNode):
    statement_type = "read_stmt"

    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        # Grammar: read <Identifier>;
        # Prompt the user and assign the entered text to the variable.
        var_name = str(self.parsed.var) if "var" in self.parsed else ""
        # Use Python input() to prompt and read
        user_in = input(f"{var_name}? ")
        # Let the engine handle typing/coercion based on prior declaration
        engine.assign_var(var_name, user_in)
        return None


class WriteStmtNode(TinyNode):
    statement_type = "write_stmt"

    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        # Two forms: write endl;  OR  write expr;
        if "expr" in self.parsed:
            val = engine.eval_expr(self.parsed.expr)
            engine._write(str(val))
        else:
            # expect a literal token 'endl' in the parsed group
            # if not present, treat as a newline anyway
            engine._writeln()
        # Flush output buffer after each write statement per spec
        engine.output_text()
        return None


class ReturnStmtNode(TinyNode):
    statement_type = "return_stmt"

    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        value = engine.eval_expr(self.parsed.expr) if "expr" in self.parsed else None
        return value


class CallStmtNode(TinyNode):
    statement_type = "call_stmt"


__all__ = [
    "TinyNode",
    "MainDeclNode",
    "DeclStmtNode",
    "AssignStmtNode",
    "IfStmtNode",
    "RepeatStmtNode",
    "ReadStmtNode",
    "WriteStmtNode",
    "ReturnStmtNode",
    "CallStmtNode",
]
