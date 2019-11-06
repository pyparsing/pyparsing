# results.py

from collections.abc import MutableMapping, Mapping, MutableSequence
import pprint
from weakref import ref as wkref

str_type = (str, bytes)
_generator_type = type((x for x in ()))


class _ParseResultsWithOffset(object):
    def __init__(self, p1, p2):
        self.tup = (p1, p2)

    def __getitem__(self, i):
        return self.tup[i]

    def __repr__(self):
        return repr(self.tup[0])

    def setOffset(self, i):
        self.tup = (self.tup[0], i)


class ParseResults(object):
    """Structured parse results, to provide multiple means of access to
    the parsed data:

       - as a list (``len(results)``)
       - by list index (``results[0], results[1]``, etc.)
       - by attribute (``results.<resultsName>`` - see :class:`ParserElement.setResultsName`)

    Example::

        integer = Word(nums)
        date_str = (integer.setResultsName("year") + '/'
                        + integer.setResultsName("month") + '/'
                        + integer.setResultsName("day"))
        # equivalent form:
        # date_str = integer("year") + '/' + integer("month") + '/' + integer("day")

        # parseString returns a ParseResults object
        result = date_str.parseString("1999/12/31")

        def test(s, fn=repr):
            print("%s -> %s" % (s, fn(eval(s))))
        test("list(result)")
        test("result[0]")
        test("result['month']")
        test("result.day")
        test("'month' in result")
        test("'minutes' in result")
        test("result.dump()", str)

    prints::

        list(result) -> ['1999', '/', '12', '/', '31']
        result[0] -> '1999'
        result['month'] -> '12'
        result.day -> '31'
        'month' in result -> True
        'minutes' in result -> False
        result.dump() -> ['1999', '/', '12', '/', '31']
        - day: 31
        - month: 12
        - year: 1999
    """

    def __new__(cls, toklist=None, name=None, asList=True, modal=True):
        if isinstance(toklist, ParseResults):
            return toklist
        retobj = object.__new__(cls)
        retobj.__doinit = True
        return retobj

    # Performance tuning: we construct a *lot* of these, so keep this
    # constructor as small and fast as possible
    def __init__(
        self, toklist=None, name=None, asList=True, modal=True, isinstance=isinstance
    ):
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
            elif isinstance(toklist, _generator_type):
                self.__toklist = list(toklist)
            else:
                self.__toklist = [toklist]
            self.__tokdict = dict()

        if name is not None and name:
            if not modal:
                self.__accumNames[name] = 0
            if isinstance(name, int):
                name = str(name)
            self.__name = name
            if not (
                isinstance(toklist, (type(None), *str_type, list))
                and toklist in (None, "", [])
            ):
                if isinstance(toklist, str_type):
                    toklist = [toklist]
                if asList:
                    if isinstance(toklist, ParseResults):
                        self[name] = _ParseResultsWithOffset(
                            ParseResults(toklist.__toklist), 0
                        )
                    else:
                        self[name] = _ParseResultsWithOffset(
                            ParseResults(toklist[0]), 0
                        )
                    self[name].__name = name
                else:
                    try:
                        self[name] = toklist[0]
                    except (KeyError, TypeError, IndexError):
                        self[name] = toklist

    def __getitem__(self, i):
        if isinstance(i, (int, slice)):
            return self.__toklist[i]
        else:
            if i not in self.__accumNames:
                return self.__tokdict[i][-1][0]
            else:
                return ParseResults([v[0] for v in self.__tokdict[i]])

    def __setitem__(self, k, v, isinstance=isinstance):
        if isinstance(v, _ParseResultsWithOffset):
            self.__tokdict[k] = self.__tokdict.get(k, list()) + [v]
            sub = v[0]
        elif isinstance(k, (int, slice)):
            self.__toklist[k] = v
            sub = v
        else:
            self.__tokdict[k] = self.__tokdict.get(k, list()) + [
                _ParseResultsWithOffset(v, 0)
            ]
            sub = v
        if isinstance(sub, ParseResults):
            sub.__parent = wkref(self)

    def __delitem__(self, i):
        if isinstance(i, (int, slice)):
            mylen = len(self.__toklist)
            del self.__toklist[i]

            # convert int to slice
            if isinstance(i, int):
                if i < 0:
                    i += mylen
                i = slice(i, i + 1)
            # get removed indices
            removed = list(range(*i.indices(mylen)))
            removed.reverse()
            # fixup indices in token dictionary
            for name, occurrences in self.__tokdict.items():
                for j in removed:
                    for k, (value, position) in enumerate(occurrences):
                        occurrences[k] = _ParseResultsWithOffset(
                            value, position - (position > j)
                        )
        else:
            del self.__tokdict[i]

    def __contains__(self, k):
        return k in self.__tokdict

    def __len__(self):
        return len(self.__toklist)

    def __bool__(self):
        return not not self.__toklist

    def __iter__(self):
        return iter(self.__toklist)

    def __reversed__(self):
        return iter(self.__toklist[::-1])

    def keys(self):
        return iter(self.__tokdict)

    def values(self):
        return (self[k] for k in self.keys())

    def items(self):
        return ((k, self[k]) for k in self.keys())

    def haskeys(self):
        """Since keys() returns an iterator, this method is helpful in bypassing
           code that looks for the existence of any defined results names."""
        return bool(self.__tokdict)

    def pop(self, *args, **kwargs):
        """
        Removes and returns item at specified index (default= ``last``).
        Supports both ``list`` and ``dict`` semantics for ``pop()``. If
        passed no argument or an integer argument, it will use ``list``
        semantics and pop tokens from the list of parsed tokens. If passed
        a non-integer argument (most likely a string), it will use ``dict``
        semantics and pop the corresponding value from any defined results
        names. A second default return value argument is supported, just as in
        ``dict.pop()``.

        Example::

            def remove_first(tokens):
                tokens.pop(0)
            print(OneOrMore(Word(nums)).parseString("0 123 321")) # -> ['0', '123', '321']
            print(OneOrMore(Word(nums)).addParseAction(remove_first).parseString("0 123 321")) # -> ['123', '321']

            label = Word(alphas)
            patt = label("LABEL") + OneOrMore(Word(nums))
            print(patt.parseString("AAB 123 321").dump())

            # Use pop() in a parse action to remove named result (note that corresponding value is not
            # removed from list form of results)
            def remove_LABEL(tokens):
                tokens.pop("LABEL")
                return tokens
            patt.addParseAction(remove_LABEL)
            print(patt.parseString("AAB 123 321").dump())

        prints::

            ['AAB', '123', '321']
            - LABEL: AAB

            ['AAB', '123', '321']
        """
        if not args:
            args = [-1]
        for k, v in kwargs.items():
            if k == "default":
                args = (args[0], v)
            else:
                raise TypeError("pop() got an unexpected keyword argument '%s'" % k)
        if isinstance(args[0], int) or len(args) == 1 or args[0] in self:
            index = args[0]
            ret = self[index]
            del self[index]
            return ret
        else:
            defaultvalue = args[1]
            return defaultvalue

    def get(self, key, defaultValue=None):
        """
        Returns named result matching the given key, or if there is no
        such name, then returns the given ``defaultValue`` or ``None`` if no
        ``defaultValue`` is specified.

        Similar to ``dict.get()``.

        Example::

            integer = Word(nums)
            date_str = integer("year") + '/' + integer("month") + '/' + integer("day")

            result = date_str.parseString("1999/12/31")
            print(result.get("year")) # -> '1999'
            print(result.get("hour", "not specified")) # -> 'not specified'
            print(result.get("hour")) # -> None
        """
        if key in self:
            return self[key]
        else:
            return defaultValue

    def insert(self, index, insStr):
        """
        Inserts new element at location index in the list of parsed tokens.

        Similar to ``list.insert()``.

        Example::

            print(OneOrMore(Word(nums)).parseString("0 123 321")) # -> ['0', '123', '321']

            # use a parse action to insert the parse location in the front of the parsed results
            def insert_locn(locn, tokens):
                tokens.insert(0, locn)
            print(OneOrMore(Word(nums)).addParseAction(insert_locn).parseString("0 123 321")) # -> [0, '0', '123', '321']
        """
        self.__toklist.insert(index, insStr)
        # fixup indices in token dictionary
        for name, occurrences in self.__tokdict.items():
            for k, (value, position) in enumerate(occurrences):
                occurrences[k] = _ParseResultsWithOffset(
                    value, position + (position > index)
                )

    def append(self, item):
        """
        Add single element to end of ParseResults list of elements.

        Example::

            print(OneOrMore(Word(nums)).parseString("0 123 321")) # -> ['0', '123', '321']

            # use a parse action to compute the sum of the parsed integers, and add it to the end
            def append_sum(tokens):
                tokens.append(sum(map(int, tokens)))
            print(OneOrMore(Word(nums)).addParseAction(append_sum).parseString("0 123 321")) # -> ['0', '123', '321', 444]
        """
        self.__toklist.append(item)

    def extend(self, itemseq):
        """
        Add sequence of elements to end of ParseResults list of elements.

        Example::

            patt = OneOrMore(Word(alphas))

            # use a parse action to append the reverse of the matched strings, to make a palindrome
            def make_palindrome(tokens):
                tokens.extend(reversed([t[::-1] for t in tokens]))
                return ''.join(tokens)
            print(patt.addParseAction(make_palindrome).parseString("lskdj sdlkjf lksd")) # -> 'lskdjsdlkjflksddsklfjkldsjdksl'
        """
        if isinstance(itemseq, ParseResults):
            self.__iadd__(itemseq)
        else:
            self.__toklist.extend(itemseq)

    def clear(self):
        """
        Clear all elements and results names.
        """
        del self.__toklist[:]
        self.__tokdict.clear()

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            return ""

    def __add__(self, other):
        ret = self.copy()
        ret += other
        return ret

    def __iadd__(self, other):
        if other.__tokdict:
            offset = len(self.__toklist)
            addoffset = lambda a: offset if a < 0 else a + offset
            otheritems = other.__tokdict.items()
            otherdictitems = [
                (k, _ParseResultsWithOffset(v[0], addoffset(v[1])))
                for k, vlist in otheritems
                for v in vlist
            ]
            for k, v in otherdictitems:
                self[k] = v
                if isinstance(v[0], ParseResults):
                    v[0].__parent = wkref(self)

        self.__toklist += other.__toklist
        self.__accumNames.update(other.__accumNames)
        return self

    def __radd__(self, other):
        if isinstance(other, int) and other == 0:
            # useful for merging many ParseResults using sum() builtin
            return self.copy()
        else:
            # this may raise a TypeError - so be it
            return other + self

    def __repr__(self):
        return "(%s, %s)" % (repr(self.__toklist), repr(self.__tokdict))

    def __str__(self):
        return (
            "["
            + ", ".join(
                str(i) if isinstance(i, ParseResults) else repr(i)
                for i in self.__toklist
            )
            + "]"
        )

    def _asStringList(self, sep=""):
        out = []
        for item in self.__toklist:
            if out and sep:
                out.append(sep)
            if isinstance(item, ParseResults):
                out += item._asStringList()
            else:
                out.append(str(item))
        return out

    def asList(self):
        """
        Returns the parse results as a nested list of matching tokens, all converted to strings.

        Example::

            patt = OneOrMore(Word(alphas))
            result = patt.parseString("sldkj lsdkj sldkj")
            # even though the result prints in string-like form, it is actually a pyparsing ParseResults
            print(type(result), result) # -> <class 'pyparsing.ParseResults'> ['sldkj', 'lsdkj', 'sldkj']

            # Use asList() to create an actual list
            result_list = result.asList()
            print(type(result_list), result_list) # -> <class 'list'> ['sldkj', 'lsdkj', 'sldkj']
        """
        return [
            res.asList() if isinstance(res, ParseResults) else res
            for res in self.__toklist
        ]

    def asDict(self):
        """
        Returns the named parse results as a nested dictionary.

        Example::

            integer = Word(nums)
            date_str = integer("year") + '/' + integer("month") + '/' + integer("day")

            result = date_str.parseString('12/31/1999')
            print(type(result), repr(result)) # -> <class 'pyparsing.ParseResults'> (['12', '/', '31', '/', '1999'], {'day': [('1999', 4)], 'year': [('12', 0)], 'month': [('31', 2)]})

            result_dict = result.asDict()
            print(type(result_dict), repr(result_dict)) # -> <class 'dict'> {'day': '1999', 'year': '12', 'month': '31'}

            # even though a ParseResults supports dict-like access, sometime you just need to have a dict
            import json
            print(json.dumps(result)) # -> Exception: TypeError: ... is not JSON serializable
            print(json.dumps(result.asDict())) # -> {"month": "31", "day": "1999", "year": "12"}
        """

        def to_item(obj):
            if isinstance(obj, ParseResults):
                return obj.asDict() if obj.haskeys() else [to_item(v) for v in obj]
            else:
                return obj

        return dict((k, to_item(v)) for k, v in self.items())

    def copy(self):
        """
        Returns a new copy of a :class:`ParseResults` object.
        """
        ret = ParseResults(self.__toklist)
        ret.__tokdict = dict(self.__tokdict.items())
        ret.__parent = self.__parent
        ret.__accumNames.update(self.__accumNames)
        ret.__name = self.__name
        return ret

    def getName(self):
        r"""
        Returns the results name for this token expression. Useful when several
        different expressions might match at a particular location.

        Example::

            integer = Word(nums)
            ssn_expr = Regex(r"\d\d\d-\d\d-\d\d\d\d")
            house_number_expr = Suppress('#') + Word(nums, alphanums)
            user_data = (Group(house_number_expr)("house_number")
                        | Group(ssn_expr)("ssn")
                        | Group(integer)("age"))
            user_info = OneOrMore(user_data)

            result = user_info.parseString("22 111-22-3333 #221B")
            for item in result:
                print(item.getName(), ':', item[0])

        prints::

            age : 22
            ssn : 111-22-3333
            house_number : 221B
        """
        if self.__name:
            return self.__name
        elif self.__parent:
            par = self.__parent()

            def lookup(self, sub):
                return next(
                    (
                        k
                        for k, vlist in par.__tokdict.items()
                        for v, loc in vlist
                        if sub is v
                    ),
                    None,
                )

            return lookup(self) if par else None
        elif (
            len(self) == 1
            and len(self.__tokdict) == 1
            and next(iter(self.__tokdict.values()))[0][1] in (0, -1)
        ):
            return next(iter(self.__tokdict.keys()))
        else:
            return None

    def dump(self, indent="", full=True, include_list=True, _depth=0):
        """
        Diagnostic method for listing out the contents of
        a :class:`ParseResults`. Accepts an optional ``indent`` argument so
        that this string can be embedded in a nested display of other data.

        Example::

            integer = Word(nums)
            date_str = integer("year") + '/' + integer("month") + '/' + integer("day")

            result = date_str.parseString('12/31/1999')
            print(result.dump())

        prints::

            ['12', '/', '31', '/', '1999']
            - day: 1999
            - month: 31
            - year: 12
        """
        out = []
        NL = "\n"
        out.append(indent + str(self.asList()) if include_list else "")

        if full:
            if self.haskeys():
                items = sorted((str(k), v) for k, v in self.items())
                for k, v in items:
                    if out:
                        out.append(NL)
                    out.append("%s%s- %s: " % (indent, ("  " * _depth), k))
                    if isinstance(v, ParseResults):
                        if v:
                            out.append(
                                v.dump(
                                    indent=indent,
                                    full=full,
                                    include_list=include_list,
                                    _depth=_depth + 1,
                                )
                            )
                        else:
                            out.append(str(v))
                    else:
                        out.append(repr(v))
            elif any(isinstance(vv, ParseResults) for vv in self):
                v = self
                for i, vv in enumerate(v):
                    if isinstance(vv, ParseResults):
                        out.append(
                            "\n%s%s[%d]:\n%s%s%s"
                            % (
                                indent,
                                ("  " * (_depth)),
                                i,
                                indent,
                                ("  " * (_depth + 1)),
                                vv.dump(
                                    indent=indent,
                                    full=full,
                                    include_list=include_list,
                                    _depth=_depth + 1,
                                ),
                            )
                        )
                    else:
                        out.append(
                            "\n%s%s[%d]:\n%s%s%s"
                            % (
                                indent,
                                ("  " * (_depth)),
                                i,
                                indent,
                                ("  " * (_depth + 1)),
                                str(vv),
                            )
                        )

        return "".join(out)

    def pprint(self, *args, **kwargs):
        """
        Pretty-printer for parsed results as a list, using the
        `pprint <https://docs.python.org/3/library/pprint.html>`_ module.
        Accepts additional positional or keyword args as defined for
        `pprint.pprint <https://docs.python.org/3/library/pprint.html#pprint.pprint>`_ .

        Example::

            ident = Word(alphas, alphanums)
            num = Word(nums)
            func = Forward()
            term = ident | num | Group('(' + func + ')')
            func <<= ident + Group(Optional(delimitedList(term)))
            result = func.parseString("fna a,b,(fnb c,d,200),100")
            result.pprint(width=40)

        prints::

            ['fna',
             ['a',
              'b',
              ['(', 'fnb', ['c', 'd', '200'], ')'],
              '100']]
        """
        pprint.pprint(self.asList(), *args, **kwargs)

    # add support for pickle protocol
    def __getstate__(self):
        return (
            self.__toklist,
            (
                self.__tokdict.copy(),
                self.__parent is not None and self.__parent() or None,
                self.__accumNames,
                self.__name,
            ),
        )

    def __setstate__(self, state):
        self.__toklist = state[0]
        self.__tokdict, par, inAccumNames, self.__name = state[1]
        self.__accumNames = {}
        self.__accumNames.update(inAccumNames)
        if par is not None:
            self.__parent = wkref(par)
        else:
            self.__parent = None

    def __getnewargs__(self):
        return self.__toklist, self.__name, self.__asList, self.__modal

    def __dir__(self):
        return dir(type(self)) + list(self.keys())

    @classmethod
    def from_dict(cls, other, name=None):
        """
        Helper classmethod to construct a ParseResults from a dict, preserving the
        name-value relations as results names. If an optional 'name' argument is
        given, a nested ParseResults will be returned
        """

        def is_iterable(obj):
            try:
                iter(obj)
            except Exception:
                return False
            else:
                return not isinstance(obj, str_type)

        ret = cls([])
        for k, v in other.items():
            if isinstance(v, Mapping):
                ret += cls.from_dict(v, name=k)
            else:
                ret += cls([v], name=k, asList=is_iterable(v))
        if name is not None:
            ret = cls([ret], name=name)
        return ret


MutableMapping.register(ParseResults)
MutableSequence.register(ParseResults)
