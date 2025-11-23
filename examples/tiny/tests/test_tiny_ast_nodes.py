from __future__ import annotations

import pytest

from examples.tiny.tiny_parser import parse_tiny
from examples.tiny.tiny_ast import TinyNode
from examples.tiny.tiny_engine import TinyEngine


def _run_main_and_capture(src: str, capsys: pytest.CaptureFixture[str]) -> tuple[int | None, str]:
    """Parse the Tiny program, build the main AST node, execute it, and capture stdout.

    Returns (return_value, stdout_text).
    """
    parsed = parse_tiny(src, parse_all=True)
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

    parsed = parse_tiny(src, parse_all=True)
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
