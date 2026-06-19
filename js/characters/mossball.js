// Mo the Mossball -- the default character. A chubby moss-green blob who
// waddle-walks on little foot-nubs, squashes and leans, blinks, changes facial
// expression, teeters at ledges, and floats home before each run.

import * as THREE from "three";
import { Character } from "./character.js";
import { COLORS, DUR } from "../palette.js";
import { easeInOutCubic, easeOutCubic, easeOutBack, lerp, lerpAngle } from "../easing.js";

// Facial expressions, eased toward in update():
//   open      vertical openness (0 = shut)   wide  overall eye size
//   innerTilt inner-corner rotation (+ up = happy ^^, - down = angry)
//   lift      vertical offset of the eyes
const EXPR = {
  neutral: { open: 1.0, wide: 1.0, innerTilt: 0.0, lift: 0.0 },
  surprised: { open: 1.4, wide: 1.32, innerTilt: -0.12, lift: 0.03 },
  happy: { open: 0.4, wide: 1.06, innerTilt: 0.55, lift: 0.04 },
  determined: { open: 0.82, wide: 1.06, innerTilt: -0.5, lift: -0.01 },
};

export class MossballCharacter extends Character {
  constructor() {
    super();
    this.rig = new THREE.Group(); // hop + squash/stretch + lean live here
    this.group.add(this.rig);

    this._expr = { ...EXPR.neutral };
    this._exprTarget = { ...EXPR.neutral };
    this._blinkAt = 1.5;
    this._blinkUntil = 0;

    this._buildBody();
    this._buildNubs();
    this._buildEyes();
    this._buildSprout();
  }

  // ---------------------------------------------------------------- contract
  placeAt(pos, heading) {
    super.placeAt(pos, heading);
    this.group.position.y = 0;
    this.rig.scale.set(1, 1, 1);
    this.rig.rotation.set(0, 0, 0);
    this._restNubs();
  }

  // Walk: glide forward with a low waddle, squash, lean and scuttling feet.
  async move(from, to, ctx) {
    const g = this.group;
    const rig = this.rig;
    await ctx.tween(DUR.move / ctx.spd, easeInOutCubic, (e) => {
      g.position.x = lerp(from.x, to.x, e);
      g.position.z = lerp(from.z, to.z, e);
      g.position.y = Math.abs(Math.sin(e * Math.PI * 2)) * 0.055;
      const sq = 1 - 0.07 * Math.cos(e * Math.PI * 4);
      rig.scale.set(1 / Math.sqrt(sq), sq, 1 / Math.sqrt(sq));
      rig.rotation.z = Math.sin(e * Math.PI * 4) * 0.06; // side-to-side
      rig.rotation.x = Math.sin(e * Math.PI) * 0.05; // forward lean
      this._walkNubs(e, 4);
    });
    g.position.set(to.x, 0, to.z);
    rig.scale.set(1, 1, 1);
    rig.rotation.set(0, 0, 0);
    this._restNubs();
  }

  // Turn: a planted pivot with a lean into the turn and shuffling feet.
  async turn(a0, a1, ctx) {
    const g = this.group;
    const rig = this.rig;
    await ctx.tween(DUR.turn / ctx.spd, easeOutBack, (e) => {
      g.rotation.y = lerpAngle(a0, a1, e);
      g.position.y = Math.sin(Math.PI * e) * 0.03;
      rig.rotation.z = Math.sin(Math.PI * e) * 0.07;
      this._walkNubs(e, 1.5);
    });
    g.rotation.y = a1;
    g.position.y = 0;
    rig.rotation.set(0, 0, 0);
    this._restNubs();
  }

