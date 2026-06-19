"""Puzzle definitions -- the static worlds an agent acts in.

A :class:`Puzzle` is a declarative environment spec: a grid of tiles (some may be
missing -> water/gaps, or solid -> walls), where the agent starts and faces,
the typed/colored **objects** in the world (gems, keys, balls, boxes, doors), an
optional goal tile, and -- required -- the **action space** the world permits.

There is no default action space and no canonical bundle: every world lists its
verbs explicitly, so a measured run can never silently use the wrong vocabulary
(e.g. ``actions=("move_forward", "turn_left", "turn_right", "pickup")``).

``from_ascii`` sketches a world as text and is the most readable way to author.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from . import actions as _actions

# Cardinal headings as the user/author writes them.
HEADINGS = ("N", "E", "S", "W")

# Single-letter colour codes used in ASCII tokens.
COLOR_CODES = {
    "r": "red",
    "g": "green",
    "b": "blue",
    "p": "purple",
    "y": "yellow",
    "e": "grey",
}
COLORS = tuple(COLOR_CODES.values())

# Start-tile glyphs that also encode the agent's facing direction (load-bearing:
# egocentric turning depends on heading). `S` is still accepted, taking heading
# from the `heading=` argument.
DIR_GLYPHS = {"^": "N", ">": "E", "v": "S", "<": "W"}


@dataclass
class Obj:
    """A thing occupying one cell.

    ``type``: 'gem' | 'key' | 'ball' | 'box' | 'door'.
    ``color``: required for key/ball/box/door (matching matters), None for gem.
    ``state``: doors only -- 'open' | 'closed' | 'locked'.
    ``contains``: boxes only -- what's revealed when the box is opened.
    ``blocking``: whether the object occupies (blocks) its cell. Keys/balls/boxes
        always block. A gem may be blocking (taken with ``pickup`` from the front)
        or non-blocking (walkable -- collected by stepping onto it).
    """

    type: str
    color: str | None = None
    state: str | None = None
    contains: "Obj | None" = None
    blocking: bool = True

    def blocks(self) -> bool:
        # Doors block unless open; everything else honours its `blocking` flag
        # (always True for keys/balls/boxes; configurable for gems).
        if self.type == "door":
            return self.state != "open"
        return self.blocking

    def copy(self) -> "Obj":
        return Obj(
            self.type,
            self.color,
            self.state,
            self.contains.copy() if self.contains else None,
            self.blocking,
        )

    def to_dict(self) -> dict:
        d: dict = {"type": self.type}
        if self.color is not None:
            d["color"] = self.color
        if self.state is not None:
            d["state"] = self.state
        if self.contains is not None:
            d["contains"] = self.contains.to_dict()
        if not self.blocking:
            d["blocking"] = False  # default (True) is omitted to keep dicts lean
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Obj":
        return cls(
            type=d["type"],
            color=d.get("color"),
            state=d.get("state"),
            contains=cls.from_dict(d["contains"]) if d.get("contains") else None,
            blocking=d.get("blocking", True),
        )


@dataclass
class Puzzle:
    name: str
    cols: int
    rows: int
    start: tuple[int, int]
    actions: tuple[str, ...] | None = None  # REQUIRED action space (no default)
    heading: str = "S"
    objects: dict[tuple[int, int], Obj] = field(default_factory=dict)
    goal: tuple[int, int] | None = None
    gaps: list[tuple[int, int]] = field(default_factory=list)
    walls: list[tuple[int, int]] = field(default_factory=list)
    heights: dict[tuple[int, int], int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.heading not in HEADINGS:
            raise ValueError(f"heading must be one of {HEADINGS}, got {self.heading!r}")
        if self.actions is None:
            raise ValueError(
                "Puzzle requires an explicit action space (there is no default). "
                "Pass actions=(...) listing the verbs this world permits, e.g. "
                "('move_forward', 'turn_left', 'turn_right', 'pickup', 'drop', 'toggle')."
            )
        self.actions = _actions.validate_space(self.actions)

    @property
    def gap_set(self) -> set[tuple[int, int]]:
        return {tuple(g) for g in self.gaps}

    @property
    def wall_set(self) -> set[tuple[int, int]]:
        return {tuple(w) for w in self.walls}

    @property
    def gem_cells(self) -> list[tuple[int, int]]:
        return [cell for cell, o in self.objects.items() if o.type == "gem"]

    @property
    def score_gem_cells(self) -> list[tuple[int, int]]:
        """Non-blocking gems -- the consumable score collectibles. Blocking gems
        are carried inventory (like balls) and don't count toward the gem score."""
        return [cell for cell, o in self.objects.items() if o.type == "gem" and not o.blocking]

    def height_at(self, col: int, row: int) -> int:
        return int(self.heights.get((col, row), 0))

    def to_dict(self) -> dict:
        """Serialize to the plain dict shipped to the frontend (a sync trait)."""
        return {
            "version": 2,
            "name": self.name,
            "cols": self.cols,
            "rows": self.rows,
            "start": list(self.start),
            "heading": self.heading,
            "actions": list(self.actions),
            # objects keyed "col,row" (JSON keys must be strings)
            "objects": {f"{c},{r}": o.to_dict() for (c, r), o in self.objects.items()},
            # derived gem cells -- kept for the current renderer + HUD count
            "gems": [list(c) for c in self.gem_cells],
            "goal": list(self.goal) if self.goal is not None else None,
            "gaps": [list(g) for g in self.gaps],
            "walls": [list(w) for w in self.walls],
            "heights": {f"{c},{r}": v for (c, r), v in self.heights.items()},
        }


