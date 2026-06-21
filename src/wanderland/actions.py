"""Actions: the verb registry and the simulation semantics.

Each verb is a registered handler that mutates a :class:`SimState` and returns
one timeline step. :class:`~wanderland.world.World` runs a program by dispatching
recorded verbs through this registry, so adding a verb means registering a
handler here -- the simulator never grows an ``if/elif`` ladder.

The *set* of verbs a world permits -- its **action space** -- is declared
explicitly by the world builder; there is no default and no canonical bundle
(see :mod:`wanderland.puzzles`). A world just lists the verbs it allows, e.g.
a gentle level might allow ``("move_forward", "turn_left", "turn_right")``
while a fuller level allows the full set including ``pickup``/``toggle``.
``move_backward`` is registered too, for free-play worlds that opt into it.

Grid-world semantics: a *blocking* object (key/ball/box, a blocking gem, a
closed/locked door) occupies and *blocks* its cell -- you interact with the cell
you *face* while standing adjacent, never by walking onto it. Open doors, the
goal tile, and non-blocking gems are walkable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

# heading int: 0=N, 1=E, 2=S, 3=W. (dcol, drow) forward delta; row grows south.
_DELTA = {0: (0, -1), 1: (1, 0), 2: (0, 1), 3: (-1, 0)}

# Inventory objects -- pickup() puts one of these in your (single) hand.
CARRY_SLOT = ("key", "ball", "box")


def _pose(col: int, row: int, heading: int) -> dict:
    return {"col": col, "row": row, "h": heading}


@dataclass
class SimState:
    """Mutable agent + world state threaded through the action handlers."""

    col: int
    row: int
    heading: int
    carrying: object | None  # a puzzles.Obj or None (duck-typed)
    objects: dict  # (col, row) -> puzzles.Obj ; mutated by pickup/drop/toggle
    puzzle: object  # the Puzzle (for bounds / gaps / walls / lava / heights)
    dead: bool = False  # True once the agent steps into lava (episode over)

    @property
    def pose(self) -> dict:
        return _pose(self.col, self.row, self.heading)

    def front(self) -> tuple[int, int]:
        dc, dr = _DELTA[self.heading]
        return (self.col + dc, self.row + dr)

    def in_bounds(self, c: int, r: int) -> bool:
        return 0 <= c < self.puzzle.cols and 0 <= r < self.puzzle.rows

    # Why a cell can't be entered: None = passable, else 'edge'|'wall'|'door'|'object'.
    def block_reason(self, c: int, r: int) -> str | None:
        p = self.puzzle
        if not self.in_bounds(c, r) or (c, r) in p.gap_set:
            return "edge"  # off the world / water -> a fall
        if (c, r) in p.wall_set:
            return "wall"
        obj = self.objects.get((c, r))
        if obj is not None and obj.blocks():
            return "door" if obj.type == "door" else "object"
        return None

    def is_empty_floor(self, c: int, r: int) -> bool:
        """A cell you could drop onto: in-bounds, solid ground, nothing on it."""
        p = self.puzzle
        return (
            self.in_bounds(c, r)
            and (c, r) not in p.gap_set
            and (c, r) not in p.wall_set
            and (c, r) not in p.lava_set
            and self.objects.get((c, r)) is None
        )


@dataclass
class Action:
    name: str
    handler: Callable[[SimState], dict]
    canonical: bool
    doc: str


_REGISTRY: dict[str, Action] = {}


def action(name: str, *, canonical: bool = False, doc: str = ""):
    def deco(fn: Callable[[SimState], dict]) -> Callable[[SimState], dict]:
        _REGISTRY[name] = Action(name, fn, canonical, doc)
        return fn

    return deco


def is_registered(name: str) -> bool:
    return name in _REGISTRY


def get(name: str) -> Action:
    return _REGISTRY[name]


def describe(names) -> list[dict]:
    """The action space as handed to an agent: name + doc for each verb."""
    return [{"name": n, "doc": _REGISTRY[n].doc} for n in names]


def validate_space(names) -> tuple[str, ...]:
    """Normalize + check an explicitly-declared action space."""
    names = tuple(names)
    if not names:
        raise ValueError("An action space must list at least one action.")
    unknown = [n for n in names if n not in _REGISTRY]
    if unknown:
        raise ValueError(
            f"Unknown action(s) {unknown}. Known actions: {sorted(_REGISTRY)}"
        )
    return names


# --- the verbs ----------------------------------------------------------------
def _step_move(state: SimState, sign: int) -> dict:
    dc, dr = _DELTA[state.heading]
    tc, tr = state.col + sign * dc, state.row + sign * dr
    reason = state.block_reason(tc, tr)
    height_ok = state.puzzle.height_at(tc, tr) - state.puzzle.height_at(state.col, state.row)
    blocked = reason is not None or abs(height_ok) > 1
    step = {
        "kind": "move",
        "ok": not blocked,
        "from": state.pose,
        "target": _pose(tc, tr, state.heading),
    }
    if blocked:
        step["to"] = state.pose
        step["blocked_by"] = reason or "wall"  # height mismatch reads as a wall
    else:
        step["to"] = _pose(tc, tr, state.heading)
        state.col, state.row = tc, tr
        if (tc, tr) in state.puzzle.lava_set:
            state.dead = True  # walked into lava -> the run ends here
            step["died"] = True
    return step


@action("move_forward", canonical=True, doc="Step one tile in the direction you face.")
def _move_forward(state: SimState) -> dict:
    return _step_move(state, +1)


@action(
    "move_backward",
    canonical=False,
    doc="Step one tile backward without turning. Free-play only; off the canonical set.",
)
def _move_backward(state: SimState) -> dict:
    return _step_move(state, -1)


def _step_turn(state: SimState, delta: int) -> dict:
    new_h = (state.heading + delta) % 4
    step = {"kind": "turn", "ok": True, "from": state.pose, "to": _pose(state.col, state.row, new_h)}
    state.heading = new_h
    return step


@action("turn_left", canonical=True, doc="Rotate 90 degrees counter-clockwise.")
def _turn_left(state: SimState) -> dict:
    return _step_turn(state, -1)


@action("turn_right", canonical=True, doc="Rotate 90 degrees clockwise.")
def _turn_right(state: SimState) -> dict:
    return _step_turn(state, +1)


@action("pickup", canonical=True, doc="Pick up the object in the cell you face (a key/ball/box, or a blocking gem) into your one hand. You don't move; carry limit is one.")
def _pickup(state: SimState) -> dict:
    cell = state.front()
    obj = state.objects.get(cell)
    step = {"kind": "pickup", "ok": False, "cell": list(cell), "from": state.pose, "to": state.pose}
    if obj is not None and _carryable(obj) and state.carrying is None:
        # into the one hand. Position is unchanged -- only the grid and carrying change.
        state.carrying = obj
        del state.objects[cell]
        step["ok"] = True
        step["obj"] = obj.to_dict()
    step["carrying"] = state.carrying.to_dict() if state.carrying else None
    return step


def _carryable(obj) -> bool:
    return obj.type in CARRY_SLOT or (obj.type == "gem" and obj.blocking)


@action("collect_gem", canonical=False, doc="Collect the non-blocking gem on the tile you're standing on. It scores (it isn't carried, and there's no limit).")
def _collect_gem(state: SimState) -> dict:
    # Walk-and-collect: you stand ON a walkable gem, then collect it. (Interaction
    # worlds use blocking gems + pickup-from-the-front instead.)
    cell = (state.col, state.row)
    obj = state.objects.get(cell)
    ok = obj is not None and obj.type == "gem" and not obj.blocking
    step = {"kind": "collect", "ok": ok, "cell": list(cell), "from": state.pose, "to": state.pose}
    if ok:
        del state.objects[cell]
        step["gem"] = list(cell)  # the frontend's existing collect animation keys off this
        step["collected"] = obj.to_dict()
    return step


@action("drop", canonical=True, doc="Drop what you're carrying onto the empty floor cell you face.")
def _drop(state: SimState) -> dict:
    cell = state.front()
    ok = state.carrying is not None and state.is_empty_floor(*cell)
    step = {"kind": "drop", "ok": ok, "cell": list(cell), "from": state.pose, "to": state.pose}
    if ok:
        obj = state.carrying
        state.objects[cell] = obj
        state.carrying = None
        step["obj"] = obj.to_dict()
    step["carrying"] = state.carrying.to_dict() if state.carrying else None
    return step


@action("toggle", canonical=True, doc="Open/close a door (unlock with a matching key) or open a box, in the cell you face.")
def _toggle(state: SimState) -> dict:
    cell = state.front()
    obj = state.objects.get(cell)
    ok, effect, reveals = False, None, None
    if obj is not None and obj.type == "door":
        if obj.state == "closed":
            obj.state, ok, effect = "open", True, "open"
        elif obj.state == "open":
            obj.state, ok, effect = "closed", True, "close"
        elif obj.state == "locked":
            carry = state.carrying
            if carry is not None and carry.type == "key" and carry.color == obj.color:
                obj.state, ok, effect = "open", True, "unlock"  # key is NOT consumed
    elif obj is not None and obj.type == "box":
        contents = obj.contains
        if contents is None:
            del state.objects[cell]
        else:
            state.objects[cell] = contents
        ok, effect = True, "open_box"
        reveals = contents.to_dict() if contents else None
    step = {
        "kind": "toggle",
        "ok": ok,
        "cell": list(cell),
        "effect": effect,
        "reveals": reveals,
        "from": state.pose,
        "to": state.pose,
    }
    if obj is not None:
        step["target"] = {"type": obj.type, "color": obj.color}
    step["carrying"] = state.carrying.to_dict() if state.carrying else None
    return step
