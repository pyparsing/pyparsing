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
        'int main(){\n'
        '    int i := 42;\n'
        '    string s := "Hello";\n'
        '    write i; write " "; write s; write "\n";\n'
        '    return 0;\n'
        '}'
    )
    ret, out = _run_main_and_capture(src, capsys)
    assert out == "42 Hello\n"
    assert ret == 0


def test_assignment_updates_value(capsys: pytest.CaptureFixture[str]) -> None:
    src = (
        'int main(){\n'
        '    int x := 1;\n'
        '    x := x + 2;\n'
        '    write x; write "\n";\n'
        '    return 0;\n'
        '}'
    )
    ret, out = _run_main_and_capture(src, capsys)
    assert out == "3\n"
    assert ret == 0


def test_repeat_until_prints_n_times(capsys: pytest.CaptureFixture[str]) -> None:
    src = (
        'int main(){\n'
        '    int i := 5;\n'
        '    repeat\n'
        '        write "Hello World!\n";\n'
        '        i := i - 1;\n'
        '    until i = 0\n'
        '    return 0;\n'
        '}'
    )
    ret, out = _run_main_and_capture(src, capsys)
    lines = [ln for ln in out.splitlines() if ln.strip() != ""]
    assert len(lines) == 5
    assert all(ln == "Hello World!" for ln in lines)
    assert ret == 0


def test_read_statement_prompts_and_assigns(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    # Program declares x as int, reads it from input, and writes it back
    src = (
        'int main(){\n'
        '    int x;\n'
        '    read x;\n'
        '    write x; write "\n";\n'
        '    return 0;\n'
        '}'
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
    assert captured.out == "x? 17\n"
    assert ret == 0
