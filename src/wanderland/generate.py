"""Procedural world generation -- a distribution of grid worlds to
experiment over. Deterministic in ``seed`` so runs are reproducible.

Worlds are solvable by construction (open rooms + a reachable key/door/goal);
:func:`wanderland.solve.solve` verifies any generated world if you want proof.
"""

from __future__ import annotations

import random as _random

from .puzzles import Obj, Puzzle

COLORS = ("red", "green", "blue", "purple", "yellow", "grey")
# The canonical action set, spelled out (there is no default bundle).
SIX = ("move_forward", "turn_left", "turn_right", "pickup", "drop", "toggle")


def random_room(
    *,
    seed: int = 0,
    cols: int = 6,
    rows: int = 5,
    locked: bool = True,
    gems: int = 0,
    actions: tuple[str, ...] = SIX,
) -> Puzzle:
    """A two-room world split by a wall with a door.

    The agent and a matching-colour key start in one room; the goal is in the
    other. With ``locked=True`` the door needs the key. ``gems`` scatters that
    many **non-blocking** collectibles (always safe -- they never block a path).
    Deterministic in ``seed``. Returns a :class:`~wanderland.puzzles.Puzzle`.
    """
    if cols < 4 or rows < 1:
        raise ValueError("random_room needs cols >= 4 and rows >= 1")

    # non-blocking gems are collected with collect_gem -- so the objective is only
    # solvable if the world actually permits that verb.
    actions = tuple(actions)
    if gems > 0 and "collect_gem" not in actions:
        actions = actions + ("collect_gem",)

    rng = _random.Random(seed)
    wc = rng.randint(2, cols - 2)  # the dividing wall column
    door_row = rng.randint(0, rows - 1)
    walls = [(wc, r) for r in range(rows) if r != door_row]
    color = rng.choice(COLORS)
    objects: dict[tuple[int, int], Obj] = {
        (wc, door_row): Obj("door", color, "locked" if locked else "closed")
    }

    left = [(c, r) for c in range(wc) for r in range(rows)]
    right = [(c, r) for c in range(wc + 1, cols) for r in range(rows)]
    # keep the cells on each side of the doorway clear, so the door stays usable
    left = [cell for cell in left if cell != (wc - 1, door_row)]
    right = [cell for cell in right if cell != (wc + 1, door_row)]
    rng.shuffle(left)
    rng.shuffle(right)

    start = left.pop()
    heading = rng.choice(("N", "E", "S", "W"))
    objects[left.pop()] = Obj("key", color)  # a matching key in the agent's room
    goal = right.pop()

    pool = left + right
    rng.shuffle(pool)
    for _ in range(gems):
        if not pool:
            break
        objects[pool.pop()] = Obj("gem", blocking=False)  # non-blocking: path-safe

    return Puzzle(
        name=f"Generated Room (seed {seed})",
        cols=cols,
        rows=rows,
        start=start,
        actions=tuple(actions),
        heading=heading,
        objects=objects,
        goal=goal,
        walls=walls,
    )
