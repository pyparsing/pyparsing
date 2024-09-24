# util.py
import inspect
import warnings
import types
import itertools
from functools import lru_cache, wraps
from operator import itemgetter
from typing import Callable, Union, Iterable, TypeVar, cast

_bslash = chr(92)
C = TypeVar("C", bound=Callable)


class __config_flags:
    """Internal class for defining compatibility and debugging flags"""

    _all_names: list[str] = []
    _fixed_names: list[str] = []
    _type_desc = "configuration"

    @classmethod
    def _set(cls, dname, value):
        if dname in cls._fixed_names:
            warnings.warn(
                f"{cls.__name__}.{dname} {cls._type_desc} is {str(getattr(cls, dname)).upper()}"
                f" and cannot be overridden",
                stacklevel=3,
            )
            return
        if dname in cls._all_names:
            setattr(cls, dname, value)
        else:
            raise ValueError(f"no such {cls._type_desc} {dname!r}")

    enable = classmethod(lambda cls, name: cls._set(name, True))
    disable = classmethod(lambda cls, name: cls._set(name, False))


@lru_cache(maxsize=128)
def col(loc: int, strg: str) -> int:
    """
    Returns current column within a string, counting newlines as line separators.
    The first column is number 1.

    Note: the default parsing behavior is to expand tabs in the input string
    before starting the parsing process.  See
    :class:`ParserElement.parse_string` for more
    information on parsing strings containing ``<TAB>`` s, and suggested
    methods to maintain a consistent view of the parsed string, the parse
    location, and line and column positions within the parsed string.
    """
    s = strg
    return 1 if 0 < loc < len(s) and s[loc - 1] == "\n" else loc - s.rfind("\n", 0, loc)


@lru_cache(maxsize=128)
def lineno(loc: int, strg: str) -> int:
    """Returns current line number within a string, counting newlines as line separators.
    The first line is number 1.

    Note - the default parsing behavior is to expand tabs in the input string
    before starting the parsing process.  See :class:`ParserElement.parse_string`
    for more information on parsing strings containing ``<TAB>`` s, and
    suggested methods to maintain a consistent view of the parsed string, the
    parse location, and line and column positions within the parsed string.
    """
    return strg.count("\n", 0, loc) + 1


@lru_cache(maxsize=128)
def line(loc: int, strg: str) -> str:
    """
    Returns the line of text containing loc within a string, counting newlines as line separators.
    """
    last_cr = strg.rfind("\n", 0, loc)
    next_cr = strg.find("\n", loc)
    return strg[last_cr + 1 : next_cr] if next_cr >= 0 else strg[last_cr + 1 :]


class _UnboundedCache:
    def __init__(self):
        cache = {}
        cache_get = cache.get
        self.not_in_cache = not_in_cache = object()

        def get(_, key):
            return cache_get(key, not_in_cache)

        def set_(_, key, value):
            cache[key] = value

        def clear(_):
            cache.clear()

        self.size = None
        self.get = types.MethodType(get, self)
        self.set = types.MethodType(set_, self)
        self.clear = types.MethodType(clear, self)


class _FifoCache:
    def __init__(self, size):
        cache = {}
        self.size = size
        self.not_in_cache = not_in_cache = object()
        cache_get = cache.get
        cache_pop = cache.pop

        def get(_, key):
            return cache_get(key, not_in_cache)

        def set_(_, key, value):
            cache[key] = value
            while len(cache) > size:
                # pop oldest element in cache by getting the first key
                cache_pop(next(iter(cache)))

        def clear(_):
            cache.clear()

        self.get = types.MethodType(get, self)
        self.set = types.MethodType(set_, self)
        self.clear = types.MethodType(clear, self)


class LRUMemo:
    """
    A memoizing mapping that retains `capacity` deleted items

    The memo tracks retained items by their access order; once `capacity` items
    are retained, the least recently used item is discarded.
    """

    def __init__(self, capacity):
        self._capacity = capacity
        self._active = {}
        self._memory = {}

    def __getitem__(self, key):
        try:
            return self._active[key]
        except KeyError:
            self._memory[key] = self._memory.pop(key)
            return self._memory[key]

    def __setitem__(self, key, value):
        self._memory.pop(key, None)
        self._active[key] = value

    def __delitem__(self, key):
        try:
            value = self._active.pop(key)
        except KeyError:
            pass
        else:
            oldest_keys = list(self._memory)[: -(self._capacity + 1)]
            for key_to_delete in oldest_keys:
                self._memory.pop(key_to_delete)
            self._memory[key] = value

    def clear(self):
        self._active.clear()
        self._memory.clear()


class UnboundedMemo(dict):
    """
    A memoizing mapping that retains all deleted items
    """

    def __delitem__(self, key):
        pass


def _escape_regex_range_chars(s: str) -> str:
    # escape these chars: ^-[]
    for c in r"\^-[]":
        s = s.replace(c, _bslash + c)
    s = s.replace("\n", r"\n")
    s = s.replace("\t", r"\t")
    return str(s)


