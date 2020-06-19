import railroad
import pyparsing
from pkg_resources import resource_filename
import typing
from jinja2 import Template
from io import StringIO

with open(resource_filename(__name__, "template.jinja2"), encoding="utf-8") as fp:
    template = Template(fp.read())

# Note: ideally this would be a dataclass, but we're supporting Python 3.5+ so we can't do this yet
NamedDiagram = typing.NamedTuple(
    "NamedDiagram", [("name", str), ("diagram", typing.Optional[railroad.DiagramItem])]
)
"""
A simple structure for associating a name with a railroad diagram
"""


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


def railroad_to_html(diagrams: typing.List[NamedDiagram], **kwargs) -> str:
    """
    Given a list of NamedDiagram, produce a single HTML string that visualises those diagrams
    :params kwargs: kwargs to be passed in to the template
    """
    data = []
    for diagram in diagrams:
        io = StringIO()
        diagram.diagram.writeSvg(io.write)
        data.append({"title": diagram.name, "text": "", "svg": io.getvalue()})

    return template.render(diagrams=data, **kwargs)


def to_railroad(
    element: pyparsing.ParserElement, diagram_kwargs: dict = {}
) -> typing.List[NamedDiagram]:
    """
    Convert a pyparsing element tree into a list of diagrams. This is the recommended entrypoint to diagram
    creation if you want to access the Railroad tree before it is converted to HTML
    :param diagram_kwargs: kwargs to pass to the Diagram() constructor
    """
    diagram_element, subdiagrams = _to_diagram_element(element)
    diagram = NamedDiagram(
        get_name(element, "Grammar"),
        railroad.Diagram(diagram_element, **diagram_kwargs),
    )
    return [diagram, *subdiagrams.values()]
    # TODO: convert all the partials into actual elements here, recursively


def _should_vertical(specification: typing.Union[int, bool], count: int) -> bool:
    """
    Returns true if we should return a vertical list of elements
    """
    if isinstance(specification, bool):
        return specification
    elif isinstance(specification, int):
        return count >= specification
    else:
        raise Exception()



class EditablePartial(typing.NamedTuple("EditablePartial", [
    ('func', typing.Callable),
    ('args', typing.Iterable),
    ('kwargs', typing.Dict)
])):
    """
    Acts like a functools.partial, but can be edited
    """
    @classmethod
    def from_call(cls, func, *args, **kwargs) -> 'EditablePartial':
        return EditablePartial(func=func, args=args, kwargs=kwargs)

    def __call__(self):
        return self.func(*self.args, **self.kwargs)


FirstInstance = typing.NamedTuple(
    "FirstInstance",
    [("parent", typing.Optional[EditablePartial]), ("element", EditablePartial),
     ('index', typing.Optional[int])],
)
Lookup = typing.Dict[int, typing.Union[NamedDiagram, FirstInstance]]

def _extract_into_diagram(el: pyparsing.Token, position: FirstInstance, lookup:Lookup, diagram_kwargs: dict) -> NamedDiagram:
    """
    Used when we encounter the same token twice in the same tree. When this happens, we replace all instances of that
    token with a terminal, and create a new subdiagram for the token
    """
    lookup = lookup.copy()
    el_id = id(el)

    # If the element has no real name, we name it Group N to at least make it unique
    count = len(lookup) + 1
    name = get_name(el, "Group {}".format(count))

    # We have to first put in a placeholder so that, if we encounter this element deeper down in the tree,
    # we won't have an infinite loop
    diagram = railroad.Diagram(position.element(), **diagram_kwargs)
    diagram.format(20)

    # Replace the original definition of this element with a regular block
    ret = railroad.NonTerminal(text=name)
    if 'item' in position.parent.kwargs:
        position.parent.kwargs['item'] = ret
    else:
        position.parent.kwargs['items'][position.index] = ret

    return NamedDiagram(name=name, diagram=diagram)

