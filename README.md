<h1>
<p align="center">
  🌱
  <br>Wanderland
</p>
</h1>

<p align="center">
  <img src="assets/wanderland.svg" width="180" alt="A top-down Wanderland grid: a red character facing a locked yellow door, a key, and a goal ring">
</p>

<p align="center">
  <a href="https://marimo.app/?src=https%3A%2F%2Fraw.githubusercontent.com%2Fktaletsk%2Fwanderland%2Frefs%2Fheads%2Fmain%2Fexample.py&mode=read"><img src="https://marimo.io/shield.svg" alt="Open in marimo" height="20"></a>
  <a href="https://notebook.link/github.com/ktaletsk/wanderland/?path=example.ipynb"><img src="https://img.shields.io/badge/notebook-link-e2d610?logo=jupyter&logoColor=white" alt="Open on notebook.link" height="20"></a>
</p>

An interactive low-poly **3D coding playground** as an [anywidget](https://anywidget.dev),
built for Python notebooks. Write simple Python commands and watch a charming
little character — **Mo the Mossball** — animate through a stylized world, collecting
gems and reaching goals.

It captures the joy of a learn-to-code playground — *write code, watch the character act
it out* — with an original character, original art, and a small Python command API,
running entirely inside an interactive notebook.

```python
# Create and show the world (it has its own ▶ Run My Code button)
# Any anywidget-compatible notebook works: Jupyter, marimo, VS Code...
import wanderland as mp
from wanderland import move_forward, turn_right, collect_gem

# For marimo, you might wrap this in mo.ui.anywidget()
world = mp.World(mp.puzzles.gem_path())
world  # renders the 3D scene + the in-scene Run button

# Your program (editing this just *loads* it; the character doesn't move yet)
# gem_path's gems are non-blocking: walk the character onto each one, then collect_gem().
def solution():
    move_forward()
    move_forward()
    move_forward()
    collect_gem()   # first gem

    turn_right()
    move_forward()
    move_forward()

    turn_right()
    move_forward()
    move_forward()
    move_forward()
    collect_gem()   # second gem

    turn_right()
    turn_right()

    move_forward()
    move_forward()
    move_forward()

# Hand the program to the widget
world.load(solution)
# ...now press ▶ Run My Code in the scene to animate it once.

# Read the outcome back in Python (synchronous, after load)
world.success            # True
world.gems_collected     # 2
world.reached_goal       # True
```

The **▶ Run My Code** button lives inside the widget. Editing the program reloads its
timeline silently; the character only moves when you press Run, and then stays at their final pose.

<p align="center">
  <video src="https://github.com/user-attachments/assets/586d888f-7a24-4376-88db-f335070b64ed" width="100%" controls="controls" muted="muted"></video>
</p>

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
```

You'll see your character (like Mo the Mossball) standing in a warm low-poly world; running a program animates them through
your commands step by step. Drag to orbit the camera.

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

## Solve puzzles with code

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
a blocking object. A blocked move is animated by *why* it failed: the character teeters at the brink
of the world's edge (a near-fall), and bonks off a wall, door, or object.

### Action space

Every world declares the **exact set of verbs it permits** — explicitly, with no default
and no canonical bundle. That declared set *is* the action space you're allowed to use, and
it's enforced: calling a verb the world didn't list raises.

```python
world.action_space     # ('move_forward', 'turn_left', 'turn_right', 'pickup', 'drop', 'toggle')
world.actions_doc      # [{'name': 'pickup', 'doc': '...'}, ...]  — documentation for the actions
```

### Running a program

Three ways to drive the character, depending on who pulls the trigger:

- **`world.load(solution)`** — the recommended notebook flow. Captures the commands,
  simulates them, and hands the timeline to the widget **without playing**. The user
  presses the widget's own **▶ Run My Code** button to animate it once; the character stays at their
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

For reactive readback (like in marimo), read `world.value` (or `world.state`) in another cell — the
frontend writes a playback report there when the animation finishes.

## For Educators: Creating Custom Worlds

Wanderland makes it easy to design your own levels and assignments for students. You can sketch out puzzles visually using simple ASCII text strings.

```python
from wanderland import from_ascii, World

level_design = """
> . # .
. . Ly .
Ky . # O
"""

allowed_actions = (
    "move_forward",
    "turn_left",
    "turn_right",
    "pickup",
    "toggle",
)

puzzle = from_ascii(
    "Locked Room",
    level_design,
    actions=allowed_actions
)

# You can also pick a different character!
world = World(puzzle, character="rover")  # A hovering drone-bot instead of Mo
```

Each cell is one whitespace-separated token; the top row is north, columns go east:

| token | meaning |
|---|---|
| `^ > v <` | start tile **and** the character's facing (N/E/S/W) — `S` also works with `heading=` |
| `.` `#` `~` `!` `O` | floor · **wall** · water (impassable) · **lava** (walkable but deadly) · goal |
| `g` / `G` | non-blocking gem (walk on, then `collect_gem()`) / blocking gem (`pickup()` from the front) |
| `Kc` `Bc` `Xc` | key / ball / box of color `c` (`r g b p y e`) — `Xc:obj` gives a box hidden contents |
| `Dc` `Lc` | closed / locked door of color `c` |

`actions=` is **required**. Built-in worlds live in `mp.puzzles` (`first_steps`,
`gem_path`, `spiral`, `locked_room`).

> **Rendering:** floor, water, walls, gems, and the colored objects (keys, balls,
> boxes, doors) all render in 3D, and `pickup`/`drop`/`toggle` animate — the carried
> item floats above the character, doors unlock and swing open, boxes open to their
> contents. (Box contents stay hidden when printing the world state.)


## License

MIT
