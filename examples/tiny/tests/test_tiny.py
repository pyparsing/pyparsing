import pyparsing as pp
import pytest

from examples.tiny.tiny_parser import parse_tiny


def test_parse_assign_read_write_in_main():
    src = "int main(){ read x; y := 42; write y; return 0; }"
    res = parse_tiny(src)
    assert "program" in res
    main = res.program.main
    stmts = main.body.stmts
    assert len(stmts) == 4
    assert stmts[0].type == "read_stmt"
    assert stmts[1].type == "assign_stmt"
    assert stmts[1].target == "y"
    assert stmts[2].type == "write_stmt"
    assert stmts[3].type == "return_stmt"


def test_parse_if_then_elseif_else():
    src = (
        "int main(){ if x < 10 then y := y + 1; write y; elseif x = 0 then write 0; else read x; end return 0; }"
    )
    res = parse_tiny(src)
    ifres = res.program.main.body.stmts[0]
    assert ifres.type == "if_stmt"
    assert hasattr(ifres, "cond")
    assert len(ifres.then) == 2
    # optional elseif list
    assert "elseif" in ifres
    # else block exists with 1 statement
    assert len(ifres["else"]) == 1


def test_repeat_until_with_c_style_comment():
    src = "int main(){ repeat /*loop*/ x := x - 1; write x; until x = 0 return 0; }"
    res = parse_tiny(src)
    rpt = res.program.main.body.stmts[0]
    assert rpt.type == "repeat_stmt"
    assert len(rpt.body) == 2
    # condition contains a relop; infix_notation flattens to [lhs, op, rhs]
    assert rpt.cond[1] == "="


def test_parse_all_required():
    # extra trailing garbage should fail when parse_all=True
    with pytest.raises(pp.ParseException):
        parse_tiny("int main(){ read x; return 0; } $$$")
