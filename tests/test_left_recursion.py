import pytest

import pyparsing as pp


@pytest.fixture(params=[None, 1, 4])
def left_recursion(request):
    with pp.pyparsing_test.reset_pyparsing_context():
        pp.ParserElement.enable_left_recursion(
            cache_size_limit=request.param, force=True
        )
        try:
            yield
        finally:
            pp.ParserElement.disable_memoization()


@pytest.mark.parametrize("length", [1, 3, 5, 9])
def test_indirect_left_and_right_recursion(left_recursion, length):
    # Issue #451: introducing a Forward must not change the accepted language.
    indirect = pp.Forward()
    production = pp.Forward()
    production <<= indirect + "a" + indirect
    indirect <<= production | "b"

    direct = pp.Forward()
    direct <<= direct + "a" + direct | "b"

    text = "ba" * (length // 2) + "b"
    expected = direct.parse_string(text, parse_all=True).as_list()
    assert indirect.parse_string(text, parse_all=True).as_list() == expected


@pytest.mark.parametrize("depth", [1, 2, 3])
def test_indirect_left_recursion_grows_completed_matches(left_recursion, depth):
    expression = pp.Forward()
    production = expression
    for _ in range(depth):
        production = pp.Forward(production)
    expression <<= production + "a" | "b"

    for text in ["b", "ba", "baaaa"]:
        assert expression.parse_string(text, parse_all=True).as_list() == list(text)


def test_indirect_left_recursion_parse_actions(left_recursion):
    expression = pp.Forward()
    production = pp.Forward()
    number = pp.Word(pp.nums).set_parse_action(lambda t: int(t[0]))
    production <<= (expression + "+" + number).set_parse_action(lambda t: t[0] + t[2])
    expression <<= production | number

    assert expression.parse_string("1+2+3+4", parse_all=True).as_list() == [10]
    # Lookahead clears its positional tokens; the cached result must remain
    # intact for the real match that follows it.
    lookahead = pp.FollowedBy(expression) + expression
    assert lookahead.parse_string("2+3+4", parse_all=True).as_list() == [9]


def test_indirect_left_recursion_grouping(left_recursion):
    expression = pp.Forward()
    production = pp.Forward()
    production <<= pp.Group(expression) + "+" + pp.Word(pp.nums)
    expression <<= production | pp.Word(pp.nums)

    assert expression.parse_string("1+2+3", parse_all=True).as_list() == [
        [["1"], "+", "2"],
        "+",
        "3",
    ]


def test_indirect_left_recursion_scan(left_recursion):
    expression = pp.Forward()
    production = pp.Forward()
    production <<= expression + "a"
    expression <<= production | "b"

    assert [
        (tokens.as_list(), start, end)
        for tokens, start, end in expression.scan_string("!baaa?baa!")
    ] == [(["b", "a", "a", "a"], 1, 5), (["b", "a", "a"], 6, 9)]


def test_indirect_left_recursion_recovers_after_failure(left_recursion):
    expression = pp.Forward()
    production = pp.Forward()
    production <<= expression + "a"
    expression <<= production | "b"

    with pytest.raises(pp.ParseException):
        expression.parse_string("c", parse_all=True)
    assert expression.parse_string("baaa", parse_all=True).as_list() == list("baaa")


def test_indirect_left_recursion_fatal_action(left_recursion):
    expression = pp.Forward()
    production = pp.Forward()
    number = pp.Word(pp.nums).set_parse_action(lambda t: int(t[0]))
    production <<= (expression + "+" + number).add_condition(
        lambda t: t[-1] != 0, fatal=True, message="zero is not allowed"
    )
    expression <<= production | number

    with pytest.raises(pp.ParseFatalException, match="zero is not allowed"):
        expression.parse_string("1+0", parse_all=True)
    assert expression.parse_string("1+2", parse_all=True).as_list() == [1, "+", 2]
