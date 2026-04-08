import pyparsing as pp
# Regression tests for issue #633
def test_issue_633_recursive_whitespace_bug():
    first = pp.Char(pp.nums)
    second = pp.match_previous_expr(first)
    expr = first + ":" + second
    expr.leave_whitespace(recursive=True)
    assert list(expr.scan_string("1:1"))
    assert not list(expr.scan_string("1:2"))
    assert not list(expr.scan_string("1:a"))

def test_issue_633_control_case():
    first = pp.Char(pp.nums)
    second = pp.match_previous_expr(first)
    expr = first + ":" + second

    assert list(expr.scan_string("1:1"))
    assert not list(expr.scan_string("1:2"))

def test_issue_633_recursive_false_still_works():
    first = pp.Char(pp.nums)
    second = pp.match_previous_expr(first)
    expr = first + ":" + second
    expr.leave_whitespace(recursive=False)

    assert list(expr.scan_string("1:1"))
    assert not list(expr.scan_string("1:2"))