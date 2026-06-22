# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.23.10",
#     "pandas==3.0.3",
#     "wanderland==0.1.1",
# ]
# ///

import marimo

__generated_with = "0.23.10"
app = marimo.App(width="medium")

with app.setup(hide_code=True):
    import marimo as mo
    import pandas as pd

    import wanderland as bp
    from wanderland import (
        collect_gem,
        drop,
        move_forward,
        pickup,
        toggle,
        turn_left,
        turn_right,
    )


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # 🌱 Wanderland

    Meet **Mo** — a curious little explorer who lives in a tiny world of grassy
    tiles. His first world is called **Gem Path**. Mo can't decide where to go on
    his own, so **you** are his guide!

    Your quest: lead Mo around the world to **collect both gems** 💎, then finish
    on the glowing **golden ring** to win. Watch out — there's a **pond** in the
    middle that Mo can't swim across, so he'll have to walk around it.

    The best part? You guide Mo by writing **real Python** — the very same
    programming language used by scientists, game makers, and engineers around
    the world.
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ---
    ### How to play

    Mo follows a **plan** — a list of simple commands, one per line. He knows
    just four:

    - **`move_forward()`** — take one step in the direction he's facing
    - **`turn_left()`** — spin a quarter-turn to the left
    - **`turn_right()`** — spin a quarter-turn to the right
    - **`collect_gem()`** — pick up the gem on the tile he's standing on

    **Write Mo's plan** in the editor below — type the commands yourself, or
    **tap the buttons** to add them for you. Mo starts in the top-left corner,
    facing right, so plan his path from there.

    When the plan looks good, press **▶ Run My Code** in the world to watch Mo
    set off. He follows your plan once and stops where he ends up. A message
    under the world tells you how many gems he collected and whether he reached
    the goal — if not, tweak the plan and try again!

    Mo's world is fully **3D** — **drag** it to spin the camera around for a
    better view, and **scroll** (or pinch) to zoom in and out.
    """)
    return


@app.cell(hide_code=True)
def _():
    # Single source of truth for Mo's program. The command buttons append to it and
    # the editor edits it -- both flow through this state so they never disagree.
    get_code, set_code = mo.state(
        "move_forward()\n"
        "move_forward()\n"
        "move_forward()\n"
        "collect_gem()\n"
    )
    return get_code, set_code


@app.cell(hide_code=True)
def _(get_code, set_code):
    # Editor definition only -- it is laid out (with the palette and the 3D scene)
    # in the layout cell below. Kept in its OWN cell so a palette-button tap
    # refreshes it: marimo preserves UI values only within the cell that *defines*
    # the element that triggered the rerun.
    solution_code = mo.ui.code_editor(
        value=get_code(),
        language="python",
        debounce=True,
        on_change=set_code,
        min_height=150,
        show_copy_button=False,
    )
    return (solution_code,)


@app.cell(hide_code=True)
def _(get_code, set_code):
    # Command palette (rendered in the layout cell). Separate cell from the editor
    # so taps refresh the editor. Buttons are global and bump their value on click
    # so on_change fires.
    def _appender(snippet):
        def _cb(_v):
            cur = get_code().rstrip("\n")
            set_code((cur + "\n" + snippet if cur else snippet) + "\n")

        return _cb

    def _undo_cb(_v):
        lines = get_code().rstrip("\n").split("\n")
        set_code(("\n".join(lines[:-1]) + "\n") if len(lines) > 1 else "")

    _bump = lambda v: (v or 0) + 1
    btn_forward = mo.ui.button(value=0, on_click=_bump, on_change=_appender("move_forward()"), label="move_forward()")
    btn_left = mo.ui.button(value=0, on_click=_bump, on_change=_appender("turn_left()"), label="turn_left()")
    btn_right = mo.ui.button(value=0, on_click=_bump, on_change=_appender("turn_right()"), label="turn_right()")
    btn_gem = mo.ui.button(value=0, on_click=_bump, on_change=_appender("collect_gem()"), label="collect_gem()")
    btn_undo = mo.ui.button(value=0, on_click=_bump, on_change=_undo_cb, label="⌫ undo")
    btn_clear = mo.ui.button(value=0, on_click=_bump, on_change=lambda _v: set_code(""), kind="danger", label="✕ clear")
    command_palette = mo.hstack(
        [btn_forward, btn_left, btn_right, btn_gem, btn_undo, btn_clear],
        justify="start", gap=0.4, wrap=True,
    )
    return (command_palette,)


@app.cell(hide_code=True)
def _():
    # The grid world Mo lives in (the "Gem Path" puzzle), with its own Run button.
    # Defined here; laid out beside the editor in the layout cell.
    world = mo.ui.anywidget(bp.World(bp.puzzles.gem_path()))
    return (world,)


@app.cell(hide_code=True)
def _(command_palette, solution_code, world):
    # Playground: editor + command palette on the LEFT, Mo's 3D world on the RIGHT.
    # Tapping a command or typing loads into the scene automatically; press Run My
    # Code in the scene to watch Mo go.
    mo.hstack(
        [
            mo.vstack([
                solution_code,
                command_palette,
            ]),
            world,
        ],
        align="start", gap=1.5, widths=[0.4, 0.6],
    )
    return


@app.cell(hide_code=True)
def _(solution_code, world):
    # Build Mo's program from the editable block above and hand the timeline to
    # the scene (reactive: recomputes whenever you edit the code). Mo only moves
    # when you press the Run button in the scene.
    _ns = {"move_forward": move_forward, "turn_left": turn_left,
           "turn_right": turn_right, "collect_gem": collect_gem}

    def solution():
        exec(compile(solution_code.value, "<solution>", "exec"), _ns)

    try:
        loaded = world.load(solution)
        solution_error = None
    except Exception as _e:
        loaded = None
        solution_error = _e
    return loaded, solution_error


@app.cell(hide_code=True)
def _(loaded, solution_error, world):
    # Re-runs both when you EDIT the program (via `loaded`) and when Mo reports
    # finishing a run (via world.value). On edit, the frontend state is cleared, so
    # this resets to "press Run" instead of showing a stale result.
    _ = loaded
    _ = world.value
    if solution_error is not None:
        _out = mo.callout(
            mo.md(
                f"""
                **Your code didn't run** &mdash; fix it and Mo will be ready:

                ```
                {type(solution_error).__name__}: {solution_error}
                ```
                """
            ),
            kind="danger",
        )
    elif not world.state.get("finished"):
        _out = mo.callout(
            mo.md("Press **▶ Run My Code** in the scene to send Mo off."),
            kind="info",
        )
    else:
        _won = world.success
        _out = mo.callout(
            mo.md(
                f"""
                **Result** &nbsp; {"🎉 Puzzle solved!" if _won else "Keep trying…"}

                - Gems collected: **{world.gems_collected} / {world.total_gems}**
                - Reached the goal: **{world.reached_goal}**
                """
            ),
            kind="success" if _won else "neutral",
        )
    _out
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ---
    ## 🛠️ Build your own world

    Mo doesn't have to stick to Gem Path — you can design a world for him! A
    world is just a **grid of tiles**, like a spreadsheet. Type one symbol in
    each square and Mo's world rebuilds in 3D right away. We can also have way
    more fun with things like **lava**, **locks**, and **keys**!

    Use the symbol key to fill in the spreadsheet. Every world needs **exactly
    one** start tile — edit any square (you can add or remove rows too) and watch
    your world take shape.
    """)
    return


