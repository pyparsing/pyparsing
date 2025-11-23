Instruction:
```
In tiny_parser.py, define number using ppc.number, not ppc.fnumber. This will convert numeric values to Python floats or ints at parse time, so no additional conversions are required in tiny_ast.py or tiny_engine.py.
```

Plan:
- Update `examples/tiny/tiny_parser.py` to use `pp.common.number` instead of `pp.common.fnumber` for the `number` literal.
- Verify that the parser still builds expressions correctly and that numeric tokens are converted to Python `int`/`float` at parse time.
- No changes required to `tiny_ast.py` or `tiny_engine.py` since runtime conversion becomes unnecessary.

Actions taken:
- Replaced `ppc.fnumber` with `ppc.number` and kept the token name as `"Number"`.
- Reviewed term and expression rules to ensure they continue to accept the `number` literal without further changes.
- Left engine and AST modules untouched, as requested.

---

#### Entry 18 — User Instruction
Instruction:
```
Implement DeclStmtNode (which may also include an assignment portion).
```

Plan:
- Review the grammar for `decl_stmt` to confirm fields: `datatype` and a list `decls`, where each decl group has `name` and optional `init` expression. ✓
- Implement `DeclStmtNode.execute(engine)` in `examples/tiny/tiny_ast.py`:
  - Determine `dtype = str(self.parsed.datatype)`.
  - Iterate `self.parsed.decls`; for each decl, evaluate `init` with `engine.eval_expr` if present, then call `engine.declare_var(name, dtype, init_val)`. ✓
- Keep return value `None` and avoid adding new scope (declarations occur in current frame). ✓
- Update this transcript entry with actions taken. ✓

Actions taken:
- Implemented `DeclStmtNode.execute` in `examples/tiny/tiny_ast.py` to declare one or more variables with optional initializers, using the engine for expression evaluation and declaration into the current frame.
- No changes to other nodes or engine were required.

#### Entry 14 — User Instruction
Instruction:
```
Add an is_implemented classmethod to TinyNode to detect if an execute() method has been defined (return False if cls.execute is TinyNode.execute). This will help us incrementally implement AST classes.
```

Plan:
- Add a `@classmethod is_implemented() -> bool` to `TinyNode` in `examples/tiny/tiny_ast.py`.
- Implement it to compare `cls.execute` against `TinyNode.execute` and return `True` only when overridden.
- Leave all other code unchanged.
- Append this entry to the running transcript.

Actions taken:
- Edited `examples/tiny/tiny_ast.py` to add `TinyNode.is_implemented` that returns `cls.execute is not TinyNode.execute`.
- No other modules required changes.

#### Entry 10 — User Instruction
Instruction:
```
Add a do-nothing execute() method to the base TinyNode class, which takes a TinyEngine as an argument. Then implement execute() for MainDeclNode, WriteStmtNode and ReturnStmtNode.
```

Plan:
- Add a no-op `execute(engine: TinyEngine) -> object | None` method to the `TinyNode` base class.
- Implement `execute` for `MainDeclNode` to:
  - Push a new frame on the `TinyEngine`.
  - Iterate the statements in `main.body.stmts`, wrapping them into `TinyNode` subclasses via `from_statement_type` and calling `execute`.
  - Stop and return when a `ReturnStmtNode` is encountered (or when a child returns a non-None value).
  - Pop the frame and return the captured value.
- Implement `execute` for `WriteStmtNode` to evaluate its `expr` via the engine and write the stringified result, or output a newline for `write endl;`.
- Implement `execute` for `ReturnStmtNode` to evaluate and return its expression value.
- Keep other node classes skeletal; no CLI changes required.

Actions taken:
- Updated `examples/tiny/tiny_ast.py`:
  - Added a default no-op `execute(self, engine)` method to `TinyNode`.
  - Implemented `execute` in `MainDeclNode` to push/pop a frame, iterate and execute statements, and stop on return.
  - Implemented `execute` in `WriteStmtNode` to write evaluated expressions or newline for `endl`.
  - Implemented `execute` in `ReturnStmtNode` to evaluate and return its expression value.
- Left other nodes skeletal and made no changes to `tiny_run.py` or `tiny_engine.py`.

---

