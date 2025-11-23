"""
Executable Tiny AST types (skeletal).

This module defines the abstract base class `TinyNode` and skeletal subclasses
for the statement types produced by `examples.tiny.tiny_parser`.

Each subclass sets a class-level `statement_type` that matches the value used
by the parser's `pp.Tag("type", ...)` for that construct. Implementations are
skeletal on purpose and currently just wrap the original `ParseResults`.
"""
from __future__ import annotations

from abc import ABC
import pyparsing as pp


class TinyNode(ABC):
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

    # Execution interface (must be overridden by subclasses)
    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        """Execute this node against the given engine.

        TinyNode is an abstract base; subclasses must implement this method.
        """
        raise NotImplementedError(f"execute() not implemented for {type(self).__name__}")


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

    def __init__(self, parsed: pp.ParseResults):
        super().__init__(parsed)
        # Pre-built branches
        self.then_statements: list[TinyNode] = []
        self.elseif_branches: list[tuple[object, list[TinyNode]]] = []  # (cond, statements)
        self.else_statements: list[TinyNode] = []
        self.build_contained_statements()

    def build_contained_statements(self) -> None:
        """Build TinyNode children for then/elseif/else branches.

        The parsed shape (see tiny_parser.If_Statement):
          - cond: condition expression for the initial if
          - then: stmt_seq("then") with .stmts
          - elseif: ZeroOrMore(Group(cond + THEN + stmt_seq("then"))) (optional)
          - else: Optional(stmt_seq("else")) (optional)
        """
        # then branch
        then_seq = self.parsed.then if "then" in self.parsed else []
        then_stmts = then_seq
        built_then: list[TinyNode] = []
        for stmt in then_stmts:
            if isinstance(stmt, pp.ParseResults) and "type" in stmt:
                node_cls = TinyNode.from_statement_type(stmt["type"])  # type: ignore[index]
                if node_cls is not None:
                    built_then.append(node_cls(stmt))
        self.then_statements = built_then

        # elseif branches
        built_elseif: list[tuple[object, list[TinyNode]]] = []
        if "elseif" in self.parsed:
            for br in self.parsed["elseif"]:
                if not isinstance(br, pp.ParseResults):
                    continue
                cond = br.get("cond")
                seq = br.get("then", [])
                seq_stmts = getattr(seq, "stmts", seq)
                branch_nodes: list[TinyNode] = []
                for stmt in seq_stmts:
                    if isinstance(stmt, pp.ParseResults) and "type" in stmt:
                        node_cls = TinyNode.from_statement_type(stmt["type"])  # type: ignore[index]
                        if node_cls is not None:
                            branch_nodes.append(node_cls(stmt))
                built_elseif.append((cond, branch_nodes))
        self.elseif_branches = built_elseif

        # else branch
        if "else" in self.parsed:
            else_seq = self.parsed["else"]
            else_stmts = else_seq  # getattr(else_seq, "stmts", else_seq)
            built_else: list[TinyNode] = []
            for stmt in else_stmts:
                if isinstance(stmt, pp.ParseResults) and "type" in stmt:
                    node_cls = TinyNode.from_statement_type(stmt["type"])  # type: ignore[index]
                    if node_cls is not None:
                        built_else.append(node_cls(stmt))
            self.else_statements = built_else
        else:
            self.else_statements = []

    def _exec_block(self, engine: "TinyEngine", nodes: list[TinyNode]) -> object | None:  # noqa: F821
        for node in nodes:
            result = node.execute(engine)
            if isinstance(node, ReturnStmtNode) or result is not None:
                return result
        return None

    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        # Evaluate main condition
        cond_val = engine.eval_expr(self.parsed.cond) if "cond" in self.parsed else False
        if bool(cond_val):
            return self._exec_block(engine, self.then_statements)

        # Elseif branches in order
        for cond, nodes in self.elseif_branches:
            if bool(engine.eval_expr(cond)):
                return self._exec_block(engine, nodes)

        # Else branch if present
        if self.else_statements:
            return self._exec_block(engine, self.else_statements)

        return None


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

    def execute(self, engine: "TinyEngine") -> object | None:  # noqa: F821 - forward ref
        """Execute a statement-style function call.

        Grammar shape (see tiny_parser.py):
          call_stmt -> Group(Tag("type","call_stmt") + function_call + ';')
          function_call -> Group(Tag("type","func_call") + name + '(' args? ')')

        We locate the nested `func_call` group, evaluate each argument using
        the engine, and invoke the function via `engine.call_function(...)`.
        Statement-form calls ignore any returned value.
        """
        func_group: pp.ParseResults | None = None
        for item in self.parsed:
            if isinstance(item, pp.ParseResults) and "type" in item and item["type"] == "func_call":  # type: ignore[index]
                func_group = item
                break

        if func_group is None:
            # Nothing to do if the structure is unexpected
            return None

        name = str(func_group.name) if "name" in func_group else ""
        raw_args = (func_group.get("args", []) or [])
        arg_values = [engine.eval_expr(arg) for arg in raw_args]
        # Invoke the function; ignore the returned value in statement context
        _ = engine.call_function(name, arg_values)
        return None


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
