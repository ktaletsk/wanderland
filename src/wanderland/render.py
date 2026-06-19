"""A fast, headless, deterministic 2D top-down renderer -- the agent-facing
*image* observation (the third encoding alongside structured/ascii text).

No browser and no required dependencies: it draws into a plain RGB buffer and
encodes PNG with the stdlib (``zlib``). ``to_numpy()`` is available if numpy is
installed (``pip install wanderland[rl]``).

    from wanderland import render, random_room
    render(random_room(seed=1)).save("world.png")     # PNG via stdlib
    obs = render(random_room(seed=1)).to_numpy()       # (H, W, 3) uint8
"""

from __future__ import annotations

import struct
import zlib

from . import actions as _actions

# --- palette (RGB) ------------------------------------------------------------
_FLOOR = (171, 199, 124)
_FLOOR_LINE = (151, 179, 106)
_WALL = (128, 136, 146)
_WATER = (92, 162, 200)
_LAVA = (231, 110, 52)
_AGENT = (214, 74, 58)
_GOAL = (240, 200, 74)
_GEM = (70, 205, 235)
_DARK = (44, 44, 50)
_GREY = (154, 163, 171)
_OBJ = {
    "red": (226, 86, 76),
    "green": (76, 191, 90),
    "blue": (74, 139, 223),
    "purple": (165, 95, 214),
    "yellow": (240, 198, 74),
    "grey": (154, 163, 171),
}
_HEADING = {"N": 0, "E": 1, "S": 2, "W": 3}


class Image:
    """A small RGB raster with stdlib PNG + optional numpy export."""

    def __init__(self, width: int, height: int, fill=(255, 255, 255)):
        self.width = width
        self.height = height
        self.buf = bytearray(fill * (width * height))

    def set(self, x: int, y: int, rgb) -> None:
        i = (y * self.width + x) * 3
        self.buf[i], self.buf[i + 1], self.buf[i + 2] = rgb

    def to_png(self) -> bytes:
        def chunk(typ: bytes, data: bytes) -> bytes:
            return (
                struct.pack(">I", len(data))
                + typ
                + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
            )

        stride = self.width * 3
        raw = bytearray()
        for y in range(self.height):
            raw.append(0)  # filter: none
            raw.extend(self.buf[y * stride : (y + 1) * stride])
        ihdr = struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0)
        return (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b"")
        )

    def to_numpy(self):
        import numpy as np  # optional

        return np.frombuffer(bytes(self.buf), dtype=np.uint8).reshape(self.height, self.width, 3)

    def save(self, path) -> None:
        with open(path, "wb") as f:
            f.write(self.to_png())


# --- shape tests (cell-local coords, u/v in [0,1]) ----------------------------
def _circle(u, v, cx, cy, r):
    return (u - cx) ** 2 + (v - cy) ** 2 <= r * r


def _ring(u, v, r0, r1):
    d = (u - 0.5) ** 2 + (v - 0.5) ** 2
    return r0 * r0 <= d <= r1 * r1


def _rect(u, v, x0, y0, x1, y1):
    return x0 <= u <= x1 and y0 <= v <= y1


def _diamond(u, v, r):
    return abs(u - 0.5) + abs(v - 0.5) <= r


def _agent_tri(heading):
    pts = [(0.20, 0.24), (0.20, 0.76), (0.84, 0.5)]  # points East
    for _ in range((heading - 1) % 4):  # rotate 90 deg per step: E->S->W->N
        pts = [(1 - y, x) for (x, y) in pts]
    return pts


def _in_tri(u, v, tri):
    (ax, ay), (bx, by), (cx, cy) = tri
    d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if d == 0:
        return False
    a = ((by - cy) * (u - cx) + (cx - bx) * (v - cy)) / d
    b = ((cy - ay) * (u - cx) + (ax - cx) * (v - cy)) / d
    return a >= 0 and b >= 0 and (a + b) <= 1


def _object_color(obj, u, v):
    """The object's colour at cell-local (u, v), or None (transparent)."""
    t = obj.type
    if t == "gem":
        return _GEM if _diamond(u, v, 0.30 if obj.blocking else 0.24) else None
    color = _OBJ.get(obj.color, _GREY)
    if t == "ball":
        return color if _circle(u, v, 0.5, 0.5, 0.30) else None
    if t == "key":
        if v < 0.5 and _ring(u, v, 0.10, 0.18):  # bow
            return color
        if _rect(u, v, 0.45, 0.42, 0.55, 0.78):  # shaft
            return color
        if _rect(u, v, 0.55, 0.60, 0.68, 0.69):  # tooth
            return color
        return None
    if t == "box":
        if _rect(u, v, 0.18, 0.18, 0.82, 0.82):
            return _DARK if _rect(u, v, 0.18, 0.30, 0.82, 0.355) else color  # lid seam
        return None
    if t == "door":
        if obj.state == "open":
            return color if (_rect(u, v, 0.12, 0.12, 0.22, 0.88) or _rect(u, v, 0.78, 0.12, 0.88, 0.88)) else None
        if _rect(u, v, 0.14, 0.10, 0.86, 0.90):
            if obj.state == "locked" and _circle(u, v, 0.5, 0.5, 0.085):
                return _DARK  # keyhole
            return color
        return None
    return None


# --- the renderer -------------------------------------------------------------
def _as_state(target):
    """Accept a Puzzle (render its start state) or an actions.SimState."""
    if isinstance(target, _actions.SimState):
        return target
    p = target  # a Puzzle
    return _actions.SimState(
        col=p.start[0],
        row=p.start[1],
        heading=_HEADING[p.heading],
        carrying=None,
        objects={cell: o.copy() for cell, o in p.objects.items()},
        puzzle=p,
    )


def render(target, *, tile: int = 24) -> Image:
    """Render a world to a top-down :class:`Image`. ``target`` is a Puzzle (its
    start state) or a live ``SimState``. ``tile`` is the pixel size per cell."""
    state = _as_state(target)
    p = state.puzzle
    img = Image(p.cols * tile, p.rows * tile)
    goal = tuple(p.goal) if p.goal is not None else None
    walls, gaps, lava = p.wall_set, p.gap_set, p.lava_set

    for r in range(p.rows):
        for c in range(p.cols):
            if (c, r) in walls:
                bg = _WALL
            elif (c, r) in gaps:
                bg = _WATER
            elif (c, r) in lava:
                bg = _LAVA
            else:
                bg = _FLOOR
            obj = state.objects.get((c, r))
            is_goal = goal == (c, r)
            tri = _agent_tri(state.heading) if (c == state.col and r == state.row) else None
            x0, y0 = c * tile, r * tile
            for py in range(tile):
                v = (py + 0.5) / tile
                for px in range(tile):
                    u = (px + 0.5) / tile
                    col = bg
                    if bg is _FLOOR and (px == 0 or py == 0):
                        col = _FLOOR_LINE  # subtle grid
                    if is_goal and _ring(u, v, 0.30, 0.42):
                        col = _GOAL
                    if obj is not None:
                        oc = _object_color(obj, u, v)
                        if oc is not None:
                            col = oc
                    if tri is not None and _in_tri(u, v, tri):
                        col = _AGENT
                    img.set(x0 + px, y0 + py, col)
    return img
