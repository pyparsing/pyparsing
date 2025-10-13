import pyparsing as pp
import pytest

from examples.tiny.tiny_parser import parse_tiny


def test_parse_assign_read_write():
    src = "read x; y := 42; write y"
    res = parse_tiny(src)
    # program holds a list of statements under 'stmts'
    assert "program" in res
    stmts = res.program.stmts
    assert len(stmts) == 3
    assert stmts[0].type == "read_stmt"
    assert stmts[1].type == "assign_stmt"
    assert stmts[1].target.id == "y"
    assert stmts[2].type == "write_stmt"


def test_parse_if_then_else():
    src = "if x < 10 then y := y + 1; write y else read x; write x end"
    res = parse_tiny(src)
    ifres = res.program.stmts[0]
    assert ifres.type == "if_stmt"
    assert hasattr(ifres, "cond")
    assert len(ifres.then) == 2
    else_len = len(ifres["else"]) if "else" in ifres else 0
    assert else_len == 2


def test_repeat_until_with_comment():
    src = "repeat {loop} x := x - 1; write x until x = 0"
    res = parse_tiny(src)
    rpt = res.program.stmts[0]
    assert rpt.type == "repeat_stmt"
    assert len(rpt.body) == 2
    # condition contains a relop
    assert rpt.cond[0].op == "="


def test_parse_all_required():
    # extra trailing garbage should fail when parse_all=True
    with pytest.raises(pp.ParseException):
        parse_tiny("read x $$$", parse_all=True)
