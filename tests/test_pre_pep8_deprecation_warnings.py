import pytest
import warnings

from pyparsing import Word, nums, ParserElement, original_text_for, sgl_quoted_string


def test_parseString_emits_DeprecationWarning_simple():
    # Using deprecated camelCase API should emit DeprecationWarning
    parser = Word(nums)
    with pytest.warns(DeprecationWarning, match="'parseString' deprecated - use 'parse_string'"):
        result = parser.parseString("12345")
        assert result.as_list() == ["12345"]


def test_parse_string_parseAll_kwarg_emits_DeprecationWarning():
    # Using parse_string with deprecated 'parseAll' kwarg should warn
    parser = Word(nums)
    with pytest.warns(DeprecationWarning, match="'parseAll' argument is deprecated, use 'parse_all'"):
        result = parser.parse_string("13579", parseAll=True)
        assert result.as_list() == ["13579"]


def test_parse_string_does_not_warn():
    # Control test: new PEP8 API should not warn
    parser = Word(nums)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        result = parser.parse_string("2468")
        assert result.as_list() == ["2468"]
    # No DeprecationWarning should be captured
    assert not any(issubclass(w.category, DeprecationWarning) for w in rec)


def test_enablePackrat_emits_DeprecationWarning_and_cleanup():
    # Record initial packrat state; restore it after test completes
    initially_enabled = getattr(ParserElement, "_packratEnabled", False)
    try:
        # Deprecated classmethod should warn
        with pytest.warns(DeprecationWarning, match="'enablePackrat' deprecated - use 'enable_packrat'"):
            ParserElement.enablePackrat()
    finally:
        # Only disable if it was not initially enabled
        if not initially_enabled:
            ParserElement.disable_memoization()


def test_setResultsName_emits_DeprecationWarning():
    parser = Word(nums)
    with pytest.warns(DeprecationWarning, match="'setResultsName' deprecated - use 'set_results_name'"):
        p2 = parser.setResultsName("value")
        assert p2 is not parser  # setResultsName returns a new ParserElement (copy)


def test_setBreak_emits_DeprecationWarning():
    parser = Word(nums)
    with pytest.warns(DeprecationWarning, match="'setBreak' deprecated - use 'set_break'"):
        parser.setBreak()


def test_setParseAction_emits_DeprecationWarning():
    parser = Word(nums)
    def as_int(t):
        return int(t[0])
    with pytest.warns(DeprecationWarning, match="'setParseAction' deprecated - use 'set_parse_action'"):
        parser.setParseAction(as_int)
    # ensure it still works
    assert parser.parse_string("42")[0] == 42


def test_addParseAction_emits_DeprecationWarning():
    parser = Word(nums)
    with pytest.warns(DeprecationWarning, match="'addParseAction' deprecated - use 'add_parse_action'"):
        parser.addParseAction(lambda t: t)
    assert parser.parse_string("7")[0] == "7"


def test_addCondition_emits_DeprecationWarning():
    parser = Word(nums)
    with pytest.warns(DeprecationWarning, match="'addCondition' deprecated - use 'add_condition'"):
        parser.addCondition(lambda t: True)
    assert parser.parse_string("123")[0] == "123"


def test_scanString_emits_DeprecationWarning():
    parser = Word(nums)
    with pytest.warns(DeprecationWarning, match="'scanString' deprecated - use 'scan_string'"):
        results = list(parser.scanString("abc 123 def 456"))
        assert results and all(str(t[0][0]).isdigit() for t in results)


def test_scan_string_maxMatches_kwarg_emits_DeprecationWarning():
    parser = Word(nums)
    with pytest.warns(DeprecationWarning, match="'maxMatches' argument is deprecated, use 'max_matches'"):
        results = list(parser.scan_string("1 2 3 4", maxMatches=2))
        assert len(results) == 2


def test_transformString_emits_DeprecationWarning():
    parser = Word(nums)
    parser.add_parse_action(lambda t: f"{t[0][::-1]}")
    with pytest.warns(DeprecationWarning, match="'transformString' deprecated - use 'transform_string'"):
        out = parser.transformString("abc 123 def")
        assert out == "abc 321 def"


def test_searchString_emits_DeprecationWarning():
    parser = Word(nums)
    with pytest.warns(DeprecationWarning, match="'searchString' deprecated - use 'search_string'"):
        res = parser.searchString("x 99 y")
        assert res.as_list() == [["99"]]


def test_setDebug_emits_DeprecationWarning():
    parser = Word(nums)
    with pytest.warns(DeprecationWarning, match="'setDebug' deprecated - use 'set_debug'"):
        parser.setDebug()


