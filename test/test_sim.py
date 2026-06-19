"""Headless semantics tests for the Wanderland simulator.

Asserts the grid-world rules the object model must honour, both gem
variants, action-space enforcement, and the structured/ASCII prompt views.
Pure Python -- no browser.

Run: ``.venv/bin/python test/test_sim.py``
"""

import sys

from wanderland import (
    World,
    collect_gem,
    drop,
    from_ascii,
    from_dict,
    from_json,
    move_backward,
    move_forward,
    pickup,
    random_room,
    render,
    solve,
    to_json,
    toggle,
    turn_left,
    turn_right,
)

# Action spaces are spelled out explicitly -- there is no default bundle.
SIX = ("turn_left", "turn_right", "move_forward", "pickup", "drop", "toggle")
WALK = ("move_forward", "turn_left", "turn_right")
COLLECT = ("move_forward", "turn_left", "turn_right", "collect_gem")
BACK = SIX + ("move_backward",)

_fails = []


def check(name, cond, extra=""):
    print(f"{'ok  ' if cond else 'FAIL'}  {name}" + ("" if cond else f"   :: {extra}"))
    if not cond:
        _fails.append(name)


def build(grid, *, actions=SIX, goal=None):
    return World(from_ascii("t", grid, actions=actions, goal=goal))


def run(world, prog):
    world.load(prog)
    return world.timeline, world.result


# 1) non-blocking gem (walk-and-collect): walk ONTO it, then collect_gem -- no auto
tl, res = run(build("> . g", actions=COLLECT), lambda: (move_forward(), move_forward()))
check("walking over a non-blocking gem does NOT auto-collect", res["gems_collected"] == 0, res)
tl, res = run(build("> . g", actions=COLLECT), lambda: (move_forward(), move_forward(), collect_gem()))
check("collect_gem() collects the gem on your current tile", res["gems_collected"] == 1 and res["success"], res)
check("  ...as a 'collect' step", tl[-1]["kind"] == "collect" and tl[-1]["ok"], tl[-1])
tl, _ = run(build("> g .", actions=COLLECT), lambda: collect_gem())
check("collect_gem acts on the current tile, not the front", tl[0]["kind"] == "collect" and tl[0]["ok"] is False, tl[0])

# 2) blocking gem (carried): blocks movement; pickup CARRIES it; you don't move -
tl, _ = run(build("> G ."), lambda: move_forward())
check("blocking gem blocks movement", tl[0]["ok"] is False and tl[0]["blocked_by"] == "object", tl[0])
tl, res = run(build("> G ."), lambda: pickup())
check("blocking gem is carried (not consumed)", res["carrying"] and res["carrying"]["type"] == "gem" and res["gems_collected"] == 0, res)
check("  ...and pickup doesn't move you", res["final"]["col"] == 0 and res["final"]["row"] == 0, res["final"])

# 3) carry limit is one --------------------------------------------------------
def carry_two():
    pickup(); move_forward(); pickup()

tl, res = run(build("> Kr Kb"), carry_two)
check("carry limit one (2nd pickup fails, hands full)", tl[2]["ok"] is False and res["carrying"]["color"] == "red", res)

# 4) drop ----------------------------------------------------------------------
def grab_drop():
    pickup(); drop()

tl, res = run(build("> Kr ."), grab_drop)
check("drop places carried object on empty front floor", tl[1]["ok"] and res["carrying"] is None, res)
tl, _ = run(build("> . ."), lambda: drop())
check("drop empty-handed is a no-op", tl[0]["ok"] is False, tl[0])

# 5) closed door: toggle opens (then walkable); toggle again closes ------------
tl, _ = run(build("> Dg ."), lambda: (toggle(), move_forward()))
check("closed door opens on toggle, then walkable", tl[0]["effect"] == "open" and tl[1]["ok"], tl)
tl, _ = run(build("> Dg ."), lambda: (toggle(), toggle()))
check("open door closes on toggle", tl[1]["effect"] == "close", tl[1])

# 6) locked door: needs a matching-colour key, which is NOT consumed -----------
def unlock_and_pass():
    pickup(); move_forward(); toggle(); move_forward(); move_forward()

tl, res = run(build("> Ky Ly O"), unlock_and_pass)
check("locked door unlocks with matching key", any(s.get("effect") == "unlock" for s in tl), tl)
check("  ...key is kept after unlocking", res["carrying"] and res["carrying"]["type"] == "key", res)
check("  ...and the goal is reached through it", res["success"], res)

tl, _ = run(build("> Ly O"), lambda: (toggle(), move_forward()))
check("locked door without a key stays shut", tl[0]["ok"] is False and tl[1]["blocked_by"] == "door", tl)

def wrong_key():
    pickup(); move_forward(); toggle()

tl, _ = run(build("> Kb Ly O"), wrong_key)
check("locked door rejects a wrong-colour key", tl[2]["ok"] is False, tl[2])

# 7) box: toggle replaces it with its (hidden) contents ------------------------
def open_box_take_key():
    toggle(); pickup()

tl, res = run(build("> Xr:Kb ."), open_box_take_key)
check("box opens to reveal its contents", tl[0]["effect"] == "open_box" and tl[0]["reveals"]["type"] == "key", tl[0])
check("  ...the revealed key can then be picked up", res["carrying"] and res["carrying"]["color"] == "blue", res)

# 8) goal is walked onto, not collected ----------------------------------------
tl, res = run(build("> . O", actions=WALK), lambda: (move_forward(), move_forward()))
check("goal won by stepping on it", res["reached_goal"] and res["success"], res)
check("  ...no collect/pickup involved", all(s["kind"] == "move" for s in tl), [s["kind"] for s in tl])

