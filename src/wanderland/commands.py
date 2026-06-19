"""The command vocabulary -- the verbs a user writes inside ``@world.program``.

A command does not move anything by itself; it *records* an ordered verb into
the program currently being captured. :class:`~wanderland.world.World` runs that
recording through the deterministic simulation (see :mod:`wanderland.actions`)
and ships the resulting timeline to the 3D frontend.

Each recording is bound to the world's **action space**: recording a verb the
world doesn't permit raises immediately, at the offending call. This is what
keeps a measured run honest -- e.g. ``move_backward`` is rejected unless the
world explicitly declared it. The canonical verbs are ``turn_left``,
``turn_right``, ``move_forward``, ``pickup``, ``drop``, ``toggle``.
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass


@dataclass
class _Recording:
    """The program being captured: the world's action space + the recorded verbs."""

    actions: tuple[str, ...]
    cmds: list[str]


# The active recording. A ``contextvars`` variable (not a plain global) keeps
# recording correct across threads / async tasks, which matters in notebooks.
_active: contextvars.ContextVar["_Recording | None"] = contextvars.ContextVar(
    "wanderland_recording", default=None
)


def _record(command: str) -> None:
    rec = _active.get()
    if rec is None:
        raise RuntimeError(
            f"{command}() can only be called inside a function decorated with "
            "@world.program (or passed to world.load/run). Define your program:\n\n"
            "    @world.program\n"
            "    def solution():\n"
            f"        {command}()\n"
        )
    if command not in rec.actions:
        raise ValueError(
            f"{command}() is not in this world's action space {rec.actions}. "
            "Either pick a different verb, or build the world with an action space "
            f"that lists {command!r} (the actions=... passed to the puzzle/world)."
        )
    rec.cmds.append(command)


def move_forward() -> None:
    """Step one tile in the direction you currently face."""
    _record("move_forward")


def move_backward() -> None:
    """Step one tile straight backward, without turning. Free-play only -- not a
    canonical action; a world must opt in via its action space."""
    _record("move_backward")


def turn_left() -> None:
    """Rotate 90 degrees to the left (counter-clockwise)."""
    _record("turn_left")


def turn_right() -> None:
    """Rotate 90 degrees to the right (clockwise)."""
    _record("turn_right")


def pickup() -> None:
    """Pick up the object in the cell you face: a gem is collected; a key/ball/box
    is carried (if your hands are empty -- carry limit is one)."""
    _record("pickup")


def drop() -> None:
    """Drop the object you're carrying onto the empty floor cell you face."""
    _record("drop")


def toggle() -> None:
    """Interact with the cell you face: open/close a door (unlock it with a
    matching key, which you keep) or open a box to reveal its contents."""
    _record("toggle")


def collect_gem() -> None:
    """Collect the non-blocking gem on the tile you're standing on (the walk-and-collect
    collectible). Distinct from :func:`pickup`, which takes a blocking object from
    the cell you face into your hand."""
    _record("collect_gem")
