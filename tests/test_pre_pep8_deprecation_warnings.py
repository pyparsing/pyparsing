import pytest
import warnings

from pyparsing import Word, nums, ParserElement


def test_parseString_emits_DeprecationWarning_simple():
    # Using deprecated camelCase API should emit DeprecationWarning
    parser = Word(nums)
    with pytest.warns(DeprecationWarning, match="'parseString' deprecated - use 'parse_string'"):
        result = parser.parseString("12345")
        assert result.as_list() == ["12345"]


def test_parseString_emits_DeprecationWarning_with_parseAll_kwarg():
    # Ensure warning is also emitted when using kwargs
    parser = Word(nums)
    with pytest.warns(DeprecationWarning, match="'parseString' deprecated - use 'parse_string'"):
        result = parser.parseString("67890", parseAll=True)
        assert result.as_list() == ["67890"]


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
