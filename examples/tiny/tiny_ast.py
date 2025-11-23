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

    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        # Main body: push a new frame for main's locals
        engine.push_frame()
        try:
            body = self.parsed.body
            stmts = body.stmts if hasattr(body, "stmts") else []

            for stmt in stmts:
                # Convert ParseResults to appropriate node if possible
                if isinstance(stmt, pp.ParseResults) and "type" in stmt:
                    node_cls = TinyNode.from_statement_type(stmt["type"])  # type: ignore[index]
                    node = node_cls(stmt) if node_cls is not None else None
                else:
                    node = None

                if node is not None:
                    result = node.execute(engine)
                    # Stop execution on explicit return (signaled by ReturnStmtNode or non-None)
                    if isinstance(node, ReturnStmtNode) or result is not None:
                        return result
                # Unknown or non-executable statement types are ignored for now
            return None
        finally:
            engine.pop_frame()


class DeclStmtNode(TinyNode):
    statement_type = "decl_stmt"


class AssignStmtNode(TinyNode):
    statement_type = "assign_stmt"


class IfStmtNode(TinyNode):
    statement_type = "if_stmt"


class RepeatStmtNode(TinyNode):
    statement_type = "repeat_stmt"


class ReadStmtNode(TinyNode):
    statement_type = "read_stmt"


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
