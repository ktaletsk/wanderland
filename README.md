<h1>
<p align="center">
  🌱
  <br>Wanderland
</p>
</h1>

An interactive low-poly **3D coding playground** as an [anywidget](https://anywidget.dev),
built for Python notebooks. Write simple Python commands and watch a charming
little character — **Mo the Mossball** — animate through a stylized world, collecting
gems and reaching goals.

It captures the joy of a learn-to-code playground — *write code, watch the character act
it out* — with an original character, original art, and a small Python command API,
running entirely inside a reactive marimo notebook.

The same engine doubles as a substrate for **agent / LLM evaluation**: worlds follow
classic grid-world mechanics (keys, doors, boxes, an explicit action space) and render to
text prompts you can hand a model — so the identical world is both a kids' puzzle and a
gridworld benchmark.

```python
# --- cell: create + show the world (it has its own ▶ Run My Code button) ---
import marimo as mo
import wanderland as mp
from wanderland import move_forward, turn_right, collect_gem

world = mo.ui.anywidget(mp.World(mp.puzzles.gem_path()))
world  # renders the 3D scene + the in-scene Run button

# --- cell: your program (editing this just *loads* it; Mo doesn't move yet) ---
# gem_path's gems are non-blocking: walk Mo onto each one, then collect_gem().
def solution():
    move_forward(); move_forward(); move_forward(); collect_gem()                # first gem
    turn_right(); move_forward(); move_forward()
    turn_right(); move_forward(); move_forward(); move_forward(); collect_gem()  # second gem
    turn_right(); turn_right(); move_forward(); move_forward(); move_forward()

# --- cell: hand the program to the widget (reactive; recomputes on edit) ---
world.load(solution)
# ...now press ▶ Run My Code in the scene to animate it once.

# --- cell: read the outcome back in Python (synchronous, after load) ---
world.success            # True
world.gems_collected     # 2
world.reached_goal       # True
```

The **▶ Run My Code** button lives inside the widget. Editing the program reloads its
timeline silently; Mo only moves when you press Run, and then he stays at his final pose.

---

## Install & run

```bash
pip install wanderland          # or: uv add wanderland
```

The published package ships the prebuilt 3D frontend — **no Node required**. It works in
any notebook that supports [anywidget](https://anywidget.dev) (marimo, Jupyter). Open the
example notebook to play:

```bash
uv run marimo edit example.py   # the teaching playground
uv run marimo edit rl_playground.py   # the agent / LLM-evaluation notebook
```

You'll see Mo standing in a warm low-poly world; running a program animates him through
your commands step by step. Drag to orbit the camera. For headless / agent use, nothing
needs a browser — `World.act(...)`, `solve(...)`, and `render(...)` all return synchronously
(add `pip install "wanderland[rl]"` for the numpy image observation).

<details>
<summary>Develop from source (rebuild the frontend)</summary>

Requires Python ≥ 3.10 and Node ≥ 18.

```bash
npm install && npm run build     # build the 3D bundle -> src/wanderland/static/index.js
uv venv && uv pip install -e ".[dev]"
uv run marimo edit example.py
```
</details>

---

## Writing Mo programs

A **program** is an ordinary Python function. Inside it you call commands in the order
you want them to happen:

| command | what it does |
|---|---|
| `move_forward()` | step one tile in the direction faced |
| `turn_left()` / `turn_right()` | rotate 90° — turning is **egocentric** (relative to the current heading) |
| `pickup()` | take the object in the cell **faced** (a key/ball/box, or a blocking gem) into your hand — carry limit one. You don't move. |
| `drop()` | drop the carried object onto the empty floor cell faced |
| `toggle()` | open/close the door faced (a locked door opens with a matching-color key, which you keep); open a box to reveal its contents |
| `collect_gem()` | collect the **non-blocking** gem on the tile you're standing on (walk on, then collect; scores, not carried) |
| `move_backward()` | step back without turning — **free-play only**, off the canonical action set |

Interaction is always on the cell you **face**, standing adjacent — you never walk onto
a blocking object. A blocked move is animated by *why* it failed: Mo teeters at the brink
of the world's edge (a near-fall), and bonks off a wall, door, or object.

### Action space

Every world declares the **exact set of verbs it permits** — explicitly, with no default
and no canonical bundle. That declared set *is* the action space you'd hand an agent, and
it's enforced: calling a verb the world didn't list raises (so a measured run can't
silently use the wrong vocabulary — `move_backward` is rejected unless the world lists it).

```python
world.action_space     # ('move_forward', 'turn_left', 'turn_right', 'pickup', 'drop', 'toggle')
world.actions_doc      # [{'name': 'pickup', 'doc': '...'}, ...]  — ready for an LLM prompt
```

### Running a program

Three ways to drive Mo, depending on who pulls the trigger:

- **`world.load(solution)`** — the recommended notebook flow. Captures the commands,
  simulates them, and hands the timeline to the widget **without playing**. The user
  presses the widget's own **▶ Run My Code** button to animate it once; Mo stays at his
  final pose. Editing the program reloads silently.
- **`world.run(solution)`** — captures *and plays immediately* (no button). Handy for
  programmatic or headless use; returns the result dict.
- **`@world.program`** — decorator form of `run()`; plays whenever the defining cell
  re-executes.

All three capture the command sequence and simulate it in Python (the source of truth);
`world.success` and friends are available synchronously regardless of which you use. The
example notebook uses `load()` + the in-scene button.

### Reading the outcome

Because the simulation runs in Python, results are available **synchronously** right
after the program runs (and work even without a browser):

```python
world.success          # all (non-blocking) gems collected AND goal reached
world.gems_collected   # int
world.total_gems       # int
world.reached_goal     # bool
world.result           # the full dict: final pose, what's carried, ...
```

For *reactive* readback, read `world.value` (or `world.state`) in another cell — the
frontend writes a playback report there when the animation finishes, which re-runs
dependent marimo cells.

### Defining your own world

```python
from wanderland import from_ascii, World

puzzle = from_ascii("Locked Room", """
    > . # .
    . . Ly .
    Ky . # O
""", actions=("move_forward", "turn_left", "turn_right", "pickup", "toggle"))

world = World(puzzle)
```

Each cell is one whitespace-separated token; the top row is north, columns go east:

| token | meaning |
|---|---|
| `^ > v <` | start tile **and** the agent's facing (N/E/S/W) — `S` also works with `heading=` |
| `.` `#` `~` `!` `O` | floor · **wall** · water (impassable) · **lava** (walkable but deadly) · goal |
| `g` / `G` | non-blocking gem (walk on, then `collect_gem()`) / blocking gem (`pickup()` from the front) |
| `Kc` `Bc` `Xc` | key / ball / box of color `c` (`r g b p y e`) — `Xc:obj` gives a box hidden contents |
| `Dc` `Lc` | closed / locked door of color `c` |

`actions=` is **required**. Built-in worlds live in `mp.puzzles` (`first_steps`,
`gem_path`, `spiral`, `locked_room`).

> **Rendering:** floor, water, walls, gems, and the colored objects (keys, balls,
> boxes, doors) all render in 3D, and `pickup`/`drop`/`toggle` animate — the carried
> item floats above the character, doors unlock and swing open, boxes open to their
> contents. (Box contents stay hidden in the agent prompt; see below.)

### For agents & RL

Wanderland doubles as a substrate for **agent / LLM evaluation** on grid-world tasks.
The research notebook is **`rl_playground.py`** (`uv run marimo edit rl_playground.py`).

**Show the agent the world — three encodings of the same state:**

```python
print(world.to_prompt("structured"))   # text: the canonical, measured input
print(world.to_prompt("ascii"))        # text: a grid picture
world.render().save("obs.png")         # a 2D top-down image (stdlib PNG, no browser)
world.render().to_numpy()              # (H, W, 3) uint8 for vision models (needs numpy)
world.action_space, world.actions_doc  # the verbs you hand the agent (+ docs)
```

`structured` is an explicit header + a coordinate-tagged object list (usually a stronger
prompt for an LLM than a raw grid picture); `ascii` and `render()` are picture views. All
**hide box contents until toggled**, so you can show the identical world three ways and
measure how much the encoding alone moves success rate. Example `structured`:

```
World: Locked Room  (4 wide x 3 tall; x east, y south, origin top-left)
You are at (0,0) facing east, carrying nothing.
Actions: move_forward, turn_left, turn_right, pickup, toggle
Goal: step onto (3,2).
Objects (box contents are hidden until opened):
- locked yellow door at (2,1)
- yellow key at (0,2)
Walls: (2,0), (2,2)
```

**Run the agent's output, generate worlds, and verify with the oracle:**

```python
from wanderland import World, random_room, solve, from_json, to_json

puzzle = random_room(seed=7, gems=1)         # a reproducible, solvable grid room
env = World(puzzle)
env.act(["turn_left", "move_forward", ...])  # Wanderland executes a list of action names
env.success, env.result                      # authoritative + synchronous (no browser needed)
env.replay(trace)                            # animate a trajectory scored by ANOTHER executor
                                             #   (a list of {action, pos, dir, carrying} steps)

plan = solve(puzzle)                         # BFS oracle: a shortest solving plan (baseline)
spec = to_json(puzzle); from_json(spec)      # save / load a world as JSON
```

`act()` validates each name against the action space (unknown/out-of-space verbs raise, so a
measured run can't cheat). `replay()` renders an *external* trace without re-simulating it —
a `move_forward` that didn't change position animates as a blocked bonk, and stepping into
lava plays a death — so failed plans are shown faithfully. `random_room` is deterministic in
`seed` and solvable by construction; `solve()` proves it and serves as a reference agent.

---

## Characters

The character is decoupled from the simulation — Python produces a timeline of
poses/events, and a **Character** decides how to *look* while replaying it. Pick
one with the `character=` argument:

```python
World(puzzle, character="rover")   # a hovering drone-bot
World(puzzle, character="mo")      # Mo the Mossball (default)
```

Adding a character is a pure frontend change: subclass `Character`
(`js/characters/character.js`) and implement how it moves, reacts and emotes,
then register it in `js/characters/index.js`. The contract is a handful of async
methods — `move`, `turn`, `blocked`, `returnHome`, `react`, `setExpression`,
`update` — each handed the Viewer's tween clock so a character owns its own
choreography and pacing. The base class is a working (if plain) character, so
overrides are opt-in. No game logic lives in characters.

---

## Architecture (and why)

**One idea drives the whole design:**

> **Python is the authoritative simulator. The frontend is a deterministic replay of a
> precomputed timeline.**

marimo is reactive/dataflow, but the user writes *sequential, imperative* commands. The
pipeline reconciles the two:

1. **Capture.** A program is run with a thread-local recorder active; each `move_forward()`
   etc. appends one command (validated against the world's action space). (`commands.py`)
2. **Simulate.** Python dispatches each recorded verb through an **action registry**
   against the world's objects, producing a **timeline** — one entry per command
   (move / turn / pickup / drop / toggle, with before/after state and what happened) —
   plus an authoritative **result**. Adding a verb means registering a handler, not
   editing the simulator. (`actions.py`, `world.py`)
3. **Sync.** The timeline + a bumped `load_nonce`/`run_nonce` are pushed to the browser
   over anywidget traits.
4. **Replay.** The frontend resets the scene to the start state and animates each step in
   order with eased motion — never snapping to the final state. (`js/`)
5. **Read back.** `world.result` is already correct in Python (no round-trip needed); the
   frontend also reports completion to the `state` trait for reactive cells.

**Why this is the right call:**

- *Determinism & replay fall out for free.* Re-running the program recomputes the same
  timeline from the same start; the frontend resets and replays.
- *State readback is synchronous and reliable* — Python owns the truth, so outcomes don't
  depend on a browser round-trip and work headless (great for tests).
- *The frontend stays a "dumb" renderer*, which keeps game logic in one place (Python).

**Technology choices:**

- **Rendering:** vanilla **Three.js**. The core experience is an imperative animation
  *timeline*, which maps directly onto an imperative engine — and it keeps the bundle lean
  (~135 KB gzipped) with full control over the art.
- **Animation:** a small hand-rolled tween scheduler with easing curves and squash/stretch
  — Mo waddle-walks with scuttling feet, leans into turns, sways his sprout, blinks and
  changes facial expression (determined / surprised / happy), teeters at ledges, and
  glides home before each run.
- **Art:** original procedural geometry (rounded primitives), warm palette, soft shadows,
  hemisphere + warm key lighting, ACES tone mapping. No external assets.
- **Build:** **esbuild** (`npm run build`) bundles `js/` → a single ESM file referenced by
  anywidget's `_esm`. `npm run dev` watches for rebuilds.

### Layout

```
src/wanderland/   # Python package
  __init__.py        # public API
  actions.py         # verb registry + grid-world simulation semantics
  commands.py        # the recorded command vocabulary (+ action-space check)
  puzzles.py         # Puzzle + objects + from_ascii/from_dict/to_json + to_prompt + built-ins
  generate.py        # random_room(): a reproducible distribution of solvable rooms
  solve.py           # solve(): a BFS oracle (shortest solving plan / baseline)
  render.py          # render(): a 2D top-down image observation (stdlib PNG; numpy optional)
  world.py           # the AnyWidget: capture -> simulate -> sync; action_space; act()
  static/            # built frontend (index.js, index.css)

js/                  # frontend source (bundled into static/)
  index.js           # anywidget entry: wires model traits <-> Viewer
  viewer.js          # orchestrator: load/return-home/step playback + render loop
  scene.js           # renderer, lights, camera, orbit controls
  board.js           # tiles, water, walls, gems, objects, goal (built from a puzzle)
  objects.js         # low-poly geometry for walls + keys/balls/boxes/doors
  characters/        # swappable characters (see "Characters" above)
    character.js     #   the Character contract (base class)
    mossball.js      #   Mo the Mossball (default)
    rover.js         #   a hovering drone-bot
    index.js         #   name -> class registry
  hud.js             # gem counter, status pill, Run button
  palette.js         # colours, sizes, animation timings
  easing.js          # easing curves

example.py           # learn-to-code playground notebook
rl_playground.py     # agent / RL research notebook (generate worlds, prompt, act, solve)
test/                # headless sim tests (test_sim.py) + render tests + fixtures
```

## License

MIT
