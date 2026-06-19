// anywidget entry point. Bridges the synced model traits to the 3D Viewer.
//
// Contract with Python (see world.py):
//   puzzle     (Dict)  static world description; build once.
//   timeline   (List)  ordered animation steps for the current program.
//   result     (Dict)  authoritative outcome (success, reached_goal, gems...).
//   load_nonce (Int)   bump => fully reset to a clean "loaded, not played" state
//                      (Mo at start, gems back, HUD cleared, Run armed).
//   run_nonce  (Int)   bump => play immediately (programmatic / headless runs).
//   speed      (Float) animation speed multiplier.
//   character  (Str)   which character renders the timeline (registry name).
//   state      (Dict)  we write playback reports back here (Python observes).

import { Viewer } from "./viewer.js";

function render({ model, el }) {
  el.classList.add("wanderland-pg");
  const viewer = new Viewer(el, { character: model.get("character") || "mo" });

  const syncSpeed = () => {
    viewer.speed = model.get("speed") || 1;
  };
  const syncResult = () => {
    viewer.result = model.get("result") || null;
  };

  const buildWorld = () => {
    const puzzle = model.get("puzzle");
    if (puzzle && puzzle.cols) viewer.setPuzzle(puzzle);
  };

  // Load the current timeline and fully reset (arms the in-scene Run button).
  const loadTimeline = () => {
    syncSpeed();
    syncResult();
    viewer.load(model.get("timeline") || []);
  };

  // Play immediately (used when Python bumps run_nonce, e.g. world.run()).
  const playTimeline = () => {
    syncSpeed();
    syncResult();
    viewer.play(model.get("timeline") || [], viewer.speed);
  };

  // When the in-scene Run button finishes, report back so marimo cells reading
  // the widget's value can react to "playback complete".
  viewer.onComplete = (report) => {
    model.set("state", { ...report, run_nonce: model.get("run_nonce") });
    model.save_changes();
  };

  syncSpeed();
  syncResult();
  buildWorld();
  viewer.load(model.get("timeline") || []);

  const onPuzzle = () => {
    buildWorld();
    viewer.load(model.get("timeline") || []);
  };
  const onCharacter = () => viewer.setCharacter(model.get("character") || "mo");
  model.on("change:puzzle", onPuzzle);
  model.on("change:load_nonce", loadTimeline);
  model.on("change:run_nonce", playTimeline);
  model.on("change:result", syncResult);
  model.on("change:speed", syncSpeed);
  model.on("change:character", onCharacter);

  return () => {
    model.off("change:puzzle", onPuzzle);
    model.off("change:load_nonce", loadTimeline);
    model.off("change:run_nonce", playTimeline);
    model.off("change:result", syncResult);
    model.off("change:speed", syncSpeed);
    model.off("change:character", onCharacter);
    viewer.dispose();
  };
}

export default { render };