def test_setName_emits_DeprecationWarning():
    parser = Word(nums)
    with pytest.warns(DeprecationWarning, match="'setName' deprecated - use 'set_name'"):
        p2 = parser.setName("digits")
        assert p2 is parser
        assert str(p2) == "digits"


def test_runTests_emits_DeprecationWarning(capsys):
    parser = Word(nums)
    # Keep the test input minimal; capture stdout to avoid noisy output
    with pytest.warns(DeprecationWarning, match="'runTests' deprecated - use 'run_tests'"):
        parser.runTests("""
            123 -> ['123']
            ABC
        """, print_results=False)
    # ensure no exception and some output captured
    captured = capsys.readouterr()
    assert captured.out is not None


# --- helpers.py compatibility function aliases ---
from pyparsing import alphas
from pyparsing.helpers import (
    countedArray,
    matchPreviousLiteral,
    matchPreviousExpr,
    oneOf,
    dictOf,
    originalTextFor,
    nestedExpr,
    makeHTMLTags,
    makeXMLTags,
    replaceHTMLEntity,
    infixNotation,
    OpAssoc,
    common_html_entity,
)


def test_countedArray_emits_DeprecationWarning():
    # countedArray should warn and still work
    word = Word(alphas)
    with pytest.warns(DeprecationWarning, match="'countedArray' deprecated - use 'counted_array'"):
        expr = countedArray(word)
        res = expr.parse_string("2 ab cd ef")
        assert res.as_list() == ["ab", "cd"]


def test_matchPreviousLiteral_emits_DeprecationWarning():
    first = Word(nums)
    with pytest.warns(DeprecationWarning, match="'matchPreviousLiteral' deprecated - use 'match_previous_literal'"):
        second = matchPreviousLiteral(first)
        res = (first + ":" + second).parse_string("12:12")
        assert res.as_list() == ["12", ":", "12"]


def test_matchPreviousExpr_emits_DeprecationWarning():
    first = Word(alphas)
    with pytest.warns(DeprecationWarning, match="'matchPreviousExpr' deprecated - use 'match_previous_expr'"):
        second = matchPreviousExpr(first)
        res = (first + ":" + second).parse_string("ab:ab")
        assert res.as_list() == ["ab", ":", "ab"]


def test_oneOf_emits_DeprecationWarning():
    with pytest.warns(DeprecationWarning, match="'oneOf' deprecated - use 'one_of'"):
        expr = oneOf("red blue")
        assert expr.parse_string("blue")[0] == "blue"


def test_dictOf_emits_DeprecationWarning():
    key = Word(alphas)
    val = Word(nums)
    with pytest.warns(DeprecationWarning, match="'dictOf' deprecated - use 'dict_of'"):
        expr = dictOf(key, val)
        res = expr.parse_string("a 1 b 2")
        # expect list of pairs
        assert res.as_list() == [["a", "1"], ["b", "2"]]


def test_originalTextFor_emits_DeprecationWarning():
    inner = Word(alphas)
    with pytest.warns(DeprecationWarning, match="'originalTextFor' deprecated - use 'original_text_for'"):
        expr = originalTextFor(inner + "," + inner)
        res = expr.parse_string("ab,cd")
        assert res[0] == "ab,cd"


def test_nestedExpr_emits_DeprecationWarning():
    with pytest.warns(DeprecationWarning, match="'nestedExpr' deprecated - use 'nested_expr'"):
        expr = nestedExpr("(", ")", content=Word(alphas))
        # parses nested parenthesized expression
        res = expr.parse_string("(a(b)c)")
        assert res.as_list() == [["a", ["b"], "c"]]


def test_makeHTMLTags_emits_DeprecationWarning():
    with pytest.warns(DeprecationWarning, match="'makeHTMLTags' deprecated - use 'make_html_tags'"):
        open_tag, close_tag = makeHTMLTags("B")
        expr = original_text_for(open_tag + Word(alphas) + close_tag)
        assert expr.parse_string("<B>hi</B>").as_list() == ["<B>hi</B>"]


def test_makeXMLTags_emits_DeprecationWarning():
    with pytest.warns(DeprecationWarning, match="'makeXMLTags' deprecated - use 'make_xml_tags'"):
        open_tag, close_tag = makeXMLTags("tag")
        expr = original_text_for(open_tag + Word(alphas) + close_tag)
        assert expr.parse_string("<tag>ok</tag>").as_list() == ["<tag>ok</tag>"]


def test_replaceHTMLEntity_emits_DeprecationWarning():
    # use as a parse action on the common_html_entity expression
    with pytest.warns(DeprecationWarning, match="'replaceHTMLEntity' deprecated - use 'replace_html_entity'"):
        expr = common_html_entity.copy()
        expr.add_parse_action(replaceHTMLEntity)
        res = expr.parse_string("&amp;")
        assert res[0] == "&"  # original token
        # apply parse action returns replacement value; ensure parse action returned '&'
        # ParseResults will hold returned value as the sole token
        assert expr.parse_string("&amp;")[0] == "&"


