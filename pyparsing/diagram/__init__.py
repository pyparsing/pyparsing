import railroad
import pyparsing
from pkg_resources import resource_filename
from typing import (
    Union,
    List,
    Optional,
    NamedTuple,
    Generic,
    TypeVar,
    Any,
    Dict,
    Callable,
)
from jinja2 import Template
from io import StringIO
import inspect

with open(resource_filename(__name__, "template.jinja2"), encoding="utf-8") as fp:
    template = Template(fp.read())

# Note: ideally this would be a dataclass, but we're supporting Python 3.5+ so we can't do this yet
NamedDiagram = NamedTuple(
    "NamedDiagram",
    [("name", str), ("diagram", Optional[railroad.DiagramItem]), ("index", int)],
)
"""
A simple structure for associating a name with a railroad diagram
"""

T = TypeVar("T")


class EditablePartial(Generic[T]):
    """
    Acts like a functools.partial, but can be edited. In other words, it represents a type that hasn't yet been
    constructed.
    """

    # We need this here because the railroad constructors actually transform the data, so can't be called until the
    # entire tree is assembled

    def __init__(self, func: Callable[..., T], args: list, kwargs: dict):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    @classmethod
    def from_call(cls, func: Callable[..., T], *args, **kwargs) -> "EditablePartial[T]":
        """
        If you call this function in the same way that you would call the constructor, it will store the arguments
        as you expect. For example EditablePartial.from_call(Fraction, 1, 3)() == Fraction(1, 3)
        """
        return EditablePartial(func=func, args=list(args), kwargs=kwargs)

    def __call__(self) -> T:
        """
        Evaluate the partial and return the result
        """
        args = self.args.copy()
        kwargs = self.kwargs.copy()

        # This is a helpful hack to allow you to specify varargs parameters (e.g. *args) as keyword args (e.g.
        # args=['list', 'of', 'things'])
        arg_spec = inspect.getfullargspec(self.func)
        if arg_spec.varargs in self.kwargs:
            args += kwargs.pop(arg_spec.varargs)

        return self.func(*args, **kwargs)


def get_name(element: pyparsing.ParserElement, default: str = None) -> str:
    """
    Returns a human readable string for a parser element. By default it will first check the element's `name` attribute
    for a user-defined string, and will fall back to the element type name if this doesn't exist. However, the fallback
    value can be customized
    """
    # return str(element)
    if default is None:
        default = element.__class__.__name__

    return getattr(element, "name", default)


def railroad_to_html(diagrams: List[NamedDiagram], **kwargs) -> str:
    """
    Given a list of NamedDiagram, produce a single HTML string that visualises those diagrams
    :params kwargs: kwargs to be passed in to the template
    """
    data = []
    for diagram in diagrams:
        io = StringIO()
        diagram.diagram.writeSvg(io.write)
        title = diagram.name
        if diagram.index == 0:
            title += " (root)"
        data.append({"title": title, "text": "", "svg": io.getvalue()})

    return template.render(diagrams=data, **kwargs)


def resolve_partial(partial: "EditablePartial[T]") -> T:
    """
    Recursively resolves a collection of Partials into whatever type they are
    """
    if isinstance(partial, EditablePartial):
        partial.args = resolve_partial(partial.args)
        partial.kwargs = resolve_partial(partial.kwargs)
        return partial()
    elif isinstance(partial, list):
        return [resolve_partial(x) for x in partial]
    elif isinstance(partial, dict):
        return {key: resolve_partial(x) for key, x in partial.items()}
    else:
        return partial


def to_railroad(
    element: pyparsing.ParserElement,
    diagram_kwargs: dict = {},
    vertical: Union[int, bool] = 5,
) -> List[NamedDiagram]:
    """
    Convert a pyparsing element tree into a list of diagrams. This is the recommended entrypoint to diagram
    creation if you want to access the Railroad tree before it is converted to HTML
    :param diagram_kwargs: kwargs to pass to the Diagram() constructor
    """
    # Convert the whole tree underneath the root
    lookup = ConverterState(diagram_kwargs=diagram_kwargs)
    _to_diagram_element(element, lookup=lookup, parent=None, vertical=vertical)

    # Convert the root if it hasn't been already
    root_id = id(element)
    if root_id in lookup.first:
        lookup.first[root_id].mark_for_extraction(root_id, lookup)

    # Now that we're finished, we can convert from intermediate structures into Railroad elements
    resolved = [resolve_partial(partial) for partial in lookup.diagrams.values()]
    return sorted(resolved, key=lambda diag: diag.index)


