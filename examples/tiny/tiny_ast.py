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


# --- Skeletal TinyNode subclasses for statements ---

class MainDeclNode(TinyNode):
    statement_type = "main_decl"


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


class ReturnStmtNode(TinyNode):
    statement_type = "return_stmt"


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
