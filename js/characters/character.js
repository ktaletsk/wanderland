// The Character contract.
//
// Separation of concerns: the Viewer owns the timeline, the board, the score and
// the tween clock. A Character owns ONLY how it looks as those events play out --
// its shape and its choreography. Swapping characters never touches game logic.
//
// Every behaviour method is async and receives `ctx = { tween, spd }`, where
// `tween(durMs, ease, onUpdate)` is the Viewer's scheduler and `spd` the speed
// multiplier. A method may await as many tweens as it likes (single- or
// multi-phase) and MUST leave the character at rest at the requested end pose.
//
// Positions are THREE.Vector3 in world space; angles are radians about Y.
//
// This base class is itself a complete, if plain, character: it glides between
// tiles with no personality. Subclasses (see mossball.js, rover.js) override the
// hooks to add flair. The minimal contract a subclass must satisfy is just a
// constructor that builds meshes under `this.group`.

import * as THREE from "three";
import { DUR } from "../palette.js";
import { easeInOutCubic, easeOutCubic, lerp, lerpAngle } from "../easing.js";

export class Character {
  constructor() {
    this.group = new THREE.Group(); // root node; the Viewer adds it to the scene
    this._mood = "neutral";
  }

  // Instantly snap to a world position facing `heading`, at rest. (resets/init)
  placeAt(pos, heading) {
    this.group.position.set(pos.x, 0, pos.z);
    this.group.rotation.set(0, heading, 0);
  }

  // Walk one tile from `from` to `to`.
  async move(from, to, ctx) {
    await ctx.tween(DUR.move / ctx.spd, easeInOutCubic, (e) => {
      this.group.position.set(lerp(from.x, to.x, e), 0, lerp(from.z, to.z, e));
    });
    this.group.position.set(to.x, 0, to.z);
  }

  // Rotate in place from heading `a0` to `a1`.
  async turn(a0, a1, ctx) {
    await ctx.tween(DUR.turn / ctx.spd, easeInOutCubic, (e) => {
      this.group.rotation.y = lerpAngle(a0, a1, e);
    });
    this.group.rotation.y = a1;
  }

  // React to a move that couldn't happen -- something solid lies in direction
  // `dir` (a unit world vector). `reason` is why: 'edge' (the world's rim / water)
  // or 'wall' | 'door' | 'object'. Ends back at `from`, at rest. The default
  // reaction is a small lunge-and-recoil; characters may distinguish reasons.
  async blocked(from, dir, ctx, reason = "edge") {
    await ctx.tween(DUR.blocked / ctx.spd, easeOutCubic, (e) => {
      const out = Math.sin(Math.PI * e) * 0.16; // lean out and back
      this.group.position.set(from.x + dir.x * out, 0, from.z + dir.z * out);
    });
    this.group.position.set(from.x, 0, from.z);
  }

  // Glide back to the start pose at the top of a run.
  async returnHome(from, to, a0, a1, ctx) {
    const dist = Math.hypot(to.x - from.x, to.z - from.z);
    const dur = Math.min(950, 420 + dist * 95) / ctx.spd;
    await ctx.tween(dur, easeInOutCubic, (e) => {
      this.group.position.set(lerp(from.x, to.x, e), 0, lerp(from.z, to.z, e));
      this.group.rotation.y = lerpAngle(a0, a1, e);
    });
    this.group.position.set(to.x, 0, to.z);
    this.group.rotation.y = a1;
  }

  // A momentary flourish in response to an event. `kind` is a semantic label --
  // currently 'cheer' (collected something) or 'confused' (nothing to collect);
  // future world objects will add more (e.g. 'pickup', 'unlock'). No-op default.
  async react(kind, ctx) {}

  // Set the character's emotional baseline. `name` is a standard intent the
  // character maps onto its own face however it can (or ignores):
  // 'neutral' | 'happy' | 'surprised' | 'determined'. Default just records it.
  setExpression(name) {
    this._mood = name;
  }

  // Per-frame ambient life: idle motion, blinking, easing the face. Called every
  // tick with elapsed time, frame delta, and whether a program is playing.
  update(t, dt, playing) {}

  dispose() {
    this.group.traverse((child) => {
      if (child.geometry) child.geometry.dispose();
      if (child.material) {
        const mats = Array.isArray(child.material) ? child.material : [child.material];
        mats.forEach((m) => m.dispose());
      }
    });
  }
}
