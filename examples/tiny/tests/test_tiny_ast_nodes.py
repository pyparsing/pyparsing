from __future__ import annotations

import textwrap

import pyparsing as pp
import pytest

from examples.tiny.tiny_parser import parse_tiny
from examples.tiny.tiny_ast import TinyNode
from examples.tiny.tiny_engine import TinyEngine


def _run_main_and_capture(src: str, capsys: pytest.CaptureFixture[str]) -> tuple[int | None, str]:
    """Parse the Tiny program, build the main AST node, execute it, and capture stdout.

    Returns (return_value, stdout_text).
    """
    try:
        parsed = parse_tiny(src)
    except pp.ParseException as pe:
        print(pe.explain())
        raise

    main_group = parsed.program.main
    # Build a MainDeclNode via the registry
    node_cls = TinyNode.from_statement_type(main_group["type"])  # type: ignore[index]
    assert node_cls is not None, "MainDeclNode class must be registered"
    main_node = node_cls(main_group)

    engine = TinyEngine()
    ret = main_node.execute(engine)  # type: ignore[assignment]
    captured = capsys.readouterr()
    return ret, captured.out


def test_declaration_with_initializers_prints_values(capsys: pytest.CaptureFixture[str]) -> None:
    src = (
        """\
        int main(){
            int i := 42;
            string s := "Hello";
            write i; write " "; write s; write endl;
            return 0;
        }
        """
    )
    ret, out = _run_main_and_capture(src, capsys)
    assert out == "42 Hello\n"
    assert ret == 0


def test_function_with_no_parameters_call_via_expr(capsys: pytest.CaptureFixture[str]) -> None:
    """Define a function that takes no parameters and returns a string.

    The main program calls it in an expression context: write greeting();
    Verifies that functions with empty parameter lists are parsed, registered,
    called via eval_expr(func_call), and their return value is used.
    """
    src = (
        """\
        string greeting(){
            return "Hello!";
        }
        int main(){
            write greeting(); write endl;
            return 0;
        }
        """
    )

    parsed = parse_tiny(src)

    # Register top-level functions with the engine
    engine = TinyEngine()
    for fdef in parsed.program.functions:
        node_cls = TinyNode.from_statement_type(fdef.type)
        fn_node = node_cls.from_parsed(fdef)
        engine.register_function(fdef.decl.name, fn_node)
        engine.register_function_signature(fdef.decl.name, fdef.decl.return_type, fdef.decl.parameters)

    # Build and execute main
    main_group = parsed.program.main
    node_cls = TinyNode.from_statement_type(main_group["type"])  # type: ignore[index]
    assert node_cls is not None
    main_node = node_cls(main_group)
    ret = main_node.execute(engine)

    captured = capsys.readouterr()
    assert captured.out == "Hello!\n"
    assert ret == 0


def test_assignment_updates_value(capsys: pytest.CaptureFixture[str]) -> None:
    src = (
        """\
        int main(){
            int x := 1;
            x := x + 2;
            write x; write endl;
            return 0;
        }
        """
    )
    ret, out = _run_main_and_capture(src, capsys)
    assert out == "3\n"
    assert ret == 0


def test_repeat_until_prints_n_times(capsys: pytest.CaptureFixture[str]) -> None:
    src = (
        """\
        int main(){
            int i := 5;
            repeat
                write "Hello World!"; write endl;
                i := i - 1;
            until i = 0
            return 0;
        }
        """
    )
    ret, out = _run_main_and_capture(src, capsys)
    lines = [ln for ln in out.splitlines() if ln.strip() != ""]
    assert len(lines) == 5
    assert all(ln == "Hello World!" for ln in lines)
    assert ret == 0


