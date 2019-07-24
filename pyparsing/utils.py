import sys


try:
    # Python 3
    from itertools import filterfalse
except ImportError:
    from itertools import ifilterfalse as filterfalse

try:
    from _thread import RLock
except ImportError:
    from threading import RLock

try:
    # Python 3
    from collections.abc import Iterable
    from collections.abc import MutableMapping, Mapping
except ImportError:
    # Python 2.7
    from collections import Iterable
    from collections import MutableMapping, Mapping

try:
    from collections import OrderedDict as _OrderedDict
except ImportError:
    try:
        from ordereddict import OrderedDict as _OrderedDict
    except ImportError:
        _OrderedDict = None

try:
    from types import SimpleNamespace
except ImportError:
    class SimpleNamespace: pass

system_version = tuple(sys.version_info)[:3]
PY_3 = system_version[0] == 3
if PY_3:
    _MAX_INT = sys.maxsize
    basestring = str
    unichr = chr
    unicode = str
    _ustr = str

    # build list of single arg builtins, that can be used as parse actions
    singleArgBuiltins = [sum, len, sorted, reversed, list, tuple, set, any, all, min, max]

else:
    _MAX_INT = sys.maxint
    range = xrange
    from __builtin__ import unicode

    def _ustr(obj):
        """Drop-in replacement for str(obj) that tries to be Unicode
        friendly. It first tries str(obj). If that fails with
        a UnicodeEncodeError, then it tries unicode(obj). It then
        < returns the unicode object | encodes it with the default
        encoding | ... >.
        """
        if isinstance(obj, unicode):
            return obj

        try:
            # If this works, then _ustr(obj) has the same behaviour as str(obj), so
            # it won't break any existing code.
            return str(obj)

        except UnicodeEncodeError:
            # Else encode it
            ret = unicode(obj).encode(sys.getdefaultencoding(), 'xmlcharrefreplace')
            xmlcharref = Regex(r'&#\d+;')
            xmlcharref.setParseAction(lambda t: '\\u' + hex(int(t[0][2:-1]))[2:])
            return xmlcharref.transformString(ret)

    # build list of single arg builtins, tolerant of Python version, that can be used as parse actions
    singleArgBuiltins = []
    import __builtin__

    for fname in "sum len sorted reversed list tuple set any all min max".split():
        try:
            singleArgBuiltins.append(getattr(__builtin__, fname))
        except AttributeError:
            continue

_generatorType = type((y for y in range(1)))


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
    if nextCR >= 0:
        return strg[lastCR + 1:nextCR]
    else:
        return strg[lastCR + 1:]
