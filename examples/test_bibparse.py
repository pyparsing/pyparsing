""" Test for bibparse grammar """

from os.path import join as pjoin, dirname

from pyparsing import ParseException
from btpyparse import Macro
import btpyparse as bp

from nose.tools import assert_true, assert_false, assert_equal, assert_raises


def test_names():
    # check various types of names
    # All names can contains alphas, but not some special chars
    bad_chars = '"#%\'(),={}'
    for name_type, dig1f in ((bp.macro_def, False),
                             (bp.field_name, False),
                             (bp.entry_type, False),
                             (bp.cite_key, True)):
        if dig1f: # can start with digit
            assert_equal(name_type.parseString('2t')[0], '2t')
        else:
            assert_raises(ParseException, name_type.parseString, '2t')
        # All of the names cannot contain some characters
        for char in bad_chars:
            assert_raises(ParseException, name_type.parseString, char)
        # standard strings all OK
        assert_equal(name_type.parseString('simple_test')[0], 'simple_test')
    # Test macro ref
    mr = bp.macro_ref
    # can't start with digit
    assert_raises(ParseException, mr.parseString, '2t')
    for char in bad_chars:
        assert_raises(ParseException, mr.parseString, char)
    assert_equal(mr.parseString('simple_test')[0].name, 'simple_test')


def test_numbers():
    assert_equal(bp.number.parseString('1066')[0], '1066')
    assert_equal(bp.number.parseString('0')[0], '0')
    assert_raises(ParseException, bp.number.parseString, '-4')
    assert_raises(ParseException, bp.number.parseString, '+4')
    assert_raises(ParseException, bp.number.parseString, '.4')
    # something point something leaves a trailing .4 unmatched
    assert_equal(bp.number.parseString('0.4')[0], '0')


def test_parse_string():
    # test string building blocks
    assert_equal(bp.chars_no_quotecurly.parseString('x')[0], 'x')
    assert_equal(bp.chars_no_quotecurly.parseString("a string")[0], 'a string')
    assert_equal(bp.chars_no_quotecurly.parseString('a "string')[0], 'a ')
    assert_equal(bp.chars_no_curly.parseString('x')[0], 'x')
    assert_equal(bp.chars_no_curly.parseString("a string")[0], 'a string')
    assert_equal(bp.chars_no_curly.parseString('a {string')[0], 'a ')
    assert_equal(bp.chars_no_curly.parseString('a }string')[0], 'a ')
    # test more general strings together
    for obj in (bp.curly_string, bp.string, bp.field_value):
        assert_equal(obj.parseString('{}').asList(), [])
        assert_equal(obj.parseString('{a "string}')[0], 'a "string')
        assert_equal(obj.parseString('{a {nested} string}').asList(),
                    ['a ', ['nested'], ' string'])
        assert_equal(obj.parseString('{a {double {nested}} string}').asList(),
                    ['a ', ['double ', ['nested']], ' string'])
    for obj in (bp.quoted_string, bp.string, bp.field_value):
        assert_equal(obj.parseString('""').asList(), [])
        assert_equal(obj.parseString('"a string"')[0], 'a string')
        assert_equal(obj.parseString('"a {nested} string"').asList(),
                    ['a ', ['nested'], ' string'])
        assert_equal(obj.parseString('"a {double {nested}} string"').asList(),
                    ['a ', ['double ', ['nested']], ' string'])
    # check macro def in string
    assert_equal(bp.string.parseString('someascii')[0], Macro('someascii'))
    assert_raises(ParseException, bp.string.parseString, '%#= validstring')
    # check number in string
    assert_equal(bp.string.parseString('1994')[0], '1994')


def test_parse_field():
    # test field value - hashes included
    fv = bp.field_value
    # Macro
    assert_equal(fv.parseString('aname')[0], Macro('aname'))
    assert_equal(fv.parseString('ANAME')[0], Macro('aname'))
    # String and macro
    assert_equal(fv.parseString('aname # "some string"').asList(),
                 [Macro('aname'), 'some string'])
    # Nested string
    assert_equal(fv.parseString('aname # {some {string}}').asList(),
                 [Macro('aname'), 'some ', ['string']])
    # String and number
    assert_equal(fv.parseString('"a string" # 1994').asList(),
                 ['a string', '1994'])
    # String and number and macro
    assert_equal(fv.parseString('"a string" # 1994 # a_macro').asList(),
                 ['a string', '1994', Macro('a_macro')])


def test_comments():
    res = bp.comment.parseString('@Comment{about something}')
    assert_equal(res.asList(), ['comment', '{about something}'])
    assert_equal(
        bp.comment.parseString('@COMMENT{about something').asList(),
        ['comment', '{about something'])
    assert_equal(
        bp.comment.parseString('@comment(about something').asList(),
        ['comment', '(about something'])
    assert_equal(
        bp.comment.parseString('@COMment about something').asList(),
        ['comment', ' about something'])
    assert_raises(ParseException, bp.comment.parseString,
                  '@commentabout something')
    assert_raises(ParseException, bp.comment.parseString,
                  '@comment+about something')
    assert_raises(ParseException, bp.comment.parseString,
                  '@comment"about something')


def test_preamble():
    res = bp.preamble.parseString('@preamble{"about something"}')
    assert_equal(res.asList(), ['preamble', 'about something'])
    assert_equal(bp.preamble.parseString(
        '@PREamble{{about something}}').asList(),
        ['preamble', 'about something'])
    assert_equal(bp.preamble.parseString("""@PREamble{
        {about something}
    }""").asList(),
        ['preamble', 'about something'])


def test_macro():
    res = bp.macro.parseString('@string{ANAME = "about something"}')
    assert_equal(res.asList(), ['string', 'aname', 'about something'])
    assert_equal(
        bp.macro.parseString('@string{aname = {about something}}').asList(),
        ['string', 'aname', 'about something'])


def test_entry():
    txt = """@some_entry{akey, aname = "about something",
    another={something else}}"""
    res = bp.entry.parseString(txt)
    assert_equal(res.asList(),
                 ['some_entry', 'akey',
                  ['aname', 'about something'], ['another', 'something else']])
    # Case conversion
    txt = """@SOME_ENTRY{akey, ANAME = "about something",
    another={something else}}"""
    res = bp.entry.parseString(txt)
    assert_equal(res.asList(),
                 ['some_entry', 'akey',
                  ['aname', 'about something'], ['another', 'something else']])


def test_bibfile():
    txt = """@some_entry{akey, aname = "about something",
    another={something else}}"""
    res = bp.bibfile.parseString(txt)
    assert_equal(res.asList(),
                 [['some_entry', 'akey',
                   ['aname', 'about something'],
                   ['another', 'something else']]])


def test_bib1():
    # First pass whole bib-like tests
    txt = """
Some introductory text
(implicit comment)

    @ARTICLE{Brett2002marsbar,
  author = {Matthew Brett and Jean-Luc Anton and Romain Valabregue and Jean-Baptise
            Poline},
  title = {{Region of interest analysis using an SPM toolbox}},
  journal = {Neuroimage},
  year = {2002},
  volume = {16},
  pages = {1140--1141},
  number = {2}
}

@some_entry{akey, aname = "about something",
another={something else}}
"""
    res = bp.bibfile.parseString(txt)
    assert_equal(len(res), 3)
    res2 = bp.parse_str(txt)
    assert_equal(res.asList(), res2.asList())
    res3 = [r.asList()[0] for r, start, end in bp.definitions.scanString(txt)]
    assert_equal(res.asList(), res3)


if __name__ == '__main__':
    import nose
    nose.main()