def test_read_statement_prompts_and_assigns(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    # Program declares x as int, reads it from input, and writes it back
    src = (
        """\
        int main(){
            int x;
            read x;
            write x; write endl;
            return 0;
        }
        """
    )

    # Simulate user entering 17 at the prompt
    monkeypatch.setattr("builtins.input", lambda prompt="": "17")

    parsed = parse_tiny(src)
    main_group = parsed.program.main
    node_cls = TinyNode.from_statement_type(main_group["type"])  # type: ignore[index]
    assert node_cls is not None
    main_node = node_cls(main_group)

    engine = TinyEngine()
    ret = main_node.execute(engine)

    captured = capsys.readouterr()
    # input() prints the prompt, then write prints the value and newline
    assert captured.out == "17\n"
    assert ret == 0


def test_if_then_true_branch(capsys: pytest.CaptureFixture[str]) -> None:
    src = (
        """\
        int main(){
            int x := 5;
            if x > 0 then
                write "T"; write endl;
            end
            return 0;
        }
        """
    )
    ret, out = _run_main_and_capture(src, capsys)
    assert out == "T\n"
    assert ret == 0


def test_if_then_else_false_goes_else(capsys: pytest.CaptureFixture[str]) -> None:
    src = (
        """\
        int main(){
            int x := 0;
            if x > 0 then
                write "T";
            else
                write "F";
            end
            write endl;
            return 0;
        }
        """
    )
    ret, out = _run_main_and_capture(src, capsys)
    assert out == "F\n"
    assert ret == 0


def test_if_then_elseif_chain_matches_middle(capsys: pytest.CaptureFixture[str]) -> None:
    src = (
        """\
        int main(){
            int x := 2;
            if x = 1 then
                write "one";
            elseif x = 2 then
                write "two";
            elseif x = 3 then
                write "three";
            else
                write "other";
            end
            write endl;
            return 0;
        }
        """
    )
    ret, out = _run_main_and_capture(src, capsys)
    assert out == "two\n"
    assert ret == 0


def test_if_then_elseif_else_falls_to_else(capsys: pytest.CaptureFixture[str]) -> None:
    src = (
        """\
        int main(){
            int x := 99;
            if x = 1 then
                write "one";
            elseif x = 2 then
                write "two";
            elseif x = 3 then
                write "three";
            else
                write "else";
            end
            write endl;
            return 0;
        }
        """
    )
    ret, out = _run_main_and_capture(src, capsys)
    assert out == "else\n"
    assert ret == 0


def test_return_inside_repeat_exits_function(capsys: pytest.CaptureFixture[str]) -> None:
    # Return from within a repeat loop body should exit the function immediately
    src = (
        """\
        int main(){
            int i := 1;
            repeat
                write "before"; write endl;
                return 7;
                write "after"; write endl;
            until i = 0
            write "unreached"; write endl;
            return 0;
        }
        """
    )
    ret, out = _run_main_and_capture(src, capsys)
    # Expect only the text before the return and the function to return 7
    assert out == "before\n"
    assert ret == 7


def test_return_inside_if_then_branch(capsys: pytest.CaptureFixture[str]) -> None:
    # Return inside the 'then' branch should exit the function
    src = (
        """\
        int main(){
            int x := 1;
            if x = 1 then
                write "T"; write endl;
                return 1;
                write "after-then"; write endl;
            end
            write "unreached"; write endl;
            return 0;
        }
        """
    )
    ret, out = _run_main_and_capture(src, capsys)
    assert out == "T\n"
    assert ret == 1


def test_return_inside_if_elseif_branch(capsys: pytest.CaptureFixture[str]) -> None:
    # Return inside an elseif branch should exit the function
    src = (
        """\
        int main(){
            int x := 2;
            if x = 1 then
                write "one"; write endl;
            elseif x = 2 then
                write "two"; write endl;
                return 2;
                write "after-elseif"; write endl;
            else
                write "else"; write endl;
            end
            write "unreached"; write endl;
            return 0;
        }
        """
    )
    ret, out = _run_main_and_capture(src, capsys)
    assert out == "two\n"
    assert ret == 2


def test_return_inside_if_else_branch(capsys: pytest.CaptureFixture[str]) -> None:
    # Return inside the else branch should exit the function
    src = (
        """\
        int main(){
            int x := 99;
            if x = 1 then
                write "one"; write endl;
            elseif x = 2 then
                write "two"; write endl;
            else
                write "else"; write endl;
                return 3;
                write "after-else"; write endl;
            end
            write "unreached"; write endl;
            return 0;
        }
        """
    )
    ret, out = _run_main_and_capture(src, capsys)
    assert out == "else\n"
    assert ret == 3


def test_all_operations_arith_string_boolean(capsys: pytest.CaptureFixture[str]) -> None:
    """Exercise arithmetic, string, relational, and boolean operators.

    Verifies:
    - Arithmetic: +, -, *, /, unary +/-
    - String concatenation with '+'
    - Relational: <, >, =, <>, >=, <= (numeric and string comparisons)
    - Boolean: &&, || with correct precedence relative to relational
    """
    src = (
        """\
        int main(){
            /* arithmetic */
            write 1 + 2; write endl;         /* 3 */
            write 5 - 3; write endl;         /* 2 */
            write 2 * 4; write endl;         /* 8 */
            write 5 / 2; write endl;         /* 2.5 */
            write -5; write endl;            /* -5 */
            write +5; write endl;            /* 5 */

            /* string concatenation */
            write "Hello " + "World"; write endl;  /* Hello World */

            /* relational numeric */
            write 1 < 2; write endl;         /* True */
            write 3 > 4; write endl;         /* False */
            write 5 = 5; write endl;         /* True */
            write 5 <> 6; write endl;        /* True */
            write 3 >= 3; write endl;        /* True */
            write 2 <= 1; write endl;        /* False */

            /* relational string (lexicographic) */
            write "a" < "b"; write endl;     /* True */
            write "b" > "a"; write endl;     /* True */
            write "x" = "x"; write endl;     /* True */
            write "a" <> "b"; write endl;    /* True */
            write "a" <= "a"; write endl;    /* True */
            write "aa" >= "ab"; write endl;  /* False */

            /* boolean ops (with relational sub-exprs) */
            write 1 && 0; write endl;        /* False */
            write 1 || 0; write endl;        /* True */
            write 0 || 0; write endl;        /* False */
            write 1 < 2 && 2 < 3; write endl;  /* True */
            write 1 < 2 && 2 > 3 || 1; write endl;  /* True (and before or) */

            return 0;
        }
        """
    )

    ret, out = _run_main_and_capture(src, capsys)

    expected = (
        textwrap.dedent(
        """\
        3
        2
        8
        2.5
        -5
        5
        Hello World
        True
        False
        True
        True
        True
        False
        True
        True
        True
        True
        True
        False
        False
        True
        False
        True
        True
        """
        )
    )
    # Normalize potential trailing spaces/newlines
    assert out == expected
    assert ret == 0