  // Blocked. At the world's edge he teeters (almost falls); into a solid wall /
  // door / object he bonks (lunges, squishes against it, recoils).
  async blocked(from, dir, ctx, reason = "edge") {
    if (reason !== "edge") return this._bonk(from, dir, ctx);
    const g = this.group;
    const rig = this.rig;
    // The gap is straight ahead or behind, so tip in Mo's LOCAL frame: derive
    // which from the heading so we always lean toward the drop.
    const h = g.rotation.y;
    const facing = dir.x * -Math.sin(h) + dir.z * -Math.cos(h); // +ahead, -behind
    const lean = facing >= 0 ? -1 : 1;
    this._setFace("surprised"); // "whoa!"

    // 1) edge-out: shuffle to the brink and tip out over the drop, peering down
    await ctx.tween(340 / ctx.spd, easeOutCubic, (e) => {
      g.position.x = from.x + dir.x * 0.32 * e;
      g.position.z = from.z + dir.z * 0.32 * e;
      g.position.y = -0.03 * e;
      rig.rotation.x = lean * 0.52 * e;
      this._walkNubs(e, 6); // feet scrambling for grip
    });
    // 2) teeter on the edge -- wobble, very nearly tips over
    await ctx.tween(440 / ctx.spd, (t) => t, (e) => {
      const w = Math.sin(e * Math.PI * 3.5) * (1 - e * 0.25);
      rig.rotation.x = lean * (0.52 + w * 0.14);
      rig.rotation.z = w * 0.1;
      const reach = 0.32 + Math.max(0, w) * 0.04;
      g.position.x = from.x + dir.x * reach;
      g.position.z = from.z + dir.z * reach;
    });
    // 3) recover: windmill back onto the tile, overshoot, settle (relieved)
    await ctx.tween(DUR.blocked / ctx.spd, easeOutBack, (e) => {
      g.position.x = from.x + dir.x * 0.32 * (1 - e);
      g.position.z = from.z + dir.z * 0.32 * (1 - e);
      g.position.y = -0.03 * (1 - e);
      rig.rotation.x = lean * (0.52 * (1 - e) - 0.16 * Math.sin(Math.PI * e));
      rig.rotation.z = Math.sin(e * Math.PI * 2) * 0.05 * (1 - e);
    });
    g.position.set(from.x, 0, from.z);
    g.position.y = 0;
    rig.rotation.set(0, 0, 0);
    this._restNubs();
    this._setFace(this._mood);
  }

  // Bonk: lunge into the obstacle, squish flat against it, recoil with a shake.
  async _bonk(from, dir, ctx) {
    const g = this.group;
    const rig = this.rig;
    const base = g.rotation.y;
    this._setFace("surprised");
    // lunge forward into it
    await ctx.tween(150 / ctx.spd, easeOutCubic, (e) => {
      g.position.x = from.x + dir.x * 0.2 * e;
      g.position.z = from.z + dir.z * 0.2 * e;
      this._walkNubs(e, 2);
    });
    // impact squish (flat against the wall) then spring back with a head-shake
    await ctx.tween(DUR.blocked / ctx.spd, easeOutBack, (e) => {
      g.position.x = from.x + dir.x * 0.2 * (1 - e);
      g.position.z = from.z + dir.z * 0.2 * (1 - e);
      g.rotation.y = base + Math.sin(e * 26) * 0.1 * (1 - e);
      const sq = 1 - 0.14 * Math.cos((e * Math.PI) / 2); // max squish at impact
      rig.scale.set(1 / Math.sqrt(sq), sq, 1 / Math.sqrt(sq));
    });
    g.position.set(from.x, 0, from.z);
    g.rotation.y = base;
    rig.scale.set(1, 1, 1);
    this._restNubs();
    this._setFace(this._mood);
  }

  // Float up and over, back to the start.
  async returnHome(from, to, a0, a1, ctx) {
    const g = this.group;
    const rig = this.rig;
    const dist = Math.hypot(to.x - from.x, to.z - from.z);
    const dur = Math.min(950, 420 + dist * 95) / ctx.spd;
    await ctx.tween(dur, easeInOutCubic, (e) => {
      g.position.x = lerp(from.x, to.x, e);
      g.position.z = lerp(from.z, to.z, e);
      g.position.y = Math.sin(Math.PI * e) * 0.75;
      g.rotation.y = lerpAngle(a0, a1, e);
      const s = 1 + 0.1 * Math.sin(Math.PI * e);
      rig.scale.set(1 / Math.sqrt(s), s, 1 / Math.sqrt(s));
    });
    g.position.set(to.x, 0, to.z);
    g.position.y = 0;
    g.rotation.y = a1;
    rig.scale.set(1, 1, 1);
  }

