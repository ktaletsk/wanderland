import marimo

__generated_with = "0.23.10"
app = marimo.App(width="columns")


@app.cell(column=0, hide_code=True)
def _():
    import marimo as mo

    import wanderland as bp
    from wanderland import collect_gem, move_forward, turn_left, turn_right

    return bp, collect_gem, mo, move_forward, turn_right


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 🌱 Wanderland

    Write simple Python commands and watch **Mo** — a curious little character —
    act them out in a low-poly 3D world. Collect the gems, then land on the golden
    ring to win.

    > **Edit the program** below — Mo won't move yet. Then press **▶ Run My Code**
    > in the scene to send him off. He runs the program once and stays where he
    > finishes. **Drag** the scene to orbit the camera.

    > ## Your program

    Mo starts in the top-left corner facing **east** (to the right). Two gems wait
    at opposite corners, with a pond in the middle you must walk around. Walk Mo
    *onto* a gem's tile, then call `collect_gem()` to pick it up.

    The commands this world allows (its *action space*):

    - `move_forward()`
    - `turn_left()` / `turn_right()`
    - `collect_gem()` — collect the gem on the tile Mo is standing on

    Define the steps in `solution()`. Editing it just *loads* the program into the
    scene — press **▶ Run My Code** (in the world on the right) to play it.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ### How it works

    Editing the program calls `world.load(solution)`: the commands are captured and
    simulated in **Python** (the authoritative source of truth), and the resulting
    *timeline* is shipped to the browser — but **not** played. The widget's own
    **▶ Run My Code** button animates that timeline once and stops at Mo's final
    pose. Because Python owns the simulation, `world.success`, `world.gems_collected`,
    and friends are available immediately — even without a browser.

    Build your own world (the start glyph encodes facing; `#`=wall, `~`=water;
    each world declares its own action space):

    ```python
    from wanderland import from_ascii, World
    puzzle = from_ascii("My World", '''
        ^ . . g
        . ~ ~ .
        g . . O
    ''', actions=("move_forward", "turn_left", "turn_right", "collect_gem"))
    world = mo.ui.anywidget(World(puzzle))
    ```
    """)
    return


@app.cell
def _():
    return


@app.cell(column=1)
def _(collect_gem, move_forward, turn_right):
    def solution():
        move_forward()
        move_forward()
        move_forward()
        collect_gem()
        turn_right()
        move_forward()
        move_forward()
        turn_right()
        move_forward()
        move_forward()
        move_forward()
        collect_gem()
        turn_right()
        turn_right()
        move_forward()
        move_forward()
        move_forward()

    return (solution,)


@app.cell(hide_code=True)
def _(bp, mo):
    # Create a world for the "Gem Path" puzzle and display it — including its own
    # in-scene ▶ Run My Code button.
    world = mo.ui.anywidget(bp.World(bp.puzzles.gem_path()))
    world
    return (world,)


@app.cell(hide_code=True)
def _(solution, world):
    # Load the program into the widget (reactive: recomputes when you edit it).
    # This does NOT animate — pressing Run in the scene does. Returning `loaded`
    # lets the result cell below react the instant you edit the program.
    loaded = world.load(solution)
    return (loaded,)


@app.cell(hide_code=True)
def _(loaded, mo, world):
    # Re-runs both when you EDIT the program (via `loaded`) and when Mo reports
    # finishing a run (via world.value). On edit, the frontend state is cleared, so
    # this resets to "press Run" instead of showing a stale result.
    _ = loaded
    _ = world.value
    if not world.state.get("finished"):
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


if __name__ == "__main__":
    app.run()
