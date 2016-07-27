# module pyparsing.py
#
# Copyright (c) 2003-2015  Paul T. McGuire
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

__doc__ = \
"""
pyparsing module - Classes and methods to define and execute parsing grammars

The pyparsing module is an alternative approach to creating and executing simple grammars,
vs. the traditional lex/yacc approach, or the use of regular expressions.  With pyparsing, you
don't need to learn a new syntax for defining grammars or matching expressions - the parsing module
provides a library of classes that you use to construct the grammar directly in Python.

Here is a program to parse "Hello, World!" (or any greeting of the form C{"<salutation>, <addressee>!"})::

    from pyparsing import Word, alphas

    # define grammar of a greeting
    greet = Word( alphas ) + "," + Word( alphas ) + "!"

    hello = "Hello, World!"
    print (hello, "->", greet.parseString( hello ))

The program outputs the following::

    Hello, World! -> ['Hello', ',', 'World', '!']

The Python representation of the grammar is quite readable, owing to the self-explanatory
class names, and the use of '+', '|' and '^' operators.

The parsed results returned from C{parseString()} can be accessed as a nested list, a dictionary, or an
object with named attributes.

The pyparsing module handles some of the problems that are typically vexing when writing text parsers:
 - extra or missing whitespace (the above program will also handle "Hello,World!", "Hello  ,  World  !", etc.)
 - quoted strings
 - embedded comments
"""

__version__ = "2.1.6"
__versionTime__ = "27 Jul 2016 06:06 UTC"
__author__ = "Paul McGuire <ptmcg@users.sourceforge.net>"

import string
from weakref import ref as wkref
import copy
import sys
import warnings
import re
import sre_constants
import collections
import pprint
import traceback
from datetime import datetime

try:
    from _thread import RLock
except ImportError:
    from threading import RLock

#~ sys.stderr.write( "testing pyparsing module, version %s, %s\n" % (__version__,__versionTime__ ) )

__all__ = [
'And', 'CaselessKeyword', 'CaselessLiteral', 'CharsNotIn', 'Combine', 'Dict', 'Each', 'Empty',
'FollowedBy', 'Forward', 'GoToColumn', 'Group', 'Keyword', 'LineEnd', 'LineStart', 'Literal',
'MatchFirst', 'NoMatch', 'NotAny', 'OneOrMore', 'OnlyOnce', 'Optional', 'Or',
'ParseBaseException', 'ParseElementEnhance', 'ParseException', 'ParseExpression', 'ParseFatalException',
'ParseResults', 'ParseSyntaxException', 'ParserElement', 'QuotedString', 'RecursiveGrammarException',
'Regex', 'SkipTo', 'StringEnd', 'StringStart', 'Suppress', 'Token', 'TokenConverter', 
'White', 'Word', 'WordEnd', 'WordStart', 'ZeroOrMore',
'alphanums', 'alphas', 'alphas8bit', 'anyCloseTag', 'anyOpenTag', 'cStyleComment', 'col',
'commaSeparatedList', 'commonHTMLEntity', 'countedArray', 'cppStyleComment', 'dblQuotedString',
'dblSlashComment', 'delimitedList', 'dictOf', 'downcaseTokens', 'empty', 'hexnums',
'htmlComment', 'javaStyleComment', 'line', 'lineEnd', 'lineStart', 'lineno',
'makeHTMLTags', 'makeXMLTags', 'matchOnlyAtCol', 'matchPreviousExpr', 'matchPreviousLiteral',
'nestedExpr', 'nullDebugAction', 'nums', 'oneOf', 'opAssoc', 'operatorPrecedence', 'printables',
'punc8bit', 'pythonStyleComment', 'quotedString', 'removeQuotes', 'replaceHTMLEntity', 
'replaceWith', 'restOfLine', 'sglQuotedString', 'srange', 'stringEnd',
'stringStart', 'traceParseAction', 'unicodeString', 'upcaseTokens', 'withAttribute',
'indentedBlock', 'originalTextFor', 'ungroup', 'infixNotation','locatedExpr', 'withClass',
'tokenMap', 'pyparsing_common',
]

system_version = tuple(sys.version_info)[:3]
PY_3 = system_version[0] == 3
if PY_3:
    _MAX_INT = sys.maxsize
    basestring = str
    unichr = chr
    _ustr = str

    # build list of single arg builtins, that can be used as parse actions
    singleArgBuiltins = [sum, len, sorted, reversed, list, tuple, set, any, all, min, max]

else:
    _MAX_INT = sys.maxint
    range = xrange

    def _ustr(obj):
        """Drop-in replacement for str(obj) that tries to be Unicode friendly. It first tries
           str(obj). If that fails with a UnicodeEncodeError, then it tries unicode(obj). It
           then < returns the unicode object | encodes it with the default encoding | ... >.
        """
        if isinstance(obj,unicode):
            return obj

        try:
            # If this works, then _ustr(obj) has the same behaviour as str(obj), so
            # it won't break any existing code.
            return str(obj)

        except UnicodeEncodeError:
            # Else encode it
            ret = unicode(obj).encode(sys.getdefaultencoding(), 'xmlcharrefreplace')
            xmlcharref = Regex('&#\d+;')
            xmlcharref.setParseAction(lambda t: '\\u' + hex(int(t[0][2:-1]))[2:])
            return xmlcharref.transformString(ret)

    # build list of single arg builtins, tolerant of Python version, that can be used as parse actions
    singleArgBuiltins = []
    import __builtin__
    for fname in "sum len sorted reversed list tuple set any all min max".split():
        try:
            singleArgBuiltins.append(getattr(__builtin__,fname))
        except AttributeError:
            continue
            
_generatorType = type((y for y in range(1)))
 
def _xml_escape(data):
    """Escape &, <, >, ", ', etc. in a string of data."""

    # ampersand must be replaced first
    from_symbols = '&><"\''
    to_symbols = ('&'+s+';' for s in "amp gt lt quot apos".split())
    for from_,to_ in zip(from_symbols, to_symbols):
        data = data.replace(from_, to_)
    return data

class _Constants(object):
    pass

alphas     = string.ascii_uppercase + string.ascii_lowercase
nums       = "0123456789"
hexnums    = nums + "ABCDEFabcdef"
alphanums  = alphas + nums
_bslash    = chr(92)
printables = "".join(c for c in string.printable if c not in string.whitespace)

class ParseBaseException(Exception):
    """base exception class for all parsing runtime exceptions"""
    # Performance tuning: we construct a *lot* of these, so keep this
    # constructor as small and fast as possible
    def __init__( self, pstr, loc=0, msg=None, elem=None ):
        self.loc = loc
        if msg is None:
            self.msg = pstr
            self.pstr = ""
        else:
            self.msg = msg
            self.pstr = pstr
        self.parserElement = elem

    def __getattr__( self, aname ):
        """supported attributes by name are:
            - lineno - returns the line number of the exception text
            - col - returns the column number of the exception text
            - line - returns the line containing the exception text
        """
        if( aname == "lineno" ):
            return lineno( self.loc, self.pstr )
        elif( aname in ("col", "column") ):
            return col( self.loc, self.pstr )
        elif( aname == "line" ):
            return line( self.loc, self.pstr )
        else:
            raise AttributeError(aname)

    def __str__( self ):
        return "%s (at char %d), (line:%d, col:%d)" % \
                ( self.msg, self.loc, self.lineno, self.column )
    def __repr__( self ):
        return _ustr(self)
    def markInputline( self, markerString = ">!<" ):
        """Extracts the exception line from the input string, and marks
           the location of the exception with a special symbol.
        """
        line_str = self.line
        line_column = self.column - 1
        if markerString:
            line_str = "".join((line_str[:line_column],
                                markerString, line_str[line_column:]))
        return line_str.strip()
    def __dir__(self):
        return "lineno col line".split() + dir(type(self))

class ParseException(ParseBaseException):
    """exception thrown when parse expressions don't match class;
       supported attributes by name are:
        - lineno - returns the line number of the exception text
        - col - returns the column number of the exception text
        - line - returns the line containing the exception text
    """
    pass

class ParseFatalException(ParseBaseException):
    """user-throwable exception thrown when inconsistent parse content
       is found; stops all parsing immediately"""
    pass

class ParseSyntaxException(ParseFatalException):
    """just like C{L{ParseFatalException}}, but thrown internally when an
       C{L{ErrorStop<And._ErrorStop>}} ('-' operator) indicates that parsing is to stop immediately because
       an unbacktrackable syntax error has been found"""
    def __init__(self, pe):
        super(ParseSyntaxException, self).__init__(
                                    pe.pstr, pe.loc, pe.msg, pe.parserElement)

#~ class ReparseException(ParseBaseException):
    #~ """Experimental class - parse actions can raise this exception to cause
       #~ pyparsing to reparse the input string:
        #~ - with a modified input string, and/or
        #~ - with a modified start location
       #~ Set the values of the ReparseException in the constructor, and raise the
       #~ exception in a parse action to cause pyparsing to use the new string/location.
       #~ Setting the values as None causes no change to be made.
       #~ """
    #~ def __init_( self, newstring, restartLoc ):
        #~ self.newParseText = newstring
        #~ self.reparseLoc = restartLoc

class RecursiveGrammarException(Exception):
    """exception thrown by C{validate()} if the grammar could be improperly recursive"""
    def __init__( self, parseElementList ):
        self.parseElementTrace = parseElementList

    def __str__( self ):
        return "RecursiveGrammarException: %s" % self.parseElementTrace

class _ParseResultsWithOffset(object):
    def __init__(self,p1,p2):
        self.tup = (p1,p2)
    def __getitem__(self,i):
        return self.tup[i]
    def __repr__(self):
        return repr(self.tup)
    def setOffset(self,i):
        self.tup = (self.tup[0],i)

class ParseResults(object):
    """Structured parse results, to provide multiple means of access to the parsed data:
       - as a list (C{len(results)})
       - by list index (C{results[0], results[1]}, etc.)
       - by attribute (C{results.<resultsName>})
       """
    def __new__(cls, toklist=None, name=None, asList=True, modal=True ):
        if isinstance(toklist, cls):
            return toklist
        retobj = object.__new__(cls)
        retobj.__doinit = True
        return retobj

    # Performance tuning: we construct a *lot* of these, so keep this
    # constructor as small and fast as possible
    def __init__( self, toklist=None, name=None, asList=True, modal=True, isinstance=isinstance ):
        if self.__doinit:
            self.__doinit = False
            self.__name = None
            self.__parent = None
            self.__accumNames = {}
            self.__asList = asList
            self.__modal = modal
            if toklist is None:
                toklist = []
            if isinstance(toklist, list):
                self.__toklist = toklist[:]
            elif isinstance(toklist, _generatorType):
                self.__toklist = list(toklist)
            else:
                self.__toklist = [toklist]
            self.__tokdict = dict()

        if name is not None and name:
            if not modal:
                self.__accumNames[name] = 0
            if isinstance(name,int):
                name = _ustr(name) # will always return a str, but use _ustr for consistency
            self.__name = name
            if not (isinstance(toklist, (type(None), basestring, list)) and toklist in (None,'',[])):
                if isinstance(toklist,basestring):
                    toklist = [ toklist ]
                if asList:
                    if isinstance(toklist,ParseResults):
                        self[name] = _ParseResultsWithOffset(toklist.copy(),0)
                    else:
                        self[name] = _ParseResultsWithOffset(ParseResults(toklist[0]),0)
                    self[name].__name = name
                else:
                    try:
                        self[name] = toklist[0]
                    except (KeyError,TypeError,IndexError):
                        self[name] = toklist

    def __getitem__( self, i ):
        if isinstance( i, (int,slice) ):
            return self.__toklist[i]
        else:
            if i not in self.__accumNames:
                return self.__tokdict[i][-1][0]
            else:
                return ParseResults([ v[0] for v in self.__tokdict[i] ])

    def __setitem__( self, k, v, isinstance=isinstance ):
        if isinstance(v,_ParseResultsWithOffset):
            self.__tokdict[k] = self.__tokdict.get(k,list()) + [v]
            sub = v[0]
        elif isinstance(k,(int,slice)):
            self.__toklist[k] = v
            sub = v
        else:
            self.__tokdict[k] = self.__tokdict.get(k,list()) + [_ParseResultsWithOffset(v,0)]
            sub = v
        if isinstance(sub,ParseResults):
            sub.__parent = wkref(self)

    def __delitem__( self, i ):
        if isinstance(i,(int,slice)):
            mylen = len( self.__toklist )
            del self.__toklist[i]

            # convert int to slice
            if isinstance(i, int):
                if i < 0:
                    i += mylen
                i = slice(i, i+1)
            # get removed indices
            removed = list(range(*i.indices(mylen)))
            removed.reverse()
            # fixup indices in token dictionary
            #~ for name in self.__tokdict:
                #~ occurrences = self.__tokdict[name]
                #~ for j in removed:
                    #~ for k, (value, position) in enumerate(occurrences):
                        #~ occurrences[k] = _ParseResultsWithOffset(value, position - (position > j))
            for name,occurrences in self.__tokdict.items():
                for j in removed:
                    for k, (value, position) in enumerate(occurrences):
                        occurrences[k] = _ParseResultsWithOffset(value, position - (position > j))
        else:
            del self.__tokdict[i]

    def __contains__( self, k ):
        return k in self.__tokdict

    def __len__( self ): return len( self.__toklist )
    def __bool__(self): return ( not not self.__toklist )
    __nonzero__ = __bool__
    def __iter__( self ): return iter( self.__toklist )
    def __reversed__( self ): return iter( self.__toklist[::-1] )
    def _iterkeys( self ):
        if hasattr(self.__tokdict, "iterkeys"):
            return self.__tokdict.iterkeys()
        else:
            return iter(self.__tokdict)

    def _itervalues( self ):
        return (self[k] for k in self._iterkeys())
            
    def _iteritems( self ):
        return ((k, self[k]) for k in self._iterkeys())

    if PY_3:
        keys = _iterkeys       
        """Returns an iterator of all named result keys (Python 3.x only)."""

        values = _itervalues
        """Returns an iterator of all named result values (Python 3.x only)."""

        items = _iteritems
        """Returns an iterator of all named result key-value tuples (Python 3.x only)."""

    else:
        iterkeys = _iterkeys
        """Returns an iterator of all named result keys (Python 2.x only)."""

        itervalues = _itervalues
        """Returns an iterator of all named result values (Python 2.x only)."""

        iteritems = _iteritems
        """Returns an iterator of all named result key-value tuples (Python 2.x only)."""

        def keys( self ):
            """Returns all named result keys (as a list in Python 2.x, as an iterator in Python 3.x)."""
            return list(self.iterkeys())

        def values( self ):
            """Returns all named result values (as a list in Python 2.x, as an iterator in Python 3.x)."""
            return list(self.itervalues())
                
        def items( self ):
            """Returns all named result key-values (as a list of tuples in Python 2.x, as an iterator in Python 3.x)."""
            return list(self.iteritems())

    def haskeys( self ):
        """Since keys() returns an iterator, this method is helpful in bypassing
           code that looks for the existence of any defined results names."""
        return bool(self.__tokdict)
        
    def pop( self, *args, **kwargs):
        """Removes and returns item at specified index (default=last).
           Supports both list and dict semantics for pop(). If passed no
           argument or an integer argument, it will use list semantics
           and pop tokens from the list of parsed tokens. If passed a 
           non-integer argument (most likely a string), it will use dict
           semantics and pop the corresponding value from any defined 
           results names. A second default return value argument is 
           supported, just as in dict.pop()."""
        if not args:
            args = [-1]
        for k,v in kwargs.items():
            if k == 'default':
                args = (args[0], v)
            else:
                raise TypeError("pop() got an unexpected keyword argument '%s'" % k)
        if (isinstance(args[0], int) or 
                        len(args) == 1 or 
                        args[0] in self):
            index = args[0]
            ret = self[index]
            del self[index]
            return ret
        else:
            defaultvalue = args[1]
            return defaultvalue

    def get(self, key, defaultValue=None):
        """Returns named result matching the given key, or if there is no
           such name, then returns the given C{defaultValue} or C{None} if no
           C{defaultValue} is specified."""
        if key in self:
            return self[key]
        else:
            return defaultValue

    def insert( self, index, insStr ):
        """Inserts new element at location index in the list of parsed tokens."""
        self.__toklist.insert(index, insStr)
        # fixup indices in token dictionary
        #~ for name in self.__tokdict:
            #~ occurrences = self.__tokdict[name]
            #~ for k, (value, position) in enumerate(occurrences):
                #~ occurrences[k] = _ParseResultsWithOffset(value, position + (position > index))
        for name,occurrences in self.__tokdict.items():
            for k, (value, position) in enumerate(occurrences):
                occurrences[k] = _ParseResultsWithOffset(value, position + (position > index))

    def append( self, item ):
        """Add single element to end of ParseResults list of elements."""
        self.__toklist.append(item)

    def extend( self, itemseq ):
        """Add sequence of elements to end of ParseResults list of elements."""
        if isinstance(itemseq, ParseResults):
            self += itemseq
        else:
            self.__toklist.extend(itemseq)

    def clear( self ):
        """Clear all elements and results names."""
        del self.__toklist[:]
        self.__tokdict.clear()

    def __getattr__( self, name ):
        try:
            return self[name]
        except KeyError:
            return ""
            
        if name in self.__tokdict:
            if name not in self.__accumNames:
                return self.__tokdict[name][-1][0]
            else:
                return ParseResults([ v[0] for v in self.__tokdict[name] ])
        else:
            return ""

    def __add__( self, other ):
        ret = self.copy()
        ret += other
        return ret

    def __iadd__( self, other ):
        if other.__tokdict:
            offset = len(self.__toklist)
            addoffset = lambda a: offset if a<0 else a+offset
            otheritems = other.__tokdict.items()
            otherdictitems = [(k, _ParseResultsWithOffset(v[0],addoffset(v[1])) )
                                for (k,vlist) in otheritems for v in vlist]
            for k,v in otherdictitems:
                self[k] = v
                if isinstance(v[0],ParseResults):
                    v[0].__parent = wkref(self)
            
        self.__toklist += other.__toklist
        self.__accumNames.update( other.__accumNames )
        return self

    def __radd__(self, other):
        if isinstance(other,int) and other == 0:
            # useful for merging many ParseResults using sum() builtin
            return self.copy()
        else:
            # this may raise a TypeError - so be it
            return other + self
        
    def __repr__( self ):
        return "(%s, %s)" % ( repr( self.__toklist ), repr( self.__tokdict ) )

    def __str__( self ):
        return '[' + ', '.join(_ustr(i) if isinstance(i, ParseResults) else repr(i) for i in self.__toklist) + ']'

    def _asStringList( self, sep='' ):
        out = []
        for item in self.__toklist:
            if out and sep:
                out.append(sep)
            if isinstance( item, ParseResults ):
                out += item._asStringList()
            else:
                out.append( _ustr(item) )
        return out

    def asList( self ):
        """Returns the parse results as a nested list of matching tokens, all converted to strings."""
        return [res.asList() if isinstance(res,ParseResults) else res for res in self.__toklist]

    def asDict( self ):
        """Returns the named parse results as a nested dictionary."""
        if PY_3:
            item_fn = self.items
        else:
            item_fn = self.iteritems
            
        def toItem(obj):
            if isinstance(obj, ParseResults):
                if obj.haskeys():
                    return obj.asDict()
                else:
                    return [toItem(v) for v in obj]
            else:
                return obj
                
        return dict((k,toItem(v)) for k,v in item_fn())

    def copy( self ):
        """Returns a new copy of a C{ParseResults} object."""
        ret = ParseResults( self.__toklist )
        ret.__tokdict = self.__tokdict.copy()
        ret.__parent = self.__parent
        ret.__accumNames.update( self.__accumNames )
        ret.__name = self.__name
        return ret

    def asXML( self, doctag=None, namedItemsOnly=False, indent="", formatted=True ):
        """Returns the parse results as XML. Tags are created for tokens and lists that have defined results names."""
        nl = "\n"
        out = []
        namedItems = dict((v[1],k) for (k,vlist) in self.__tokdict.items()
                                                            for v in vlist)
        nextLevelIndent = indent + "  "

        # collapse out indents if formatting is not desired
        if not formatted:
            indent = ""
            nextLevelIndent = ""
            nl = ""

        selfTag = None
        if doctag is not None:
            selfTag = doctag
        else:
            if self.__name:
                selfTag = self.__name

        if not selfTag:
            if namedItemsOnly:
                return ""
            else:
                selfTag = "ITEM"

        out += [ nl, indent, "<", selfTag, ">" ]

        for i,res in enumerate(self.__toklist):
            if isinstance(res,ParseResults):
                if i in namedItems:
                    out += [ res.asXML(namedItems[i],
                                        namedItemsOnly and doctag is None,
                                        nextLevelIndent,
                                        formatted)]
                else:
                    out += [ res.asXML(None,
                                        namedItemsOnly and doctag is None,
                                        nextLevelIndent,
                                        formatted)]
            else:
                # individual token, see if there is a name for it
                resTag = None
                if i in namedItems:
                    resTag = namedItems[i]
                if not resTag:
                    if namedItemsOnly:
                        continue
                    else:
                        resTag = "ITEM"
                xmlBodyText = _xml_escape(_ustr(res))
                out += [ nl, nextLevelIndent, "<", resTag, ">",
                                                xmlBodyText,
                                                "</", resTag, ">" ]

        out += [ nl, indent, "</", selfTag, ">" ]
        return "".join(out)

    def __lookup(self,sub):
        for k,vlist in self.__tokdict.items():
            for v,loc in vlist:
                if sub is v:
                    return k
        return None

    def getName(self):
        """Returns the results name for this token expression."""
        if self.__name:
            return self.__name
        elif self.__parent:
            par = self.__parent()
            if par:
                return par.__lookup(self)
            else:
                return None
        elif (len(self) == 1 and
               len(self.__tokdict) == 1 and
               self.__tokdict.values()[0][0][1] in (0,-1)):
            return self.__tokdict.keys()[0]
        else:
            return None

    def dump(self,indent='',depth=0):
        """Diagnostic method for listing out the contents of a C{ParseResults}.
           Accepts an optional C{indent} argument so that this string can be embedded
           in a nested display of other data."""
        out = []
        NL = '\n'
        out.append( indent+_ustr(self.asList()) )
        if self.haskeys():
            items = sorted(self.items())
            for k,v in items:
                if out:
                    out.append(NL)
                out.append( "%s%s- %s: " % (indent,('  '*depth), k) )
                if isinstance(v,ParseResults):
                    if v:
                        out.append( v.dump(indent,depth+1) )
                    else:
                        out.append(_ustr(v))
                else:
                    out.append(_ustr(v))
        elif any(isinstance(vv,ParseResults) for vv in self):
            v = self
            for i,vv in enumerate(v):
                if isinstance(vv,ParseResults):
                    out.append("\n%s%s[%d]:\n%s%s%s" % (indent,('  '*(depth)),i,indent,('  '*(depth+1)),vv.dump(indent,depth+1) ))
                else:
                    out.append("\n%s%s[%d]:\n%s%s%s" % (indent,('  '*(depth)),i,indent,('  '*(depth+1)),_ustr(vv)))
            
        return "".join(out)

    def pprint(self, *args, **kwargs):
        """Pretty-printer for parsed results as a list, using the C{pprint} module.
           Accepts additional positional or keyword args as defined for the 
           C{pprint.pprint} method. (U{http://docs.python.org/3/library/pprint.html#pprint.pprint})"""
        pprint.pprint(self.asList(), *args, **kwargs)

    # add support for pickle protocol
    def __getstate__(self):
        return ( self.__toklist,
                 ( self.__tokdict.copy(),
                   self.__parent is not None and self.__parent() or None,
                   self.__accumNames,
                   self.__name ) )

    def __setstate__(self,state):
        self.__toklist = state[0]
        (self.__tokdict,
         par,
         inAccumNames,
         self.__name) = state[1]
        self.__accumNames = {}
        self.__accumNames.update(inAccumNames)
        if par is not None:
            self.__parent = wkref(par)
        else:
            self.__parent = None

    def __getnewargs__(self):
        return self.__toklist, self.__name, self.__asList, self.__modal

    def __dir__(self):
        return (dir(type(self)) + list(self.keys()))

