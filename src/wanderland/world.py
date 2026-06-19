"""The ``World`` anywidget: capture a program, simulate it, animate it.

Design in one sentence: **Python is the authoritative simulator; the frontend
is a deterministic replay of a precomputed timeline.**

Flow:

1. The user authors an ordered program inside ``@world.program``.
2. :meth:`World.program` records the commands and runs them through
   :meth:`World._simulate`, producing a *timeline* (one entry per command, each
   with the before/after pose and what happened) plus a *result* (gems, goal,
   success).
3. The timeline + a bumped ``run_nonce`` are synced to the browser, which resets
   the scene to the puzzle's start state and animates each step in order.
4. Because Python already simulated everything, ``world.result`` /
   ``world.success`` are available *synchronously* and work even headless.

Re-running the program cell in marimo recomputes the same timeline from the same
start state and bumps ``run_nonce`` -> the frontend cleanly resets and replays.
"""

from __future__ import annotations

import pathlib

import anywidget
import traitlets

from . import actions, commands
from .puzzles import Puzzle, render_ascii, render_structured

_STATIC = pathlib.Path(__file__).parent / "static"

# heading int <-> name. 0=N, 1=E, 2=S, 3=W.
_HEADING_TO_INT = {"N": 0, "E": 1, "S": 2, "W": 3}

_EMPTY_RESULT = {
    "ran": False,
    "success": False,
    "reached_goal": False,
    "gems_collected": 0,
    "total_gems": 0,
    "final": None,
    "carrying": None,
    "steps": 0,
}


def _pose(col: int, row: int, heading: int) -> dict:
    return {"col": col, "row": row, "h": heading}


