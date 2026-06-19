"""A breadth-first oracle: find a shortest action sequence that solves a world
(collect every gem and reach the goal). Useful to verify generated worlds are
solvable and as a baseline/reference agent.

It reuses the authoritative action handlers, so it solves exactly the worlds the
simulator does. It searches the world's action space minus ``drop``/
``move_backward`` (never needed for collect-and-reach goals), which keeps the
state space small.
"""

from __future__ import annotations

from collections import deque

from . import actions as _actions

_HEADING = {"N": 0, "E": 1, "S": 2, "W": 3}
_SEARCHABLE = ("move_forward", "turn_left", "turn_right", "pickup", "toggle", "collect_gem")


def _clone(state):
    return _actions.SimState(
        col=state.col,
        row=state.row,
        heading=state.heading,
        carrying=state.carrying.copy() if state.carrying else None,
        objects={cell: o.copy() for cell, o in state.objects.items()},
        puzzle=state.puzzle,
    )


def _key(state):
    carry = (state.carrying.type, state.carrying.color) if state.carrying else None
    objs = frozenset(
        (cell, o.type, o.color, o.state, o.blocking) for cell, o in state.objects.items()
    )
    return (state.col, state.row, state.heading, carry, objs)


def _solved(state) -> bool:
    p = state.puzzle
    gems_left = any(o.type == "gem" and not o.blocking for o in state.objects.values())
    reached = p.goal is None or (state.col, state.row) == tuple(p.goal)
    return reached and not gems_left


def solve(puzzle, *, max_nodes: int = 300_000):
    """Return a shortest list of action names that solves ``puzzle``, or ``None``
    if none is found within ``max_nodes`` expansions."""
    search = [a for a in puzzle.actions if a in _SEARCHABLE]
    start = _actions.SimState(
        col=puzzle.start[0],
        row=puzzle.start[1],
        heading=_HEADING[puzzle.heading],
        carrying=None,
        objects={cell: o.copy() for cell, o in puzzle.objects.items()},
        puzzle=puzzle,
    )
    if _solved(start):
        return []

    seen = {_key(start)}
    queue = deque([(start, [])])
    nodes = 0
    while queue and nodes < max_nodes:
        state, path = queue.popleft()
        for name in search:
            nodes += 1
            nxt = _clone(state)
            _actions.get(name).handler(nxt)
            k = _key(nxt)
            if k in seen:
                continue
            seen.add(k)
            plan = path + [name]
            if _solved(nxt):
                return plan
            queue.append((nxt, plan))
    return None