collections.MutableMapping.register(ParseResults)

def col (loc,strg):
    """Returns current column within a string, counting newlines as line separators.
   The first column is number 1.

   Note: the default parsing behavior is to expand tabs in the input string
   before starting the parsing process.  See L{I{ParserElement.parseString}<ParserElement.parseString>} for more information
   on parsing strings containing C{<TAB>}s, and suggested methods to maintain a
   consistent view of the parsed string, the parse location, and line and column
   positions within the parsed string.
   """
    s = strg
    return 1 if loc<len(s) and s[loc] == '\n' else loc - s.rfind("\n", 0, loc)

def lineno(loc,strg):
    """Returns current line number within a string, counting newlines as line separators.
   The first line is number 1.

   Note: the default parsing behavior is to expand tabs in the input string
   before starting the parsing process.  See L{I{ParserElement.parseString}<ParserElement.parseString>} for more information
   on parsing strings containing C{<TAB>}s, and suggested methods to maintain a
   consistent view of the parsed string, the parse location, and line and column
   positions within the parsed string.
   """
    return strg.count("\n",0,loc) + 1

def line( loc, strg ):
    """Returns the line of text containing loc within a string, counting newlines as line separators.
       """
    lastCR = strg.rfind("\n", 0, loc)
    nextCR = strg.find("\n", loc)
    if nextCR >= 0:
        return strg[lastCR+1:nextCR]
    else:
        return strg[lastCR+1:]

def _defaultStartDebugAction( instring, loc, expr ):
    print (("Match " + _ustr(expr) + " at loc " + _ustr(loc) + "(%d,%d)" % ( lineno(loc,instring), col(loc,instring) )))

def _defaultSuccessDebugAction( instring, startloc, endloc, expr, toks ):
    print ("Matched " + _ustr(expr) + " -> " + str(toks.asList()))

def _defaultExceptionDebugAction( instring, loc, expr, exc ):
    print ("Exception raised:" + _ustr(exc))

def nullDebugAction(*args):
    """'Do-nothing' debug action, to suppress debugging output during parsing."""
    pass

# Only works on Python 3.x - nonlocal is toxic to Python 2 installs
#~ 'decorator to trim function calls to match the arity of the target'
#~ def _trim_arity(func, maxargs=3):
    #~ if func in singleArgBuiltins:
        #~ return lambda s,l,t: func(t)
    #~ limit = 0
    #~ foundArity = False
    #~ def wrapper(*args):
        #~ nonlocal limit,foundArity
        #~ while 1:
            #~ try:
                #~ ret = func(*args[limit:])
                #~ foundArity = True
                #~ return ret
            #~ except TypeError:
                #~ if limit == maxargs or foundArity:
                    #~ raise
                #~ limit += 1
                #~ continue
    #~ return wrapper

# this version is Python 2.x-3.x cross-compatible
'decorator to trim function calls to match the arity of the target'
def _trim_arity(func, maxargs=2):
    if func in singleArgBuiltins:
        return lambda s,l,t: func(t)
    limit = [0]
    foundArity = [False]
    
    # traceback return data structure changed in Py3.5 - normalize back to plain tuples
    if system_version[:2] >= (3,5):
        def extract_stack():
            # special handling for Python 3.5.0 - extra deep call stack by 1
            offset = -3 if system_version == (3,5,0) else -2
            frame_summary = traceback.extract_stack()[offset]
            return [(frame_summary.filename, frame_summary.lineno)]
        def extract_tb(tb):
            frames = traceback.extract_tb(tb)
            frame_summary = frames[-1]
            return [(frame_summary.filename, frame_summary.lineno)]
    else:
        extract_stack = traceback.extract_stack
        extract_tb = traceback.extract_tb
    
    # synthesize what would be returned by traceback.extract_stack at the call to 
    # user's parse action 'func', so that we don't incur call penalty at parse time
    
    LINE_DIFF = 6
    # IF ANY CODE CHANGES, EVEN JUST COMMENTS OR BLANK LINES, BETWEEN THE NEXT LINE AND 
    # THE CALL TO FUNC INSIDE WRAPPER, LINE_DIFF MUST BE MODIFIED!!!!
    this_line = extract_stack()[-1]
    pa_call_line_synth = (this_line[0], this_line[1]+LINE_DIFF)

    def wrapper(*args):
        while 1:
            try:
                ret = func(*args[limit[0]:])
                foundArity[0] = True
                return ret
            except TypeError:
                # re-raise TypeErrors if they did not come from our arity testing
                if foundArity[0]:
                    raise
                else:
                    try:
                        tb = sys.exc_info()[-1]
                        if not extract_tb(tb)[-1][:2] == pa_call_line_synth:
                            raise
                    finally:
                        del tb

                if limit[0] <= maxargs:
                    limit[0] += 1
                    continue
                raise

    # copy func name to wrapper for sensible debug output
    func_name = "<parse action>"
    try:
        func_name = getattr(func, '__name__', 
                            getattr(func, '__class__').__name__)
    except Exception:
        func_name = str(func)
    wrapper.__name__ = func_name

    return wrapper

# argument cache for optimizing repeated calls when backtracking through recursive expressions
class _TTLCache(object):
    
    @classmethod
    def get_cache(cls, maxsize):
        if maxsize is None:
            return _UnboundedTTLCache(maxsize)
        if maxsize == 0:
            return _DisabledTTLCache(maxsize)
        return cls(maxsize)

    def __init__(self, maxsize=None):
        self.lookup = {}
        self.maxsize = maxsize
        self.key_ttl_queue = collections.deque(maxlen=maxsize)
        self.clear()

    def clear(self):
        self.lookup.clear()
        self.key_ttl_queue.clear()
        self.isfull = isinstance(self.maxsize, int) and len(self.key_ttl_queue) >= self.maxsize

    def __contains__(self, key):
        return key in self.lookup

    def __len__(self):
        return len(self.lookup)

    def __getitem__(self, key):
        return self.lookup.get(key)

    def get(self, key, default=None):
        return self.lookup.get(key, default)
    
    def __setitem__(self, key, value):
        # once we are full, we stay full until we are reset
        if not self.isfull:
            self.isfull = len(self) >= self.maxsize

        if self.isfull:
            self.lookup.pop(self.key_ttl_queue.popleft(), None)

        self.lookup[key] = value
        self.key_ttl_queue.append(key)

class _UnboundedTTLCache(_TTLCache):
    def __setitem__(self, key, value):
        # unbounded cache, just add new item
        self.lookup[key] = value
        self.key_ttl_queue.append(key)
        
class _DisabledTTLCache(_TTLCache):
    def __setitem__(self, key, value):
        # cacheing is effectively disabled, do nothing
        pass