@app.cell(hide_code=True)
def _():
    # The symbol key -- shown beside the spreadsheet so kids can look up tiles
    # while they fill it in.
    symbol_table = mo.md(r"""
    | Symbol | Tile |
    | :---: | :--- |
    | `.` | grass — Mo can walk here |
    | `#` | a wall — blocks the way |
    | `~` | water — Mo can't swim across |
    | `!` | lava — looks cool, but stepping in ends the adventure! 🔥 |
    | `g` | a gem to collect 💎 |
    | `Ky` | a yellow key 🔑 — pick it up to open a matching door |
    | `Ly` | a locked yellow door — only the matching key opens it |
    | `O` | the golden goal ring |
    | `>` | where Mo starts (the arrow is the way he faces: `>` `<` `^` `v`) |

    Keys and doors come in colors — use the color's first letter: `r` red,
    `g` green, `b` blue, `p` purple, `y` yellow, `e` grey. So `Kb` is a blue key
    and `Lb` is the blue door it opens.
    """)
    return (symbol_table,)


@app.cell(hide_code=True)
def _():
    # The tile grid Mo's world is built from -- one symbol per square. Editing a
    # cell (or adding/removing rows) rebuilds the 3D world below.
    _starter = [
        [">", ".", "#", ".", "g"],
        [".", "g", "Ly", ".", "."],
        ["Ky", ".", "#", "!", "."],
        [".", ".", "#", ".", "O"],
    ]
    grid_df = pd.DataFrame(_starter, columns=[str(i) for i in range(len(_starter[0]))])
    grid_designer = mo.ui.data_editor(grid_df, label="Tile editor")
    return (grid_designer,)


@app.cell(hide_code=True)
def _(grid_designer, symbol_table):
    # Layout 1: the symbol key on the LEFT, the tile spreadsheet on the RIGHT.
    mo.hstack(
        [symbol_table, grid_designer],
        align="start", gap=1.5, widths=[0.4, 0.6],
    )
    return


@app.cell(hide_code=True)
def _(grid_designer):
    # Turn the spreadsheet of tiles into an ASCII map, then build a world from it.
    # A bad grid (e.g. no start tile) is reported below as a friendly hint.
    def _grid_to_ascii(val):
        rows = val.values.tolist() if hasattr(val, "values") else [list(r.values()) for r in val]
        return "\n".join(" ".join((str(c).strip() or ".") for c in row) for row in rows)

    designed_ascii = _grid_to_ascii(grid_designer.value)
    try:
        designed = bp.from_ascii(
            "Your World", designed_ascii,
            actions=("move_forward", "turn_left", "turn_right", "collect_gem",
                     "pickup", "drop", "toggle"),
        )
        designed_world = mo.ui.anywidget(bp.World(designed))
        build_error = None
    except Exception as _e:
        designed_world = None
        build_error = _e
    return build_error, designed_world