def _should_vertical(specification: Union[int, bool], count: int) -> bool:
    """
    Returns true if we should return a vertical list of elements
    """
    if isinstance(specification, bool):
        return specification
    elif isinstance(specification, int):
        return count >= specification
    else:
        raise Exception()


class ElementState:
    """
    State recorded for an individual pyparsing Element
    """

    # Note: this should be a dataclass, but we have to support Python 3.5
    def __init__(
        self,
        element: pyparsing.ParserElement,
        converted: EditablePartial,
        parent: EditablePartial,
        number: int = None,
        name: str = None,
        index: Optional[int] = None,
    ):
        #: The pyparsing element that this represents
        self.element: pyparsing.ParserElement = element
        #: The name of the element
        self.name = name
        #: The output Railroad element in an unconverted state
        self.converted: EditablePartial = converted
        #: The parent Railroad element, which we store so that we can extract this if it's duplicated
        self.parent: EditablePartial = parent
        #: The diagram number of this, when it gets turned into a diagram. This is only set when we know it's going to
        # be extracted into a new diagram
        self.number: int = number
        #: The index of this inside its parent
        self.parent_index: Optional[int] = index
        #: If true, we should extract this out into a subdiagram
        self.extract: bool = False
        #: If true, all of this element's chilren have been filled out
        self.complete: bool = False

    def mark_for_extraction(self, el_id: int, state: "ConverterState"):
        """
        Called when this instance has been seen twice, and thus should eventually be extracted into a sub-diagram
        """
        self.extract = True

        if self.number is None:
            if self.parent is None:
                self.number = 0
            else:
                self.number = state.generate_index()

        # Set the name
        if not self.name:
            if hasattr(self.element, "name") and self.element.name:
                self.name = self.element.name
            else:
                unnamed_number = 1 if self.parent is None else state.generate_unnamed()
                self.name = "Unnamed {}".format(unnamed_number)

        # Just because this is marked for extraction doesn't mean we can do it yet. We may have to wait for children
        # to be added
        if self.complete:
            state.extract_into_diagram(el_id)


class ConverterState:
    """
    Stores some state that persists between recursions into the element tree
    """

    def __init__(self, diagram_kwargs: dict = {}):
        #: A dictionary mapping ParserElement IDs to state relating to them
        self.first: Dict[int, ElementState] = {}
        #: A dictionary mapping ParserElement IDs to subdiagrams generated from them
        self.diagrams: Dict[int, EditablePartial[NamedDiagram]] = {}
        #: The index of the next unnamed element
        self.unnamed_index: int = 1
        #: The index of the next element. This is used for sorting
        self.index: int = 0
        #: Shared kwargs that are used to customize the construction of diagrams
        self.diagram_kwargs: dict = diagram_kwargs

    def generate_unnamed(self) -> int:
        """
        Generate a number used in the name of an otherwise unnamed diagram
        """
        self.unnamed_index += 1
        return self.unnamed_index

    def generate_index(self) -> int:
        """
        Generate a number used to index a diagram
        """
        self.index += 1
        return self.index

    def extract_into_diagram(self, el_id: int):
        """
        Used when we encounter the same token twice in the same tree. When this happens, we replace all instances of that
        token with a terminal, and create a new subdiagram for the token
        """
        position = self.first[el_id]

        # Replace the original definition of this element with a regular block
        if position.parent:
            ret = EditablePartial.from_call(railroad.NonTerminal, text=position.name)
            if "item" in position.parent.kwargs:
                position.parent.kwargs["item"] = ret
            else:
                if position.parent_index < len(position.parent.kwargs["items"]):
                    position.parent.kwargs["items"][position.parent_index] = ret

        self.diagrams[el_id] = EditablePartial.from_call(
            NamedDiagram,
            name=position.name,
            diagram=EditablePartial.from_call(
                railroad.Diagram, position.converted, **self.diagram_kwargs
            ),
            index=position.number,
        )
        del self.first[el_id]


def _worth_extracting(children: List[pyparsing.ParserElement]) -> bool:
    """
    Returns true if the element with these children is worth having its own element. Simply, if any of its children
    themselves have children, then its complex enough to extract
    """
    return any(
        [hasattr(child, "expr") or hasattr(child, "exprs") for child in children]
    )


def _element_children(
    element: pyparsing.ParserElement,
) -> List[Union[str, pyparsing.ParserElement]]:
    """
    Converts the nebulous list of child elements into a single list objects for easy use
    """
    if hasattr(element, "exprs"):
        return list(element.exprs)
    elif hasattr(element, "expr"):
        return [element.expr]
    else:
        return []


