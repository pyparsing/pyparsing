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


def _should_vertical(specification: typing.Tuple[int, bool], count: int) -> bool:
    """
    Returns true if we should return a vertical list of elements
    """
    if isinstance(specification, bool):
        return specification
    elif isinstance(specification, int):
        return count >= specification
    else:
        raise Exception()


def _extract_into_diagram(el: pyparsing.Token) -> NamedDiagram:
    """
    Used when we encounter the same token twice in the same tree. When this happens, we replace all instances of that
    token with a terminal, and create a new subdiagram for the token
    """
    # If the Forward has no real name, we name it Group N to at least make it unique
    count = len(diagrams) + 1
    name = get_name(element, "Group {}".format(count))
    # We have to first put in a placeholder so that, if we encounter this element deeper down in the tree,
    # we won't have an infinite loop
    diagrams[el_id] = NamedDiagram(name=name, diagram=None)

    # At this point we create a new subdiagram, and add it to the dictionary of diagrams
    forward_element, forward_diagrams = _to_diagram_element(exprs[0], diagrams)
    diagram = railroad.Diagram(forward_element, **diagram_kwargs)
    diagrams.update(forward_diagrams)
    diagrams[el_id] = diagrams[el_id]._replace(diagram=diagram)
    diagram.format(20)

    # Here we just use the element's name as a placeholder for the recursive grammar which is defined separately
    ret = railroad.NonTerminal(text=name)


FirstInstance = typing.NamedTuple(
    "FirstInstance",
    [("parent", railroad.DiagramItem), ("element", railroad.DiagramItem)],
)
lookup_result = typing.Union[NamedDiagram, FirstInstance]


def _to_diagram_element(
    element: pyparsing.ParserElement,
    lookup=None,
    vertical: typing.Union[int, bool] = 5,
    diagram_kwargs: dict = {},
) -> typing.Tuple[
    typing.Optional[railroad.DiagramItem], typing.Dict[int, NamedDiagram]
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
            lookup[el_id] = _extract_into_diagram(diagrams[el_id])

        # Now we are guaranteed to have a sub-diagram for this element, so just return a node referencing it
        return railroad.NonTerminal(text=diagrams[el_id].name), lookup

    else:
        # If we haven't seen this element before, we can continue to recurse into the tree
        lookup[el_id] = FirstInstance(self.p)

        # Recursively convert child elements
        children = []
        for expr in exprs:
            item, subdiagrams = _to_diagram_element(expr, diagrams)
            # Some elements don't need to be shown in the diagram
            if item is not None:
                children.append(item)
            diagrams.update(subdiagrams)
        if len(exprs) > 0 and len(children) == 0:
            ret = None
        # Here we find the most relevant Railroad element for matching pyparsing Element
        elif isinstance(element, pyparsing.And):
            if _should_vertical(vertical, len(children)):
                ret = railroad.Stack(*children)
            else:
                ret = railroad.Sequence(*children)
        elif isinstance(element, (pyparsing.Or, pyparsing.MatchFirst)):
            if _should_vertical(vertical, len(children)):
                ret = railroad.HorizontalChoice(*children)
            else:
                ret = railroad.Choice(0, *children)
        elif isinstance(element, pyparsing.Optional):
            ret = railroad.Optional(children[0])
        elif isinstance(element, pyparsing.OneOrMore):
            ret = railroad.OneOrMore(children[0])
        elif isinstance(element, pyparsing.ZeroOrMore):
            ret = railroad.ZeroOrMore(children[0])
        elif isinstance(element, pyparsing.Group):
            # Generally there isn't any merit in labelling a group as a group if it doesn't have a custom name
            if name != "Group":
                ret = railroad.Group(children[0], label=name)
            else:
                ret = children[0]
        elif isinstance(element, pyparsing.Empty) and name == "Empty":
            # Skip unnamed "Empty" elements
            ret = None
        elif len(exprs) > 1:
            ret = railroad.Sequence(children[0])
        elif len(exprs) > 0:
            ret = railroad.Group(children[0], label=name)
        else:
            ret = railroad.Terminal(name)

    return ret, diagrams