def test_infixNotation_emits_DeprecationWarning():
    # simple arithmetic with '+' only
    integer = Word(nums).set_parse_action(lambda t: int(t[0]))
    with pytest.warns(DeprecationWarning, match="'infixNotation' deprecated - use 'infix_notation'"):
        expr = infixNotation(
            integer,
            [
                ('+', 2, OpAssoc.LEFT, lambda t: [sum(t[0][0::2])])
            ]
        )
        res = expr.parse_string("2+3+4", parse_all=True)
        # 2+3=5; 5+4=9
        assert res[0] == 9

# Additional tests for deprecated arguments in helpers.py (PEP8 functions accepting camelCase kwargs)
from pyparsing.helpers import (
    counted_array as counted_array_pep8,
    one_of as one_of_pep8,
    nested_expr as nested_expr_pep8,
)


def test_counted_array_intExpr_kwarg_emits_DeprecationWarning():
    # Provide custom int expression using deprecated 'intExpr' kwarg
    binary_constant = Word("01").set_parse_action(lambda t: int(t[0], 2))
    with pytest.warns(DeprecationWarning, match="'intExpr' argument is deprecated, use 'int_expr'"):
        expr = counted_array_pep8(Word("ab"), intExpr=binary_constant)
        # '10' (binary 2) -> parse two items
        res = expr.parse_string("10 ab ab ab")
        assert res.as_list() == ["ab", "ab"]


def test_one_of_useRegex_kwarg_emits_DeprecationWarning():
    with pytest.warns(DeprecationWarning, match="'useRegex' argument is deprecated, use 'use_regex'"):
        expr = one_of_pep8(["a", "aa"], useRegex=False)
        # Should still parse a and aa
        assert expr.parse_string("aa")[0] in {"a", "aa", "aa"}


def test_one_of_asKeyword_kwarg_emits_DeprecationWarning():
    with pytest.warns(DeprecationWarning, match="'asKeyword' argument is deprecated, use 'as_keyword'"):
        expr = one_of_pep8(["if", "in"], asKeyword=True)
        # Keyword behavior: word breaks required
        assert expr.search_string(" if ").as_list() == [["if"]]


def test_original_text_for_asString_kwarg_emits_DeprecationWarning():
    # Using original_text_for with deprecated 'asString' kwarg
    inner = Word(alphas) + "," + Word(alphas)
    with pytest.warns(DeprecationWarning, match="'asString' argument is deprecated, use 'as_string'"):
        expr = original_text_for(inner, asString=False)
        res = expr.parse_string("ab,cd")
        # Returns original matched text as sole token
        assert res[0] == "ab,cd"


def test_nested_expr_ignoreExpr_kwarg_emits_DeprecationWarning():
    # Disable default ignoring of quoted strings using deprecated 'ignoreExpr'
    with pytest.warns(DeprecationWarning, match="'ignoreExpr' argument is deprecated, use 'ignore_expr'"):
        expr = nested_expr_pep8("(", ")", content=Word(alphas), ignoreExpr=None)
        res = expr.parse_string("(a(b)c)")
        assert res.as_list() == [["a", ["b"], "c"]]


# --- actions.py compatibility function aliases ---
from pyparsing import quoted_string
from pyparsing.actions import (
    replaceWith,
    removeQuotes,
    withAttribute,
    withClass,
    matchOnlyAtCol,
)
from pyparsing.helpers import make_html_tags
from pyparsing.results import ParseResults


def test_replaceWith_emits_DeprecationWarning():
    # replaceWith should warn and still function as a parse action factory
    from pyparsing import Word, nums

    parser = Word(nums)
    with pytest.warns(DeprecationWarning, match="'replaceWith' deprecated - use 'replace_with'"):
        parser = parser.set_parse_action(replaceWith(0))
    assert parser.parse_string("123").as_list() == [0]


def test_removeQuotes_emits_DeprecationWarning():
    # removeQuotes should warn and strip quotes from quoted_string
    from pyparsing import Regex
    qs = Regex(r"'[^']*'")
    with pytest.warns(DeprecationWarning, match="'removeQuotes' deprecated - use 'remove_quotes'"):
        parser = qs.set_parse_action(removeQuotes)
        res = parser.parse_string("'abc'")
    assert res[0] == "abc"