# --- ASCII authoring ----------------------------------------------------------
def _parse_simple(tok: str) -> Obj:
    head, rest = tok[0], tok[1:]
    if head == "G":
        return Obj("gem")  # blocking: take it with pickup() from the front
    if head == "g":
        return Obj("gem", blocking=False)  # non-blocking: collect by walking onto it
    color = COLOR_CODES.get(rest)
    if head in "KBXDLd" and color is None:
        raise ValueError(
            f"token {tok!r} needs a colour suffix (r/g/b/p/y/e), e.g. 'Kr' for a red key"
        )
    if head == "K":
        return Obj("key", color)
    if head == "B":
        return Obj("ball", color)
    if head == "X":
        return Obj("box", color)
    if head == "D":
        return Obj("door", color, "closed")
    if head == "L":
        return Obj("door", color, "locked")
    if head == "d":
        return Obj("door", color, "open")
    raise ValueError(f"Unknown object token {tok!r}")


def _parse_obj(tok: str) -> Obj:
    # A box may declare contents: "Xr:Kb" = red box containing a blue key.
    if ":" in tok:
        outer, inner = tok.split(":", 1)
        box = _parse_simple(outer)
        if box.type != "box":
            raise ValueError(f"only boxes take contents, got {tok!r}")
        box.contains = _parse_simple(inner)
        return box
    return _parse_simple(tok)