  async react(kind, ctx) {
    const g = this.group;
    if (kind === "cheer") {
      // a real jump-to-grab: crouch, spring up tall, land. Timed so the apex
      // meets the gem the Viewer floats over his head.
      this._setFace("happy");
      const rig = this.rig;
      await ctx.tween(DUR.collect / ctx.spd, (t) => t, (e) => {
        let y, sy;
        if (e < 0.2) {
          const k = e / 0.2; // anticipation: crouch + squash
          y = -0.07 * k;
          sy = 1 - 0.14 * k;
        } else {
          const k = (e - 0.2) / 0.8; // spring into an arc, then land
          const arc = Math.sin(k * Math.PI);
          y = arc * 0.5 - 0.07 * (1 - k);
          sy = 1 + arc * 0.16; // stretch tall at the peak
        }
        g.position.y = y;
        rig.scale.set(1 / Math.sqrt(sy), sy, 1 / Math.sqrt(sy));
        rig.rotation.y = Math.sin(e * Math.PI) * 0.15; // small reach
      });
      g.position.y = 0;
      rig.scale.set(1, 1, 1);
      rig.rotation.y = 0;
    } else if (kind === "confused") {
      this._setFace("surprised");
      const base = g.rotation.y;
      await ctx.tween(DUR.collect / ctx.spd, easeInOutCubic, (e) => {
        g.rotation.y = base + Math.sin(e * Math.PI * 3) * 0.12; // "huh?" head-shake
      });
      g.rotation.y = base;
    } else if (kind === "win") {
      // victory dance: three joyful bounces while spinning a full turn
      this._setFace("happy");
      const rig = this.rig;
      const base = g.rotation.y;
      await ctx.tween(1500 / ctx.spd, (t) => t, (e) => {
        const bounce = Math.abs(Math.sin(e * Math.PI * 3));
        g.position.y = bounce * 0.4;
        g.rotation.y = base + e * Math.PI * 2; // a full 360 spin
        const s = 1 + bounce * 0.18; // stretch at each peak
        rig.scale.set(1 / Math.sqrt(s), s, 1 / Math.sqrt(s));
        rig.rotation.z = Math.sin(e * Math.PI * 6) * 0.1; // wiggle
      });
      g.position.y = 0;
      g.rotation.y = base;
      rig.scale.set(1, 1, 1);
      rig.rotation.set(0, 0, 0);
    } else if (kind === "die") {
      // stepped into lava: a panicked flail, sink, and vanish
      this._setFace("surprised");
      const rig = this.rig;
      await ctx.tween(650 / ctx.spd, (t) => t, (e) => {
        g.position.y = -0.78 * e * e; // accelerating sink
        const s = 1 - 0.5 * e;
        rig.scale.set(s, s, s);
        rig.rotation.y = Math.sin(e * Math.PI * 6) * 0.4 * (1 - e);
      });
      g.visible = false;
      return; // gone -- don't restore the mood
    }
    this._setFace(this._mood); // back to baseline
  }

  setExpression(name) {
    this._mood = name;
    this._setFace(name);
  }

  update(t, dt, playing) {
    // ambient: the sprout sways gently
    this.sprout.rotation.z = Math.sin(t * 1.6) * 0.09;
    this.sprout.rotation.x = -0.12 + Math.sin(t * 1.1) * 0.03;
    // idle bob + breathing while not actively playing
    if (!playing) {
      this.group.position.y = Math.abs(Math.sin(t * 1.6)) * 0.05;
      this.rig.scale.set(1, 1 + Math.sin(t * 1.6) * 0.02, 1);
    }
    // occasional blink
    if (t > this._blinkAt) {
      this._blinkAt = t + 2.6 + (Math.floor(t) % 3);
      this._blinkUntil = t + 0.13;
    }
    this._applyEyes(dt, t < this._blinkUntil ? 1 : 0);
  }

  // ------------------------------------------------------------------ internals
  _setFace(name) {
    this._exprTarget = EXPR[name] || EXPR.neutral;
  }

  _applyEyes(dt, blink) {
    const tgt = this._exprTarget;
    const cur = this._expr;
    const k = 1 - Math.exp(-dt * 16); // smooth but snappy
    for (const p of ["open", "wide", "innerTilt", "lift"]) {
      cur[p] += (tgt[p] - cur[p]) * k;
    }
    const b = this._eyeBase;
    const openY = Math.max(0.04, cur.open * (1 - blink * 0.94));
    for (const e of this.eyes) {
      e.mesh.scale.set(b.sx * cur.wide, b.sy * cur.wide * openY, b.sz);
      e.mesh.position.y = b.y + cur.lift;
      e.mesh.rotation.z = cur.innerTilt * (e.sign < 0 ? 1 : -1);
      e.spark.position.y = b.y + cur.lift + 0.03;
      e.spark.visible = cur.open * (1 - blink) > 0.32;
    }
  }

  _walkNubs(e, cycles) {
    for (const n of this.nubs) {
      const v = Math.sin((e * cycles + n.userData.phase) * Math.PI * 2);
      n.position.y = n.userData.baseY + Math.max(0, v) * 0.045;
    }
  }

