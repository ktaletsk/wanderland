"""Wanderland -- write Python commands, watch a charming low-poly
character act them out in an animated 3D world, inside marimo.

Quick start::

    import marimo as mo
    import wanderland as bp
    from wanderland import move_forward, turn_left, turn_right, collect_gem

    world = mo.ui.anywidget(bp.World(bp.puzzles.gem_path()))

    @world.program
    def solution():
        move_forward()
        move_forward()
        move_forward()
        collect_gem()

    world  # display the widget

    # ... and read the outcome back in Python:
    world.success, world.gems_collected, world.total_gems
"""

from __future__ import annotations

from . import actions, puzzles
from .commands import (
    collect_gem,
    drop,
    move_backward,
    move_forward,
    pickup,
    toggle,
    turn_left,
    turn_right,
)
from .generate import random_room
from .puzzles import Obj, Puzzle, from_ascii, from_dict, from_json, to_json
from .render import render
from .solve import solve
from .world import World

__version__ = "0.1.0"

__all__ = [
    "World",
    "Puzzle",
    "Obj",
    "from_ascii",
    "from_dict",
    "to_json",
    "from_json",
    "random_room",
    "solve",
    "render",
    "puzzles",
    "actions",
    # the verbs
    "move_forward",
    "move_backward",
    "turn_left",
    "turn_right",
    "pickup",
    "drop",
    "toggle",
    "collect_gem",
    "__version__",
]
