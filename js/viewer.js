// The Viewer orchestrates the stage, the board and the character, and owns the
// playback: loading a program, the return-home glide, and per-command stepping.
// It holds no game logic (Python is authoritative) and no character choreography
// (each Character owns how it looks -- see characters/character.js). The Viewer
// just supplies world positions + a tween clock and awaits the character.

import * as THREE from "three";
import { createStage, frameCamera } from "./scene.js";
import { Board } from "./board.js";
import { createCharacter, DEFAULT_CHARACTER } from "./characters/index.js";
import { Hud } from "./hud.js";
import { DUR, headingAngle } from "./palette.js";
import { easeInCubic, easeOutCubic, easeOutBack, lerp } from "./easing.js";

export class Viewer {
  constructor(el, opts = {}) {
    this.el = el;
    this.playing = false;
    this._runId = 0;
    this.score = 0;
    this.speed = 1;
    this.timeline = [];
    this.result = null; // authoritative outcome from Python (success, goal, ...)
    this.onComplete = null;
    this.carried = null; // the board object currently held by the character

    const stage = createStage(el);
    this.renderer = stage.renderer;
    this.scene = stage.scene;
    this.camera = stage.camera;
    this.controls = stage.controls;

    this._boundTween = this._tween.bind(this);
    this.character = null;
    this.setCharacter(opts.character || DEFAULT_CHARACTER);

    this.hud = new Hud(el, () => this._onRunClick());

    this.clock = new THREE.Clock();
    this._lastT = 0;

    this._resize = this._resize.bind(this);
    this._ro = new ResizeObserver(this._resize);
    this._ro.observe(el);
    this._resize();

    this._tick = this._tick.bind(this);
    this._raf = requestAnimationFrame(this._tick);
  }

  // ------------------------------------------------------------- character
  setCharacter(name) {
    if (this.character) {
      this.scene.remove(this.character.group);
      this.character.dispose();
    }
    this.character = createCharacter(name);
    this.characterName = name;
    this.scene.add(this.character.group);
    // re-place onto the current pose if the board already exists
    if (this.board && this.pose) {
      this.character.placeAt(this.board.worldPos(this.pose.col, this.pose.row), headingAngle(this.pose.h));
      this.character.setExpression(this.playing ? "determined" : "neutral");
    }
  }

  // ----------------------------------------------------------------- board
  setPuzzle(puzzle) {
    this.puzzle = puzzle;
    if (this.board) {
      this.scene.remove(this.board.group);
      this.board.dispose();
    }
    this.board = new Board(puzzle);
    this.scene.add(this.board.group);
    frameCamera(this.camera, this.controls, puzzle.cols, puzzle.rows);
    this.resetToStart();
  }

  _startPose() {
    const [c, r] = this.puzzle.start;
    return { col: c, row: r, h: { N: 0, E: 1, S: 2, W: 3 }[this.puzzle.heading] };
  }

  _ctx(spd) {
    return { tween: this._boundTween, spd: spd > 0 ? spd : 1 };
  }

  // ----------------------------------------------------------------- reset
  // Reset the WORLD (gems back, score/status cleared, face neutral) WITHOUT
  // moving the character -- so it stays wherever it last finished.
  _restoreWorld() {
    // drop a carried item's orphaned mesh before rebuilding (it's not in the map)
    if (this.carried) this.board.disposeDetached(this.carried.group);
    this.carried = null;
    this.board.resetGems();
    this.board.resetObjects();
    this.score = 0;
    this.hud.setScore(0, this.puzzle.gems.length);
    this.hud.hideStatus();
    this.character.setExpression("neutral");
  }

  // Instantly place the character at the start + restore the world.
  resetToStart() {
    if (!this.puzzle) return;
    const sp = this._startPose();
    this.pose = sp;
    this.character.placeAt(this.board.worldPos(sp.col, sp.row), headingAngle(sp.h));
    this._restoreWorld();
  }

  // Load a program's timeline. The character STAYS where it last finished (it
  // only returns home when you press Run); the world is refreshed, button armed.
  load(timeline) {
    this._runId++; // abort any in-flight play loop or victory dance
    this.playing = false;
    if (this.board && this.pose) {
      // snap the character to rest at its current pose (cleans up a mid-animation)
      this.character.placeAt(this.board.worldPos(this.pose.col, this.pose.row), headingAngle(this.pose.h));
    }
    this.timeline = Array.isArray(timeline) ? timeline : [];
    this._restoreWorld();
    this.hud.setButton(this.timeline.length ? "ready" : "empty");
  }

  _onRunClick() {
    if (this.playing || !this.timeline.length) return;
    this.play(this.timeline, this.speed);
  }