  _restNubs() {
    for (const n of this.nubs) n.position.y = n.userData.baseY;
  }

  // ------------------------------------------------------------------ geometry
  _buildBody() {
    const body = new THREE.Mesh(
      new THREE.SphereGeometry(0.36, 32, 26),
      new THREE.MeshStandardMaterial({ color: COLORS.moss, roughness: 0.82, metalness: 0.0 })
    );
    body.scale.set(1.12, 0.94, 1.06);
    body.position.y = 0.35;
    body.castShadow = true;
    body.receiveShadow = true;
    this.rig.add(body);
  }

  _buildNubs() {
    const nubGeo = new THREE.SphereGeometry(0.075, 14, 12);
    const nubMat = new THREE.MeshStandardMaterial({ color: COLORS.mossDark, roughness: 0.88 });
    this.nubs = [];
    const nubCount = 8;
    for (let i = 0; i < nubCount; i++) {
      const a = (i / nubCount) * Math.PI * 2 + Math.PI / nubCount;
      const nub = new THREE.Mesh(nubGeo, nubMat);
      nub.scale.set(1, 0.78, 1);
      const baseY = 0.055;
      nub.position.set(Math.sin(a) * 0.32, baseY, Math.cos(a) * 0.3);
      nub.castShadow = true;
      nub.userData = { baseY, phase: i / nubCount };
      this.rig.add(nub);
      this.nubs.push(nub);
    }
  }

  _buildEyes() {
    const eyeGeo = new THREE.SphereGeometry(0.07, 18, 14);
    const eyeMat = new THREE.MeshStandardMaterial({ color: COLORS.eyeDark, roughness: 0.35 });
    const sparkGeo = new THREE.SphereGeometry(0.018, 8, 8);
    const sparkMat = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      emissive: 0xffffff,
      emissiveIntensity: 0.45,
      roughness: 0.2,
    });
    this._eyeBase = { sx: 0.9, sy: 1.15, sz: 0.55, x: 0.135, y: 0.32, z: -0.38 };
    this.eyes = [];
    for (const s of [-1, 1]) {
      const eye = new THREE.Mesh(eyeGeo, eyeMat);
      eye.scale.set(this._eyeBase.sx, this._eyeBase.sy, this._eyeBase.sz);
      eye.position.set(this._eyeBase.x * s, this._eyeBase.y, this._eyeBase.z);
      this.rig.add(eye);
      const spark = new THREE.Mesh(sparkGeo, sparkMat); // catchlight
      spark.position.set(this._eyeBase.x * s + 0.022, this._eyeBase.y + 0.03, this._eyeBase.z - 0.05);
      this.rig.add(spark);
      this.eyes.push({ mesh: eye, spark, sign: s });
    }
  }

  _buildSprout() {
    const sprout = new THREE.Group();
    const stem = new THREE.Mesh(
      new THREE.CylinderGeometry(0.022, 0.032, 0.2, 8),
      new THREE.MeshStandardMaterial({ color: COLORS.stem, roughness: 0.6 })
    );
    stem.position.y = 0.1;
    stem.castShadow = true;
    sprout.add(stem);

    const bud = new THREE.Mesh(
      new THREE.SphereGeometry(0.06, 16, 12),
      new THREE.MeshStandardMaterial({ color: COLORS.bud, roughness: 0.55 })
    );
    bud.scale.set(0.8, 1.4, 0.8);
    bud.position.y = 0.25;
    bud.castShadow = true;
    sprout.add(bud);

    const leafMat = new THREE.MeshStandardMaterial({ color: COLORS.leaf, roughness: 0.55 });
    const leaf1 = new THREE.Mesh(new THREE.SphereGeometry(0.07, 16, 12), leafMat);
    leaf1.scale.set(1.55, 0.2, 0.85);
    leaf1.position.set(0.085, 0.15, 0);
    leaf1.rotation.z = -0.75;
    leaf1.castShadow = true;
    sprout.add(leaf1);

    const leaf2 = new THREE.Mesh(new THREE.SphereGeometry(0.052, 16, 12), leafMat);
    leaf2.scale.set(1.45, 0.2, 0.82);
    leaf2.position.set(-0.07, 0.11, 0.015);
    leaf2.rotation.z = 0.85;
    sprout.add(leaf2);

    sprout.position.set(0.0, 0.66, 0.05);
    sprout.rotation.x = -0.12;
    this.sprout = sprout;
    this.rig.add(sprout);
  }
}