def test_withAttribute_emits_DeprecationWarning():
    # withAttribute should warn and validate attribute presence/value
    div, div_end = make_html_tags("div")
    with pytest.warns(DeprecationWarning, match="'withAttribute' deprecated - use 'with_attribute'"):
        start = div().set_parse_action(withAttribute(type="grid"))
    # Parse succeeds when attribute matches
    res = start.parse_string('<div type="grid">')
    assert res.type == "grid"


def test_withClass_emits_DeprecationWarning():
    div, _ = make_html_tags("div")
    with pytest.warns(DeprecationWarning, match="'withClass' deprecated - use 'with_class'"):
        start = div().set_parse_action(withClass("grid"))
    res = start.parse_string('<div class="grid">')
    assert res.tag == "div"
    assert res["class"] == "grid"


def test_matchOnlyAtCol_emits_DeprecationWarning():
    from pyparsing import Word, nums

    parser = Word(nums)
    with pytest.warns(DeprecationWarning, match="'matchOnlyAtCol' deprecated - use 'match_only_at_col'"):
        parser.add_parse_action(matchOnlyAtCol(3))
    # number starts at column 3 (1-based): two leading spaces
    res = parser.parse_string("  123")
    assert res[0] == "123"


def test_ParseResults_asList_kwarg_emits_DeprecationWarning():
    # Using deprecated 'asList' kwarg in ParseResults constructor should warn
    with pytest.warns(DeprecationWarning, match="'asList' argument is deprecated, use 'aslist'"):
        pr = ParseResults([["a", "b"]], "items", asList=True)
    # Ensure behavior: named entry is preserved as a nested ParseResults containing the list
    assert isinstance(pr["items"], ParseResults)
    assert pr["items"].as_list() == ["a", "b"]


# --- common.py compatibility methods (deprecated camelCase) ---
import pyparsing as pp
from datetime import date, datetime as dt


def test_common_convertToInteger_emits_DeprecationWarning():
    # convertToInteger is a parse action alias; warning emitted when action runs
    parser = Word(nums).set_parse_action(pp.common.convertToInteger)
    with pytest.warns(DeprecationWarning, match="'convertToInteger' deprecated - use 'convert_to_integer'"):
        res = parser.parse_string("1234")
    assert res[0] == 1234


def test_common_convertToFloat_emits_DeprecationWarning():
    parser = Word("0123456789.").set_parse_action(pp.common.convertToFloat)
    with pytest.warns(DeprecationWarning, match="'convertToFloat' deprecated - use 'convert_to_float'"):
        res = parser.parse_string("3.14")
    assert isinstance(res[0], float)
    assert abs(res[0] - 3.14) < 1e-8


def test_common_convertToDate_emits_DeprecationWarning():
    # convertToDate is a factory; warning emitted when called
    with pytest.warns(DeprecationWarning, match="'convertToDate' deprecated - use 'convert_to_date'"):
        pa = pp.common.convertToDate()
    expr = pp.common.iso8601_date.copy().set_parse_action(pa)
    res = expr.parse_string("1999-12-31")
    assert res[0] == date(1999, 12, 31)


def test_common_convertToDatetime_emits_DeprecationWarning():
    with pytest.warns(DeprecationWarning, match="'convertToDatetime' deprecated - use 'convert_to_datetime'"):
        pa = pp.common.convertToDatetime()
    expr = pp.common.iso8601_datetime.copy().set_parse_action(pa)
    res = expr.parse_string("1999-12-31T23:59:59.999")
    assert res[0] == dt(1999, 12, 31, 23, 59, 59, 999000)


def test_common_stripHTMLTags_emits_DeprecationWarning():
    # Use stripHTMLTags as a parse action on some HTML content
    td, td_end = pp.helpers.make_html_tags("td")
    body = pp.SkipTo(td_end).set_parse_action(pp.common.stripHTMLTags)("body")
    expr = td + body + td_end
    with pytest.warns(DeprecationWarning, match="'stripHTMLTags' deprecated - use 'strip_html_tags'"):
        res = expr.parse_string('<td>Click <a href="https://example.com">here</a></td>')
    assert res.body == "Click here"


def test_common_upcaseTokens_emits_DeprecationWarning():
    parser = Word("abc").set_parse_action(pp.common.upcaseTokens)
    with pytest.warns(DeprecationWarning, match="'upcaseTokens' deprecated - use 'upcase_tokens'"):
        res = parser.parse_string("abca")
    assert res[0] == "ABCA"


def test_common_downcaseTokens_emits_DeprecationWarning():
    parser = Word("ABC").set_parse_action(pp.common.downcaseTokens)
    with pytest.warns(DeprecationWarning, match="'downcaseTokens' deprecated - use 'downcase_tokens'"):
        res = parser.parse_string("ABCA")
    assert res[0] == "abca"