def _to_diagram_element(
    element: pyparsing.ParserElement,
    lookup=None,
    vertical: typing.Union[int, bool] = 5,
    diagram_kwargs: dict = {},
) -> typing.Tuple[
    typing.Optional[EditablePartial], typing.Dict[int, NamedDiagram]
]:
    """
    Recursively converts a PyParsing Element to a railroad Element
    :param vertical: Controls at what point we make a list of elements vertical. If this is an integer (the default),
    it sets the threshold of the number of items before we go vertical. If True, always go vertical, if False, never
    do so
    :returns: A tuple, where the first item is the converted version of the input element, and the second item is a
    list of extra diagrams that also need to be displayed in order to represent recursive grammars
    """
    if lookup is None:
        diagrams = {}
    else:
        # We don't want to be modifying the parent's version of the dict, although we do use it as a foundation
        diagrams = lookup.copy()

    # Convert the nebulous list of child elements into a single list objects for easy use
    if hasattr(element, "exprs"):
        exprs = element.exprs
    elif hasattr(element, "expr"):
        exprs = [element.expr]
    else:
        exprs = []

    name = get_name(element)
    # Python's id() is used to provide a unique identifier for elements
    el_id = id(element)

    if el_id in diagrams:
        if isinstance(diagrams[el_id], FirstInstance):
            # If we've seen this element exactly once before, we are only just now finding out that it's a duplicate,
            # so we have to extract it into a new diagram
            lookup[el_id] = _extract_into_diagram(element, position=diagrams[el_id], diagram_kwargs=diagram_kwargs, lookup=lookup)

        # Now we are guaranteed to have a sub-diagram for this element, so just return a node referencing it
        return EditablePartial.from_call(railroad.NonTerminal, text=diagrams[el_id].name), lookup

    else:
        # Recursively convert child elements
        children = []
        for expr in exprs:
            item, subdiagrams = _to_diagram_element(expr)
            # Some elements don't need to be shown in the diagram
            if item is not None:
                children.append(item)
            diagrams.update(subdiagrams)
        if len(exprs) > 0 and len(children) == 0:
            ret = None
        # Here we find the most relevant Railroad element for matching pyparsing Element
        elif isinstance(element, pyparsing.And):
            if _should_vertical(vertical, len(children)):
                ret = EditablePartial.from_call(railroad.Stack, items=children)
            else:
                ret = EditablePartial.from_call(railroad.Sequence, items=children)
        elif isinstance(element, (pyparsing.Or, pyparsing.MatchFirst)):
            if _should_vertical(vertical, len(children)):
                ret = EditablePartial.from_call(railroad.HorizontalChoice, items=children)
            else:
                ret = EditablePartial.from_call(railroad.Choice, 0, items=children)
        elif isinstance(element, pyparsing.Optional):
            ret = EditablePartial.from_call(railroad.Optional, item=children[0])
        elif isinstance(element, pyparsing.OneOrMore):
            ret = EditablePartial.from_call(railroad.OneOrMore, item=children[0])
        elif isinstance(element, pyparsing.ZeroOrMore):
            ret = EditablePartial.from_call(railroad.ZeroOrMore, item=children[0])
        elif isinstance(element, pyparsing.Group):
            # Generally there isn't any merit in labelling a group as a group if it doesn't have a custom name
            if name != "Group":
                ret = EditablePartial.from_call(railroad.Group, children[0], label=name)
            else:
                ret = children[0]
        elif isinstance(element, pyparsing.Empty) and name == "Empty":
            # Skip unnamed "Empty" elements
            ret = None
        elif len(exprs) > 1:
            ret = EditablePartial.from_call(railroad.Sequence, items=children)
        elif len(exprs) > 0:
            ret = EditablePartial.from_call(railroad.Group, item=children[0], label=name)
        else:
            ret = EditablePartial.from_call(railroad.Terminal, name)

        # Indicate this element's position in the tree so we can extract it if necessary
        lookup[el_id] = FirstInstance(parent=None, element=ret, index=None)

        # Set all the children's parent to this
        for i, child in enumerate(children):
            child_id = id(child)
            if child_id in lookup and isinstance(lookup[child_id], FirstInstance):
                lookup[child_id].parent = ret
                lookup[child_id].index = i

        return ret, diagrams