  // Smoothly arc the character back home to the start pose (top of a run).
  async _returnToStart(spd) {
    const sp = this._startPose();
    const cur = this.pose;
    if (cur && cur.col === sp.col && cur.row === sp.row && cur.h === sp.h) return;
    const from = this.board.worldPos(cur.col, cur.row);
    const to = this.board.worldPos(sp.col, sp.row);
    const a0 = this.character.group.rotation.y;
    const a1 = headingAngle(sp.h);
    await this.character.returnHome(from, to, a0, a1, this._ctx(spd));
    this.pose = { ...sp };
  }

  // ------------------------------------------------------------- tween util
  _tween(durMs, ease, onUpdate) {
    return new Promise((resolve) => {
      const t0 = performance.now();
      const step = () => {
        let p = (performance.now() - t0) / durMs;
        if (p > 1) p = 1;
        onUpdate(ease(p), p);
        if (p < 1) requestAnimationFrame(step);
        else resolve();
      };
      requestAnimationFrame(step);
    });
  }

  // -------------------------------------------------------------- play loop
  async play(timeline, speed = 1) {
    if (!this.puzzle) return;
    this.timeline = Array.isArray(timeline) ? timeline : [];
    const myRun = ++this._runId;
    this.playing = true;
    this.hud.setButton("running");
    this.character.setExpression("determined"); // focused while running
    const spd = speed > 0 ? speed : 1;

    // Refresh the world, then glide back home before replaying.
    this._restoreWorld();
    await this._returnToStart(spd);
    if (this._runId !== myRun) return;

    for (const step of this.timeline) {
      if (this._runId !== myRun) return; // superseded by a newer run
      await this._animateStep(step, spd);
    }

    if (this._runId === myRun) {
      this.hud.setButton("done");
      const total = this.puzzle.gems.length;
      // "Solved!" reflects Python's authoritative result (gems AND goal).
      const success = this.result ? !!this.result.success : this.score === total;
      this.character.setExpression(success ? "happy" : "neutral");
      this.hud.setScore(this.score, total);
      this.hud.setStatus(success ? "Solved!" : "Keep trying", success ? "win" : "done");
      if (this.onComplete) {
        this.onComplete({
          finished: true,
          success,
          gems_collected: this.score,
          total_gems: total,
          pose: this.pose,
        });
      }
      // a victory dance on success. `playing` stays true through it so the idle
      // motion in _tick doesn't fight it; a fresh load() aborts it via _runId.
      if (success) await this.character.react("win", this._ctx(spd));
      if (this._runId === myRun) this.playing = false;
    }
  }

  async _animateStep(step, spd) {
    const ctx = this._ctx(spd);
    if (step.kind === "move") {
      const from = this.board.worldPos(step.from.col, step.from.row);
      if (step.ok) {
        const to = this.board.worldPos(step.to.col, step.to.row);
        await this.character.move(from, to, ctx);
        this.pose = { ...step.to };
        if (step.died) await this.character.react("die", ctx); // walked into lava
      } else {
        const target = this.board.worldPos(step.target.col, step.target.row);
        const dir = target.clone().sub(from).normalize();
        await this.character.blocked(from, dir, ctx, step.blocked_by);
        this.pose = { ...step.from };
      }
    } else if (step.kind === "turn") {
      await this.character.turn(headingAngle(step.from.h), headingAngle(step.to.h), ctx);
      this.pose = { ...step.to };
    } else if (step.kind === "collect") {
      if (step.ok && step.gem) {
        const gem = this.board.gems.get(`${step.gem[0]},${step.gem[1]}`);
        await Promise.all([this._collectGemTween(gem, ctx), this.character.react("cheer", ctx)]);
        this.score += 1;
        this.hud.setScore(this.score, this.puzzle.gems.length);
      } else {
        await this.character.react("confused", ctx);
      }
    } else if (step.kind === "pickup") {
      if (step.ok) await this._pickupObject(step, ctx);
      else await this.character.react("confused", ctx);
    } else if (step.kind === "drop") {
      if (step.ok) await this._dropObject(step, ctx);
      else await this.character.react("confused", ctx);
    } else if (step.kind === "toggle") {
      if (step.ok) await this._toggleObject(step, ctx);
      else await this.character.react("confused", ctx);
    }
  }

  // Pickup: the object on the faced cell floats up into the character's hands
  // (a carried slot above his head). Position is unchanged.
  async _pickupObject(step, ctx) {
    const key = `${step.cell[0]},${step.cell[1]}`;
    const entry = this.board.objects.get(key);
    if (!entry) return;
    this.board.objects.delete(key); // it's carried now, not on a cell
    const from = entry.group.position.clone();
    const cp = this.character.group.position;
    await this._tween(DUR.collect / ctx.spd, easeOutCubic, (e) => {
      entry.group.position.x = lerp(from.x, cp.x, e);
      entry.group.position.z = lerp(from.z, cp.z, e);
      entry.group.position.y = lerp(from.y, cp.y + 1.25, e) + Math.sin(Math.PI * e) * 0.25;
      entry.group.rotation.y += 0.3;
    });
    entry.carried = true;
    this.carried = entry;
  }

