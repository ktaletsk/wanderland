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
# (dcol, drow) for a forward step at each heading (row grows southward).
_DELTA = {0: (0, -1), 1: (1, 0), 2: (0, 1), 3: (-1, 0)}

_EMPTY_RESULT = {
    "ran": False,
    "success": False,
    "reached_goal": False,
    "gems_collected": 0,
    "total_gems": 0,
    "final": None,
    "carrying": None,
    "died": False,
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

    def replay(self, frames, *, success=None, play: bool = True):
        """Animate an **external** trace -- a trajectory produced by some *other*
        executor (not Wanderland's own sim). Use this to render a run scored
        elsewhere without re-simulating it (e.g. a separate grid engine).

        ``frames`` is a list of per-step dicts, each the state AFTER one action::

            {"action":   "move_forward",          # the verb taken (drives the event)
             "pos":      [col, row],               # resulting position (or col=/row=)
             "dir":      0..3,                     # resulting heading, 0=N 1=E 2=S 3=W
                                                   #   (or "N".."W", or dir=/h=/heading=)
             "carrying": {"type", "color"} | None} # optional

        Heading uses Wanderland's convention (0=N,1=E,2=S,3=W) -- convert any
        other convention before calling. The agent's start is the puzzle's start;
        each frame's ``action`` labels the event (so a ``move_forward`` whose
        position did *not* change renders as a *blocked* move -- the failed-plan
        animation). ``success`` overrides the displayed verdict (e.g. an external
        scorer's); else it is derived from the final pose. Returns the result dict.
        """
        p = self._puzzle
        names = {"N": 0, "E": 1, "S": 2, "W": 3}
        # a probe carrying the initial objects, for blocked-reason + toggle lookups
        probe = actions.SimState(
            col=p.start[0], row=p.start[1], heading=_HEADING_TO_INT[p.heading],
            carrying=None, objects={c: o.copy() for c, o in p.objects.items()}, puzzle=p,
        )
        prev = {"col": p.start[0], "row": p.start[1], "h": _HEADING_TO_INT[p.heading], "carrying": None}

        def norm(f):
            pos = f.get("pos")
            h = f.get("dir", f.get("h", f.get("heading", prev["h"])))
            return {
                "col": pos[0] if pos else f.get("col", prev["col"]),
                "row": pos[1] if pos else f.get("row", prev["row"]),
                "h": names[h] if isinstance(h, str) else h,
                "carrying": f.get("carrying", prev["carrying"]),
            }

        def pose(s):
            return {"col": s["col"], "row": s["row"], "h": s["h"]}

        timeline, gems = [], 0
        for i, f in enumerate(frames):
            cur = norm(f)
            act = f.get("action")
            moved = (cur["col"], cur["row"]) != (prev["col"], prev["row"])
            carry_changed = (cur["carrying"] is None) != (prev["carrying"] is None)
            step = {"i": i, "cmd": act or "?", "from": pose(prev), "to": pose(cur)}
            fc, fr = prev["col"] + _DELTA[prev["h"]][0], prev["row"] + _DELTA[prev["h"]][1]

            if act in ("turn_left", "turn_right"):
                step.update(kind="turn", ok=True)
            elif act in ("move_forward", "move_backward") or (moved and not act):
                if moved:
                    step.update(kind="move", ok=True, target=pose(cur))
                    if (cur["col"], cur["row"]) in p.lava_set:
                        step["died"] = True
                else:  # action taken but didn't move -> blocked (the flail)
                    sign = -1 if act == "move_backward" else 1
                    tgt = (prev["col"] + sign * _DELTA[prev["h"]][0], prev["row"] + sign * _DELTA[prev["h"]][1])
                    step.update(kind="move", ok=False, to=pose(prev),
                                blocked_by=probe.block_reason(*tgt) or "wall",
                                target={"col": tgt[0], "row": tgt[1], "h": prev["h"]})
            elif act in ("pickup", "drop"):
                step.update(kind=act, ok=carry_changed, to=pose(prev), cell=[fc, fr],
                            carrying=cur["carrying"])
                held = cur["carrying"] if act == "pickup" else prev["carrying"]
                if carry_changed and held:
                    step["obj"] = held
            elif act == "toggle":
                door = probe.objects.get((fc, fr))
                effect = "open"
                if door is not None and door.type == "door":
                    effect = "unlock" if door.state == "locked" else ("close" if door.state == "open" else "open")
                    door.state = "closed" if effect == "close" else "open"
                elif door is not None and door.type == "box":
                    effect = "open_box"
                step.update(kind="toggle", ok=True, to=pose(prev), cell=[fc, fr],
                            effect=effect, carrying=cur["carrying"])
            elif act == "collect_gem":
                step.update(kind="collect", ok=True, to=pose(prev), gem=[prev["col"], prev["row"]])
                gems += 1
            else:  # no action hint -> infer from the pose delta
                step["kind"] = "move" if moved else "turn"
                step["ok"] = True
                if moved:
                    step["target"] = pose(cur)

            timeline.append(step)
            prev = cur
            if step.get("died"):
                break

        goal = tuple(p.goal) if p.goal is not None else None
        reached = goal is None or (prev["col"], prev["row"]) == goal
        died = any(s.get("died") for s in timeline)
        self.timeline = timeline
        self.result = {
            "ran": True,
            "success": bool(success if success is not None else (reached and not died)),
            "reached_goal": reached,
            "gems_collected": gems,
            "total_gems": len(p.score_gem_cells),
            "final": _pose(prev["col"], prev["row"], prev["h"]),
            "carrying": prev["carrying"],
            "died": died,
            "steps": len(timeline),
        }
        self.state = {}
        self.load_nonce += 1
        if play:
            self.run_nonce += 1
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
            if state.dead:
                break  # stepped into lava -- the episode ends here

        total = len(p.score_gem_cells)
        collected = sum(1 for s in timeline if s.get("collected"))  # gem events
        reached_goal = p.goal is None or (state.col, state.row) == tuple(p.goal)
        result = {
            "ran": True,
            "success": collected >= total and reached_goal and not state.dead,
            "reached_goal": reached_goal,
            "gems_collected": collected,
            "total_gems": total,
            "final": _pose(state.col, state.row, state.heading),
            "carrying": state.carrying.to_dict() if state.carrying else None,
            "died": state.dead,
            "steps": len(timeline),
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

    def render(self, *, tile: int = 24):
        """Render the world's start state to a top-down 2D image -- the third
        agent observation alongside ``to_prompt('structured'|'ascii')``. Returns
        a :class:`wanderland.render.Image` (``.to_png()`` / ``.to_numpy()`` /
        ``.save(path)``); ``tile`` is the pixel size per cell."""
        from .render import render as _render

        return _render(self._puzzle, tile=tile)

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