class ParserElement(object):
    """Abstract base level parser element class."""
    DEFAULT_WHITE_CHARS = " \n\t\r"
    verbose_stacktrace = False

    @staticmethod
    def setDefaultWhitespaceChars( chars ):
        """Overrides the default whitespace chars
        """
        ParserElement.DEFAULT_WHITE_CHARS = chars

    @staticmethod
    def inlineLiteralsUsing(cls):
        """
        Set class to be used for inclusion of string literals into a parser.
        """
        ParserElement._literalStringClass = cls

    def __init__( self, savelist=False ):
        self.parseAction = list()
        self.failAction = None
        #~ self.name = "<unknown>"  # don't define self.name, let subclasses try/except upcall
        self.strRepr = None
        self.resultsName = None
        self.saveAsList = savelist
        self.skipWhitespace = True
        self.whiteChars = ParserElement.DEFAULT_WHITE_CHARS
        self.copyDefaultWhiteChars = True
        self.mayReturnEmpty = False # used when checking for left-recursion
        self.keepTabs = False
        self.ignoreExprs = list()
        self.debug = False
        self.streamlined = False
        self.mayIndexError = True # used to optimize exception handling for subclasses that don't advance parse index
        self.errmsg = ""
        self.modalResults = True # used to mark results names as modal (report only last) or cumulative (list all)
        self.debugActions = ( None, None, None ) #custom debug actions
        self.re = None
        self.callPreparse = True # used to avoid redundant calls to preParse
        self.callDuringTry = False

    def copy( self ):
        """Make a copy of this C{ParserElement}.  Useful for defining different parse actions
           for the same parsing pattern, using copies of the original parse element."""
        cpy = copy.copy( self )
        cpy.parseAction = self.parseAction[:]
        cpy.ignoreExprs = self.ignoreExprs[:]
        if self.copyDefaultWhiteChars:
            cpy.whiteChars = ParserElement.DEFAULT_WHITE_CHARS
        return cpy

    def setName( self, name ):
        """Define name for this expression, for use in debugging."""
        self.name = name
        self.errmsg = "Expected " + self.name
        if hasattr(self,"exception"):
            self.exception.msg = self.errmsg
        return self

    def setResultsName( self, name, listAllMatches=False ):
        """Define name for referencing matching tokens as a nested attribute
           of the returned parse results.
           NOTE: this returns a *copy* of the original C{ParserElement} object;
           this is so that the client can define a basic element, such as an
           integer, and reference it in multiple places with different names.
           
           You can also set results names using the abbreviated syntax,
           C{expr("name")} in place of C{expr.setResultsName("name")} - 
           see L{I{__call__}<__call__>}.
        """
        newself = self.copy()
        if name.endswith("*"):
            name = name[:-1]
            listAllMatches=True
        newself.resultsName = name
        newself.modalResults = not listAllMatches
        return newself

    def setBreak(self,breakFlag = True):
        """Method to invoke the Python pdb debugger when this element is
           about to be parsed. Set C{breakFlag} to True to enable, False to
           disable.
        """
        if breakFlag:
            _parseMethod = self._parse
            def breaker(instring, loc, doActions=True, callPreParse=True):
                import pdb
                pdb.set_trace()
                return _parseMethod( instring, loc, doActions, callPreParse )
            breaker._originalParseMethod = _parseMethod
            self._parse = breaker
        else:
            if hasattr(self._parse,"_originalParseMethod"):
                self._parse = self._parse._originalParseMethod
        return self

    def setParseAction( self, *fns, **kwargs ):
        """Define action to perform when successfully matching parse element definition.
           Parse action fn is a callable method with 0-3 arguments, called as C{fn(s,loc,toks)},
           C{fn(loc,toks)}, C{fn(toks)}, or just C{fn()}, where:
            - s   = the original string being parsed (see note below)
            - loc = the location of the matching substring
            - toks = a list of the matched tokens, packaged as a C{L{ParseResults}} object
           If the functions in fns modify the tokens, they can return them as the return
           value from fn, and the modified list of tokens will replace the original.
           Otherwise, fn does not need to return any value.
           
           Optional keyword arguments:
            - callDuringTry = (default=False) indicate if parse action should be run during lookaheads and alternate testing

           Note: the default parsing behavior is to expand tabs in the input string
           before starting the parsing process.  See L{I{parseString}<parseString>} for more information
           on parsing strings containing C{<TAB>}s, and suggested methods to maintain a
           consistent view of the parsed string, the parse location, and line and column
           positions within the parsed string.
           """
        self.parseAction = list(map(_trim_arity, list(fns)))
        self.callDuringTry = kwargs.get("callDuringTry", False)
        return self

    def addParseAction( self, *fns, **kwargs ):
        """Add parse action to expression's list of parse actions. See L{I{setParseAction}<setParseAction>}."""
        self.parseAction += list(map(_trim_arity, list(fns)))
        self.callDuringTry = self.callDuringTry or kwargs.get("callDuringTry", False)
        return self

    def addCondition(self, *fns, **kwargs):
        """Add a boolean predicate function to expression's list of parse actions. See 
        L{I{setParseAction}<setParseAction>} for function call signatures. Unlike C{setParseAction}, 
        functions passed to C{addCondition} need to return boolean success/fail of the condition.

        Optional keyword arguments:
         - message = define a custom message to be used in the raised exception
         - fatal   = if True, will raise ParseFatalException to stop parsing immediately; otherwise will raise ParseException
        """
        msg = kwargs.get("message", "failed user-defined condition")
        exc_type = ParseFatalException if kwargs.get("fatal", False) else ParseException
        for fn in fns:
            def pa(s,l,t):
                if not bool(_trim_arity(fn)(s,l,t)):
                    raise exc_type(s,l,msg)
            self.parseAction.append(pa)
        self.callDuringTry = self.callDuringTry or kwargs.get("callDuringTry", False)
        return self

    def setFailAction( self, fn ):
        """Define action to perform if parsing fails at this expression.
           Fail acton fn is a callable function that takes the arguments
           C{fn(s,loc,expr,err)} where:
            - s = string being parsed
            - loc = location where expression match was attempted and failed
            - expr = the parse expression that failed
            - err = the exception thrown
           The function returns no value.  It may throw C{L{ParseFatalException}}
           if it is desired to stop parsing immediately."""
        self.failAction = fn
        return self

    def _skipIgnorables( self, instring, loc ):
        exprsFound = True
        while exprsFound:
            exprsFound = False
            for e in self.ignoreExprs:
                try:
                    while 1:
                        loc,dummy = e._parse( instring, loc )
                        exprsFound = True
                except ParseException:
                    pass
        return loc

    def preParse( self, instring, loc ):
        if self.ignoreExprs:
            loc = self._skipIgnorables( instring, loc )

        if self.skipWhitespace:
            wt = self.whiteChars
            instrlen = len(instring)
            while loc < instrlen and instring[loc] in wt:
                loc += 1

        return loc

    def parseImpl( self, instring, loc, doActions=True ):
        return loc, []

    def postParse( self, instring, loc, tokenlist ):
        return tokenlist

    #~ @profile
    def _parseNoCache( self, instring, loc, doActions=True, callPreParse=True ):
        debugging = ( self.debug ) #and doActions )

        if debugging or self.failAction:
            #~ print ("Match",self,"at loc",loc,"(%d,%d)" % ( lineno(loc,instring), col(loc,instring) ))
            if (self.debugActions[0] ):
                self.debugActions[0]( instring, loc, self )
            if callPreParse and self.callPreparse:
                preloc = self.preParse( instring, loc )
            else:
                preloc = loc
            tokensStart = preloc
            try:
                try:
                    loc,tokens = self.parseImpl( instring, preloc, doActions )
                except IndexError:
                    raise ParseException( instring, len(instring), self.errmsg, self )
            except ParseBaseException as err:
                #~ print ("Exception raised:", err)
                if self.debugActions[2]:
                    self.debugActions[2]( instring, tokensStart, self, err )
                if self.failAction:
                    self.failAction( instring, tokensStart, self, err )
                raise
        else:
            if callPreParse and self.callPreparse:
                preloc = self.preParse( instring, loc )
            else:
                preloc = loc
            tokensStart = preloc
            if self.mayIndexError or loc >= len(instring):
                try:
                    loc,tokens = self.parseImpl( instring, preloc, doActions )
                except IndexError:
                    raise ParseException( instring, len(instring), self.errmsg, self )
            else:
                loc,tokens = self.parseImpl( instring, preloc, doActions )

        tokens = self.postParse( instring, loc, tokens )

        retTokens = ParseResults( tokens, self.resultsName, asList=self.saveAsList, modal=self.modalResults )
        if self.parseAction and (doActions or self.callDuringTry):
            if debugging:
                try:
                    for fn in self.parseAction:
                        tokens = fn( instring, tokensStart, retTokens )
                        if tokens is not None:
                            retTokens = ParseResults( tokens,
                                                      self.resultsName,
                                                      asList=self.saveAsList and isinstance(tokens,(ParseResults,list)),
                                                      modal=self.modalResults )
                except ParseBaseException as err:
                    #~ print "Exception raised in user parse action:", err
                    if (self.debugActions[2] ):
                        self.debugActions[2]( instring, tokensStart, self, err )
                    raise
            else:
                for fn in self.parseAction:
                    tokens = fn( instring, tokensStart, retTokens )
                    if tokens is not None:
                        retTokens = ParseResults( tokens,
                                                  self.resultsName,
                                                  asList=self.saveAsList and isinstance(tokens,(ParseResults,list)),
                                                  modal=self.modalResults )

        if debugging:
            #~ print ("Matched",self,"->",retTokens.asList())
            if (self.debugActions[1] ):
                self.debugActions[1]( instring, tokensStart, loc, self, retTokens )

        return loc, retTokens

    def tryParse( self, instring, loc ):
        try:
            return self._parse( instring, loc, doActions=False )[0]
        except ParseFatalException:
            raise ParseException( instring, loc, self.errmsg, self)
    
    def canParseNext(self, instring, loc):
        try:
            self.tryParse(instring, loc)
        except (ParseException, IndexError):
            return False
        else:
            return True

    packrat_cache = _TTLCache()
    packrat_cache_stats = [0, 0, 0]
    packrat_cache_lock = RLock()
    
    # this method gets repeatedly called during backtracking with the same arguments -
    # we can cache these arguments and save ourselves the trouble of re-parsing the contained expression
    def _parseCache( self, instring, loc, doActions=True, callPreParse=True ):
        SIZE, HIT, MISS = 0, 1, 2
        lookup = (self, instring, loc, callPreParse, doActions)
        with ParserElement.packrat_cache_lock:
            value = ParserElement.packrat_cache.get(lookup, None)
            if value is not None:
                ParserElement.packrat_cache_stats[HIT] += 1
                if isinstance(value, Exception):
                    raise value
                return (value[0], value[1].copy())
            else:
                ParserElement.packrat_cache_stats[MISS] += 1
                try:
                    value = self._parseNoCache( instring, loc, doActions, callPreParse )
                    ParserElement.packrat_cache[lookup] = (value[0], value[1].copy())
                    ParserElement.packrat_cache_stats[SIZE] = len(ParserElement.packrat_cache)
                    return value
                except ParseBaseException as pe:
                    pe.__traceback__ = None
                    ParserElement.packrat_cache[lookup] = pe
                    ParserElement.packrat_cache_stats[SIZE] = len(ParserElement.packrat_cache)
                    raise

    _parse = _parseNoCache

    @staticmethod
    def resetCache():
        ParserElement.packrat_cache.clear()
        ParserElement.packrat_cache_stats[:] = [0] * len(ParserElement.packrat_cache_stats)

    _packratEnabled = False
    @staticmethod
    def enablePackrat(cache_size_limit=128):
        """Enables "packrat" parsing, which adds memoizing to the parsing logic.
           Repeated parse attempts at the same string location (which happens
           often in many complex grammars) can immediately return a cached value,
           instead of re-executing parsing/validating code.  Memoizing is done of
           both valid results and parsing exceptions.
           
           Parameters:
            - cache_size_limit - (default=128) - if an integer value is provided
              will limit the size of the packrat cache; if None is passed, then
              the cache size will be unbounded; if 0 is passed, the cache will
              be effectively disabled
            
           This speedup may break existing programs that use parse actions that
           have side-effects.  For this reason, packrat parsing is disabled when
           you first import pyparsing.  To activate the packrat feature, your
           program must call the class method C{ParserElement.enablePackrat()}.  If
           your program uses C{psyco} to "compile as you go", you must call
           C{enablePackrat} before calling C{psyco.full()}.  If you do not do this,
           Python will crash.  For best results, call C{enablePackrat()} immediately
           after importing pyparsing.
        """
        if not ParserElement._packratEnabled:
            ParserElement._packratEnabled = True
            ParserElement.packrat_cache = _TTLCache.get_cache(cache_size_limit)
            ParserElement._parse = ParserElement._parseCache

    def parseString( self, instring, parseAll=False ):
        """Execute the parse expression with the given string.
           This is the main interface to the client code, once the complete
           expression has been built.

           If you want the grammar to require that the entire input string be
           successfully parsed, then set C{parseAll} to True (equivalent to ending
           the grammar with C{L{StringEnd()}}).

           Note: C{parseString} implicitly calls C{expandtabs()} on the input string,
           in order to report proper column numbers in parse actions.
           If the input string contains tabs and
           the grammar uses parse actions that use the C{loc} argument to index into the
           string being parsed, you can ensure you have a consistent view of the input
           string by:
            - calling C{parseWithTabs} on your grammar before calling C{parseString}
              (see L{I{parseWithTabs}<parseWithTabs>})
            - define your parse action using the full C{(s,loc,toks)} signature, and
              reference the input string using the parse action's C{s} argument
            - explictly expand the tabs in your input string before calling
              C{parseString}
        """
        ParserElement.resetCache()
        if not self.streamlined:
            self.streamline()
            #~ self.saveAsList = True
        for e in self.ignoreExprs:
            e.streamline()
        if not self.keepTabs:
            instring = instring.expandtabs()
        try:
            loc, tokens = self._parse( instring, 0 )
            if parseAll:
                loc = self.preParse( instring, loc )
                se = Empty() + StringEnd()
                se._parse( instring, loc )
        except ParseBaseException as exc:
            if ParserElement.verbose_stacktrace:
                raise
            else:
                # catch and re-raise exception from here, clears out pyparsing internal stack trace
                raise exc
        else:
            return tokens

    def scanString( self, instring, maxMatches=_MAX_INT, overlap=False ):
        """Scan the input string for expression matches.  Each match will return the
           matching tokens, start location, and end location.  May be called with optional
           C{maxMatches} argument, to clip scanning after 'n' matches are found.  If
           C{overlap} is specified, then overlapping matches will be reported.

           Note that the start and end locations are reported relative to the string
           being parsed.  See L{I{parseString}<parseString>} for more information on parsing
           strings with embedded tabs."""
        if not self.streamlined:
            self.streamline()
        for e in self.ignoreExprs:
            e.streamline()

        if not self.keepTabs:
            instring = _ustr(instring).expandtabs()
        instrlen = len(instring)
        loc = 0
        preparseFn = self.preParse
        parseFn = self._parse
        ParserElement.resetCache()
        matches = 0
        try:
            while loc <= instrlen and matches < maxMatches:
                try:
                    preloc = preparseFn( instring, loc )
                    nextLoc,tokens = parseFn( instring, preloc, callPreParse=False )
                except ParseException:
                    loc = preloc+1
                else:
                    if nextLoc > loc:
                        matches += 1
                        yield tokens, preloc, nextLoc
                        if overlap:
                            nextloc = preparseFn( instring, loc )
                            if nextloc > loc:
                                loc = nextLoc
                            else:
                                loc += 1
                        else:
                            loc = nextLoc
                    else:
                        loc = preloc+1
        except ParseBaseException as exc:
            if ParserElement.verbose_stacktrace:
                raise
            else:
                # catch and re-raise exception from here, clears out pyparsing internal stack trace
                raise exc

    def transformString( self, instring ):
        """Extension to C{L{scanString}}, to modify matching text with modified tokens that may
           be returned from a parse action.  To use C{transformString}, define a grammar and
           attach a parse action to it that modifies the returned token list.
           Invoking C{transformString()} on a target string will then scan for matches,
           and replace the matched text patterns according to the logic in the parse
           action.  C{transformString()} returns the resulting transformed string."""
        out = []
        lastE = 0
        # force preservation of <TAB>s, to minimize unwanted transformation of string, and to
        # keep string locs straight between transformString and scanString
        self.keepTabs = True
        try:
            for t,s,e in self.scanString( instring ):
                out.append( instring[lastE:s] )
                if t:
                    if isinstance(t,ParseResults):
                        out += t.asList()
                    elif isinstance(t,list):
                        out += t
                    else:
                        out.append(t)
                lastE = e
            out.append(instring[lastE:])
            out = [o for o in out if o]
            return "".join(map(_ustr,_flatten(out)))
        except ParseBaseException as exc:
            if ParserElement.verbose_stacktrace:
                raise
            else:
                # catch and re-raise exception from here, clears out pyparsing internal stack trace
                raise exc

    def searchString( self, instring, maxMatches=_MAX_INT ):
        """Another extension to C{L{scanString}}, simplifying the access to the tokens found
           to match the given parse expression.  May be called with optional
           C{maxMatches} argument, to clip searching after 'n' matches are found.
        """
        try:
            return ParseResults([ t for t,s,e in self.scanString( instring, maxMatches ) ])
        except ParseBaseException as exc:
            if ParserElement.verbose_stacktrace:
                raise
            else:
                # catch and re-raise exception from here, clears out pyparsing internal stack trace
                raise exc

    def split(self, instring, maxsplit=_MAX_INT, includeSeparators=False):
        """Generator method to split a string using the given expression as a separator.
           May be called with optional C{maxsplit} argument, to limit the number of splits;
           and the optional C{includeSeparators} argument (default=C{False}), if the separating
           matching text should be included in the split results.
        """
        splits = 0
        last = 0
        for t,s,e in self.scanString(instring, maxMatches=maxsplit):
            yield instring[last:s]
            if includeSeparators:
                yield t[0]
            last = e
        yield instring[last:]

    def __add__(self, other ):
        """Implementation of + operator - returns C{L{And}}"""
        if isinstance( other, basestring ):
            other = ParserElement._literalStringClass( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return And( [ self, other ] )

    def __radd__(self, other ):
        """Implementation of + operator when left operand is not a C{L{ParserElement}}"""
        if isinstance( other, basestring ):
            other = ParserElement._literalStringClass( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other + self

    def __sub__(self, other):
        """Implementation of - operator, returns C{L{And}} with error stop"""
        if isinstance( other, basestring ):
            other = ParserElement._literalStringClass( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return And( [ self, And._ErrorStop(), other ] )

    def __rsub__(self, other ):
        """Implementation of - operator when left operand is not a C{L{ParserElement}}"""
        if isinstance( other, basestring ):
            other = ParserElement._literalStringClass( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other - self

    def __mul__(self,other):
        """Implementation of * operator, allows use of C{expr * 3} in place of
           C{expr + expr + expr}.  Expressions may also me multiplied by a 2-integer
           tuple, similar to C{{min,max}} multipliers in regular expressions.  Tuples
           may also include C{None} as in:
            - C{expr*(n,None)} or C{expr*(n,)} is equivalent
              to C{expr*n + L{ZeroOrMore}(expr)}
              (read as "at least n instances of C{expr}")
            - C{expr*(None,n)} is equivalent to C{expr*(0,n)}
              (read as "0 to n instances of C{expr}")
            - C{expr*(None,None)} is equivalent to C{L{ZeroOrMore}(expr)}
            - C{expr*(1,None)} is equivalent to C{L{OneOrMore}(expr)}

           Note that C{expr*(None,n)} does not raise an exception if
           more than n exprs exist in the input stream; that is,
           C{expr*(None,n)} does not enforce a maximum number of expr
           occurrences.  If this behavior is desired, then write
           C{expr*(None,n) + ~expr}

        """
        if isinstance(other,int):
            minElements, optElements = other,0
        elif isinstance(other,tuple):
            other = (other + (None, None))[:2]
            if other[0] is None:
                other = (0, other[1])
            if isinstance(other[0],int) and other[1] is None:
                if other[0] == 0:
                    return ZeroOrMore(self)
                if other[0] == 1:
                    return OneOrMore(self)
                else:
                    return self*other[0] + ZeroOrMore(self)
            elif isinstance(other[0],int) and isinstance(other[1],int):
                minElements, optElements = other
                optElements -= minElements
            else:
                raise TypeError("cannot multiply 'ParserElement' and ('%s','%s') objects", type(other[0]),type(other[1]))
        else:
            raise TypeError("cannot multiply 'ParserElement' and '%s' objects", type(other))

        if minElements < 0:
            raise ValueError("cannot multiply ParserElement by negative value")
        if optElements < 0:
            raise ValueError("second tuple value must be greater or equal to first tuple value")
        if minElements == optElements == 0:
            raise ValueError("cannot multiply ParserElement by 0 or (0,0)")

        if (optElements):
            def makeOptionalList(n):
                if n>1:
                    return Optional(self + makeOptionalList(n-1))
                else:
                    return Optional(self)
            if minElements:
                if minElements == 1:
                    ret = self + makeOptionalList(optElements)
                else:
                    ret = And([self]*minElements) + makeOptionalList(optElements)
            else:
                ret = makeOptionalList(optElements)
        else:
            if minElements == 1:
                ret = self
            else:
                ret = And([self]*minElements)
        return ret

    def __rmul__(self, other):
        return self.__mul__(other)

    def __or__(self, other ):
        """Implementation of | operator - returns C{L{MatchFirst}}"""
        if isinstance( other, basestring ):
            other = ParserElement._literalStringClass( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return MatchFirst( [ self, other ] )

    def __ror__(self, other ):
        """Implementation of | operator when left operand is not a C{L{ParserElement}}"""
        if isinstance( other, basestring ):
            other = ParserElement._literalStringClass( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other | self

    def __xor__(self, other ):
        """Implementation of ^ operator - returns C{L{Or}}"""
        if isinstance( other, basestring ):
            other = ParserElement._literalStringClass( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return Or( [ self, other ] )

    def __rxor__(self, other ):
        """Implementation of ^ operator when left operand is not a C{L{ParserElement}}"""
        if isinstance( other, basestring ):
            other = ParserElement._literalStringClass( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other ^ self

    def __and__(self, other ):
        """Implementation of & operator - returns C{L{Each}}"""
        if isinstance( other, basestring ):
            other = ParserElement._literalStringClass( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return Each( [ self, other ] )

    def __rand__(self, other ):
        """Implementation of & operator when left operand is not a C{L{ParserElement}}"""
        if isinstance( other, basestring ):
            other = ParserElement._literalStringClass( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other & self

    def __invert__( self ):
        """Implementation of ~ operator - returns C{L{NotAny}}"""
        return NotAny( self )

    def __call__(self, name=None):
        """Shortcut for C{L{setResultsName}}, with C{listAllMatches=default}::
             userdata = Word(alphas).setResultsName("name") + Word(nums+"-").setResultsName("socsecno")
           could be written as::
             userdata = Word(alphas)("name") + Word(nums+"-")("socsecno")
             
           If C{name} is given with a trailing C{'*'} character, then C{listAllMatches} will be
           passed as C{True}.
           
           If C{name} is omitted, same as calling C{L{copy}}.
           """
        if name is not None:
            return self.setResultsName(name)
        else:
            return self.copy()

    def suppress( self ):
        """Suppresses the output of this C{ParserElement}; useful to keep punctuation from
           cluttering up returned output.
        """
        return Suppress( self )

    def leaveWhitespace( self ):
        """Disables the skipping of whitespace before matching the characters in the
           C{ParserElement}'s defined pattern.  This is normally only used internally by
           the pyparsing module, but may be needed in some whitespace-sensitive grammars.
        """
        self.skipWhitespace = False
        return self

    def setWhitespaceChars( self, chars ):
        """Overrides the default whitespace chars
        """
        self.skipWhitespace = True
        self.whiteChars = chars
        self.copyDefaultWhiteChars = False
        return self

    def parseWithTabs( self ):
        """Overrides default behavior to expand C{<TAB>}s to spaces before parsing the input string.
           Must be called before C{parseString} when the input grammar contains elements that
           match C{<TAB>} characters."""
        self.keepTabs = True
        return self

    def ignore( self, other ):
        """Define expression to be ignored (e.g., comments) while doing pattern
           matching; may be called repeatedly, to define multiple comment or other
           ignorable patterns.
        """
        if isinstance(other, basestring):
            other = Suppress(other)

        if isinstance( other, Suppress ):
            if other not in self.ignoreExprs:
                self.ignoreExprs.append(other)
        else:
            self.ignoreExprs.append( Suppress( other.copy() ) )
        return self

    def setDebugActions( self, startAction, successAction, exceptionAction ):
        """Enable display of debugging messages while doing pattern matching."""
        self.debugActions = (startAction or _defaultStartDebugAction,
                             successAction or _defaultSuccessDebugAction,
                             exceptionAction or _defaultExceptionDebugAction)
        self.debug = True
        return self

    def setDebug( self, flag=True ):
        """Enable display of debugging messages while doing pattern matching.
           Set C{flag} to True to enable, False to disable."""
        if flag:
            self.setDebugActions( _defaultStartDebugAction, _defaultSuccessDebugAction, _defaultExceptionDebugAction )
        else:
            self.debug = False
        return self

    def __str__( self ):
        return self.name

    def __repr__( self ):
        return _ustr(self)

    def streamline( self ):
        self.streamlined = True
        self.strRepr = None
        return self

    def checkRecursion( self, parseElementList ):
        pass

    def validate( self, validateTrace=[] ):
        """Check defined expressions for valid structure, check for infinite recursive definitions."""
        self.checkRecursion( [] )

    def parseFile( self, file_or_filename, parseAll=False ):
        """Execute the parse expression on the given file or filename.
           If a filename is specified (instead of a file object),
           the entire file is opened, read, and closed before parsing.
        """
        try:
            file_contents = file_or_filename.read()
        except AttributeError:
            with open(file_or_filename, "r") as f:
                file_contents = f.read()
        try:
            return self.parseString(file_contents, parseAll)
        except ParseBaseException as exc:
            if ParserElement.verbose_stacktrace:
                raise
            else:
                # catch and re-raise exception from here, clears out pyparsing internal stack trace
                raise exc

    def __eq__(self,other):
        if isinstance(other, ParserElement):
            return self is other or vars(self) == vars(other)
        elif isinstance(other, basestring):
            return self.matches(other)
        else:
            return super(ParserElement,self)==other

    def __ne__(self,other):
        return not (self == other)

    def __hash__(self):
        return hash(id(self))

    def __req__(self,other):
        return self == other

    def __rne__(self,other):
        return not (self == other)

    def matches(self, testString, parseAll=True):
        """Method for quick testing of a parser against a test string. Good for simple 
           inline microtests of sub expressions while building up larger parser, as in::
           
               expr = Word(nums)
               assert expr.matches("100")
           
           Parameters:
            - testString - to test against this expression for a match
            - parseAll - (default=True) - flag to pass to C{L{parseString}} when running tests           
        """
        try:
            self.parseString(_ustr(testString), parseAll=parseAll)
            return True
        except ParseBaseException:
            return False
                
    def runTests(self, tests, parseAll=True, comment='#', printResults=True, failureTests=False):
        """Execute the parse expression on a series of test strings, showing each
           test, the parsed results or where the parse failed. Quick and easy way to
           run a parse expression against a list of sample strings.
           
           Parameters:
            - tests - a list of separate test strings, or a multiline string of test strings
            - parseAll - (default=True) - flag to pass to C{L{parseString}} when running tests           
            - comment - (default='#') - expression for indicating embedded comments in the test 
              string; pass None to disable comment filtering
            - printResults - (default=True) prints test output to stdout
            - failureTests - (default=False) indicates if these tests are expected to fail parsing

            Returns: a (success, results) tuple, where success indicates that all tests succeeded
            (or failed if C{failureTest} is True), and the results contain a list of lines of each 
            test's output
        """
        if isinstance(tests, basestring):
            tests = list(map(str.strip, tests.rstrip().splitlines()))
        if isinstance(comment, basestring):
            comment = Literal(comment)
        allResults = []
        comments = []
        success = True
        for t in tests:
            if comment is not None and comment.matches(t, False) or comments and not t:
                comments.append(t)
                continue
            if not t:
                continue
            out = ['\n'.join(comments), t]
            comments = []
            try:
                result = self.parseString(t, parseAll=parseAll)
                out.append(result.dump())
                success = success and not failureTests
            except ParseBaseException as pe:
                fatal = "(FATAL)" if isinstance(pe, ParseFatalException) else ""
                if '\n' in t:
                    out.append(line(pe.loc, t))
                    out.append(' '*(col(pe.loc,t)-1) + '^' + fatal)
                else:
                    out.append(' '*pe.loc + '^' + fatal)
                out.append("FAIL: " + str(pe))
                success = success and failureTests
                result = pe

            if printResults:
                out.append('')
                print('\n'.join(out))

            allResults.append((t, result))
        
        return success, allResults

        
class Token(ParserElement):
    """Abstract C{ParserElement} subclass, for defining atomic matching patterns."""
    def __init__( self ):
        super(Token,self).__init__( savelist=False )


class Empty(Token):
    """An empty token, will always match."""
    def __init__( self ):
        super(Empty,self).__init__()
        self.name = "Empty"
        self.mayReturnEmpty = True
        self.mayIndexError = False


class NoMatch(Token):
    """A token that will never match."""
    def __init__( self ):
        super(NoMatch,self).__init__()
        self.name = "NoMatch"
        self.mayReturnEmpty = True
        self.mayIndexError = False
        self.errmsg = "Unmatchable token"

    def parseImpl( self, instring, loc, doActions=True ):
        raise ParseException(instring, loc, self.errmsg, self)


class Literal(Token):
    """Token to exactly match a specified string."""
    def __init__( self, matchString ):
        super(Literal,self).__init__()
        self.match = matchString
        self.matchLen = len(matchString)
        try:
            self.firstMatchChar = matchString[0]
        except IndexError:
            warnings.warn("null string passed to Literal; use Empty() instead",
                            SyntaxWarning, stacklevel=2)
            self.__class__ = Empty
        self.name = '"%s"' % _ustr(self.match)
        self.errmsg = "Expected " + self.name
        self.mayReturnEmpty = False
        self.mayIndexError = False

    # Performance tuning: this routine gets called a *lot*
    # if this is a single character match string  and the first character matches,
    # short-circuit as quickly as possible, and avoid calling startswith
    #~ @profile
    def parseImpl( self, instring, loc, doActions=True ):
        if (instring[loc] == self.firstMatchChar and
            (self.matchLen==1 or instring.startswith(self.match,loc)) ):
            return loc+self.matchLen, self.match
        raise ParseException(instring, loc, self.errmsg, self)
_L = Literal
ParserElement._literalStringClass = Literal

class Keyword(Token):
    """Token to exactly match a specified string as a keyword, that is, it must be
       immediately followed by a non-keyword character.  Compare with C{L{Literal}}:
        - C{Literal("if")} will match the leading C{'if'} in C{'ifAndOnlyIf'}.
        - C{Keyword("if")} will not; it will only match the leading C{'if'} in C{'if x=1'}, or C{'if(y==2)'}
       Accepts two optional constructor arguments in addition to the keyword string:
        - C{identChars} is a string of characters that would be valid identifier characters,
          defaulting to all alphanumerics + "_" and "$"
        - C{caseless} allows case-insensitive matching, default is C{False}.
    """
    DEFAULT_KEYWORD_CHARS = alphanums+"_$"

    def __init__( self, matchString, identChars=DEFAULT_KEYWORD_CHARS, caseless=False ):
        super(Keyword,self).__init__()
        self.match = matchString
        self.matchLen = len(matchString)
        try:
            self.firstMatchChar = matchString[0]
        except IndexError:
            warnings.warn("null string passed to Keyword; use Empty() instead",
                            SyntaxWarning, stacklevel=2)
        self.name = '"%s"' % self.match
        self.errmsg = "Expected " + self.name
        self.mayReturnEmpty = False
        self.mayIndexError = False
        self.caseless = caseless
        if caseless:
            self.caselessmatch = matchString.upper()
            identChars = identChars.upper()
        self.identChars = set(identChars)

    def parseImpl( self, instring, loc, doActions=True ):
        if self.caseless:
            if ( (instring[ loc:loc+self.matchLen ].upper() == self.caselessmatch) and
                 (loc >= len(instring)-self.matchLen or instring[loc+self.matchLen].upper() not in self.identChars) and
                 (loc == 0 or instring[loc-1].upper() not in self.identChars) ):
                return loc+self.matchLen, self.match
        else:
            if (instring[loc] == self.firstMatchChar and
                (self.matchLen==1 or instring.startswith(self.match,loc)) and
                (loc >= len(instring)-self.matchLen or instring[loc+self.matchLen] not in self.identChars) and
                (loc == 0 or instring[loc-1] not in self.identChars) ):
                return loc+self.matchLen, self.match
        raise ParseException(instring, loc, self.errmsg, self)

    def copy(self):
        c = super(Keyword,self).copy()
        c.identChars = Keyword.DEFAULT_KEYWORD_CHARS
        return c

    @staticmethod
    def setDefaultKeywordChars( chars ):
        """Overrides the default Keyword chars
        """
        Keyword.DEFAULT_KEYWORD_CHARS = chars

class CaselessLiteral(Literal):
    """Token to match a specified string, ignoring case of letters.
       Note: the matched results will always be in the case of the given
       match string, NOT the case of the input text.
    """
    def __init__( self, matchString ):
        super(CaselessLiteral,self).__init__( matchString.upper() )
        # Preserve the defining literal.
        self.returnString = matchString
        self.name = "'%s'" % self.returnString
        self.errmsg = "Expected " + self.name

    def parseImpl( self, instring, loc, doActions=True ):
        if instring[ loc:loc+self.matchLen ].upper() == self.match:
            return loc+self.matchLen, self.returnString
        raise ParseException(instring, loc, self.errmsg, self)

class CaselessKeyword(Keyword):
    def __init__( self, matchString, identChars=Keyword.DEFAULT_KEYWORD_CHARS ):
        super(CaselessKeyword,self).__init__( matchString, identChars, caseless=True )

    def parseImpl( self, instring, loc, doActions=True ):
        if ( (instring[ loc:loc+self.matchLen ].upper() == self.caselessmatch) and
             (loc >= len(instring)-self.matchLen or instring[loc+self.matchLen].upper() not in self.identChars) ):
            return loc+self.matchLen, self.match
        raise ParseException(instring, loc, self.errmsg, self)

class Word(Token):
    """Token for matching words composed of allowed character sets.
       Defined with string containing all allowed initial characters,
       an optional string containing allowed body characters (if omitted,
       defaults to the initial character set), and an optional minimum,
       maximum, and/or exact length.  The default value for C{min} is 1 (a
       minimum value < 1 is not valid); the default values for C{max} and C{exact}
       are 0, meaning no maximum or exact length restriction. An optional
       C{excludeChars} parameter can list characters that might be found in 
       the input C{bodyChars} string; useful to define a word of all printables
       except for one or two characters, for instance.
    """
    def __init__( self, initChars, bodyChars=None, min=1, max=0, exact=0, asKeyword=False, excludeChars=None ):
        super(Word,self).__init__()
        if excludeChars:
            initChars = ''.join(c for c in initChars if c not in excludeChars)
            if bodyChars:
                bodyChars = ''.join(c for c in bodyChars if c not in excludeChars)
        self.initCharsOrig = initChars
        self.initChars = set(initChars)
        if bodyChars :
            self.bodyCharsOrig = bodyChars
            self.bodyChars = set(bodyChars)
        else:
            self.bodyCharsOrig = initChars
            self.bodyChars = set(initChars)

        self.maxSpecified = max > 0

        if min < 1:
            raise ValueError("cannot specify a minimum length < 1; use Optional(Word()) if zero-length word is permitted")

        self.minLen = min

        if max > 0:
            self.maxLen = max
        else:
            self.maxLen = _MAX_INT

        if exact > 0:
            self.maxLen = exact
            self.minLen = exact

        self.name = _ustr(self)
        self.errmsg = "Expected " + self.name
        self.mayIndexError = False
        self.asKeyword = asKeyword

        if ' ' not in self.initCharsOrig+self.bodyCharsOrig and (min==1 and max==0 and exact==0):
            if self.bodyCharsOrig == self.initCharsOrig:
                self.reString = "[%s]+" % _escapeRegexRangeChars(self.initCharsOrig)
            elif len(self.initCharsOrig) == 1:
                self.reString = "%s[%s]*" % \
                                      (re.escape(self.initCharsOrig),
                                      _escapeRegexRangeChars(self.bodyCharsOrig),)
            else:
                self.reString = "[%s][%s]*" % \
                                      (_escapeRegexRangeChars(self.initCharsOrig),
                                      _escapeRegexRangeChars(self.bodyCharsOrig),)
            if self.asKeyword:
                self.reString = r"\b"+self.reString+r"\b"
            try:
                self.re = re.compile( self.reString )
            except:
                self.re = None

    def parseImpl( self, instring, loc, doActions=True ):
        if self.re:
            result = self.re.match(instring,loc)
            if not result:
                raise ParseException(instring, loc, self.errmsg, self)

            loc = result.end()
            return loc, result.group()

        if not(instring[ loc ] in self.initChars):
            raise ParseException(instring, loc, self.errmsg, self)

        start = loc
        loc += 1
        instrlen = len(instring)
        bodychars = self.bodyChars
        maxloc = start + self.maxLen
        maxloc = min( maxloc, instrlen )
        while loc < maxloc and instring[loc] in bodychars:
            loc += 1

        throwException = False
        if loc - start < self.minLen:
            throwException = True
        if self.maxSpecified and loc < instrlen and instring[loc] in bodychars:
            throwException = True
        if self.asKeyword:
            if (start>0 and instring[start-1] in bodychars) or (loc<instrlen and instring[loc] in bodychars):
                throwException = True

        if throwException:
            raise ParseException(instring, loc, self.errmsg, self)

        return loc, instring[start:loc]

    def __str__( self ):
        try:
            return super(Word,self).__str__()
        except:
            pass


        if self.strRepr is None:

            def charsAsStr(s):
                if len(s)>4:
                    return s[:4]+"..."
                else:
                    return s

            if ( self.initCharsOrig != self.bodyCharsOrig ):
                self.strRepr = "W:(%s,%s)" % ( charsAsStr(self.initCharsOrig), charsAsStr(self.bodyCharsOrig) )
            else:
                self.strRepr = "W:(%s)" % charsAsStr(self.initCharsOrig)

        return self.strRepr


class Regex(Token):
    """Token for matching strings that match a given regular expression.
       Defined with string specifying the regular expression in a form recognized by the inbuilt Python re module.
    """
    compiledREtype = type(re.compile("[A-Z]"))
    def __init__( self, pattern, flags=0):
        """The parameters C{pattern} and C{flags} are passed to the C{re.compile()} function as-is. See the Python C{re} module for an explanation of the acceptable patterns and flags."""
        super(Regex,self).__init__()

        if isinstance(pattern, basestring):
            if not pattern:
                warnings.warn("null string passed to Regex; use Empty() instead",
                        SyntaxWarning, stacklevel=2)

            self.pattern = pattern
            self.flags = flags

            try:
                self.re = re.compile(self.pattern, self.flags)
                self.reString = self.pattern
            except sre_constants.error:
                warnings.warn("invalid pattern (%s) passed to Regex" % pattern,
                    SyntaxWarning, stacklevel=2)
                raise

        elif isinstance(pattern, Regex.compiledREtype):
            self.re = pattern
            self.pattern = \
            self.reString = str(pattern)
            self.flags = flags
            
        else:
            raise ValueError("Regex may only be constructed with a string or a compiled RE object")

        self.name = _ustr(self)
        self.errmsg = "Expected " + self.name
        self.mayIndexError = False
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        result = self.re.match(instring,loc)
        if not result:
            raise ParseException(instring, loc, self.errmsg, self)

        loc = result.end()
        d = result.groupdict()
        ret = ParseResults(result.group())
        if d:
            for k in d:
                ret[k] = d[k]
        return loc,ret

    def __str__( self ):
        try:
            return super(Regex,self).__str__()
        except:
            pass

        if self.strRepr is None:
            self.strRepr = "Re:(%s)" % repr(self.pattern)

        return self.strRepr


class QuotedString(Token):
    """Token for matching strings that are delimited by quoting characters.
    """
    def __init__( self, quoteChar, escChar=None, escQuote=None, multiline=False, unquoteResults=True, endQuoteChar=None, convertWhitespaceEscapes=True):
        r"""Defined with the following parameters:
            - quoteChar - string of one or more characters defining the quote delimiting string
            - escChar - character to escape quotes, typically backslash (default=None)
            - escQuote - special quote sequence to escape an embedded quote string (such as SQL's "" to escape an embedded ") (default=None)
            - multiline - boolean indicating whether quotes can span multiple lines (default=C{False})
            - unquoteResults - boolean indicating whether the matched text should be unquoted (default=C{True})
            - endQuoteChar - string of one or more characters defining the end of the quote delimited string (default=C{None} => same as quoteChar)
            - convertWhitespaceEscapes - convert escaped whitespace (C{'\t'}, C{'\n'}, etc.) to actual whitespace (default=C{True})
        """
        super(QuotedString,self).__init__()

        # remove white space from quote chars - wont work anyway
        quoteChar = quoteChar.strip()
        if not quoteChar:
            warnings.warn("quoteChar cannot be the empty string",SyntaxWarning,stacklevel=2)
            raise SyntaxError()

        if endQuoteChar is None:
            endQuoteChar = quoteChar
        else:
            endQuoteChar = endQuoteChar.strip()
            if not endQuoteChar:
                warnings.warn("endQuoteChar cannot be the empty string",SyntaxWarning,stacklevel=2)
                raise SyntaxError()

        self.quoteChar = quoteChar
        self.quoteCharLen = len(quoteChar)
        self.firstQuoteChar = quoteChar[0]
        self.endQuoteChar = endQuoteChar
        self.endQuoteCharLen = len(endQuoteChar)
        self.escChar = escChar
        self.escQuote = escQuote
        self.unquoteResults = unquoteResults
        self.convertWhitespaceEscapes = convertWhitespaceEscapes

        if multiline:
            self.flags = re.MULTILINE | re.DOTALL
            self.pattern = r'%s(?:[^%s%s]' % \
                ( re.escape(self.quoteChar),
                  _escapeRegexRangeChars(self.endQuoteChar[0]),
                  (escChar is not None and _escapeRegexRangeChars(escChar) or '') )
        else:
            self.flags = 0
            self.pattern = r'%s(?:[^%s\n\r%s]' % \
                ( re.escape(self.quoteChar),
                  _escapeRegexRangeChars(self.endQuoteChar[0]),
                  (escChar is not None and _escapeRegexRangeChars(escChar) or '') )
        if len(self.endQuoteChar) > 1:
            self.pattern += (
                '|(?:' + ')|(?:'.join("%s[^%s]" % (re.escape(self.endQuoteChar[:i]),
                                               _escapeRegexRangeChars(self.endQuoteChar[i]))
                                    for i in range(len(self.endQuoteChar)-1,0,-1)) + ')'
                )
        if escQuote:
            self.pattern += (r'|(?:%s)' % re.escape(escQuote))
        if escChar:
            self.pattern += (r'|(?:%s.)' % re.escape(escChar))
            self.escCharReplacePattern = re.escape(self.escChar)+"(.)"
        self.pattern += (r')*%s' % re.escape(self.endQuoteChar))

        try:
            self.re = re.compile(self.pattern, self.flags)
            self.reString = self.pattern
        except sre_constants.error:
            warnings.warn("invalid pattern (%s) passed to Regex" % self.pattern,
                SyntaxWarning, stacklevel=2)
            raise

        self.name = _ustr(self)
        self.errmsg = "Expected " + self.name
        self.mayIndexError = False
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        result = instring[loc] == self.firstQuoteChar and self.re.match(instring,loc) or None
        if not result:
            raise ParseException(instring, loc, self.errmsg, self)

        loc = result.end()
        ret = result.group()

        if self.unquoteResults:

            # strip off quotes
            ret = ret[self.quoteCharLen:-self.endQuoteCharLen]

            if isinstance(ret,basestring):
                # replace escaped whitespace
                if '\\' in ret and self.convertWhitespaceEscapes:
                    ws_map = {
                        r'\t' : '\t',
                        r'\n' : '\n',
                        r'\f' : '\f',
                        r'\r' : '\r',
                    }
                    for wslit,wschar in ws_map.items():
                        ret = ret.replace(wslit, wschar)

                # replace escaped characters
                if self.escChar:
                    ret = re.sub(self.escCharReplacePattern,"\g<1>",ret)

                # replace escaped quotes
                if self.escQuote:
                    ret = ret.replace(self.escQuote, self.endQuoteChar)

        return loc, ret

    def __str__( self ):
        try:
            return super(QuotedString,self).__str__()
        except:
            pass

        if self.strRepr is None:
            self.strRepr = "quoted string, starting with %s ending with %s" % (self.quoteChar, self.endQuoteChar)

        return self.strRepr


class CharsNotIn(Token):
    """Token for matching words composed of characters *not* in a given set.
       Defined with string containing all disallowed characters, and an optional
       minimum, maximum, and/or exact length.  The default value for C{min} is 1 (a
       minimum value < 1 is not valid); the default values for C{max} and C{exact}
       are 0, meaning no maximum or exact length restriction.
    """
    def __init__( self, notChars, min=1, max=0, exact=0 ):
        super(CharsNotIn,self).__init__()
        self.skipWhitespace = False
        self.notChars = notChars

        if min < 1:
            raise ValueError("cannot specify a minimum length < 1; use Optional(CharsNotIn()) if zero-length char group is permitted")

        self.minLen = min

        if max > 0:
            self.maxLen = max
        else:
            self.maxLen = _MAX_INT

        if exact > 0:
            self.maxLen = exact
            self.minLen = exact

        self.name = _ustr(self)
        self.errmsg = "Expected " + self.name
        self.mayReturnEmpty = ( self.minLen == 0 )
        self.mayIndexError = False

    def parseImpl( self, instring, loc, doActions=True ):
        if instring[loc] in self.notChars:
            raise ParseException(instring, loc, self.errmsg, self)

        start = loc
        loc += 1
        notchars = self.notChars
        maxlen = min( start+self.maxLen, len(instring) )
        while loc < maxlen and \
              (instring[loc] not in notchars):
            loc += 1

        if loc - start < self.minLen:
            raise ParseException(instring, loc, self.errmsg, self)

        return loc, instring[start:loc]

    def __str__( self ):
        try:
            return super(CharsNotIn, self).__str__()
        except:
            pass

        if self.strRepr is None:
            if len(self.notChars) > 4:
                self.strRepr = "!W:(%s...)" % self.notChars[:4]
            else:
                self.strRepr = "!W:(%s)" % self.notChars

        return self.strRepr

class White(Token):
    """Special matching class for matching whitespace.  Normally, whitespace is ignored
       by pyparsing grammars.  This class is included when some whitespace structures
       are significant.  Define with a string containing the whitespace characters to be
       matched; default is C{" \\t\\r\\n"}.  Also takes optional C{min}, C{max}, and C{exact} arguments,
       as defined for the C{L{Word}} class."""
    whiteStrs = {
        " " : "<SPC>",
        "\t": "<TAB>",
        "\n": "<LF>",
        "\r": "<CR>",
        "\f": "<FF>",
        }
    def __init__(self, ws=" \t\r\n", min=1, max=0, exact=0):
        super(White,self).__init__()
        self.matchWhite = ws
        self.setWhitespaceChars( "".join(c for c in self.whiteChars if c not in self.matchWhite) )
        #~ self.leaveWhitespace()
        self.name = ("".join(White.whiteStrs[c] for c in self.matchWhite))
        self.mayReturnEmpty = True
        self.errmsg = "Expected " + self.name

        self.minLen = min

        if max > 0:
            self.maxLen = max
        else:
            self.maxLen = _MAX_INT

        if exact > 0:
            self.maxLen = exact
            self.minLen = exact

    def parseImpl( self, instring, loc, doActions=True ):
        if not(instring[ loc ] in self.matchWhite):
            raise ParseException(instring, loc, self.errmsg, self)
        start = loc
        loc += 1
        maxloc = start + self.maxLen
        maxloc = min( maxloc, len(instring) )
        while loc < maxloc and instring[loc] in self.matchWhite:
            loc += 1

        if loc - start < self.minLen:
            raise ParseException(instring, loc, self.errmsg, self)

        return loc, instring[start:loc]


class _PositionToken(Token):
    def __init__( self ):
        super(_PositionToken,self).__init__()
        self.name=self.__class__.__name__
        self.mayReturnEmpty = True
        self.mayIndexError = False

class GoToColumn(_PositionToken):
    """Token to advance to a specific column of input text; useful for tabular report scraping."""
    def __init__( self, colno ):
        super(GoToColumn,self).__init__()
        self.col = colno

    def preParse( self, instring, loc ):
        if col(loc,instring) != self.col:
            instrlen = len(instring)
            if self.ignoreExprs:
                loc = self._skipIgnorables( instring, loc )
            while loc < instrlen and instring[loc].isspace() and col( loc, instring ) != self.col :
                loc += 1
        return loc

    def parseImpl( self, instring, loc, doActions=True ):
        thiscol = col( loc, instring )
        if thiscol > self.col:
            raise ParseException( instring, loc, "Text not in expected column", self )
        newloc = loc + self.col - thiscol
        ret = instring[ loc: newloc ]
        return newloc, ret

class LineStart(_PositionToken):
    """Matches if current position is at the beginning of a line within the parse string"""
    def __init__( self ):
        super(LineStart,self).__init__()
        self.setWhitespaceChars( ParserElement.DEFAULT_WHITE_CHARS.replace("\n","") )
        self.errmsg = "Expected start of line"

    def preParse( self, instring, loc ):
        preloc = super(LineStart,self).preParse(instring,loc)
        if instring[preloc] == "\n":
            loc += 1
        return loc

    def parseImpl( self, instring, loc, doActions=True ):
        if not( loc==0 or
            (loc == self.preParse( instring, 0 )) or
            (instring[loc-1] == "\n") ): #col(loc, instring) != 1:
            raise ParseException(instring, loc, self.errmsg, self)
        return loc, []

class LineEnd(_PositionToken):
    """Matches if current position is at the end of a line within the parse string"""
    def __init__( self ):
        super(LineEnd,self).__init__()
        self.setWhitespaceChars( ParserElement.DEFAULT_WHITE_CHARS.replace("\n","") )
        self.errmsg = "Expected end of line"

    def parseImpl( self, instring, loc, doActions=True ):
        if loc<len(instring):
            if instring[loc] == "\n":
                return loc+1, "\n"
            else:
                raise ParseException(instring, loc, self.errmsg, self)
        elif loc == len(instring):
            return loc+1, []
        else:
            raise ParseException(instring, loc, self.errmsg, self)

class StringStart(_PositionToken):
    """Matches if current position is at the beginning of the parse string"""
    def __init__( self ):
        super(StringStart,self).__init__()
        self.errmsg = "Expected start of text"

    def parseImpl( self, instring, loc, doActions=True ):
        if loc != 0:
            # see if entire string up to here is just whitespace and ignoreables
            if loc != self.preParse( instring, 0 ):
                raise ParseException(instring, loc, self.errmsg, self)
        return loc, []

class StringEnd(_PositionToken):
    """Matches if current position is at the end of the parse string"""
    def __init__( self ):
        super(StringEnd,self).__init__()
        self.errmsg = "Expected end of text"

    def parseImpl( self, instring, loc, doActions=True ):
        if loc < len(instring):
            raise ParseException(instring, loc, self.errmsg, self)
        elif loc == len(instring):
            return loc+1, []
        elif loc > len(instring):
            return loc, []
        else:
            raise ParseException(instring, loc, self.errmsg, self)

class WordStart(_PositionToken):
    """Matches if the current position is at the beginning of a Word, and
       is not preceded by any character in a given set of C{wordChars}
       (default=C{printables}). To emulate the C{\b} behavior of regular expressions,
       use C{WordStart(alphanums)}. C{WordStart} will also match at the beginning of
       the string being parsed, or at the beginning of a line.
    """
    def __init__(self, wordChars = printables):
        super(WordStart,self).__init__()
        self.wordChars = set(wordChars)
        self.errmsg = "Not at the start of a word"

    def parseImpl(self, instring, loc, doActions=True ):
        if loc != 0:
            if (instring[loc-1] in self.wordChars or
                instring[loc] not in self.wordChars):
                raise ParseException(instring, loc, self.errmsg, self)
        return loc, []

class WordEnd(_PositionToken):
    """Matches if the current position is at the end of a Word, and
       is not followed by any character in a given set of C{wordChars}
       (default=C{printables}). To emulate the C{\b} behavior of regular expressions,
       use C{WordEnd(alphanums)}. C{WordEnd} will also match at the end of
       the string being parsed, or at the end of a line.
    """
    def __init__(self, wordChars = printables):
        super(WordEnd,self).__init__()
        self.wordChars = set(wordChars)
        self.skipWhitespace = False
        self.errmsg = "Not at the end of a word"

    def parseImpl(self, instring, loc, doActions=True ):
        instrlen = len(instring)
        if instrlen>0 and loc<instrlen:
            if (instring[loc] in self.wordChars or
                instring[loc-1] not in self.wordChars):
                raise ParseException(instring, loc, self.errmsg, self)
        return loc, []


class ParseExpression(ParserElement):
    """Abstract subclass of ParserElement, for combining and post-processing parsed tokens."""
    def __init__( self, exprs, savelist = False ):
        super(ParseExpression,self).__init__(savelist)
        if isinstance( exprs, _generatorType ):
            exprs = list(exprs)

        if isinstance( exprs, basestring ):
            self.exprs = [ ParserElement._literalStringClass( exprs ) ]
        elif isinstance( exprs, collections.Sequence ):
            # if sequence of strings provided, wrap with Literal
            if all(isinstance(expr, basestring) for expr in exprs):
                exprs = map(ParserElement._literalStringClass, exprs)
            self.exprs = list(exprs)
        else:
            try:
                self.exprs = list( exprs )
            except TypeError:
                self.exprs = [ exprs ]
        self.callPreparse = False

    def __getitem__( self, i ):
        return self.exprs[i]

    def append( self, other ):
        self.exprs.append( other )
        self.strRepr = None
        return self

    def leaveWhitespace( self ):
        """Extends C{leaveWhitespace} defined in base class, and also invokes C{leaveWhitespace} on
           all contained expressions."""
        self.skipWhitespace = False
        self.exprs = [ e.copy() for e in self.exprs ]
        for e in self.exprs:
            e.leaveWhitespace()
        return self

    def ignore( self, other ):
        if isinstance( other, Suppress ):
            if other not in self.ignoreExprs:
                super( ParseExpression, self).ignore( other )
                for e in self.exprs:
                    e.ignore( self.ignoreExprs[-1] )
        else:
            super( ParseExpression, self).ignore( other )
            for e in self.exprs:
                e.ignore( self.ignoreExprs[-1] )
        return self

    def __str__( self ):
        try:
            return super(ParseExpression,self).__str__()
        except:
            pass

        if self.strRepr is None:
            self.strRepr = "%s:(%s)" % ( self.__class__.__name__, _ustr(self.exprs) )
        return self.strRepr

    def streamline( self ):
        super(ParseExpression,self).streamline()

        for e in self.exprs:
            e.streamline()

        # collapse nested And's of the form And( And( And( a,b), c), d) to And( a,b,c,d )
        # but only if there are no parse actions or resultsNames on the nested And's
        # (likewise for Or's and MatchFirst's)
        if ( len(self.exprs) == 2 ):
            other = self.exprs[0]
            if ( isinstance( other, self.__class__ ) and
                  not(other.parseAction) and
                  other.resultsName is None and
                  not other.debug ):
                self.exprs = other.exprs[:] + [ self.exprs[1] ]
                self.strRepr = None
                self.mayReturnEmpty |= other.mayReturnEmpty
                self.mayIndexError  |= other.mayIndexError

            other = self.exprs[-1]
            if ( isinstance( other, self.__class__ ) and
                  not(other.parseAction) and
                  other.resultsName is None and
                  not other.debug ):
                self.exprs = self.exprs[:-1] + other.exprs[:]
                self.strRepr = None
                self.mayReturnEmpty |= other.mayReturnEmpty
                self.mayIndexError  |= other.mayIndexError

        self.errmsg = "Expected " + _ustr(self)
        
        return self

    def setResultsName( self, name, listAllMatches=False ):
        ret = super(ParseExpression,self).setResultsName(name,listAllMatches)
        return ret

    def validate( self, validateTrace=[] ):
        tmp = validateTrace[:]+[self]
        for e in self.exprs:
            e.validate(tmp)
        self.checkRecursion( [] )
        
    def copy(self):
        ret = super(ParseExpression,self).copy()
        ret.exprs = [e.copy() for e in self.exprs]
        return ret

class And(ParseExpression):
    """Requires all given C{ParseExpression}s to be found in the given order.
       Expressions may be separated by whitespace.
       May be constructed using the C{'+'} operator.
       May also be constructed using the C{'-'} operator, which will suppress backtracking.
    """

    class _ErrorStop(Empty):
        def __init__(self, *args, **kwargs):
            super(And._ErrorStop,self).__init__(*args, **kwargs)
            self.name = '-'
            self.leaveWhitespace()

    def __init__( self, exprs, savelist = True ):
        super(And,self).__init__(exprs, savelist)
        self.mayReturnEmpty = all(e.mayReturnEmpty for e in self.exprs)
        self.setWhitespaceChars( self.exprs[0].whiteChars )
        self.skipWhitespace = self.exprs[0].skipWhitespace
        self.callPreparse = True

    def parseImpl( self, instring, loc, doActions=True ):
        # pass False as last arg to _parse for first element, since we already
        # pre-parsed the string as part of our And pre-parsing
        loc, resultlist = self.exprs[0]._parse( instring, loc, doActions, callPreParse=False )
        errorStop = False
        for e in self.exprs[1:]:
            if isinstance(e, And._ErrorStop):
                errorStop = True
                continue
            if errorStop:
                try:
                    loc, exprtokens = e._parse( instring, loc, doActions )
                except ParseSyntaxException:
                    raise
                except ParseBaseException as pe:
                    pe.__traceback__ = None
                    raise ParseSyntaxException(pe)
                except IndexError:
                    raise ParseSyntaxException( ParseException(instring, len(instring), self.errmsg, self) )
            else:
                loc, exprtokens = e._parse( instring, loc, doActions )
            if exprtokens or exprtokens.haskeys():
                resultlist += exprtokens
        return loc, resultlist

    def __iadd__(self, other ):
        if isinstance( other, basestring ):
            other = ParserElement._literalStringClass( other )
        return self.append( other ) #And( [ self, other ] )

    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )
            if not e.mayReturnEmpty:
                break

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + " ".join(_ustr(e) for e in self.exprs) + "}"

        return self.strRepr


class Or(ParseExpression):
    """Requires that at least one C{ParseExpression} is found.
       If two expressions match, the expression that matches the longest string will be used.
       May be constructed using the C{'^'} operator.
    """
    def __init__( self, exprs, savelist = False ):
        super(Or,self).__init__(exprs, savelist)
        if self.exprs:
            self.mayReturnEmpty = any(e.mayReturnEmpty for e in self.exprs)
        else:
            self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        maxExcLoc = -1
        maxException = None
        matches = []
        for e in self.exprs:
            try:
                loc2 = e.tryParse( instring, loc )
            except ParseException as err:
                err.__traceback__ = None
                if err.loc > maxExcLoc:
                    maxException = err
                    maxExcLoc = err.loc
            except IndexError:
                if len(instring) > maxExcLoc:
                    maxException = ParseException(instring,len(instring),e.errmsg,self)
                    maxExcLoc = len(instring)
            else:
                # save match among all matches, to retry longest to shortest
                matches.append((loc2, e))

        if matches:
            matches.sort(key=lambda x: -x[0])
            for _,e in matches:
                try:
                    return e._parse( instring, loc, doActions )
                except ParseException as err:
                    err.__traceback__ = None
                    if err.loc > maxExcLoc:
                        maxException = err
                        maxExcLoc = err.loc

        if maxException is not None:
            maxException.msg = self.errmsg
            raise maxException
        else:
            raise ParseException(instring, loc, "no defined alternatives to match", self)


    def __ixor__(self, other ):
        if isinstance( other, basestring ):
            other = ParserElement._literalStringClass( other )
        return self.append( other ) #Or( [ self, other ] )

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + " ^ ".join(_ustr(e) for e in self.exprs) + "}"

        return self.strRepr

    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )


class MatchFirst(ParseExpression):
    """Requires that at least one C{ParseExpression} is found.
       If two expressions match, the first one listed is the one that will match.
       May be constructed using the C{'|'} operator.
    """
    def __init__( self, exprs, savelist = False ):
        super(MatchFirst,self).__init__(exprs, savelist)
        if self.exprs:
            self.mayReturnEmpty = any(e.mayReturnEmpty for e in self.exprs)
        else:
            self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        maxExcLoc = -1
        maxException = None
        for e in self.exprs:
            try:
                ret = e._parse( instring, loc, doActions )
                return ret
            except ParseException as err:
                if err.loc > maxExcLoc:
                    maxException = err
                    maxExcLoc = err.loc
            except IndexError:
                if len(instring) > maxExcLoc:
                    maxException = ParseException(instring,len(instring),e.errmsg,self)
                    maxExcLoc = len(instring)

        # only got here if no expression matched, raise exception for match that made it the furthest
        else:
            if maxException is not None:
                maxException.msg = self.errmsg
                raise maxException
            else:
                raise ParseException(instring, loc, "no defined alternatives to match", self)

    def __ior__(self, other ):
        if isinstance( other, basestring ):
            other = ParserElement._literalStringClass( other )
        return self.append( other ) #MatchFirst( [ self, other ] )

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + " | ".join(_ustr(e) for e in self.exprs) + "}"

        return self.strRepr

    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )


class Each(ParseExpression):
    """Requires all given C{ParseExpression}s to be found, but in any order.
       Expressions may be separated by whitespace.
       May be constructed using the C{'&'} operator.
    """
    def __init__( self, exprs, savelist = True ):
        super(Each,self).__init__(exprs, savelist)
        self.mayReturnEmpty = all(e.mayReturnEmpty for e in self.exprs)
        self.skipWhitespace = True
        self.initExprGroups = True

    def parseImpl( self, instring, loc, doActions=True ):
        if self.initExprGroups:
            self.opt1map = dict((id(e.expr),e) for e in self.exprs if isinstance(e,Optional))
            opt1 = [ e.expr for e in self.exprs if isinstance(e,Optional) ]
            opt2 = [ e for e in self.exprs if e.mayReturnEmpty and not isinstance(e,Optional)]
            self.optionals = opt1 + opt2
            self.multioptionals = [ e.expr for e in self.exprs if isinstance(e,ZeroOrMore) ]
            self.multirequired = [ e.expr for e in self.exprs if isinstance(e,OneOrMore) ]
            self.required = [ e for e in self.exprs if not isinstance(e,(Optional,ZeroOrMore,OneOrMore)) ]
            self.required += self.multirequired
            self.initExprGroups = False
        tmpLoc = loc
        tmpReqd = self.required[:]
        tmpOpt  = self.optionals[:]
        matchOrder = []

        keepMatching = True
        while keepMatching:
            tmpExprs = tmpReqd + tmpOpt + self.multioptionals + self.multirequired
            failed = []
            for e in tmpExprs:
                try:
                    tmpLoc = e.tryParse( instring, tmpLoc )
                except ParseException:
                    failed.append(e)
                else:
                    matchOrder.append(self.opt1map.get(id(e),e))
                    if e in tmpReqd:
                        tmpReqd.remove(e)
                    elif e in tmpOpt:
                        tmpOpt.remove(e)
            if len(failed) == len(tmpExprs):
                keepMatching = False

        if tmpReqd:
            missing = ", ".join(_ustr(e) for e in tmpReqd)
            raise ParseException(instring,loc,"Missing one or more required elements (%s)" % missing )

        # add any unmatched Optionals, in case they have default values defined
        matchOrder += [e for e in self.exprs if isinstance(e,Optional) and e.expr in tmpOpt]

        resultlist = []
        for e in matchOrder:
            loc,results = e._parse(instring,loc,doActions)
            resultlist.append(results)

        finalResults = ParseResults()
        for r in resultlist:
            dups = {}
            for k in r.keys():
                if k in finalResults:
                    tmp = ParseResults(finalResults[k])
                    tmp += ParseResults(r[k])
                    dups[k] = tmp
            finalResults += ParseResults(r)
            for k,v in dups.items():
                finalResults[k] = v
        return loc, finalResults

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + " & ".join(_ustr(e) for e in self.exprs) + "}"

        return self.strRepr

    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )


class ParseElementEnhance(ParserElement):
    """Abstract subclass of C{ParserElement}, for combining and post-processing parsed tokens."""
    def __init__( self, expr, savelist=False ):
        super(ParseElementEnhance,self).__init__(savelist)
        if isinstance( expr, basestring ):
            expr = ParserElement._literalStringClass(expr)
        self.expr = expr
        self.strRepr = None
        if expr is not None:
            self.mayIndexError = expr.mayIndexError
            self.mayReturnEmpty = expr.mayReturnEmpty
            self.setWhitespaceChars( expr.whiteChars )
            self.skipWhitespace = expr.skipWhitespace
            self.saveAsList = expr.saveAsList
            self.callPreparse = expr.callPreparse
            self.ignoreExprs.extend(expr.ignoreExprs)

    def parseImpl( self, instring, loc, doActions=True ):
        if self.expr is not None:
            return self.expr._parse( instring, loc, doActions, callPreParse=False )
        else:
            raise ParseException("",loc,self.errmsg,self)

    def leaveWhitespace( self ):
        self.skipWhitespace = False
        self.expr = self.expr.copy()
        if self.expr is not None:
            self.expr.leaveWhitespace()
        return self

    def ignore( self, other ):
        if isinstance( other, Suppress ):
            if other not in self.ignoreExprs:
                super( ParseElementEnhance, self).ignore( other )
                if self.expr is not None:
                    self.expr.ignore( self.ignoreExprs[-1] )
        else:
            super( ParseElementEnhance, self).ignore( other )
            if self.expr is not None:
                self.expr.ignore( self.ignoreExprs[-1] )
        return self

    def streamline( self ):
        super(ParseElementEnhance,self).streamline()
        if self.expr is not None:
            self.expr.streamline()
        return self

    def checkRecursion( self, parseElementList ):
        if self in parseElementList:
            raise RecursiveGrammarException( parseElementList+[self] )
        subRecCheckList = parseElementList[:] + [ self ]
        if self.expr is not None:
            self.expr.checkRecursion( subRecCheckList )

    def validate( self, validateTrace=[] ):
        tmp = validateTrace[:]+[self]
        if self.expr is not None:
            self.expr.validate(tmp)
        self.checkRecursion( [] )

    def __str__( self ):
        try:
            return super(ParseElementEnhance,self).__str__()
        except:
            pass

        if self.strRepr is None and self.expr is not None:
            self.strRepr = "%s:(%s)" % ( self.__class__.__name__, _ustr(self.expr) )
        return self.strRepr


class FollowedBy(ParseElementEnhance):
    """Lookahead matching of the given parse expression.  C{FollowedBy}
    does *not* advance the parsing position within the input string, it only
    verifies that the specified parse expression matches at the current
    position.  C{FollowedBy} always returns a null token list."""
    def __init__( self, expr ):
        super(FollowedBy,self).__init__(expr)
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        self.expr.tryParse( instring, loc )
        return loc, []


class NotAny(ParseElementEnhance):
    """Lookahead to disallow matching with the given parse expression.  C{NotAny}
    does *not* advance the parsing position within the input string, it only
    verifies that the specified parse expression does *not* match at the current
    position.  Also, C{NotAny} does *not* skip over leading whitespace. C{NotAny}
    always returns a null token list.  May be constructed using the '~' operator."""
    def __init__( self, expr ):
        super(NotAny,self).__init__(expr)
        #~ self.leaveWhitespace()
        self.skipWhitespace = False  # do NOT use self.leaveWhitespace(), don't want to propagate to exprs
        self.mayReturnEmpty = True
        self.errmsg = "Found unwanted token, "+_ustr(self.expr)

    def parseImpl( self, instring, loc, doActions=True ):
        if self.expr.canParseNext(instring, loc):
            raise ParseException(instring, loc, self.errmsg, self)
        return loc, []

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "~{" + _ustr(self.expr) + "}"

        return self.strRepr


class OneOrMore(ParseElementEnhance):
    """Repetition of one or more of the given expression.
    
       Parameters:
        - expr - expression that must match one or more times
        - stopOn - (default=None) - expression for a terminating sentinel
          (only required if the sentinel would ordinarily match the repetition 
          expression)          
    """
    def __init__( self, expr, stopOn=None):
        super(OneOrMore, self).__init__(expr)
        ender = stopOn
        if isinstance(ender, basestring):
            ender = ParserElement._literalStringClass(ender)
        self.not_ender = ~ender if ender is not None else None

    def parseImpl( self, instring, loc, doActions=True ):
        self_expr_parse = self.expr._parse
        self_skip_ignorables = self._skipIgnorables
        check_ender = self.not_ender is not None
        if check_ender:
            try_not_ender = self.not_ender.tryParse
        
        # must be at least one (but first see if we are the stopOn sentinel;
        # if so, fail)
        if check_ender:
            try_not_ender(instring, loc)
        loc, tokens = self_expr_parse( instring, loc, doActions, callPreParse=False )
        try:
            hasIgnoreExprs = (not not self.ignoreExprs)
            while 1:
                if check_ender:
                    try_not_ender(instring, loc)
                if hasIgnoreExprs:
                    preloc = self_skip_ignorables( instring, loc )
                else:
                    preloc = loc
                loc, tmptokens = self_expr_parse( instring, preloc, doActions )
                if tmptokens or tmptokens.haskeys():
                    tokens += tmptokens
        except (ParseException,IndexError):
            pass

        return loc, tokens

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + _ustr(self.expr) + "}..."

        return self.strRepr

    def setResultsName( self, name, listAllMatches=False ):
        ret = super(OneOrMore,self).setResultsName(name,listAllMatches)
        ret.saveAsList = True
        return ret

class ZeroOrMore(OneOrMore):
    """Optional repetition of zero or more of the given expression.
    
       Parameters:
        - expr - expression that must match zero or more times
        - stopOn - (default=None) - expression for a terminating sentinel
          (only required if the sentinel would ordinarily match the repetition 
          expression)          
    """
    def __init__( self, expr, stopOn=None):
        super(ZeroOrMore,self).__init__(expr, stopOn=stopOn)
        self.mayReturnEmpty = True
        
    def parseImpl( self, instring, loc, doActions=True ):
        try:
            return super(ZeroOrMore, self).parseImpl(instring, loc, doActions)
        except (ParseException,IndexError):
            return loc, []

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "[" + _ustr(self.expr) + "]..."

        return self.strRepr

class _NullToken(object):
    def __bool__(self):
        return False
    __nonzero__ = __bool__
    def __str__(self):
        return ""

_optionalNotMatched = _NullToken()
class Optional(ParseElementEnhance):
    """Optional matching of the given expression.

       Parameters:
        - expr - expression that must match zero or more times
        - default (optional) - value to be returned if the optional expression
          is not found.
    """
    def __init__( self, expr, default=_optionalNotMatched ):
        super(Optional,self).__init__( expr, savelist=False )
        self.defaultValue = default
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        try:
            loc, tokens = self.expr._parse( instring, loc, doActions, callPreParse=False )
        except (ParseException,IndexError):
            if self.defaultValue is not _optionalNotMatched:
                if self.expr.resultsName:
                    tokens = ParseResults([ self.defaultValue ])
                    tokens[self.expr.resultsName] = self.defaultValue
                else:
                    tokens = [ self.defaultValue ]
            else:
                tokens = []
        return loc, tokens

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "[" + _ustr(self.expr) + "]"

        return self.strRepr

class SkipTo(ParseElementEnhance):
    """Token for skipping over all undefined text until the matched expression is found.

       Parameters:
        - expr - target expression marking the end of the data to be skipped
        - include - (default=False) if True, the target expression is also parsed 
          (the skipped text and target expression are returned as a 2-element list).
        - ignore - (default=None) used to define grammars (typically quoted strings and 
          comments) that might contain false matches to the target expression
        - failOn - (default=None) define expressions that are not allowed to be 
          included in the skipped test; if found before the target expression is found, 
          the SkipTo is not a match
    """
    def __init__( self, other, include=False, ignore=None, failOn=None ):
        super( SkipTo, self ).__init__( other )
        self.ignoreExpr = ignore
        self.mayReturnEmpty = True
        self.mayIndexError = False
        self.includeMatch = include
        self.asList = False
        if isinstance(failOn, basestring):
            self.failOn = ParserElement._literalStringClass(failOn)
        else:
            self.failOn = failOn
        self.errmsg = "No match found for "+_ustr(self.expr)

    def parseImpl( self, instring, loc, doActions=True ):
        startloc = loc
        instrlen = len(instring)
        expr = self.expr
        expr_parse = self.expr._parse
        self_failOn_canParseNext = self.failOn.canParseNext if self.failOn is not None else None
        self_ignoreExpr_tryParse = self.ignoreExpr.tryParse if self.ignoreExpr is not None else None
        
        tmploc = loc
        while tmploc <= instrlen:
            if self_failOn_canParseNext is not None:
                # break if failOn expression matches
                if self_failOn_canParseNext(instring, tmploc):
                    break
                    
            if self_ignoreExpr_tryParse is not None:
                # advance past ignore expressions
                while 1:
                    try:
                        tmploc = self_ignoreExpr_tryParse(instring, tmploc)
                    except ParseBaseException:
                        break
            
            try:
                expr_parse(instring, tmploc, doActions=False, callPreParse=False)
            except (ParseException, IndexError):
                # no match, advance loc in string
                tmploc += 1
            else:
                # matched skipto expr, done
                break

        else:
            # ran off the end of the input string without matching skipto expr, fail
            raise ParseException(instring, loc, self.errmsg, self)

        # build up return values
        loc = tmploc
        skiptext = instring[startloc:loc]
        skipresult = ParseResults(skiptext)
        
        if self.includeMatch:
            loc, mat = expr_parse(instring,loc,doActions,callPreParse=False)
            skipresult += mat

        return loc, skipresult

class Forward(ParseElementEnhance):
    """Forward declaration of an expression to be defined later -
       used for recursive grammars, such as algebraic infix notation.
       When the expression is known, it is assigned to the C{Forward} variable using the '<<' operator.

       Note: take care when assigning to C{Forward} not to overlook precedence of operators.
       Specifically, '|' has a lower precedence than '<<', so that::
          fwdExpr << a | b | c
       will actually be evaluated as::
          (fwdExpr << a) | b | c
       thereby leaving b and c out as parseable alternatives.  It is recommended that you
       explicitly group the values inserted into the C{Forward}::
          fwdExpr << (a | b | c)
       Converting to use the '<<=' operator instead will avoid this problem.
    """
    def __init__( self, other=None ):
        super(Forward,self).__init__( other, savelist=False )

    def __lshift__( self, other ):
        if isinstance( other, basestring ):
            other = ParserElement._literalStringClass(other)
        self.expr = other
        self.strRepr = None
        self.mayIndexError = self.expr.mayIndexError
        self.mayReturnEmpty = self.expr.mayReturnEmpty
        self.setWhitespaceChars( self.expr.whiteChars )
        self.skipWhitespace = self.expr.skipWhitespace
        self.saveAsList = self.expr.saveAsList
        self.ignoreExprs.extend(self.expr.ignoreExprs)
        return self
        
    def __ilshift__(self, other):
        return self << other
    
    def leaveWhitespace( self ):
        self.skipWhitespace = False
        return self

    def streamline( self ):
        if not self.streamlined:
            self.streamlined = True
            if self.expr is not None:
                self.expr.streamline()
        return self

    def validate( self, validateTrace=[] ):
        if self not in validateTrace:
            tmp = validateTrace[:]+[self]
            if self.expr is not None:
                self.expr.validate(tmp)
        self.checkRecursion([])

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name
        return self.__class__.__name__ + ": ..."

        # stubbed out for now - creates awful memory and perf issues
        self._revertClass = self.__class__
        self.__class__ = _ForwardNoRecurse
        try:
            if self.expr is not None:
                retString = _ustr(self.expr)
            else:
                retString = "None"
        finally:
            self.__class__ = self._revertClass
        return self.__class__.__name__ + ": " + retString

    def copy(self):
        if self.expr is not None:
            return super(Forward,self).copy()
        else:
            ret = Forward()
            ret <<= self
            return ret

class _ForwardNoRecurse(Forward):
    def __str__( self ):
        return "..."

class TokenConverter(ParseElementEnhance):
    """Abstract subclass of C{ParseExpression}, for converting parsed results."""
    def __init__( self, expr, savelist=False ):
        super(TokenConverter,self).__init__( expr )#, savelist )
        self.saveAsList = False

class Combine(TokenConverter):
    """Converter to concatenate all matching tokens to a single string.
       By default, the matching patterns must also be contiguous in the input string;
       this can be disabled by specifying C{'adjacent=False'} in the constructor.
    """
    def __init__( self, expr, joinString="", adjacent=True ):
        super(Combine,self).__init__( expr )
        # suppress whitespace-stripping in contained parse expressions, but re-enable it on the Combine itself
        if adjacent:
            self.leaveWhitespace()
        self.adjacent = adjacent
        self.skipWhitespace = True
        self.joinString = joinString
        self.callPreparse = True

    def ignore( self, other ):
        if self.adjacent:
            ParserElement.ignore(self, other)
        else:
            super( Combine, self).ignore( other )
        return self

    def postParse( self, instring, loc, tokenlist ):
        retToks = tokenlist.copy()
        del retToks[:]
        retToks += ParseResults([ "".join(tokenlist._asStringList(self.joinString)) ], modal=self.modalResults)

        if self.resultsName and retToks.haskeys():
            return [ retToks ]
        else:
            return retToks

class Group(TokenConverter):
    """Converter to return the matched tokens as a list - useful for returning tokens of C{L{ZeroOrMore}} and C{L{OneOrMore}} expressions."""
    def __init__( self, expr ):
        super(Group,self).__init__( expr )
        self.saveAsList = True

    def postParse( self, instring, loc, tokenlist ):
        return [ tokenlist ]

class Dict(TokenConverter):
    """Converter to return a repetitive expression as a list, but also as a dictionary.
       Each element can also be referenced using the first token in the expression as its key.
       Useful for tabular report scraping when the first column can be used as a item key.
    """
    def __init__( self, expr ):
        super(Dict,self).__init__( expr )
        self.saveAsList = True

    def postParse( self, instring, loc, tokenlist ):
        for i,tok in enumerate(tokenlist):
            if len(tok) == 0:
                continue
            ikey = tok[0]
            if isinstance(ikey,int):
                ikey = _ustr(tok[0]).strip()
            if len(tok)==1:
                tokenlist[ikey] = _ParseResultsWithOffset("",i)
            elif len(tok)==2 and not isinstance(tok[1],ParseResults):
                tokenlist[ikey] = _ParseResultsWithOffset(tok[1],i)
            else:
                dictvalue = tok.copy() #ParseResults(i)
                del dictvalue[0]
                if len(dictvalue)!= 1 or (isinstance(dictvalue,ParseResults) and dictvalue.haskeys()):
                    tokenlist[ikey] = _ParseResultsWithOffset(dictvalue,i)
                else:
                    tokenlist[ikey] = _ParseResultsWithOffset(dictvalue[0],i)

        if self.resultsName:
            return [ tokenlist ]
        else:
            return tokenlist


class Suppress(TokenConverter):
    """Converter for ignoring the results of a parsed expression."""
    def postParse( self, instring, loc, tokenlist ):
        return []

    def suppress( self ):
        return self


class OnlyOnce(object):
    """Wrapper for parse actions, to ensure they are only called once."""
    def __init__(self, methodCall):
        self.callable = _trim_arity(methodCall)
        self.called = False
    def __call__(self,s,l,t):
        if not self.called:
            results = self.callable(s,l,t)
            self.called = True
            return results
        raise ParseException(s,l,"")
    def reset(self):
        self.called = False

def traceParseAction(f):
    """Decorator for debugging parse actions."""
    f = _trim_arity(f)
    def z(*paArgs):
        thisFunc = f.__name__
        s,l,t = paArgs[-3:]
        if len(paArgs)>3:
            thisFunc = paArgs[0].__class__.__name__ + '.' + thisFunc
        sys.stderr.write( ">>entering %s(line: '%s', %d, %s)\n" % (thisFunc,line(l,s),l,t) )
        try:
            ret = f(*paArgs)
        except Exception as exc:
            sys.stderr.write( "<<leaving %s (exception: %s)\n" % (thisFunc,exc) )
            raise
        sys.stderr.write( "<<leaving %s (ret: %s)\n" % (thisFunc,ret) )
        return ret
    try:
        z.__name__ = f.__name__
    except AttributeError:
        pass
    return z

#
# global helpers
#
def delimitedList( expr, delim=",", combine=False ):
    """Helper to define a delimited list of expressions - the delimiter defaults to ','.
       By default, the list elements and delimiters can have intervening whitespace, and
       comments, but this can be overridden by passing C{combine=True} in the constructor.
       If C{combine} is set to C{True}, the matching tokens are returned as a single token
       string, with the delimiters included; otherwise, the matching tokens are returned
       as a list of tokens, with the delimiters suppressed.
    """
    dlName = _ustr(expr)+" ["+_ustr(delim)+" "+_ustr(expr)+"]..."
    if combine:
        return Combine( expr + ZeroOrMore( delim + expr ) ).setName(dlName)
    else:
        return ( expr + ZeroOrMore( Suppress( delim ) + expr ) ).setName(dlName)

def countedArray( expr, intExpr=None ):
    """Helper to define a counted list of expressions.
       This helper defines a pattern of the form::
           integer expr expr expr...
       where the leading integer tells how many expr expressions follow.
       The matched tokens returns the array of expr tokens as a list - the leading count token is suppressed.
    """
    arrayExpr = Forward()
    def countFieldParseAction(s,l,t):
        n = t[0]
        arrayExpr << (n and Group(And([expr]*n)) or Group(empty))
        return []
    if intExpr is None:
        intExpr = Word(nums).setParseAction(lambda t:int(t[0]))
    else:
        intExpr = intExpr.copy()
    intExpr.setName("arrayLen")
    intExpr.addParseAction(countFieldParseAction, callDuringTry=True)
    return ( intExpr + arrayExpr ).setName('(len) ' + _ustr(expr) + '...')

def _flatten(L):
    ret = []
    for i in L:
        if isinstance(i,list):
            ret.extend(_flatten(i))
        else:
            ret.append(i)
    return ret

def matchPreviousLiteral(expr):
    """Helper to define an expression that is indirectly defined from
       the tokens matched in a previous expression, that is, it looks
       for a 'repeat' of a previous expression.  For example::
           first = Word(nums)
           second = matchPreviousLiteral(first)
           matchExpr = first + ":" + second
       will match C{"1:1"}, but not C{"1:2"}.  Because this matches a
       previous literal, will also match the leading C{"1:1"} in C{"1:10"}.
       If this is not desired, use C{matchPreviousExpr}.
       Do *not* use with packrat parsing enabled.
    """
    rep = Forward()
    def copyTokenToRepeater(s,l,t):
        if t:
            if len(t) == 1:
                rep << t[0]
            else:
                # flatten t tokens
                tflat = _flatten(t.asList())
                rep << And(Literal(tt) for tt in tflat)
        else:
            rep << Empty()
    expr.addParseAction(copyTokenToRepeater, callDuringTry=True)
    rep.setName('(prev) ' + _ustr(expr))
    return rep

def matchPreviousExpr(expr):
    """Helper to define an expression that is indirectly defined from
       the tokens matched in a previous expression, that is, it looks
       for a 'repeat' of a previous expression.  For example::
           first = Word(nums)
           second = matchPreviousExpr(first)
           matchExpr = first + ":" + second
       will match C{"1:1"}, but not C{"1:2"}.  Because this matches by
       expressions, will *not* match the leading C{"1:1"} in C{"1:10"};
       the expressions are evaluated first, and then compared, so
       C{"1"} is compared with C{"10"}.
       Do *not* use with packrat parsing enabled.
    """
    rep = Forward()
    e2 = expr.copy()
    rep <<= e2
    def copyTokenToRepeater(s,l,t):
        matchTokens = _flatten(t.asList())
        def mustMatchTheseTokens(s,l,t):
            theseTokens = _flatten(t.asList())
            if  theseTokens != matchTokens:
                raise ParseException("",0,"")
        rep.setParseAction( mustMatchTheseTokens, callDuringTry=True )
    expr.addParseAction(copyTokenToRepeater, callDuringTry=True)
    rep.setName('(prev) ' + _ustr(expr))
    return rep

def _escapeRegexRangeChars(s):
    #~  escape these chars: ^-]
    for c in r"\^-]":
        s = s.replace(c,_bslash+c)
    s = s.replace("\n",r"\n")
    s = s.replace("\t",r"\t")
    return _ustr(s)

def oneOf( strs, caseless=False, useRegex=True ):
    """Helper to quickly define a set of alternative Literals, and makes sure to do
       longest-first testing when there is a conflict, regardless of the input order,
       but returns a C{L{MatchFirst}} for best performance.

       Parameters:
        - strs - a string of space-delimited literals, or a list of string literals
        - caseless - (default=False) - treat all literals as caseless
        - useRegex - (default=True) - as an optimization, will generate a Regex
          object; otherwise, will generate a C{MatchFirst} object (if C{caseless=True}, or
          if creating a C{Regex} raises an exception)
    """
    if caseless:
        isequal = ( lambda a,b: a.upper() == b.upper() )
        masks = ( lambda a,b: b.upper().startswith(a.upper()) )
        parseElementClass = CaselessLiteral
    else:
        isequal = ( lambda a,b: a == b )
        masks = ( lambda a,b: b.startswith(a) )
        parseElementClass = Literal

    symbols = []
    if isinstance(strs,basestring):
        symbols = strs.split()
    elif isinstance(strs, collections.Sequence):
        symbols = list(strs[:])
    elif isinstance(strs, _generatorType):
        symbols = list(strs)
    else:
        warnings.warn("Invalid argument to oneOf, expected string or list",
                SyntaxWarning, stacklevel=2)
    if not symbols:
        return NoMatch()

    i = 0
    while i < len(symbols)-1:
        cur = symbols[i]
        for j,other in enumerate(symbols[i+1:]):
            if ( isequal(other, cur) ):
                del symbols[i+j+1]
                break
            elif ( masks(cur, other) ):
                del symbols[i+j+1]
                symbols.insert(i,other)
                cur = other
                break
        else:
            i += 1

    if not caseless and useRegex:
        #~ print (strs,"->", "|".join( [ _escapeRegexChars(sym) for sym in symbols] ))
        try:
            if len(symbols)==len("".join(symbols)):
                return Regex( "[%s]" % "".join(_escapeRegexRangeChars(sym) for sym in symbols) ).setName(' | '.join(symbols))
            else:
                return Regex( "|".join(re.escape(sym) for sym in symbols) ).setName(' | '.join(symbols))
        except:
            warnings.warn("Exception creating Regex for oneOf, building MatchFirst",
                    SyntaxWarning, stacklevel=2)


    # last resort, just use MatchFirst
    return MatchFirst(parseElementClass(sym) for sym in symbols).setName(' | '.join(symbols))

def dictOf( key, value ):
    """Helper to easily and clearly define a dictionary by specifying the respective patterns
       for the key and value.  Takes care of defining the C{L{Dict}}, C{L{ZeroOrMore}}, and C{L{Group}} tokens
       in the proper order.  The key pattern can include delimiting markers or punctuation,
       as long as they are suppressed, thereby leaving the significant key text.  The value
       pattern can include named results, so that the C{Dict} results can include named token
       fields.
    """
    return Dict( ZeroOrMore( Group ( key + value ) ) )

def originalTextFor(expr, asString=True):
    """Helper to return the original, untokenized text for a given expression.  Useful to
       restore the parsed fields of an HTML start tag into the raw tag text itself, or to
       revert separate tokens with intervening whitespace back to the original matching
       input text. By default, returns astring containing the original parsed text.  
       
       If the optional C{asString} argument is passed as C{False}, then the return value is a 
       C{L{ParseResults}} containing any results names that were originally matched, and a 
       single token containing the original matched text from the input string.  So if 
       the expression passed to C{L{originalTextFor}} contains expressions with defined
       results names, you must set C{asString} to C{False} if you want to preserve those
       results name values."""
    locMarker = Empty().setParseAction(lambda s,loc,t: loc)
    endlocMarker = locMarker.copy()
    endlocMarker.callPreparse = False
    matchExpr = locMarker("_original_start") + expr + endlocMarker("_original_end")
    if asString:
        extractText = lambda s,l,t: s[t._original_start:t._original_end]
    else:
        def extractText(s,l,t):
            t[:] = [s[t.pop('_original_start'):t.pop('_original_end')]]
    matchExpr.setParseAction(extractText)
    matchExpr.ignoreExprs = expr.ignoreExprs
    return matchExpr

def ungroup(expr): 
    """Helper to undo pyparsing's default grouping of And expressions, even
       if all but one are non-empty."""
    return TokenConverter(expr).setParseAction(lambda t:t[0])

def locatedExpr(expr):
    """Helper to decorate a returned token with its starting and ending locations in the input string.
       This helper adds the following results names:
        - locn_start = location where matched expression begins
        - locn_end = location where matched expression ends
        - value = the actual parsed results

       Be careful if the input text contains C{<TAB>} characters, you may want to call
       C{L{ParserElement.parseWithTabs}}
    """
    locator = Empty().setParseAction(lambda s,l,t: l)
    return Group(locator("locn_start") + expr("value") + locator.copy().leaveWhitespace()("locn_end"))


# convenience constants for positional expressions
empty       = Empty().setName("empty")
lineStart   = LineStart().setName("lineStart")
lineEnd     = LineEnd().setName("lineEnd")
stringStart = StringStart().setName("stringStart")
stringEnd   = StringEnd().setName("stringEnd")

_escapedPunc = Word( _bslash, r"\[]-*.$+^?()~ ", exact=2 ).setParseAction(lambda s,l,t:t[0][1])
_escapedHexChar = Regex(r"\\0?[xX][0-9a-fA-F]+").setParseAction(lambda s,l,t:unichr(int(t[0].lstrip(r'\0x'),16)))
_escapedOctChar = Regex(r"\\0[0-7]+").setParseAction(lambda s,l,t:unichr(int(t[0][1:],8)))
_singleChar = _escapedPunc | _escapedHexChar | _escapedOctChar | Word(printables, excludeChars=r'\]', exact=1) | Regex(r"\w", re.UNICODE)
_charRange = Group(_singleChar + Suppress("-") + _singleChar)
_reBracketExpr = Literal("[") + Optional("^").setResultsName("negate") + Group( OneOrMore( _charRange | _singleChar ) ).setResultsName("body") + "]"

def srange(s):
    r"""Helper to easily define string ranges for use in Word construction.  Borrows
       syntax from regexp '[]' string range definitions::
          srange("[0-9]")   -> "0123456789"
          srange("[a-z]")   -> "abcdefghijklmnopqrstuvwxyz"
          srange("[a-z$_]") -> "abcdefghijklmnopqrstuvwxyz$_"
       The input string must be enclosed in []'s, and the returned string is the expanded
       character set joined into a single string.
       The values enclosed in the []'s may be::
          a single character
          an escaped character with a leading backslash (such as \- or \])
          an escaped hex character with a leading '\x' (\x21, which is a '!' character) 
            (\0x## is also supported for backwards compatibility) 
          an escaped octal character with a leading '\0' (\041, which is a '!' character)
          a range of any of the above, separated by a dash ('a-z', etc.)
          any combination of the above ('aeiouy', 'a-zA-Z0-9_$', etc.)
    """
    _expanded = lambda p: p if not isinstance(p,ParseResults) else ''.join(unichr(c) for c in range(ord(p[0]),ord(p[1])+1))
    try:
        return "".join(_expanded(part) for part in _reBracketExpr.parseString(s).body)
    except:
        return ""

def matchOnlyAtCol(n):
    """Helper method for defining parse actions that require matching at a specific
       column in the input text.
    """
    def verifyCol(strg,locn,toks):
        if col(locn,strg) != n:
            raise ParseException(strg,locn,"matched token not at column %d" % n)
    return verifyCol

def replaceWith(replStr):
    """Helper method for common parse actions that simply return a literal value.  Especially
       useful when used with C{L{transformString<ParserElement.transformString>}()}.
    """
    return lambda s,l,t: [replStr]

def removeQuotes(s,l,t):
    """Helper parse action for removing quotation marks from parsed quoted strings.
       To use, add this parse action to quoted string using::
         quotedString.setParseAction( removeQuotes )
    """
    return t[0][1:-1]

def tokenMap(func, *args):
    """Helper to define a parse action by mapping a function to all elements of a ParseResults list.If any additional 
       args are passed, they are forwarded to the given function as additional arguments after
       the token, as in C{hex_integer = Word(hexnums).setParseAction(tokenMap(int, 16))}, which will convert the
       parsed data to an integer using base 16.
    """
    def pa(s,l,t):
        t[:] = [func(tokn, *args) for tokn in t]

    try:
        func_name = getattr(func, '__name__', 
                            getattr(func, '__class__').__name__)
    except Exception:
        func_name = str(func)
    pa.__name__ = func_name

    return pa

upcaseTokens = tokenMap(lambda t: _ustr(t).upper())
"""Helper parse action to convert tokens to upper case."""

downcaseTokens = tokenMap(lambda t: _ustr(t).lower())
"""Helper parse action to convert tokens to lower case."""
    
def _makeTags(tagStr, xml):
    """Internal helper to construct opening and closing tag expressions, given a tag name"""
    if isinstance(tagStr,basestring):
        resname = tagStr
        tagStr = Keyword(tagStr, caseless=not xml)
    else:
        resname = tagStr.name

    tagAttrName = Word(alphas,alphanums+"_-:")
    if (xml):
        tagAttrValue = dblQuotedString.copy().setParseAction( removeQuotes )
        openTag = Suppress("<") + tagStr("tag") + \
                Dict(ZeroOrMore(Group( tagAttrName + Suppress("=") + tagAttrValue ))) + \
                Optional("/",default=[False]).setResultsName("empty").setParseAction(lambda s,l,t:t[0]=='/') + Suppress(">")
    else:
        printablesLessRAbrack = "".join(c for c in printables if c not in ">")
        tagAttrValue = quotedString.copy().setParseAction( removeQuotes ) | Word(printablesLessRAbrack)
        openTag = Suppress("<") + tagStr("tag") + \
                Dict(ZeroOrMore(Group( tagAttrName.setParseAction(downcaseTokens) + \
                Optional( Suppress("=") + tagAttrValue ) ))) + \
                Optional("/",default=[False]).setResultsName("empty").setParseAction(lambda s,l,t:t[0]=='/') + Suppress(">")
    closeTag = Combine(_L("</") + tagStr + ">")

    openTag = openTag.setResultsName("start"+"".join(resname.replace(":"," ").title().split())).setName("<%s>" % resname)
    closeTag = closeTag.setResultsName("end"+"".join(resname.replace(":"," ").title().split())).setName("</%s>" % resname)
    openTag.tag = resname
    closeTag.tag = resname
    return openTag, closeTag

def makeHTMLTags(tagStr):
    """Helper to construct opening and closing tag expressions for HTML, given a tag name"""
    return _makeTags( tagStr, False )

def makeXMLTags(tagStr):
    """Helper to construct opening and closing tag expressions for XML, given a tag name"""
    return _makeTags( tagStr, True )

def withAttribute(*args,**attrDict):
    """Helper to create a validating parse action to be used with start tags created
       with C{L{makeXMLTags}} or C{L{makeHTMLTags}}. Use C{withAttribute} to qualify a starting tag
       with a required attribute value, to avoid false matches on common tags such as
       C{<TD>} or C{<DIV>}.

       Call C{withAttribute} with a series of attribute names and values. Specify the list
       of filter attributes names and values as:
        - keyword arguments, as in C{(align="right")}, or
        - as an explicit dict with C{**} operator, when an attribute name is also a Python
          reserved word, as in C{**{"class":"Customer", "align":"right"}}
        - a list of name-value tuples, as in ( ("ns1:class", "Customer"), ("ns2:align","right") )
       For attribute names with a namespace prefix, you must use the second form.  Attribute
       names are matched insensitive to upper/lower case.
       
       If just testing for C{class} (with or without a namespace), use C{L{withClass}}.

       To verify that the attribute exists, but without specifying a value, pass
       C{withAttribute.ANY_VALUE} as the value.
       """
    if args:
        attrs = args[:]
    else:
        attrs = attrDict.items()
    attrs = [(k,v) for k,v in attrs]
    def pa(s,l,tokens):
        for attrName,attrValue in attrs:
            if attrName not in tokens:
                raise ParseException(s,l,"no matching attribute " + attrName)
            if attrValue != withAttribute.ANY_VALUE and tokens[attrName] != attrValue:
                raise ParseException(s,l,"attribute '%s' has value '%s', must be '%s'" %
                                            (attrName, tokens[attrName], attrValue))
    return pa
withAttribute.ANY_VALUE = object()

def withClass(classname, namespace=''):
    """Simplified version of C{L{withAttribute}} when matching on a div class - made
       difficult because C{class} is a reserved word in Python.
       """
    classattr = "%s:class" % namespace if namespace else "class"
    return withAttribute(**{classattr : classname})        

opAssoc = _Constants()
opAssoc.LEFT = object()
opAssoc.RIGHT = object()

def infixNotation( baseExpr, opList, lpar=Suppress('('), rpar=Suppress(')') ):
    """Helper method for constructing grammars of expressions made up of
       operators working in a precedence hierarchy.  Operators may be unary or
       binary, left- or right-associative.  Parse actions can also be attached
       to operator expressions.

       Parameters:
        - baseExpr - expression representing the most basic element for the nested
        - opList - list of tuples, one for each operator precedence level in the
          expression grammar; each tuple is of the form
          (opExpr, numTerms, rightLeftAssoc, parseAction), where:
           - opExpr is the pyparsing expression for the operator;
              may also be a string, which will be converted to a Literal;
              if numTerms is 3, opExpr is a tuple of two expressions, for the
              two operators separating the 3 terms
           - numTerms is the number of terms for this operator (must
              be 1, 2, or 3)
           - rightLeftAssoc is the indicator whether the operator is
              right or left associative, using the pyparsing-defined
              constants C{opAssoc.RIGHT} and C{opAssoc.LEFT}.
           - parseAction is the parse action to be associated with
              expressions matching this operator expression (the
              parse action tuple member may be omitted)
        - lpar - expression for matching left-parentheses (default=Suppress('('))
        - rpar - expression for matching right-parentheses (default=Suppress(')'))
    """
    ret = Forward()
    lastExpr = baseExpr | ( lpar + ret + rpar )
    for i,operDef in enumerate(opList):
        opExpr,arity,rightLeftAssoc,pa = (operDef + (None,))[:4]
        termName = "%s term" % opExpr if arity < 3 else "%s%s term" % opExpr
        if arity == 3:
            if opExpr is None or len(opExpr) != 2:
                raise ValueError("if numterms=3, opExpr must be a tuple or list of two expressions")
            opExpr1, opExpr2 = opExpr
        thisExpr = Forward().setName(termName)
        if rightLeftAssoc == opAssoc.LEFT:
            if arity == 1:
                matchExpr = FollowedBy(lastExpr + opExpr) + Group( lastExpr + OneOrMore( opExpr ) )
            elif arity == 2:
                if opExpr is not None:
                    matchExpr = FollowedBy(lastExpr + opExpr + lastExpr) + Group( lastExpr + OneOrMore( opExpr + lastExpr ) )
                else:
                    matchExpr = FollowedBy(lastExpr+lastExpr) + Group( lastExpr + OneOrMore(lastExpr) )
            elif arity == 3:
                matchExpr = FollowedBy(lastExpr + opExpr1 + lastExpr + opExpr2 + lastExpr) + \
                            Group( lastExpr + opExpr1 + lastExpr + opExpr2 + lastExpr )
            else:
                raise ValueError("operator must be unary (1), binary (2), or ternary (3)")
        elif rightLeftAssoc == opAssoc.RIGHT:
            if arity == 1:
                # try to avoid LR with this extra test
                if not isinstance(opExpr, Optional):
                    opExpr = Optional(opExpr)
                matchExpr = FollowedBy(opExpr.expr + thisExpr) + Group( opExpr + thisExpr )
            elif arity == 2:
                if opExpr is not None:
                    matchExpr = FollowedBy(lastExpr + opExpr + thisExpr) + Group( lastExpr + OneOrMore( opExpr + thisExpr ) )
                else:
                    matchExpr = FollowedBy(lastExpr + thisExpr) + Group( lastExpr + OneOrMore( thisExpr ) )
            elif arity == 3:
                matchExpr = FollowedBy(lastExpr + opExpr1 + thisExpr + opExpr2 + thisExpr) + \
                            Group( lastExpr + opExpr1 + thisExpr + opExpr2 + thisExpr )
            else:
                raise ValueError("operator must be unary (1), binary (2), or ternary (3)")
        else:
            raise ValueError("operator must indicate right or left associativity")
        if pa:
            matchExpr.setParseAction( pa )
        thisExpr <<= ( matchExpr.setName(termName) | lastExpr )
        lastExpr = thisExpr
    ret <<= lastExpr
    return ret

operatorPrecedence = infixNotation
"""(Deprecated) Former name of C{L{infixNotation}}, will be dropped in a future release."""

dblQuotedString = Combine(Regex(r'"(?:[^"\n\r\\]|(?:"")|(?:\\(?:[^x]|x[0-9a-fA-F]+)))*')+'"').setName("string enclosed in double quotes")
sglQuotedString = Combine(Regex(r"'(?:[^'\n\r\\]|(?:'')|(?:\\(?:[^x]|x[0-9a-fA-F]+)))*")+"'").setName("string enclosed in single quotes")
quotedString = Combine(Regex(r'"(?:[^"\n\r\\]|(?:"")|(?:\\(?:[^x]|x[0-9a-fA-F]+)))*')+'"'|
                       Regex(r"'(?:[^'\n\r\\]|(?:'')|(?:\\(?:[^x]|x[0-9a-fA-F]+)))*")+"'").setName("quotedString using single or double quotes")
unicodeString = Combine(_L('u') + quotedString.copy()).setName("unicode string literal")

def nestedExpr(opener="(", closer=")", content=None, ignoreExpr=quotedString.copy()):
    """Helper method for defining nested lists enclosed in opening and closing
       delimiters ("(" and ")" are the default).

       Parameters:
        - opener - opening character for a nested list (default="("); can also be a pyparsing expression
        - closer - closing character for a nested list (default=")"); can also be a pyparsing expression
        - content - expression for items within the nested lists (default=None)
        - ignoreExpr - expression for ignoring opening and closing delimiters (default=quotedString)

       If an expression is not provided for the content argument, the nested
       expression will capture all whitespace-delimited content between delimiters
       as a list of separate values.

       Use the C{ignoreExpr} argument to define expressions that may contain
       opening or closing characters that should not be treated as opening
       or closing characters for nesting, such as quotedString or a comment
       expression.  Specify multiple expressions using an C{L{Or}} or C{L{MatchFirst}}.
       The default is L{quotedString}, but if no expressions are to be ignored,
       then pass C{None} for this argument.
    """
    if opener == closer:
        raise ValueError("opening and closing strings cannot be the same")
    if content is None:
        if isinstance(opener,basestring) and isinstance(closer,basestring):
            if len(opener) == 1 and len(closer)==1:
                if ignoreExpr is not None:
                    content = (Combine(OneOrMore(~ignoreExpr +
                                    CharsNotIn(opener+closer+ParserElement.DEFAULT_WHITE_CHARS,exact=1))
                                ).setParseAction(lambda t:t[0].strip()))
                else:
                    content = (empty.copy()+CharsNotIn(opener+closer+ParserElement.DEFAULT_WHITE_CHARS
                                ).setParseAction(lambda t:t[0].strip()))
            else:
                if ignoreExpr is not None:
                    content = (Combine(OneOrMore(~ignoreExpr + 
                                    ~Literal(opener) + ~Literal(closer) +
                                    CharsNotIn(ParserElement.DEFAULT_WHITE_CHARS,exact=1))
                                ).setParseAction(lambda t:t[0].strip()))
                else:
                    content = (Combine(OneOrMore(~Literal(opener) + ~Literal(closer) +
                                    CharsNotIn(ParserElement.DEFAULT_WHITE_CHARS,exact=1))
                                ).setParseAction(lambda t:t[0].strip()))
        else:
            raise ValueError("opening and closing arguments must be strings if no content expression is given")
    ret = Forward()
    if ignoreExpr is not None:
        ret <<= Group( Suppress(opener) + ZeroOrMore( ignoreExpr | ret | content ) + Suppress(closer) )
    else:
        ret <<= Group( Suppress(opener) + ZeroOrMore( ret | content )  + Suppress(closer) )
    ret.setName('nested %s%s expression' % (opener,closer))
    return ret

def indentedBlock(blockStatementExpr, indentStack, indent=True):
    """Helper method for defining space-delimited indentation blocks, such as
       those used to define block statements in Python source code.

       Parameters:
        - blockStatementExpr - expression defining syntax of statement that
            is repeated within the indented block
        - indentStack - list created by caller to manage indentation stack
            (multiple statementWithIndentedBlock expressions within a single grammar
            should share a common indentStack)
        - indent - boolean indicating whether block must be indented beyond the
            the current level; set to False for block of left-most statements
            (default=True)

       A valid block must contain at least one C{blockStatement}.
    """
    def checkPeerIndent(s,l,t):
        if l >= len(s): return
        curCol = col(l,s)
        if curCol != indentStack[-1]:
            if curCol > indentStack[-1]:
                raise ParseFatalException(s,l,"illegal nesting")
            raise ParseException(s,l,"not a peer entry")

    def checkSubIndent(s,l,t):
        curCol = col(l,s)
        if curCol > indentStack[-1]:
            indentStack.append( curCol )
        else:
            raise ParseException(s,l,"not a subentry")

    def checkUnindent(s,l,t):
        if l >= len(s): return
        curCol = col(l,s)
        if not(indentStack and curCol < indentStack[-1] and curCol <= indentStack[-2]):
            raise ParseException(s,l,"not an unindent")
        indentStack.pop()

    NL = OneOrMore(LineEnd().setWhitespaceChars("\t ").suppress())
    INDENT = (Empty() + Empty().setParseAction(checkSubIndent)).setName('INDENT')
    PEER   = Empty().setParseAction(checkPeerIndent).setName('')
    UNDENT = Empty().setParseAction(checkUnindent).setName('UNINDENT')
    if indent:
        smExpr = Group( Optional(NL) +
            #~ FollowedBy(blockStatementExpr) +
            INDENT + (OneOrMore( PEER + Group(blockStatementExpr) + Optional(NL) )) + UNDENT)
    else:
        smExpr = Group( Optional(NL) +
            (OneOrMore( PEER + Group(blockStatementExpr) + Optional(NL) )) )
    blockStatementExpr.ignore(_bslash + LineEnd())
    return smExpr.setName('indented block')

alphas8bit = srange(r"[\0xc0-\0xd6\0xd8-\0xf6\0xf8-\0xff]")
punc8bit = srange(r"[\0xa1-\0xbf\0xd7\0xf7]")

anyOpenTag,anyCloseTag = makeHTMLTags(Word(alphas,alphanums+"_:").setName('any tag'))
_htmlEntityMap = dict(zip("gt lt amp nbsp quot apos".split(),'><& "\''))
commonHTMLEntity = Regex('&(?P<entity>' + '|'.join(_htmlEntityMap.keys()) +");").setName("common HTML entity")
def replaceHTMLEntity(t):
    """Helper parser action to replace common HTML entities with their special characters"""
    return _htmlEntityMap.get(t.entity)

# it's easy to get these comment structures wrong - they're very common, so may as well make them available
cStyleComment = Combine(Regex(r"/\*(?:[^*]|\*(?!/))*") + '*/').setName("C style comment")
"Comment of the form C{/* ... */}"

htmlComment = Regex(r"<!--[\s\S]*?-->").setName("HTML comment")
"Comment of the form C{<!-- ... -->}"

restOfLine = Regex(r".*").leaveWhitespace().setName("rest of line")
dblSlashComment = Regex(r"//(?:\\\n|[^\n])*").setName("// comment")
"Comment of the form C{// ... (to end of line)}"

cppStyleComment = Combine(Regex(r"/\*(?:[^*]|\*(?!/))*") + '*/'| dblSlashComment).setName("C++ style comment")
"Comment of either form C{L{cStyleComment}} or C{L{dblSlashComment}}"

javaStyleComment = cppStyleComment
"Same as C{L{cppStyleComment}}"

pythonStyleComment = Regex(r"#.*").setName("Python style comment")
"Comment of the form C{# ... (to end of line)}"

_commasepitem = Combine(OneOrMore(Word(printables, excludeChars=',') +
                                  Optional( Word(" \t") +
                                            ~Literal(",") + ~LineEnd() ) ) ).streamline().setName("commaItem")
commaSeparatedList = delimitedList( Optional( quotedString.copy() | _commasepitem, default="") ).setName("commaSeparatedList")
"""Predefined expression of 1 or more printable words or quoted strings, separated by commas."""

# some other useful expressions - using lower-case class name since we are really using this as a namespace
class pyparsing_common:
    """
    Here are some common low-level expressions that may be useful in jump-starting parser development:
     - numeric forms (L{integers<integer>}, L{reals<real>}, L{scientific notation<sciReal>})
     - common L{programming identifiers<identifier>}
     - network addresses (L{MAC<mac_address>}, L{IPv4<ipv4_address>}, L{IPv6<ipv6_address>})
     - ISO8601 L{dates<iso8601_date>} and L{datetime<iso8601_datetime>}
     - L{UUID<uuid>}
    Parse actions:
     - C{L{convertToInteger}}
     - C{L{convertToFloat}}
     - C{L{convertToDate}}
     - C{L{convertToDatetime}}
     - C{L{stripHTMLTags}}
    """

    convertToInteger = tokenMap(int)
    """
    Parse action for converting parsed integers to Python int
    """

    convertToFloat = tokenMap(float)
    """
    Parse action for converting parsed numbers to Python float
    """

    integer = Word(nums).setName("integer").setParseAction(convertToInteger)
    """expression that parses an unsigned integer, returns an int"""

    hex_integer = Word(hexnums).setName("hex integer").setParseAction(tokenMap(int,16))
    """expression that parses a hexadecimal integer, returns an int"""

    signedInteger = Regex(r'[+-]?\d+').setName("signed integer").setParseAction(convertToInteger)
    """expression that parses an integer with optional leading sign, returns an int"""

    fraction = (signedInteger().setParseAction(convertToFloat) + '/' + signedInteger().setParseAction(convertToFloat)).setName("fraction")
    """fractional expression of an integer divided by an integer, returns a float"""
    fraction.addParseAction(lambda t: t[0]/t[-1])

    mixed_integer = (fraction | integer + Optional(Optional('-').suppress() + fraction)).setName("fraction or mixed integer-fraction")
    """mixed integer of the form 'integer - fraction', with optional leading integer, returns float"""
    mixed_integer.addParseAction(sum)

    real = Regex(r'[+-]?\d+\.\d*').setName("real number").setParseAction(convertToFloat)
    """expression that parses a floating point number and returns a float"""

    sciReal = Regex(r'[+-]?\d+([eE][+-]?\d+|\.\d*([eE][+-]?\d+)?)').setName("real number with scientific notation").setParseAction(convertToFloat)
    """expression that parses a floating point number with optional scientific notation and returns a float"""

    # streamlining this expression makes the docs nicer-looking
    numeric = (sciReal | real | signedInteger).streamline()
    """any numeric expression, returns the corresponding Python type"""

    number = Regex(r'[+-]?\d+\.?\d*([eE][+-]?\d+)?').setName("number").setParseAction(convertToFloat)
    """any int or real number, returned as float"""
    
    identifier = Word(alphas+'_', alphanums+'_').setName("identifier")
    """typical code identifier (leading alpha or '_', followed by 0 or more alphas, nums, or '_')"""
    
    ipv4_address = Regex(r'(25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})(\.(25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})){3}').setName("IPv4 address")
    "IPv4 address (C{0.0.0.0 - 255.255.255.255})"

    _ipv6_part = Regex(r'[0-9a-fA-F]{1,4}').setName("hex_integer")
    _full_ipv6_address = (_ipv6_part + (':' + _ipv6_part)*7).setName("full IPv6 address")
    _short_ipv6_address = (Optional(_ipv6_part + (':' + _ipv6_part)*(0,6)) + "::" + Optional(_ipv6_part + (':' + _ipv6_part)*(0,6))).setName("short IPv6 address")
    _short_ipv6_address.addCondition(lambda t: sum(1 for tt in t if pyparsing_common._ipv6_part.matches(tt)) < 8)
    _mixed_ipv6_address = ("::ffff:" + ipv4_address).setName("mixed IPv6 address")
    ipv6_address = Combine((_full_ipv6_address | _mixed_ipv6_address | _short_ipv6_address).setName("IPv6 address")).setName("IPv6 address")
    "IPv6 address (long, short, or mixed form)"
    
    mac_address = Regex(r'[0-9a-fA-F]{2}([:.-])[0-9a-fA-F]{2}(?:\1[0-9a-fA-F]{2}){4}').setName("MAC address")
    "MAC address xx:xx:xx:xx:xx (may also have '-' or '.' delimiters)"

    @staticmethod
    def convertToDate(fmt="%Y-%m-%d"):
        """
        Helper to create a parse action for converting parsed date string to Python datetime.date

        Params -
         - fmt - format to be passed to datetime.strptime (default=C{"%Y-%m-%d"})
        """
        return lambda s,l,t: datetime.strptime(t[0], fmt).date()

    @staticmethod
    def convertToDatetime(fmt="%Y-%m-%dT%H:%M:%S.%f"):
        """
        Helper to create a parse action for converting parsed datetime string to Python datetime.datetime

        Params -
         - fmt - format to be passed to datetime.strptime (default=C{"%Y-%m-%dT%H:%M:%S.%f"})
        """
        return lambda s,l,t: datetime.strptime(t[0], fmt)

    iso8601_date = Regex(r'(?P<year>\d{4})(?:-(?P<month>\d\d)(?:-(?P<day>\d\d))?)?').setName("ISO8601 date")
    "ISO8601 date (C{yyyy-mm-dd})"

    iso8601_datetime = Regex(r'(?P<year>\d{4})-(?P<month>\d\d)-(?P<day>\d\d)[T ](?P<hour>\d\d):(?P<minute>\d\d)(:(?P<second>\d\d(\.\d*)?)?)?(?P<tz>Z|[+-]\d\d:?\d\d)?').setName("ISO8601 datetime")
    "ISO8601 datetime (C{yyyy-mm-ddThh:mm:ss.s(Z|+-00:00)}) - trailing seconds, milliseconds, and timezone optional; accepts separating C{'T'} or C{' '}"

    uuid = Regex(r'[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}').setName("UUID")
    "UUID (C{xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx})"

    _html_stripper = anyOpenTag.suppress() | anyCloseTag.suppress()
    @staticmethod
    def stripHTMLTags(s, l, tokens):
        """Parse action to remove HTML tags from web page HTML source"""
        return pyparsing_common._html_stripper.transformString(tokens[0])

if __name__ == "__main__":

    selectToken    = CaselessLiteral("select")
    fromToken      = CaselessLiteral("from")

    ident          = Word(alphas, alphanums + "_$")

    columnName     = delimitedList(ident, ".", combine=True).setParseAction(upcaseTokens)
    columnNameList = Group(delimitedList(columnName)).setName("columns")
    columnSpec     = ('*' | columnNameList)

    tableName      = delimitedList(ident, ".", combine=True).setParseAction(upcaseTokens)
    tableNameList  = Group(delimitedList(tableName)).setName("tables")
    
    simpleSQL      = selectToken("command") + columnSpec("columns") + fromToken + tableNameList("tables")

    # demo runTests method, including embedded comments in test string
    simpleSQL.runTests("""
        # '*' as column list and dotted table name
        select * from SYS.XYZZY

        # caseless match on "SELECT", and casts back to "select"
        SELECT * from XYZZY, ABC

        # list of column names, and mixed case SELECT keyword
        Select AA,BB,CC from Sys.dual

        # multiple tables
        Select A, B, C from Sys.dual, Table2

        # invalid SELECT keyword - should fail
        Xelect A, B, C from Sys.dual

        # incomplete command - should fail
        Select

        # invalid column name - should fail
        Select ^^^ frox Sys.dual

        """)

    pyparsing_common.numeric.runTests("""
        100
        -100
        +100
        3.14159
        6.02e23
        1e-12
        """)

    # any int or real number, returned as float
    pyparsing_common.number.runTests("""
        100
        -100
        +100
        3.14159
        6.02e23
        1e-12
        """)

    pyparsing_common.hex_integer.runTests("""
        100
        FF
        """)

    import uuid
    pyparsing_common.uuid.setParseAction(tokenMap(uuid.UUID))
    pyparsing_common.uuid.runTests("""
        12345678-1234-5678-1234-567812345678
        """)