def _collapse_string_to_ranges(
    s: Union[str, Iterable[str]], re_escape: bool = True
) -> str:

    # Developer notes:
    # - Do not optimize this code assuming that the given input string
    #   or internal lists will be short (such as in loading generators into
    #   lists to make it easier to find the last element); this method is also
    #   used to generate regex ranges for character sets in the pyparsing.unicode
    #   classes, and these can be _very_ long strings

    def is_consecutive(c):
        c_int = ord(c)
        is_consecutive.prev, prev = c_int, is_consecutive.prev
        if c_int - prev > 1:
            is_consecutive.value = next(is_consecutive.counter)
        return is_consecutive.value

    is_consecutive.prev = 0  # type: ignore [attr-defined]
    is_consecutive.counter = itertools.count()  # type: ignore [attr-defined]
    is_consecutive.value = -1  # type: ignore [attr-defined]

    def escape_re_range_char(c):
        return "\\" + c if c in r"\^-][" else c

    def no_escape_re_range_char(c):
        return c

    if not re_escape:
        escape_re_range_char = no_escape_re_range_char

    ret = []

    # reduce input string to remove duplicates, and put in sorted order
    s = "".join(sorted(set(s)))
    if len(s) > 2:
        # find groups of characters that are consecutive (can be replaced
        # with "<first>-<last>")
        for _, chars in itertools.groupby(s, key=is_consecutive):
            first = last = next(chars)
            for c in chars:
                last = c
            if first == last:
                ret.append(escape_re_range_char(first))
            else:
                sep = "" if ord(last) == ord(first) + 1 else "-"
                ret.append(
                    f"{escape_re_range_char(first)}{sep}{escape_re_range_char(last)}"
                )
    else:
        # no need to list this (or these 2) chars with "-", just return as a list
        ret = [escape_re_range_char(c) for c in s]

    return "".join(ret)


def _flatten(ll: Iterable) -> list:
    ret = []
    to_visit = [*ll]
    while to_visit:
        i = to_visit.pop(0)
        if isinstance(i, Iterable) and not isinstance(i, str):
            to_visit[:0] = i
        else:
            ret.append(i)
    return ret


def make_compressed_re(
    word_list: Iterable[str], max_level: int = 2, _level: int = 1
) -> str:
    """
    Create a regular expression string from a list of words, collapsing by common
    prefixes and optional suffixes.

    Calls itself recursively to build nested sublists for each group of suffixes
    that have a shared prefix.
    """

    def get_suffixes_from_common_prefixes(namelist: list[str]):
        if len(namelist) > 1:
            for prefix, suffixes in itertools.groupby(namelist, key=lambda s: s[:1]):
                yield prefix, sorted([s[1:] for s in suffixes], key=len, reverse=True)
        else:
            yield namelist[0][0], [namelist[0][1:]]

    ret = []
    first = True
    for initial, suffixes in get_suffixes_from_common_prefixes(sorted(word_list)):
        if not first:
            ret.append("|")
        first = False

        trailing = ""
        if '' in suffixes:
            trailing = "?"
            suffixes.remove('')

        if len(suffixes) > 1:
            if all(len(s) == 1 for s in suffixes):
                ret.append(f"{initial}[{''.join(suffixes)}]{trailing}")
            else:
                if _level < max_level:
                    suffix_re = make_compressed_re(sorted(suffixes), max_level, _level + 1)
                    ret.append(f"{initial}({suffix_re}){trailing}")
                else:
                    ret.append(f"{initial}({'|'.join(suffixes)}){trailing}")
        else:
            if suffixes:
                if len(suffixes[0]) > 1 and trailing:
                    ret.append(f"{initial}({suffixes[0]}){trailing}")
                else:
                    ret.append(f"{initial}{suffixes[0]}{trailing}")
            else:
                ret.append(initial)
    return "".join(ret)


def replaced_by_pep8(compat_name: str, fn: C) -> C:
    # In a future version, uncomment the code in the internal _inner() functions
    # to begin emitting DeprecationWarnings.

    # Unwrap staticmethod/classmethod
    fn = getattr(fn, "__func__", fn)

    # (Presence of 'self' arg in signature is used by explain_exception() methods, so we take
    # some extra steps to add it if present in decorated function.)
    if ["self"] == list(inspect.signature(fn).parameters)[:1]:

        @wraps(fn)
        def _inner(self, *args, **kwargs):
            # warnings.warn(
            #     f"Deprecated - use {fn.__name__}", DeprecationWarning, stacklevel=2
            # )
            return fn(self, *args, **kwargs)

    else:

        @wraps(fn)
        def _inner(*args, **kwargs):
            # warnings.warn(
            #     f"Deprecated - use {fn.__name__}", DeprecationWarning, stacklevel=2
            # )
            return fn(*args, **kwargs)

    _inner.__doc__ = f"""Deprecated - use :class:`{fn.__name__}`"""
    _inner.__name__ = compat_name
    _inner.__annotations__ = fn.__annotations__
    if isinstance(fn, types.FunctionType):
        _inner.__kwdefaults__ = fn.__kwdefaults__  # type: ignore [attr-defined]
    elif isinstance(fn, type) and hasattr(fn, "__init__"):
        _inner.__kwdefaults__ = fn.__init__.__kwdefaults__  # type: ignore [misc,attr-defined]
    else:
        _inner.__kwdefaults__ = None  # type: ignore [attr-defined]
    _inner.__qualname__ = fn.__qualname__
    return cast(C, _inner)
