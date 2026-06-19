import marimo

__generated_with = "0.23.10"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo

    from wanderland import World, from_ascii, random_room, solve

    return World, from_ascii, mo, random_room, solve


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 🤖 Wanderland — Agent / RL Playground

    Grid worlds for **evaluating agents** (LLMs, RL policies). Build a
    world with walls, doors and keys; render it to a text prompt; hand an agent the
    action space; replay its actions and score the result.

    **Python is the authoritative simulator** — every result is available
    synchronously (no browser needed), so the same world drives both an offline
    benchmark and this live 3D view.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1 · Build a world

    A locked room: stone walls (`#`), a **locked yellow door** (`Ly`) set in the wall,
    a **yellow key** (`Ky`), and the goal (`O`). The start glyph (`>` `<` `^` `v`)
    encodes the agent's position **and** facing. Every world declares its exact
    **action space** — there is no default.
    """)
    return


@app.cell
def _(World, from_ascii, mo):
    puzzle = from_ascii(
        "Unlock the Room",
        """
        > . # .
        . . Ly .
        Ky . # O
        """,
        actions=("move_forward", "turn_left", "turn_right", "pickup", "toggle"),
    )

    env = World(puzzle, character="rover")
    world = mo.ui.anywidget(env)
    world
    return env, world


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2 · What the agent sees

    Three encodings of the *same* state: **structured** text (the canonical, measured
    prompt — an explicit header + a coordinate-tagged object list), an **ascii** view,
    and a 2D **image** observation (`render()`) for vision models. Box contents stay
    hidden until opened. Hand a model any of them and compare — same world, different
    encoding.
    """)
    return


@app.cell(hide_code=True)
def _(env, mo):
    mo.md(f"""
    **`to_prompt("structured")`** — the measured input:

    ```
    {env.to_prompt("structured")}
    ```

    **`to_prompt("ascii")`** — a second view of the same state:

    ```
    {env.to_prompt("ascii")}
    ```
    """)
    return


@app.cell(hide_code=True)
def _(env, mo):
    # render() — the 2D top-down image observation (headless, no browser)
    mo.image(env.render(tile=32).to_png(), width=env.puzzle["cols"] * 32)
    return


@app.cell(hide_code=True)
def _(env, mo):
    mo.md(
        "## 3 · The action space\n\n"
        "Exactly the verbs you hand the agent (and enforce in measured runs):\n\n"
        + "\n".join(f"- `{a['name']}` — {a['doc']}" for a in env.actions_doc)
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4 · Run an agent's actions

    An agent emits a list of action names. `env.act([...])` simulates them in Python
    (validating each against the action space) and returns the result **immediately**;
    the widget above replays them when you press **▶ Run My Code**. Edit the plan and
    watch the outcome change.
    """)
    return


@app.cell
def _(env):
    # An agent's plan: grab the key, unlock the door, walk to the goal.
    plan = [
        "turn_right", "move_forward", "pickup",    # take the yellow key
        "turn_left", "move_forward", "toggle",     # unlock & swing the door open
        "move_forward", "move_forward",            # through the doorway
        "turn_right", "move_forward",              # onto the goal
    ]

    result = env.act(plan)
    return (result,)


@app.cell(hide_code=True)
def _(mo, result, world):
    _ = world.value  # also re-run when a playback finishes
    mo.callout(
        mo.md(
            f"""
        **Result** &nbsp; {"✅ solved" if result["success"] else "❌ not solved"}

        - reached goal: **{result["reached_goal"]}**
        - carrying: **{result["carrying"]}**
        - steps taken: **{result["steps"]}**
        """
        ),
        kind="success" if result["success"] else "neutral",
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 5 · Generate worlds (+ an oracle baseline)

    `random_room(seed=...)` emits a fresh, **solvable-by-construction** locked room
    — a reproducible distribution to evaluate over. `solve(puzzle)` is a BFS oracle
    that returns a shortest solving plan (verify a world, or use it as a baseline /
    imitation target). Drag the sliders to roll new worlds.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    seed = mo.ui.slider(0, 30, value=7, label="seed")
    n_gems = mo.ui.slider(0, 3, value=1, label="gems")
    mo.hstack([seed, n_gems], justify="start", gap=2)
    return n_gems, seed


@app.cell
def _(World, mo, n_gems, random_room, seed):
    gen_puzzle = random_room(seed=seed.value, cols=6, rows=5, gems=n_gems.value)
    gen_env = World(gen_puzzle, character="rover")
    gen_world = mo.ui.anywidget(gen_env)
    gen_world
    return gen_env, gen_puzzle, gen_world


@app.cell
def _(gen_env, gen_puzzle, solve):
    # the oracle solves the generated world; load its plan so Run replays it
    oracle_plan = solve(gen_puzzle)
    oracle_result = gen_env.act(oracle_plan) if oracle_plan else None
    return oracle_plan, oracle_result


@app.cell(hide_code=True)
def _(gen_env, mo, oracle_plan, oracle_result):
    mo.callout(
        mo.md(
            f"""
        **Oracle** &nbsp; {f"solved in **{len(oracle_plan)}** steps" if oracle_plan else "**no solution found**"}

        - actions: `{oracle_plan}`
        - structured prompt:

        ```
        {gen_env.to_prompt("structured")}
        ```
        """
        ),
        kind="success" if oracle_result and oracle_result["success"] else "neutral",
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ### Notes for experiments

    - **`env.act([...])`** is the agent interface — pass the model's action-name output
      straight in. Unknown or out-of-space verbs raise, so a measured run can't cheat.
    - **`env.success`, `env.result`, `env.reached_goal`** are authoritative and
      synchronous — drive an offline benchmark loop with no browser in sight.
    - **Encoding study:** compare `to_prompt("structured")` vs `to_prompt("ascii")`
      success rates on the identical world (the encoding alone can move the numbers).
    - **`character="rover"`** is only a render skin; swap to `"mo"` freely.
    """)
    return


if __name__ == "__main__":
    app.run()