# 9) blocked reasons: # is a WALL, ~ is water (both impassable) ----------------
tl, _ = run(build("> # ."), lambda: move_forward())
check("# is a wall (blocked_by=wall)", tl[0]["blocked_by"] == "wall", tl[0])
tl, _ = run(build("> ~ ."), lambda: move_forward())
check("~ is water (impassable; blocked_by=edge)", tl[0]["blocked_by"] == "edge", tl[0])

# 10) facing direction is encoded in the start glyph --------------------------
tl, _ = run(build("> . .\n. . .", actions=WALK), lambda: (move_forward(), turn_right(), move_forward()))
check("'>' faces east, 'v'/turns are egocentric", tl[0]["to"]["col"] == 1 and tl[2]["to"]["row"] == 1, tl)
wd = World(from_ascii("t", "v\n.", actions=WALK))
check("'v' faces south", wd.puzzle["heading"] == "S", wd.puzzle["heading"])

# 11) action space: explicit + enforced ---------------------------------------
wd = build("> . .")
check("world exposes its action space", wd.action_space == SIX, wd.action_space)
check("actions_doc carries name+doc", wd.actions_doc[0].keys() >= {"name", "doc"}, wd.actions_doc[0])

raised = False
try:
    build("> . .").load(lambda: move_backward())
except ValueError:
    raised = True
check("move_backward rejected outside the action space", raised)

allowed = True
try:
    build("> . .", actions=BACK).load(lambda: move_backward())
except ValueError:
    allowed = False
check("move_backward allowed when the world lists it", allowed)

raised = False
try:
    from_ascii("x", "> .", actions=("bogus",))
except ValueError:
    raised = True
check("unknown action rejected at build time", raised)

# 12) prompts: structured is canonical; ASCII is a view; box contents hidden ---
wd = build("> Xr:Kb .")
s = wd.to_prompt("structured")
a = wd.to_prompt("ascii")
check("structured prompt: agent pos+dir + actions", "facing east" in s and "Actions:" in s, s)
check("structured hides box contents", "red box" in s and "blue" not in s, s)
check("ascii view renders the agent glyph + box without contents", a.startswith(">") and "Xr" in a and "Kb" not in a, a)
wd2 = build("> # ~", actions=WALK)
check("ascii uses # for wall and ~ for water", "#" in wd2.to_prompt("ascii") and "~" in wd2.to_prompt("ascii"), wd2.to_prompt("ascii"))

# 13) idempotent load: re-loading the same program must not reset a finished run
wd = World(from_ascii("t", "> . .", actions=WALK))
prog = lambda: (move_forward(), move_forward())
wd.load(prog)
n1 = wd.load_nonce
wd.state = {"finished": True}  # the frontend's "run complete" report
wd.load(prog)  # a reactive re-run with the SAME program
check("idempotent load: load_nonce unchanged", wd.load_nonce == n1, wd.load_nonce)
check("idempotent load: finished state preserved", wd.state.get("finished") is True, wd.state)
wd.load(lambda: move_forward())  # a real edit -> different program
check("changed program reloads (nonce bumps, state cleared)", wd.load_nonce == n1 + 1 and wd.state == {}, (wd.load_nonce, wd.state))

# 14) World.act: run a flat list of action-name strings (the agent interface)
wd = World(from_ascii("t", "> . g", actions=COLLECT))
res = wd.act(["move_forward", "move_forward", "collect_gem"])
check("World.act runs an action-name list", res["success"] and res["gems_collected"] == 1, res)
raised = False
try:
    wd.act(["fly"])
except ValueError:
    raised = True
check("World.act rejects an unknown action", raised)

# 15) serialization round-trips (structured dict + JSON) ----------------------
rt = from_ascii("rt", "> . # .\n. . Ly .\nKy . # O", actions=SIX)
check("from_dict round-trips to_dict", from_dict(rt.to_dict()).to_dict() == rt.to_dict())
check("from_json round-trips to_json", from_json(to_json(rt)).to_dict() == rt.to_dict())
gen = random_room(seed=3, gems=2)
check("a generated world round-trips", from_dict(gen.to_dict()).to_dict() == gen.to_dict())

# 16) generated worlds are solvable (oracle finds a plan; the sim confirms it) --
gen_ok = True
for seed in range(8):
    rp = random_room(seed=seed, cols=6, rows=5, gems=2)
    plan = solve(rp)
    gen_ok = gen_ok and plan is not None and World(rp).act(plan)["success"]
check("random_room worlds are solvable (oracle-verified)", gen_ok)
check("solve() returns an action list (oracle baseline)", isinstance(solve(gen), list))

# 17) image observation renderer (2D top-down) --------------------------------
img = World(from_ascii("img", "> . #\n. Ly .\nKy . O", actions=SIX)).render(tile=20)
check("render: image size = cols*tile x rows*tile", img.width == 3 * 20 and img.height == 3 * 20)
check("render: emits a valid PNG (stdlib)", img.to_png()[:8] == b"\x89PNG\r\n\x1a\n")
check("render: distinct worlds produce distinct images",
      render(random_room(seed=1)).to_png() != render(random_room(seed=2)).to_png())

# ---------------------------------------------------------------------------
print()
if _fails:
    print(f"SIM TEST FAILED ({len(_fails)} failing): {_fails}")
    sys.exit(1)
print("SIM TEST PASSED")