def from_ascii(
    name: str,
    grid: str,
    *,
    actions: tuple[str, ...],
    heading: str = "S",
    goal: tuple[int, int] | None = None,
) -> Puzzle:
    """Build a :class:`Puzzle` from an ASCII sketch.

    Tokens (whitespace-separated), top row is ``row == 0`` (north):

    ===========  ====================================================
    token        meaning
    ===========  ====================================================
    ``^ > v <``  start tile + the agent's facing (N/E/S/W)
    ``S``        start tile, heading from the ``heading=`` argument
    ``.``        walkable floor
    ``#``        wall -- not walkable (the universal ``#``-is-wall convention)
    ``~``        water -- not walkable (Byte-flavored; treated as a wall)
    ``O``        goal tile (walkable; won by stepping on it)
    ``G``        a blocking gem -- carried via pickup() from the front
    ``g``        a non-blocking gem -- collected by walking onto it
    ``Kc``       a key of colour ``c``        (r/g/b/p/y/e)
    ``Bc``       a ball of colour ``c``
    ``Xc``       a box of colour ``c``  (``Xc:obj`` to give it hidden contents)
    ``Dc``       a closed door of colour ``c``
    ``Lc``       a locked door of colour ``c`` (needs a matching key to open)
    ===========  ====================================================

    ``actions`` is required -- the explicit list of verbs this world permits.

    Example::

        from_ascii("Locked Room", '''
            > . . Ky
            ~ ~ ~ .
            O Ly . .
        ''', actions=("turn_left", "turn_right", "move_forward", "pickup", "toggle"))
    """
    lines = [ln.split() for ln in grid.strip("\n").splitlines() if ln.strip()]
    rows = len(lines)
    cols = max(len(ln) for ln in lines)

    start: tuple[int, int] | None = None
    start_heading: str | None = None
    objects: dict[tuple[int, int], Obj] = {}
    gaps: list[tuple[int, int]] = []
    walls: list[tuple[int, int]] = []
    ascii_goal: tuple[int, int] | None = None

    for r, line in enumerate(lines):
        for c, token in enumerate(line):
            cell = (c, r)
            if token == ".":
                pass
            elif token == "#":
                walls.append(cell)
            elif token == "~":
                gaps.append(cell)  # water: impassable (rendered as a fall, wall-like)
            elif token in DIR_GLYPHS:
                start, start_heading = cell, DIR_GLYPHS[token]
            elif token == "S":
                start = cell  # heading taken from the `heading=` argument
            elif token == "O":
                ascii_goal = cell
            else:
                objects[cell] = _parse_obj(token)

    if start is None:
        raise ValueError("ASCII grid must contain a start tile (^ > v < or S)")

    return Puzzle(
        name=name,
        cols=cols,
        rows=rows,
        start=start,
        actions=actions,
        heading=start_heading or heading,
        objects=objects,
        goal=goal if goal is not None else ascii_goal,
        gaps=gaps,
        walls=walls,
    )


# --- serialization round-trip (structured dict / JSON) ------------------------
def _cells(pairs):
    return [tuple(p) for p in pairs]


def from_dict(d: dict) -> Puzzle:
    """Rebuild a :class:`Puzzle` from its :meth:`Puzzle.to_dict` form.

    The inverse of ``to_dict`` -- load a world that was generated or stored as
    structured data. Round-trips: ``from_dict(p.to_dict()).to_dict() == p.to_dict()``.
    """
    objects = {}
    for k, od in (d.get("objects") or {}).items():
        c, r = (int(x) for x in k.split(","))
        objects[(c, r)] = Obj.from_dict(od)
    heights = {}
    for k, v in (d.get("heights") or {}).items():
        c, r = (int(x) for x in k.split(","))
        heights[(c, r)] = int(v)
    return Puzzle(
        name=d["name"],
        cols=d["cols"],
        rows=d["rows"],
        start=tuple(d["start"]),
        actions=tuple(d["actions"]),
        heading=d.get("heading", "S"),
        objects=objects,
        goal=tuple(d["goal"]) if d.get("goal") else None,
        gaps=_cells(d.get("gaps", [])),
        walls=_cells(d.get("walls", [])),
        heights=heights,
    )


def to_json(puzzle: Puzzle, **kwargs) -> str:
    """Serialize a puzzle to a JSON string (``json.dumps`` kwargs accepted)."""
    return json.dumps(puzzle.to_dict(), **kwargs)


def from_json(text: str) -> Puzzle:
    """Load a puzzle from a JSON string produced by :func:`to_json`."""
    return from_dict(json.loads(text))


# --- prompt rendering: structured (canonical) and ASCII (a view) --------------
# Both render from the one source of truth (the Puzzle), so the SAME world can be
# shown two ways -- useful for measuring how much the encoding moves an agent's
# success rate. Box contents are hidden until toggled (so opening a box is a real step).
_REV_DIR = {"N": "^", "E": ">", "S": "v", "W": "<"}
_REV_COLOR = {v: k for k, v in COLOR_CODES.items()}
_DIR_NAME = {"N": "north", "E": "east", "S": "south", "W": "west"}


def _describe(o: Obj) -> str:
    parts: list[str] = []
    if o.type == "door" and o.state:
        parts.append(o.state)
    if o.color:
        parts.append(o.color)
    parts.append(o.type)
    return " ".join(parts)


