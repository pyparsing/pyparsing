# util.py
import warnings
import types
import collections

class __config_flags:
    """Internal class for defining compatibility and debugging flags"""
    _all_names = []
    _fixed_names = []
    _type_desc = "configuration"

    @classmethod
    def _set(cls, dname, value):
        if dname in cls._fixed_names:
            warnings.warn("{}.{} {} is {} and cannot be overridden".format(cls.__name__, dname, cls._type_desc,
                                                                           str(getattr(cls, dname)).upper()))
            return
        if dname in cls._all_names:
            setattr(cls, dname, value)
        else:
            raise ValueError("no such {} {!r}".format(cls._type_desc, dname))

    enable = classmethod(lambda cls, name: cls._set(name, True))
    disable = classmethod(lambda cls, name: cls._set(name, False))


def col (loc, strg):
    """Returns current column within a string, counting newlines as line separators.
   The first column is number 1.

   Note: the default parsing behavior is to expand tabs in the input string
   before starting the parsing process.  See
   :class:`ParserElement.parseString` for more
   information on parsing strings containing ``<TAB>`` s, and suggested
   methods to maintain a consistent view of the parsed string, the parse
   location, and line and column positions within the parsed string.
   """
    s = strg
    return 1 if 0 < loc < len(s) and s[loc-1] == '\n' else loc - s.rfind("\n", 0, loc)


def lineno(loc, strg):
    """Returns current line number within a string, counting newlines as line separators.
    The first line is number 1.

    Note - the default parsing behavior is to expand tabs in the input string
    before starting the parsing process.  See :class:`ParserElement.parseString`
    for more information on parsing strings containing ``<TAB>`` s, and
    suggested methods to maintain a consistent view of the parsed string, the
    parse location, and line and column positions within the parsed string.
    """
    return strg.count("\n", 0, loc) + 1


def line(loc, strg):
    """Returns the line of text containing loc within a string, counting newlines as line separators.
       """
    lastCR = strg.rfind("\n", 0, loc)
    nextCR = strg.find("\n", loc)
    return strg[lastCR + 1:nextCR] if nextCR >= 0 else strg[lastCR + 1:]


class _UnboundedCache:
    def __init__(self):
        cache = {}
        self.not_in_cache = not_in_cache = object()

        def get(self, key):
            return cache.get(key, not_in_cache)

        def set(self, key, value):
            cache[key] = value

        def clear(self):
            cache.clear()

        def cache_len(self):
            return len(cache)

        self.get = types.MethodType(get, self)
        self.set = types.MethodType(set, self)
        self.clear = types.MethodType(clear, self)
        self.__len__ = types.MethodType(cache_len, self)


class _FifoCache:
    def __init__(self, size):
        self.not_in_cache = not_in_cache = object()
        cache = collections.OrderedDict()

        def get(self, key):
            return cache.get(key, not_in_cache)

        def set(self, key, value):
            cache[key] = value
            while len(cache) > size:
                try:
                    cache.popitem(False)
                except KeyError:
                    pass

        def clear(self):
            cache.clear()

        def cache_len(self):
            return len(cache)

        self.get = types.MethodType(get, self)
        self.set = types.MethodType(set, self)
        self.clear = types.MethodType(clear, self)
        self.__len__ = types.MethodType(cache_len, self)

