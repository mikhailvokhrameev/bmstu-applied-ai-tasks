"""Structural class-graph metrics from specification 1.3, section 4.2.

The caller supplies named user classes and explicit parent-to-child arcs.  Depth
statistics aggregate all root-to-leaf paths without enumerating the DAG paths.
"""
from collections import deque
from dataclasses import dataclass
import statistics


class StructuralError(ValueError):
    pass


@dataclass(frozen=True)
class StructuralMetrics:
    N: int
    H: int
    U: int
    D1: int | None
    D2: float | None
    D3: int | None
    W1: int | None
    W2: float | None
    W3: int | None
    T1: int
    T2: float
    T3: float
    I1: float
    I2: float
    I3: float
    I4: float
    CY1: int
    CY2: float


def normalize_graph(graph):
    """Return unique vertices and arcs, rejecting missing or invented vertices."""
    if not isinstance(graph, dict) or 'vertices' not in graph or 'edges' not in graph:
        raise StructuralError('Explicit graph with vertices and edges is required')
    vertices, edges = graph['vertices'], graph['edges']
    if not isinstance(vertices, (list, tuple, set, frozenset)):
        raise StructuralError('vertices must be a collection of class names')
    if any(not isinstance(v, str) or not v.strip() for v in vertices):
        raise StructuralError('vertices must contain nonempty class names')
    vertices = frozenset(vertices)
    if not vertices:
        raise StructuralError('Structural metrics are undefined for an empty graph')
    if not isinstance(edges, (list, tuple, set, frozenset)):
        raise StructuralError('edges must be a collection of parent-child pairs')
    unique_edges = set()
    for edge in edges:
        if not isinstance(edge, (list, tuple)) or len(edge) != 2:
            raise StructuralError('Each edge must be one parent-child pair')
        parent, child = edge
        if not isinstance(parent, str) or not isinstance(child, str):
            raise StructuralError('Edge endpoints must be class names')
        if parent not in vertices or child not in vertices:
            raise StructuralError('Edge references a class absent from vertices')
        unique_edges.add((parent, child))
    return vertices, frozenset(unique_edges)


def _adjacency(vertices, edges):
    children = {v: set() for v in vertices}
    parents = {v: set() for v in vertices}
    for parent, child in edges:
        children[parent].add(child)
        parents[child].add(parent)
    return children, parents


def _topological_order(vertices, children, parents):
    remaining = {v: len(parents[v]) for v in vertices}
    ready = deque(sorted(v for v in vertices if not remaining[v]))
    order = []
    while ready:
        vertex = ready.popleft()
        order.append(vertex)
        for child in sorted(children[vertex]):
            remaining[child] -= 1
            if not remaining[child]:
                ready.append(child)
    return order


def graph_has_cycle(graph):
    """Detect cycles in linear time without computing depth or enumerating cycles."""
    vertices, edges = normalize_graph(graph)
    children, parents = _adjacency(vertices, edges)
    return len(_topological_order(vertices, children, parents)) != len(vertices)


def _cyclic_components(vertices, children):
    # Tarjan components restrict exact cycle enumeration to the cyclic subgraph.
    indices, low, stack, on_stack, components = {}, {}, [], set(), []

    def visit(vertex):
        indices[vertex] = low[vertex] = len(indices)
        stack.append(vertex)
        on_stack.add(vertex)
        for child in sorted(children[vertex]):
            if child not in indices:
                visit(child)
                low[vertex] = min(low[vertex], low[child])
            elif child in on_stack:
                low[vertex] = min(low[vertex], indices[child])
        if low[vertex] == indices[vertex]:
            component = set()
            while True:
                member = stack.pop()
                on_stack.remove(member)
                component.add(member)
                if member == vertex:
                    break
            if len(component) > 1 or vertex in children[vertex]:
                components.append(component)

    for vertex in sorted(vertices):
        if vertex not in indices:
            visit(vertex)
    return components


def _cycle_statistics(vertices, children):
    components = _cyclic_components(vertices, children)
    cycle_count = 0
    cycle_vertices = set()
    for component in components:
        cycle_vertices.update(component)
        for start in sorted(component):
            # Every directed simple cycle has one lexicographically least
            # vertex. Starting only there removes cyclic rotations, while
            # opposite directed traversals remain distinct cycles.
            active = {start}

            def count_from(vertex):
                count = 0
                for child in sorted(children[vertex] & component):
                    if child == start:
                        count += 1
                    elif child > start and child not in active:
                        active.add(child)
                        count += count_from(child)
                        active.remove(child)
                return count

            cycle_count += count_from(start)
    return cycle_count, len(cycle_vertices) / len(vertices)


def compute_structural_metrics(graph):
    """Compute all fifteen metrics; cyclic depth and width are explicit None."""
    vertices, edges = normalize_graph(graph)
    children, parents = _adjacency(vertices, edges)
    size = len(vertices)
    degrees = [len(parents[v]) + len(children[v]) for v in vertices]
    multiple_parents = sum(len(parents[v]) > 1 for v in vertices)
    overloaded = sum(degree > 9 for degree in degrees)
    order = _topological_order(vertices, children, parents)
    cycle_count, cycle_fraction = (0, 0.0)
    if len(order) != size:
        cycle_count, cycle_fraction = _cycle_statistics(vertices, children)
        depth_max = depth_mean = depth_total = None
        width_max = width_mean = width_total = None
    else:
        path_counts = {v: int(not parents[v]) for v in vertices}
        path_lengths = {v: 0 for v in vertices}
        levels = {v: 0 for v in vertices}
        for vertex in order:
            for child in children[vertex]:
                path_counts[child] += path_counts[vertex]
                path_lengths[child] += path_lengths[vertex] + path_counts[vertex]
                levels[child] = max(levels[child], levels[vertex] + 1)
        leaves = [v for v in vertices if not children[v]]
        path_count = sum(path_counts[v] for v in leaves)
        depth_total = sum(path_lengths[v] for v in leaves)
        depth_max = max(levels.values())
        depth_mean = depth_total / path_count
        widths = [0] * (depth_max + 1)
        for level in levels.values():
            widths[level] += 1
        width_max = max(widths)
        width_mean = size / len(widths)
        width_total = sum(widths)
    return StructuralMetrics(
        N=size, H=len(edges), U=overloaded,
        D1=depth_max, D2=depth_mean, D3=depth_total,
        W1=width_max, W2=width_mean, W3=width_total,
        T1=multiple_parents, T2=len(edges) / size, T3=multiple_parents / size,
        I1=(size - overloaded) / size, I2=sum(degrees) / size,
        I3=float(statistics.median(degrees)),
        I4=statistics.stdev(degrees) if size > 1 else 0.0,
        CY1=cycle_count, CY2=cycle_fraction,
    )


compute_graph_metrics = compute_structural_metrics
