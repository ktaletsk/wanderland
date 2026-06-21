# Wanderland — working notes for Claude Code

Interactive low-poly 3D coding playground built as an **anywidget** for **marimo**: write
Python commands, watch a character act them out in a tile/grid world. Dual purpose —
teaching coding, and evaluating agents/LLMs on grid-world tasks. Default character: **Mo**.

## Architecture (don't break these)

- **Python is the authoritative simulator; the frontend is a deterministic replay of a
  precomputed timeline.** All game logic lives in `src/wanderland/`. The frontend (`js/`)
  holds no game logic — it just animates the timeline. Results are available synchronously
  in Python (work headless).
- **The timeline event vocabulary is the versioned Python↔JS contract.** Add a verb by
  registering a handler in `actions.py` — never grow an `if/elif` in `world.py::_simulate`.
- **Every world declares an explicit, required action space** (no default, no canonical
  bundle). Recording a verb outside it raises.
- **Characters are a pure frontend concern** — the contract is `js/characters/character.js`;
  Mo (`mossball.js`) and Rover (`rover.js`) implement it. Adding a character never touches
  Python.

## Layout

- `src/wanderland/`: `actions.py` (verb registry + sim semantics), `commands.py` (recorded
  verbs), `puzzles.py` (Puzzle + objects + `from_ascii`/`from_dict`/`to_prompt` + built-ins),
  `generate.py` (`random_room`), `solve.py` (BFS oracle), `world.py` (the AnyWidget; `act()`),
  `static/` (built bundle).
- `js/`: `index.js` (entry), `viewer.js` (orchestrator), `scene.js`, `board.js` + `objects.js`
  (world render), `characters/`, `hud.js`, `palette.js`, `easing.js`.
- Notebooks: `example.py` (education), `rl_playground.py` (agent/RL). Tests in `test/`.

## Build / test

- **After editing anything in `js/`, rebuild the bundle:** `npm run build` (esbuild →
  `src/wanderland/static/index.js`). The committed bundle is what ships; source edits do
  nothing until rebuilt.
- Python sim tests (headless, fast): `.venv/bin/python test/test_sim.py`
- Frontend render test (headless, software WebGL): `node test/browser_test.mjs`
- Characters end-to-end: `node test/shot_characters.mjs`
- Notebooks: smoke-test with `.venv/bin/python -m marimo export html <nb>.py -o /tmp/x.html`.
- Editable install lives in `.venv` (`uv pip install -e ".[dev]"`).

## Conventions

- **No Claude attribution** in commits or PRs (no `Co-Authored-By`, no "Generated with…").
- **Neutral language** — no external framework or paper names; keep it a generic grid-world
  playground.
- `todo.md` (gitignored) and `layouts/` (untracked) are local-only — don't commit them.

## Model / gotchas

- Gems come in two kinds: non-blocking `g` (walk onto it, then `collect_gem`; scores) and
  blocking `G` (`pickup` from the front; carried). Keys/balls/boxes are carry-slot inventory
  (limit one). Doors are tiles with open/closed/locked state; a locked door needs a matching
  key (kept). Box opens to its contents.
- `World.load()` is **idempotent** (re-loading the same program is a no-op) so a reactive
  marimo re-run after a finished run doesn't reset the scene. Keep that.
- A blocked move carries `blocked_by` → the character distinguishes (edge = teeter, near
  fall; wall/door/object = bonk).
- In `World.act(actions, ...)` the `actions` param shadows the `actions` module — alias it
  (`from . import actions as actions_mod`) if you need the registry there.
