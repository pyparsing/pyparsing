# -*- coding: utf-8 -*-
import sys
from itertools import filterfalse

# unicode.py

class _lazyclassproperty:
    def __init__(self, fn):
        self.fn = fn
        self.__doc__ = fn.__doc__
        self.__name__ = fn.__name__

    def __get__(self, obj, cls):
        if cls is None:
            cls = type(obj)
        if not hasattr(cls, '_intern') or any(cls._intern is getattr(superclass, '_intern', [])
                                              for superclass in cls.__mro__[1:]):
            cls._intern = {}
        attrname = self.fn.__name__
        if attrname not in cls._intern:
            cls._intern[attrname] = self.fn(cls)
        return cls._intern[attrname]


class unicode_set:
    """
    A set of Unicode characters, for language-specific strings for
    ``alphas``, ``nums``, ``alphanums``, and ``printables``.
    A unicode_set is defined by a list of ranges in the Unicode character
    set, in a class attribute ``_ranges``, such as::

        _ranges = [(0x0020, 0x007e), (0x00a0, 0x00ff),]

    A unicode set can also be defined using multiple inheritance of other unicode sets::

        class CJK(Chinese, Japanese, Korean):
            pass
    """
    _ranges = []

    @classmethod
    def _get_chars_for_ranges(cls):
        ret = []
        for cc in cls.__mro__:
            if cc is unicode_set:
                break
            for rr in cc._ranges:
                ret.extend(range(rr[0], rr[-1] + 1))
        return [chr(c) for c in sorted(set(ret))]

    @_lazyclassproperty
    def printables(cls):
        "all non-whitespace characters in this range"
        return ''.join(filterfalse(str.isspace, cls._get_chars_for_ranges()))

    @_lazyclassproperty
    def alphas(cls):
        "all alphabetic characters in this range"
        return ''.join(filter(str.isalpha, cls._get_chars_for_ranges()))

    @_lazyclassproperty
    def nums(cls):
        "all numeric digit characters in this range"
        return ''.join(filter(str.isdigit, cls._get_chars_for_ranges()))

    @_lazyclassproperty
    def alphanums(cls):
        "all alphanumeric characters in this range"
        return cls.alphas + cls.nums


class pyparsing_unicode(unicode_set):
    """
    A namespace class for defining common language unicode_sets.
    """
    _ranges = [(32, sys.maxunicode)]

    class Latin1(unicode_set):
        "Unicode set for Latin-1 Unicode Character Range"
        _ranges = [(0x0020, 0x007e), (0x00a0, 0x00ff),]

    class LatinA(unicode_set):
        "Unicode set for Latin-A Unicode Character Range"
        _ranges = [(0x0100, 0x017f),]

    class LatinB(unicode_set):
        "Unicode set for Latin-B Unicode Character Range"
        _ranges = [(0x0180, 0x024f),]

    class Greek(unicode_set):
        "Unicode set for Greek Unicode Character Ranges"
        _ranges = [
            (0x0370, 0x03ff), (0x1f00, 0x1f15), (0x1f18, 0x1f1d), (0x1f20, 0x1f45), (0x1f48, 0x1f4d),
            (0x1f50, 0x1f57), (0x1f59,), (0x1f5b,), (0x1f5d,), (0x1f5f, 0x1f7d), (0x1f80, 0x1fb4), (0x1fb6, 0x1fc4),
            (0x1fc6, 0x1fd3), (0x1fd6, 0x1fdb), (0x1fdd, 0x1fef), (0x1ff2, 0x1ff4), (0x1ff6, 0x1ffe),
        ]

    class Cyrillic(unicode_set):
        "Unicode set for Cyrillic Unicode Character Range"
        _ranges = [(0x0400, 0x04ff)]

    class Chinese(unicode_set):
        "Unicode set for Chinese Unicode Character Range"
        _ranges = [(0x4e00, 0x9fff), (0x3000, 0x303f),]

    class Japanese(unicode_set):
        "Unicode set for Japanese Unicode Character Range, combining Kanji, Hiragana, and Katakana ranges"
        _ranges = []

        class Kanji(unicode_set):
            "Unicode set for Kanji Unicode Character Range"
            _ranges = [(0x4E00, 0x9Fbf), (0x3000, 0x303f),]

        class Hiragana(unicode_set):
            "Unicode set for Hiragana Unicode Character Range"
            _ranges = [(0x3040, 0x309f),]

        class Katakana(unicode_set):
            "Unicode set for Katakana  Unicode Character Range"
            _ranges = [(0x30a0, 0x30ff),]

    class Korean(unicode_set):
        "Unicode set for Korean Unicode Character Range"
        _ranges = [(0xac00, 0xd7af), (0x1100, 0x11ff), (0x3130, 0x318f), (0xa960, 0xa97f), (0xd7b0, 0xd7ff), (0x3000, 0x303f),]

    class CJK(Chinese, Japanese, Korean):
        "Unicode set for combined Chinese, Japanese, and Korean (CJK) Unicode Character Range"
        pass

    class Thai(unicode_set):
        "Unicode set for Thai Unicode Character Range"
        _ranges = [(0x0e01, 0x0e3a), (0x0e3f, 0x0e5b),]

    class Arabic(unicode_set):
        "Unicode set for Arabic Unicode Character Range"
        _ranges = [(0x0600, 0x061b), (0x061e, 0x06ff), (0x0700, 0x077f),]

    class Hebrew(unicode_set):
        "Unicode set for Hebrew Unicode Character Range"
        _ranges = [(0x0590, 0x05ff),]

    class Devanagari(unicode_set):
        "Unicode set for Devanagari Unicode Character Range"
        _ranges = [(0x0900, 0x097f), (0xa8e0, 0xa8ff)]

pyparsing_unicode.Japanese._ranges = (pyparsing_unicode.Japanese.Kanji._ranges
                                      + pyparsing_unicode.Japanese.Hiragana._ranges
                                      + pyparsing_unicode.Japanese.Katakana._ranges)

# define ranges in language character sets
pyparsing_unicode.العربية = pyparsing_unicode.Arabic
pyparsing_unicode.中文 = pyparsing_unicode.Chinese
pyparsing_unicode.кириллица = pyparsing_unicode.Cyrillic
pyparsing_unicode.Ελληνικά = pyparsing_unicode.Greek
pyparsing_unicode.עִברִית = pyparsing_unicode.Hebrew
pyparsing_unicode.日本語 = pyparsing_unicode.Japanese
pyparsing_unicode.Japanese.漢字 = pyparsing_unicode.Japanese.Kanji
pyparsing_unicode.Japanese.カタカナ = pyparsing_unicode.Japanese.Katakana
pyparsing_unicode.Japanese.ひらがな = pyparsing_unicode.Japanese.Hiragana
pyparsing_unicode.한국어 = pyparsing_unicode.Korean
pyparsing_unicode.ไทย = pyparsing_unicode.Thai
pyparsing_unicode.देवनागरी = pyparsing_unicode.Devanagari