#### Entry 11 — User Instruction
Instruction:
```
Modify TinyEngine to also keep a dict of globals, for variables that can be accessed from any TinyFrame. Store any variables or functions defined at the program level in the dict of globals.
```

Plan:
- Extend `TinyEngine` with a dedicated program-level globals store and a functions registry.
- Keep locals in stack `TinyFrame`s as before; the current frame remains the last item in the stack.
- Update lookup/assignment logic to search local frames first, then fall back to globals.
- Add explicit APIs for manipulating globals (`declare_global_var`, `assign_global_var`, `get_var` to read from globals if not found locally) and for function registration (`register_function`, `get_function`).
- Ensure `eval_expr` also consults globals when resolving identifiers.
- No parser/CLI changes required in this step; future steps can populate globals/functions based on program-level constructs.

Actions taken:
- Updated `examples/tiny/tiny_engine.py`:
  - Added `_globals: TinyFrame` and `_functions: dict[str, object]`.
  - Frame stack `_frames` now holds only local frames; globals are separate and always present.
  - Implemented program-level registry methods `register_function` and `get_function`.
  - Implemented globals API: `declare_global_var`, `assign_global_var`; updated `get_var`, `_find_frame_for_var`, and `assign_var` to consult and write to globals when appropriate.
  - Adjusted `current_frame` to guard against use when no local frame exists.
    - Updated `eval_expr` identifier resolution to check locals first, then globals.
- No changes to `tiny_ast.py` or `tiny_run.py` were required for this step.
 
---

#### Entry 12 — User Instruction
Instruction:
```
Change lines 71-77 in tiny_run.py to:
- create a new TinyEngine
- build nodes for the nodes in parsed
- save all top-level functions (including main()) into the TinyEngine functions, and any top-level variables in to the TinyEngine globals
- extract the AST node for the top-level "main" function, and call its execute() method passing in the TinyEngine object
```

Plan:
- Modify `examples/tiny/tiny_run.py` to replace the placeholder post-parse logic.
- Instantiate a `TinyEngine`.
- Register all top-level function definitions from `parsed.program.functions` into the engine via `register_function`.
- If present, load any top-level globals into the engine using `declare_global_var` (guarded, since the current grammar may not expose them).
- Build the AST node for `program.main` using `_build_nodes`, register it as `"main"`, and execute it by calling `execute(engine)`.
- Keep CLI return code and error handling intact.

Actions taken:
- Updated `examples/tiny/tiny_run.py` lines after parsing to:
  - Create `engine = TinyEngine()`.
  - Iterate `program.functions` to `register_function(name, fdef)`.
  - Best-effort import of any `program.globals` into engine globals when present.
  - Build `main_node = _build_nodes(program.main)`, register it as `"main"`, and execute it when it is a `TinyNode`.
- Left parsing and `--dump` behavior unchanged.

---

#### Entry 13 — User Instruction
Instruction:
```
At the end of WriteStmtNode, add "engine.output_text()".  Change TInyEngine's output_text() method to print("".join(self._out)), followed by self._out.clear()
```

Plan:
- Update `WriteStmtNode.execute` in `examples/tiny/tiny_ast.py` to call `engine.output_text()` after writing output or newline, to flush the buffer. *
- Modify `TinyEngine.output_text` in `examples/tiny/tiny_engine.py` to print the buffered output and clear the buffer (no return value). *
- Verify that no other code depends on `output_text()` returning a string. ✓
- Update `examples/tiny/tiny_interpreter_transcript.md` with this entry documenting instruction, plan, and actions. *
- Quick sanity check by running `hello.tiny` manually (not executed here). 

Actions taken:
- Edited `examples/tiny/tiny_ast.py`: in `WriteStmtNode.execute`, added a call to `engine.output_text()` after `_write`/`_writeln` to flush output immediately.
- Edited `examples/tiny/tiny_engine.py`: changed `output_text` to `print("".join(self._out), end="")` and then `self._out.clear()`; updated signature to return `None`.
- Searched current usages; no part of the codebase relied on the previous return value of `output_text`.