  // Drop: the carried object floats down onto the faced floor cell.
  async _dropObject(step, ctx) {
    const entry = this.carried;
    this.carried = null;
    if (!entry) return;
    const target = this.board.worldPos(step.cell[0], step.cell[1]);
    const restY = entry.float ? 0.28 : 0;
    const from = entry.group.position.clone();
    await this._tween(DUR.collect / ctx.spd, easeInCubic, (e) => {
      entry.group.position.x = lerp(from.x, target.x, e);
      entry.group.position.z = lerp(from.z, target.z, e);
      entry.group.position.y = lerp(from.y, restY, e);
    });
    entry.carried = false;
    entry.base = target.clone();
    entry.group.position.set(target.x, restY, target.z);
    this.board.objects.set(`${step.cell[0]},${step.cell[1]}`, entry);
  }

  // Toggle: swing a door (unlocking first if needed) or open a box -> contents.
  async _toggleObject(step, ctx) {
    const entry = this.board.objects.get(`${step.cell[0]},${step.cell[1]}`);
    if (!entry) return;
    if (entry.type === "door") {
      if (step.effect === "unlock" && entry.lock) {
        await this._tween(220 / ctx.spd, easeOutCubic, (e) => entry.lock.scale.setScalar(Math.max(0.001, 1 - e)));
        entry.lock.visible = false;
      }
      const open = step.effect === "open" || step.effect === "unlock";
      const target = open ? entry.group.userData.openAngle : 0;
      const start = entry.hinge.rotation.y;
      await this._tween(DUR.turn / ctx.spd, easeOutBack, (e) => {
        entry.hinge.rotation.y = lerp(start, target, e);
      });
      entry.hinge.rotation.y = target;
    } else if (entry.type === "box") {
      await this._tween(DUR.collect / ctx.spd, easeOutCubic, (e) => {
        if (entry.lid) entry.lid.position.y = 0.33 + e * 0.18;
        entry.group.scale.setScalar(Math.max(0.001, 1 - e * 0.7));
      });
      this.board.replaceObject(step.cell[0], step.cell[1], step.reveals || null);
    }
  }

  // The gem hovering over the character's head is grabbed as he jumps up to it:
  // it floats to a peak, then (as he reaches the apex) is snatched down into him.
  // Runs in parallel with the character's jump (react("cheer")).
  _collectGemTween(gem, ctx) {
    if (!gem) return Promise.resolve();
    gem.collected = true; // hand the gem over to this tween (board.tick lets go)
    const y0 = gem.mesh.position.y;
    const peak = gem.base.y + 1.5;
    return ctx
      .tween(DUR.collect / ctx.spd, (t) => t, (e) => {
        gem.mesh.rotation.y += 0.4;
        if (e < 0.5) {
          // bob up to the peak while he crouches and springs
          gem.mesh.position.y = y0 + (peak - y0) * easeOutCubic(e / 0.5);
        } else {
          // snatched: dip toward his reaching head, shrink and fade away
          const k = (e - 0.5) / 0.5;
          gem.mesh.position.y = peak - k * 0.6;
          gem.mesh.scale.setScalar(Math.max(0.001, 1 - k));
          gem.mat.opacity = 1 - k;
        }
      })
      .then(() => {
        gem.mesh.visible = false;
      });
  }

  // ------------------------------------------------------------- main loop
  _tick() {
    this._raf = requestAnimationFrame(this._tick);
    const t = this.clock.getElapsedTime();
    const dt = Math.min(0.05, t - this._lastT);
    this._lastT = t;

    if (this.board) this.board.tick(t, this.pose ? `${this.pose.col},${this.pose.row}` : null);
    if (this.pose) this.character.update(t, dt, this.playing);
    if (this.carried) {
      const cp = this.character.group.position;
      this.carried.group.position.set(cp.x, cp.y + 1.25, cp.z);
      this.carried.group.rotation.y = t * 1.6;
    }

    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }

  _resize() {
    const w = this.el.clientWidth || 600;
    const h = this.el.clientHeight || 460;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  dispose() {
    cancelAnimationFrame(this._raf);
    this._runId++; // abort any in-flight play loop
    this._ro.disconnect();
    this.controls.dispose();
    if (this.board) this.board.dispose();
    this.character.dispose();
    this.hud.dispose();
    this.renderer.dispose();
    if (this.renderer.domElement.parentNode) {
      this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
    }
  }
}