def _to_diagram_element(
    element: pyparsing.ParserElement,
    parent: Optional[EditablePartial],
    lookup: ConverterState = None,
    vertical: Union[int, bool] = 5,
    index: int = 0,
) -> Optional[EditablePartial]:
    """
    Recursively converts a PyParsing Element to a railroad Element
    :param lookup: The shared converter state that keeps track of useful things
    :param index: The index of this element within the parent
    :param parent: The parent of this element in the output tree
    :param vertical: Controls at what point we make a list of elements vertical. If this is an integer (the default),
    it sets the threshold of the number of items before we go vertical. If True, always go vertical, if False, never
    do so
    :returns: The converted version of the input element, but as a Partial that hasn't yet been constructed
    """
    exprs = _element_children(element)

    name = get_name(element)
    # Python's id() is used to provide a unique identifier for elements
    el_id = id(element)

    if el_id in lookup.first:
        # If we've seen this element exactly once before, we are only just now finding out that it's a duplicate,
        # so we have to extract it into a new diagram.
        looked_up = lookup.first[el_id]
        looked_up.mark_for_extraction(el_id, lookup)
        return EditablePartial.from_call(railroad.NonTerminal, text=looked_up.name)

    elif el_id in lookup.diagrams:
        # If we have seen the element at least twice before, and have already extracted it into a subdiagram, we
        # just put in a marker element that refers to the sub-diagram
        return EditablePartial.from_call(
            railroad.NonTerminal, text=lookup.diagrams[el_id].kwargs["name"]
        )

    else:
        # Recursively convert child elements
        # Here we find the most relevant Railroad element for matching pyparsing Element
        # We use ``items=None`` here to hold the place for where the child elements will go once created
        if isinstance(element, pyparsing.And):
            if _should_vertical(vertical, len(exprs)):
                ret = EditablePartial.from_call(railroad.Stack, items=[])
            else:
                ret = EditablePartial.from_call(railroad.Sequence, items=[])
        elif isinstance(element, (pyparsing.Or, pyparsing.MatchFirst)):
            if _should_vertical(vertical, len(exprs)):
                ret = EditablePartial.from_call(railroad.HorizontalChoice, items=[])
            else:
                ret = EditablePartial.from_call(railroad.Choice, 0, items=[])
        elif isinstance(element, pyparsing.Optional):
            ret = EditablePartial.from_call(railroad.Optional, item="")
        elif isinstance(element, pyparsing.OneOrMore):
            ret = EditablePartial.from_call(railroad.OneOrMore, item="")
        elif isinstance(element, pyparsing.ZeroOrMore):
            ret = EditablePartial.from_call(railroad.ZeroOrMore, item="")
        elif isinstance(element, pyparsing.Group):
            # Generally there isn't any merit in labelling a group as a group if it doesn't have a custom name
            if name != "Group":
                ret = EditablePartial.from_call(railroad.Group, item=None, label=name)
            else:
                ret = EditablePartial.from_call(railroad.Group, item=None, label="")
        elif isinstance(element, pyparsing.Empty) and name == "Empty":
            # Skip unnamed "Empty" elements
            ret = None
        elif len(exprs) > 1:
            ret = EditablePartial.from_call(railroad.Sequence, items=[])
        elif len(exprs) > 0:
            ret = EditablePartial.from_call(railroad.Group, item="", label=name)
        else:
            ret = EditablePartial.from_call(railroad.Terminal, name)

        # Indicate this element's position in the tree so we can extract it if necessary
        if _worth_extracting(exprs):
            lookup.first[el_id] = ElementState(
                element=element, converted=ret, parent=parent, index=index
            )

        i = 0
        for expr in exprs:
            item = _to_diagram_element(
                expr, parent=ret, lookup=lookup, vertical=vertical, index=i
            )

            # Some elements don't need to be shown in the diagram
            if item is not None:
                if "item" in ret.kwargs:
                    ret.kwargs["item"] = item
                elif "items" in ret.kwargs:
                    ret.kwargs["items"].append(item)
                    i += 1

        # Mark this element as "complete", ie it has all of its children
        if el_id in lookup.first:
            lookup.first[el_id].complete = True

        if (
            el_id in lookup.first
            and lookup.first[el_id].extract
            and lookup.first[el_id].complete
        ):
            lookup.extract_into_diagram(el_id)
            return EditablePartial.from_call(
                railroad.NonTerminal, text=lookup.diagrams[el_id].kwargs["name"]
            )
        else:
            return ret