@app.cell(hide_code=True)
def _():
    # Single source of truth for the solution to YOUR world (editor + buttons both
    # edit it). Separate from Gem Path's program so the two never interfere.
    get_build_code, set_build_code = mo.state(
        "# Write Mo's plan to solve the world you built!\n"
        "move_forward()\n"
    )
    return get_build_code, set_build_code


@app.cell(hide_code=True)
def _(get_build_code, set_build_code):
    # Editor for your world's solution -- in its own cell so a button tap refreshes
    # it (marimo keeps UI values only within the defining cell).
    build_code = mo.ui.code_editor(
        value=get_build_code(),
        language="python",
        debounce=True,
        on_change=set_build_code,
        min_height=150,
        show_copy_button=False,
    )
    return (build_code,)


@app.cell(hide_code=True)
def _(get_build_code, set_build_code):
    # Command palette for the builder -- includes the key/door verbs since worlds
    # you design can have locks.
    def _appender(snippet):
        def _cb(_v):
            cur = get_build_code().rstrip("\n")
            set_build_code((cur + "\n" + snippet if cur else snippet) + "\n")

        return _cb

    def _undo_cb(_v):
        lines = get_build_code().rstrip("\n").split("\n")
        set_build_code(("\n".join(lines[:-1]) + "\n") if len(lines) > 1 else "")

    _bump = lambda v: (v or 0) + 1
    _verbs = ["move_forward", "turn_left", "turn_right", "collect_gem", "pickup", "drop", "toggle"]
    _cmd_btns = [
        mo.ui.button(value=0, on_click=_bump, on_change=_appender(f"{v}()"), label=f"{v}()")
        for v in _verbs
    ]
    _cmd_btns.append(mo.ui.button(value=0, on_click=_bump, on_change=_undo_cb, label="⌫ undo"))
    _cmd_btns.append(mo.ui.button(value=0, on_click=_bump, on_change=lambda _v: set_build_code(""), kind="danger", label="✕ clear"))
    build_palette = mo.hstack(_cmd_btns, justify="start", gap=0.4, wrap=True)
    return (build_palette,)


@app.cell(hide_code=True)
def _(build_code, designed_world):
    # Build the solution program and hand its timeline to YOUR world (reactive:
    # recomputes when you edit the code or redesign the grid). Mo only moves when
    # you press Run in the scene.
    _ns = {"move_forward": move_forward, "turn_left": turn_left,
           "turn_right": turn_right, "collect_gem": collect_gem,
           "pickup": pickup, "drop": drop, "toggle": toggle}

    def _solution():
        exec(compile(build_code.value, "<solution>", "exec"), _ns)

    build_loaded, build_run_error = None, None
    if designed_world is not None:
        try:
            build_loaded = designed_world.load(_solution)
        except Exception as _e:
            build_run_error = _e
    return build_loaded, build_run_error


@app.cell(hide_code=True)
def _(build_code, build_error, build_palette, designed_world):
    # Layout 2: the code editor (with command buttons) on the LEFT, YOUR generated
    # world on the RIGHT -- so you can write a plan and watch Mo solve it. If the
    # grid can't build a world yet, a friendly hint takes the world's place.
    if designed_world is not None:
        _right = designed_world
    else:
        _right = mo.callout(
            mo.md(
                f"**Can't build that world yet:** {build_error}\n\n"
                "Remember: every world needs exactly **one** start tile "
                "(`>`, `<`, `^`, or `v`)."
            ),
            kind="warn",
        )
    mo.hstack(
        [mo.vstack([build_code, build_palette]), _right],
        align="start", gap=1.5, widths=[0.4, 0.6],
    )
    return


@app.cell(hide_code=True)
def _(build_loaded, build_run_error, designed_world):
    # Feedback for your world: code error / press Run / solved-or-keep-trying.
    _ = build_loaded
    if designed_world is not None:
        _ = designed_world.value
    if designed_world is None:
        _out = None
    elif build_run_error is not None:
        _out = mo.callout(
            mo.md(
                f"""
                **Your code didn't run** &mdash; fix it and Mo will be ready:

                ```
                {type(build_run_error).__name__}: {build_run_error}
                ```
                """
            ),
            kind="danger",
        )
    elif not designed_world.state.get("finished"):
        _out = mo.callout(
            mo.md("Press **▶ Run My Code** in your world to send Mo off."),
            kind="info",
        )
    else:
        _won = designed_world.success
        _out = mo.callout(
            mo.md(
                f"""
                **Result** &nbsp; {"🎉 You solved your own world!" if _won else "Keep trying…"}

                - Gems collected: **{designed_world.gems_collected} / {designed_world.total_gems}**
                - Reached the goal: **{designed_world.reached_goal}**
                """
            ),
            kind="success" if _won else "neutral",
        )
    _out
    return


if __name__ == "__main__":
    app.run()
