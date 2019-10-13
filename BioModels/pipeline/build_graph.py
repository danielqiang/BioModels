import networkx
from typing import Iterable, Tuple

__all__ = ['build_graph']


def build_graph(data: Iterable[Tuple[dict, dict, dict]]):
    """
    Builds a NetworkX DiGraph object from (Child, Edge, Parent) 3-tuples.

    Child and Parent must be dictionaries containing a 'name' key; this
    is the name of the node in the DiGraph.

    :param data: Iterable of (Child, Edge, Parent) 3-tuples.
    :rtype: networkx.DiGraph
    """
    g = networkx.DiGraph()

    for child_attrs, edge, parent_attrs in data:
        child_name, parent_name = child_attrs.pop('name'), parent_attrs.pop('name')

        g.add_node(child_name, **child_attrs)
        g.add_node(parent_name, **parent_attrs)
        g.add_edge(child_name, parent_name, label=edge)

    return g