class World(anywidget.AnyWidget):
    """A Mo playground bound to a single :class:`~wanderland.puzzles.Puzzle`.

    Typical use inside marimo::

        import marimo as mo
        import wanderland as bp
        from wanderland import move_forward, turn_right, collect_gem

        world = mo.ui.anywidget(bp.World(bp.puzzles.gem_path()))

        @world.program
        def solution():
            move_forward(); move_forward(); move_forward(); collect_gem()

        world  # renders the animated 3D scene
    """

    # --- frontend assets -------------------------------------------------
    _esm = _STATIC / "index.js"
    _css = _STATIC / "index.css"

    # --- synced state ----------------------------------------------------
    # Static world description (sent once at construction).
    puzzle = traitlets.Dict().tag(sync=True)
    # The precomputed, ordered animation timeline (one entry per command).
    timeline = traitlets.List().tag(sync=True)
    # Bumped on every load() so the frontend always fully resets to a clean
    # "loaded, not played" state -- even when the timeline content is unchanged.
    load_nonce = traitlets.Int(0).tag(sync=True)
    # Additionally bumped when the program should animate immediately (run()).
    run_nonce = traitlets.Int(0).tag(sync=True)
    # Authoritative outcome, computed by the Python simulation.
    result = traitlets.Dict(default_value=dict(_EMPTY_RESULT)).tag(sync=True)
    # Frontend -> Python playback report (e.g. {"finished": True, ...}).
    state = traitlets.Dict().tag(sync=True)
    # Animation speed multiplier (1.0 = default).
    speed = traitlets.Float(1.0).tag(sync=True)
    # Which character renders/animates the timeline (frontend registry name).
    character = traitlets.Unicode("mo").tag(sync=True)

    def __init__(
        self,
        puzzle: Puzzle,
        *,
        speed: float = 1.0,
        character: str = "mo",
        actions: tuple[str, ...] | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._puzzle = puzzle
        # The action space the world permits: the puzzle's declared space, or an
        # explicit (e.g. narrower) override for a measured run. Never a default.
        from . import actions as _act  # local alias; module name shadowed by param

        self._action_space = _act.validate_space(
            actions if actions is not None else puzzle.actions
        )
        # Ship the *effective* action space to the frontend/agent.
        self.puzzle = {**puzzle.to_dict(), "actions": list(self._action_space)}
        self.speed = speed
        self.character = character
        self.result = dict(_EMPTY_RESULT, total_gems=len(puzzle.score_gem_cells))

    # --- authoring API ---------------------------------------------------
    def _execute(self, fn, *, autoplay: bool) -> None:
        """Record the commands ``fn`` issues, then simulate them.

        With ``autoplay=False`` the timeline is shipped to the widget but not
        animated -- the in-scene **Run** button plays it. With ``autoplay=True``
        the widget animates immediately (used for programmatic/headless runs).
        """
        recording = commands._Recording(actions=self._action_space, cmds=[])
        token = commands._active.set(recording)
        try:
            fn()
        finally:
            commands._active.reset(token)
        self._simulate(recording.cmds, autoplay=autoplay)

    def load(self, fn):
        """Capture ``fn``'s commands and hand the timeline to the widget WITHOUT
        playing it.

        This is the recommended notebook flow: call it reactively, then press
        the widget's **▶ Run My Code** button to animate. Editing the program
        recomputes the timeline silently; Mo only moves when you press Run.
        Returns the authoritative :attr:`result` dict (available synchronously).
        """
        self._execute(fn, autoplay=False)
        return self.result

    def run(self, fn):
        """Capture the program defined by ``fn`` and play it immediately.

        Drives Mo without the button -- handy for programmatic or headless
        use. Returns the authoritative :attr:`result` dict. Mo animates the
        program and then stays at its final pose.
        """
        self._execute(fn, autoplay=True)
        return self.result

    def program(self, fn):
        """Decorator form of :meth:`run`: capture and play ``fn`` immediately.

        ``fn`` runs as soon as it is decorated, replaying whenever the defining
        cell re-executes. Prefer :meth:`load` + the in-scene button for the
        smooth, game-like "edit freely, press Run" loop. Returns ``fn``.
        """
        self._execute(fn, autoplay=True)
        return fn

    def act(self, actions, *, play: bool = False):
        """Run a flat sequence of action-name strings -- an agent's output.

        e.g. ``world.act(["turn_left", "move_forward", "pickup"])``. Each name
        must be one of the verbs in this world's :attr:`action_space` (otherwise
        it raises, exactly like calling a disallowed command). Returns the
        authoritative :attr:`result` (available synchronously, no browser
        needed). By default it loads without animating -- press **Run** to watch,
        or read the result directly; pass ``play=True`` to animate immediately.
        """
        from . import actions as actions_mod  # module shadowed by the `actions` arg

        def _program():
            for name in actions:
                if not actions_mod.is_registered(name):
                    raise ValueError(f"unknown action {name!r}")
                getattr(commands, name)()

        self._execute(_program, autoplay=play)
        return self.result

    def reset(self) -> None:
        """Clear any program back to the puzzle's start state."""
        self.timeline = []
        self.result = dict(_EMPTY_RESULT, total_gems=len(self._puzzle.score_gem_cells))
        self.state = {}
        self.load_nonce += 1

    # --- authoritative simulation ---------------------------------------
    def _simulate(self, cmds: list[str], *, autoplay: bool = True) -> None:
        p = self._puzzle
        state = actions.SimState(
            col=p.start[0],
            row=p.start[1],
            heading=_HEADING_TO_INT[p.heading],
            carrying=None,
            objects={cell: o.copy() for cell, o in p.objects.items()},  # mutable copy
            puzzle=p,
        )

        timeline: list[dict] = []
        for i, cmd in enumerate(cmds):
            step = actions.get(cmd).handler(state)  # mutates state, returns step
            timeline.append({"i": i, "cmd": cmd, **step})

        total = len(p.score_gem_cells)
        collected = sum(1 for s in timeline if s.get("collected"))  # gem events
        reached_goal = p.goal is None or (state.col, state.row) == tuple(p.goal)
        result = {
            "ran": True,
            "success": collected >= total and reached_goal,
            "reached_goal": reached_goal,
            "gems_collected": collected,
            "total_gems": total,
            "final": _pose(state.col, state.row, state.heading),
            "carrying": state.carrying.to_dict() if state.carrying else None,
            "steps": len(cmds),
        }

        # Idempotent load: in marimo, the frontend reporting a finished run writes
        # the `state` trait, which is a value-change on `world` -- so any reactive
        # cell that calls load() re-runs. If the program is unchanged, reloading
        # would clobber the just-finished run (reset the gems, clear "Solved!").
        # So when a load() reproduces the exact same timeline, do nothing. (run()
        # always replays, so it is exempt.)
        if not autoplay and self.timeline and timeline == list(self.timeline):
            return

        # Push state to the frontend. Setting `timeline`/`result` updates the
        # program; clearing `state` drops any prior playback report. Bumping
        # `load_nonce` makes the widget fully reset (Mo to start, gems back,
        # HUD cleared, Run button armed). `run_nonce` additionally triggers
        # immediate animation -- only when autoplay is requested.
        self.timeline = timeline
        self.result = result
        self.state = {}
        self.load_nonce += 1
        if autoplay:
            self.run_nonce += 1

    # --- action space (the verbs this world permits) --------------------
    @property
    def action_space(self) -> tuple[str, ...]:
        """The explicit verb vocabulary for this world -- what you hand an agent."""
        return self._action_space

    @property
    def actions_doc(self) -> list[dict]:
        """``[{name, doc}, ...]`` for the action space -- handy for LLM prompts."""
        return actions.describe(self._action_space)

    def to_prompt(self, fmt: str = "structured") -> str:
        """Render this world as text for an agent.

        ``fmt="structured"`` (the canonical, measured input) is an explicit
        header + a coordinate-tagged object list -- usually a stronger prompt for an
        LLM than a raw grid picture. ``fmt="ascii"`` is a second *view* of the very
        same state (a render, not the measured prompt). Both come from the one
        source of truth, so you can show the same world two ways and measure how
        much the encoding alone moves an agent's success rate.
        """
        if fmt == "structured":
            return render_structured(self._puzzle, self._action_space)
        if fmt == "ascii":
            return render_ascii(self._puzzle)
        raise ValueError(f"unknown format {fmt!r}; use 'structured' or 'ascii'")

    # --- convenient Python-side readback --------------------------------
    @property
    def total_gems(self) -> int:
        return len(self._puzzle.score_gem_cells)

    @property
    def gems_collected(self) -> int:
        return int(self.result.get("gems_collected", 0))

    @property
    def reached_goal(self) -> bool:
        return bool(self.result.get("reached_goal", False))

    @property
    def success(self) -> bool:
        return bool(self.result.get("success", False))

    @property
    def has_run(self) -> bool:
        return bool(self.result.get("ran", False))

    def __repr__(self) -> str:
        return (
            f"World(puzzle={self._puzzle.name!r}, "
            f"gems={self.gems_collected}/{self.total_gems}, "
            f"success={self.success})"
        )
