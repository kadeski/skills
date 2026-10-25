"""Builds graph.html, the knowledge graph page (spec section 10).

Stub from the base commit: the graph-page slice fills it in. The signature is the
contract the MCP server's `open_graph_page` codes against.
"""


def build(store, goal_id=None):
    """Writes <data>/graph.html and returns its Path.

    `store` is a store.Store. `goal_id` preselects that goal in the page's goal
    picker; None shows every goal.
    """
    raise NotImplementedError("graph_page.build is not built yet")