def _glyph(o: Obj) -> str:
    cc = _REV_COLOR.get(o.color, "")
    if o.type == "gem":
        return "G" if o.blocking else "g"
    if o.type == "door":
        return {"locked": "L", "open": "d", "closed": "D"}.get(o.state, "D") + cc
    return {"key": "K", "ball": "B", "box": "X"}[o.type] + cc


def render_structured(puzzle: "Puzzle", action_space) -> str:
    """The canonical, measured prompt: a header + a coordinate object list."""
    p = puzzle
    sc, sr = p.start
    lines = [
        f"World: {p.name}  ({p.cols} wide x {p.rows} tall; x east, y south, origin top-left)",
        f"You are at ({sc},{sr}) facing {_DIR_NAME[p.heading]}, carrying nothing.",
        "Actions: " + ", ".join(action_space),
    ]
    if p.goal is not None:
        lines.append(f"Goal: step onto ({p.goal[0]},{p.goal[1]}).")
    objs = [
        f"- {_describe(o)} at ({c},{r})"
        for (c, r), o in sorted(p.objects.items(), key=lambda kv: (kv[0][1], kv[0][0]))
    ]
    if objs:
        lines.append("Objects (box contents are hidden until opened):")
        lines.extend(objs)
    walls = sorted(p.wall_set, key=lambda cr: (cr[1], cr[0]))
    water = sorted(p.gap_set, key=lambda cr: (cr[1], cr[0]))
    if walls:
        lines.append("Walls: " + ", ".join(f"({c},{r})" for c, r in walls))
    if water:
        lines.append("Water (impassable): " + ", ".join(f"({c},{r})" for c, r in water))
    return "\n".join(lines)


def render_ascii(puzzle: "Puzzle") -> str:
    """An ASCII *view* of the same state (a render, not the measured input)."""
    p = puzzle
    grid = [["." for _ in range(p.cols)] for _ in range(p.rows)]
    for c, r in p.wall_set:
        grid[r][c] = "#"
    for c, r in p.gap_set:
        grid[r][c] = "~"
    if p.goal is not None:
        gc, gr = p.goal
        grid[gr][gc] = "O"
    for (c, r), o in p.objects.items():
        grid[r][c] = _glyph(o)  # box rendered without its contents (hidden)
    sc, sr = p.start
    grid[sr][sc] = _REV_DIR[p.heading]
    return "\n".join(" ".join(row) for row in grid)


# --- built-in worlds (each declares its own action space) ---------------------
# Gem levels move + collect_gem (walk onto a gem, then collect it); interaction
# levels add pickup/drop/toggle. Spelled out per world -- no default bundle.
_WALK = ("move_forward", "turn_left", "turn_right")
_COLLECT = ("move_forward", "turn_left", "turn_right", "collect_gem")
_BABYAI = ("move_forward", "turn_left", "turn_right", "pickup", "drop", "toggle")


def first_steps() -> Puzzle:
    """The gentlest world: walk up to the gem, then collect it."""
    return from_ascii("First Steps", "> . . g", actions=_COLLECT)


def gem_path() -> Puzzle:
    """Turns, a water gap, and two gems -- walk onto each one and collect_gem()."""
    return from_ascii(
        "Gem Path",
        """
        > . . g
        . ~ ~ .
        g . . O
        """,
        actions=_COLLECT,
    )


def spiral() -> Puzzle:
    """A roomier world that rewards turning -- gems around the rim, end at home."""
    return from_ascii(
        "Grand Tour",
        """
        > . . g
        . . . .
        . . . .
        g . . g
        """,
        actions=_COLLECT,
        goal=(0, 0),
    )


def locked_room() -> Puzzle:
    """A key-and-door room: the locked door sits in a wall between two rooms.
    Grab the yellow key, unlock the door, pass through to the goal."""
    return from_ascii(
        "Locked Room",
        """
        > . # .
        . . Ly .
        Ky . # O
        """,
        actions=_BABYAI,
    )


#: Convenient registry for tab-completion / discovery.
ALL = {
    "first_steps": first_steps,
    "gem_path": gem_path,
    "spiral": spiral,
    "locked_room": locked_room,
}