#### Entry 15 — User Instruction
Instruction:
```
Refactor MainDeclNode.execute() to remove the conversion from ParseResults to AST nodes. Instead, this conversion should be done in a build_contained_statements() method that is called from __init__() after calling super().__init__. build_contained_statements() will iterate over the statements in the parsed body, and create a list of statement nodes. Then execute() merely has to iterate over those nodes and call execute on each one. If those nodes themselves contain a body of statements, then building that AST node will in turn recursively build AST node lists - this will be the case for the main, function, repeat, and if statements.
```

Plan:
- In `examples/tiny/tiny_ast.py`, update `MainDeclNode` to pre-build its contained statements:
  - Add `__init__` that calls `super().__init__(parsed)` then `self.build_contained_statements()`.
  - Implement `build_contained_statements()` to iterate `self.parsed.body.stmts`, resolve each via `TinyNode.from_statement_type`, and instantiate nodes into `self.statements: list[TinyNode]`.
- Refactor `MainDeclNode.execute()` to only iterate over `self.statements`, executing each node and stopping on `ReturnStmtNode` or non-None result; keep frame push/pop with `finally`.
- Keep type annotations in Python 3.12+ style; avoid import cycles by using forward ref for `TinyEngine`.
- Append this entry to the transcript.

Actions taken:
- Edited `examples/tiny/tiny_ast.py`:
  - Added `__init__` and `build_contained_statements()` to `MainDeclNode` to construct `self.statements` at initialization.
  - Simplified `MainDeclNode.execute()` to iterate over prebuilt `self.statements` and execute them, preserving early return behavior and frame management.
- No changes were required in other files.

---

#### Entry 16 — User Instruction
Instruction:
```
Implement AssignStmtNode.execute() method and RepeatStmtNode.build_contained_statements() and .execute() methods
```

Plan:
- In `examples/tiny/tiny_ast.py`, implement `AssignStmtNode.execute(engine)` to evaluate the RHS using `engine.eval_expr(self.parsed.value)` and assign it to `self.parsed.target` via `engine.assign_var(...)`. ✓
- Implement `RepeatStmtNode` to pre-build its body statements:
  - Add `__init__` that calls `super().__init__(parsed)` then `build_contained_statements()`. ✓
  - Implement `build_contained_statements()` to iterate `self.parsed.body.stmts`, map each to a `TinyNode` subclass, and store in `self.statements: list[TinyNode]`. ✓
- Implement `RepeatStmtNode.execute(engine)` with do-while semantics:
  - Execute all body statements in order; if any returns a non-None result or is a `ReturnStmtNode`, propagate that result immediately (to allow function returns inside loops). ✓
  - After each body execution, evaluate `self.parsed.cond` with `engine.eval_expr`; break the loop when the condition is truthy. ✓
- Do not push/pop frames in `RepeatStmtNode` (no new scope). ✓
- Update the running transcript with this entry. ✓

Actions taken:
- Edited `examples/tiny/tiny_ast.py`:
  - Implemented `AssignStmtNode.execute` to evaluate and assign the RHS to the target variable via the engine.
  - Added `__init__`, `build_contained_statements`, and `execute` to `RepeatStmtNode` to pre-build its body and run it with repeat-until semantics, including early return propagation.
- Updated `examples/tiny/tiny_interpreter_transcript.md` with this plan and the actions performed.

---

#### Entry 17 — User Instruction
Instruction:
```
TinyEngine._to_number() must be modified:
- do not convert v to float if v is an int or float
- if v is a string, get the value of the variable v; return that value if int or float, otherwise raise TypeError
```

Plan:
- Update `_to_number` in `examples/tiny/tiny_engine.py` to conform to the specified behavior:
  - If `v` is `int` or `float`, return `v` unchanged. ✓
  - If `v` is `str`, resolve it as a variable name using existing lookup (`get_var`). If the value is numeric, return it; otherwise raise `TypeError`. ✓
  - For any other type, raise `TypeError`. ✓
- Ensure arithmetic and relational operations that use `_to_number` continue to work without further changes. ✓
- Append this entry to the transcript. ✓

Actions taken:
- Edited `examples/tiny/tiny_engine.py`:
  - Rewrote `_to_number` to return `int | float` and to return numeric inputs unchanged, resolve strings as identifiers via `get_var`, and raise `TypeError` for non-numeric or unresolved identifiers.
  - Removed previous generic `float(str(v))` coercion path to avoid unintended conversions.
