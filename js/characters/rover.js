// Rover -- a second character that proves the contract generalizes. A hovering
// drone-bot: it banks and tilts instead of waddling, has no face-squash, and
// expresses itself through a single glowing LED eye (colour + size) rather than
// eyelids. Same Character contract, completely different anatomy and motion.

import * as THREE from "three";
import { Character } from "./character.js";
import { DUR } from "../palette.js";
import { easeInOutCubic, easeOutCubic, easeOutBack, lerp, lerpAngle } from "../easing.js";

const HOVER = 0.18; // resting height of the hull above the tile

// LED-eye expression targets: colour, relative size, glow strength.
const FACE = {
  neutral: { color: 0x37d0ff, scale: 1.0, glow: 0.85 },
  happy: { color: 0x49e06b, scale: 1.08, glow: 1.3 },
  surprised: { color: 0xffd23d, scale: 1.55, glow: 1.5 },
  determined: { color: 0xff7a3d, scale: 0.72, glow: 1.05 },
};

export class RoverCharacter extends Character {
  constructor() {
    super();
    this.hull = new THREE.Group(); // hover + tilt + bank + bob live here
    this.hull.position.y = HOVER;
    this.group.add(this.hull);

    this._eye = { color: new THREE.Color(FACE.neutral.color), scale: 1, glow: 0.85 };
    this._eyeTarget = { color: new THREE.Color(FACE.neutral.color), scale: 1, glow: 0.85 };

    this._build();
  }

  // ---------------------------------------------------------------- contract
  placeAt(pos, heading) {
    super.placeAt(pos, heading);
    this.hull.position.set(0, HOVER, 0);
    this.hull.rotation.set(0, 0, 0);
  }

  async move(from, to, ctx) {
    const g = this.group;
    const hull = this.hull;
    await ctx.tween(DUR.move / ctx.spd, easeInOutCubic, (e) => {
      g.position.x = lerp(from.x, to.x, e);
      g.position.z = lerp(from.z, to.z, e);
      // accelerate-dip then decelerate-rise: nose pitches into the travel
      hull.rotation.x = -Math.sin(e * Math.PI) * 0.22;
      hull.position.y = HOVER + Math.sin(e * Math.PI * 2) * 0.04;
      this._spinRotors(e * 6);
    });
    g.position.set(to.x, 0, to.z);
    hull.rotation.x = 0;
    hull.position.y = HOVER;
  }

  async turn(a0, a1, ctx) {
    const g = this.group;
    const hull = this.hull;
    const dir = Math.sign(lerpAngle(a0, a1, 1) - a0) || 1;
    await ctx.tween(DUR.turn / ctx.spd, easeInOutCubic, (e) => {
      g.rotation.y = lerpAngle(a0, a1, e);
      hull.rotation.z = -dir * Math.sin(Math.PI * e) * 0.28; // bank into the turn
      this._spinRotors(e * 5);
    });
    g.rotation.y = a1;
    hull.rotation.z = 0;
  }

  // Blocked: thrust at the edge, jam to a halt, bounce back -- eye flashes alarm.
  async blocked(from, dir, ctx) {
    const g = this.group;
    const hull = this.hull;
    const h = g.rotation.y;
    const facing = dir.x * -Math.sin(h) + dir.z * -Math.cos(h);
    const pitch = facing >= 0 ? -1 : 1;
    this._setFace("surprised");
    // 1) thrust out toward the edge, nose down
    await ctx.tween(300 / ctx.spd, easeOutCubic, (e) => {
      g.position.x = from.x + dir.x * 0.3 * e;
      g.position.z = from.z + dir.z * 0.3 * e;
      hull.rotation.x = pitch * 0.3 * e;
      hull.position.y = HOVER + 0.05 * e;
    });
    // 2) recoil hard and shimmy back onto the tile
    await ctx.tween(DUR.blocked / ctx.spd, easeOutBack, (e) => {
      g.position.x = from.x + dir.x * 0.3 * (1 - e);
      g.position.z = from.z + dir.z * 0.3 * (1 - e);
      hull.rotation.x = pitch * 0.3 * (1 - e);
      hull.rotation.z = Math.sin(e * Math.PI * 4) * 0.12 * (1 - e); // shake
      hull.position.y = HOVER + 0.05 * (1 - e);
    });
    g.position.set(from.x, 0, from.z);
    hull.rotation.set(0, 0, 0);
    hull.position.y = HOVER;
    this._setFace(this._mood);
  }

  async returnHome(from, to, a0, a1, ctx) {
    const g = this.group;
    const hull = this.hull;
    const dist = Math.hypot(to.x - from.x, to.z - from.z);
    const dur = Math.min(950, 420 + dist * 95) / ctx.spd;
    await ctx.tween(dur, easeInOutCubic, (e) => {
      g.position.x = lerp(from.x, to.x, e);
      g.position.z = lerp(from.z, to.z, e);
      g.rotation.y = lerpAngle(a0, a1, e);
      hull.position.y = HOVER + Math.sin(Math.PI * e) * 0.55; // lift and cruise
      hull.rotation.x = -Math.sin(Math.PI * e) * 0.12;
      this._spinRotors(e * 10);
    });
    g.position.set(to.x, 0, to.z);
    g.rotation.y = a1;
    hull.position.y = HOVER;
    hull.rotation.x = 0;
  }

  async react(kind, ctx) {
    const hull = this.hull;
    if (kind === "cheer") {
      this._setFace("happy");
      const base = this.group.rotation.y;
      await ctx.tween(DUR.collect / ctx.spd, easeOutBack, (e) => {
        this.group.rotation.y = base + e * Math.PI * 2; // celebratory 360 spin
        hull.position.y = HOVER + Math.sin(Math.PI * e) * 0.32; // pop up
        this._spinRotors(e * 14);
      });
      this.group.rotation.y = base;
      hull.position.y = HOVER;
    } else if (kind === "confused") {
      this._setFace("surprised");
      await ctx.tween(DUR.collect / ctx.spd, easeInOutCubic, (e) => {
        hull.rotation.z = Math.sin(e * Math.PI * 3) * 0.18; // scan side to side
      });
      hull.rotation.z = 0;
    } else if (kind === "win") {
      // victory: lift off, two fast barrel spins, rotors roaring, LED green
      this._setFace("happy");
      const base = this.group.rotation.y;
      await ctx.tween(1500 / ctx.spd, (t) => t, (e) => {
        this.group.rotation.y = base + e * Math.PI * 4; // two spins
        hull.position.y = HOVER + Math.abs(Math.sin(e * Math.PI * 2)) * 0.42; // hop up high
        hull.rotation.z = Math.sin(e * Math.PI * 6) * 0.12;
        this._spinRotors(e * 30);
      });
      this.group.rotation.y = base;
      hull.position.y = HOVER;
      hull.rotation.z = 0;
    } else if (kind === "die") {
      // stepped into lava: stall, drop, and vanish
      this._setFace("surprised");
      await ctx.tween(650 / ctx.spd, (t) => t, (e) => {
        hull.position.y = HOVER - e * e * 0.95;
        hull.rotation.z = Math.sin(e * Math.PI * 7) * 0.5 * (1 - e);
        this._spinRotors(e * 40);
      });
      this.group.visible = false;
      return;
    }
    this._setFace(this._mood);
  }

  setExpression(name) {
    this._mood = name;
    this._setFace(name);
  }

  update(t, dt, playing) {
    // constant rotor idle + a gentle hover bob when resting
    this._spinRotors(t * 4);
    if (!playing) {
      this.hull.position.y = HOVER + Math.sin(t * 2.2) * 0.03;
      this.hull.rotation.z = Math.sin(t * 1.3) * 0.02;
    }
    // ease the LED eye toward its expression
    const k = 1 - Math.exp(-dt * 12);
    this._eye.color.lerp(this._eyeTarget.color, k);
    this._eye.scale += (this._eyeTarget.scale - this._eye.scale) * k;
    this._eye.glow += (this._eyeTarget.glow - this._eye.glow) * k;
    const pulse = 1 + Math.sin(t * 4) * 0.08;
    this.eyeMat.color.copy(this._eye.color);
    this.eyeMat.emissive.copy(this._eye.color);
    this.eyeMat.emissiveIntensity = this._eye.glow * pulse;
    this.eye.scale.set(this._eye.scale, this._eye.scale, 1);
  }

  // ------------------------------------------------------------------ internals
  _setFace(name) {
    const f = FACE[name] || FACE.neutral;
    this._eyeTarget.color.set(f.color);
    this._eyeTarget.scale = f.scale;
    this._eyeTarget.glow = f.glow;
  }

  _spinRotors(a) {
    if (this.rotors) for (const r of this.rotors) r.rotation.y = a;
  }

  // ------------------------------------------------------------------ geometry
  _build() {
    const shell = new THREE.MeshStandardMaterial({ color: 0xc3d2df, roughness: 0.42, metalness: 0.55 });
    const dark = new THREE.MeshStandardMaterial({ color: 0x44525f, roughness: 0.5, metalness: 0.55 });

    // chassis: a smooth rounded body
    const body = new THREE.Mesh(new THREE.SphereGeometry(0.3, 28, 22), shell);
    body.scale.set(1.18, 0.66, 0.98);
    body.position.y = 0.36;
    body.castShadow = true;
    body.receiveShadow = true;
    this.hull.add(body);

    // a little sensor dome on top
    const dome = new THREE.Mesh(new THREE.SphereGeometry(0.15, 20, 14), shell);
    dome.scale.set(1, 0.8, 1);
    dome.position.y = 0.52;
    dome.castShadow = true;
    this.hull.add(dome);

    // the LED eye -- a glowing disc on the front, tilted up to face the camera
    this.eyeMat = new THREE.MeshStandardMaterial({
      color: FACE.neutral.color,
      emissive: FACE.neutral.color,
      emissiveIntensity: 0.85,
      roughness: 0.2,
    });
    const eyeRing = new THREE.Mesh(new THREE.TorusGeometry(0.12, 0.028, 12, 24), dark);
    eyeRing.position.set(0, 0.4, -0.3);
    eyeRing.rotation.x = -0.32;
    this.hull.add(eyeRing);
    this.eye = new THREE.Mesh(new THREE.CircleGeometry(0.11, 24), this.eyeMat);
    this.eye.position.set(0, 0.4, -0.31);
    this.eye.rotation.x = -0.32;
    this.hull.add(this.eye);

    // four rotor discs on stubby arms (translucent blur, like spinning props)
    this.rotors = [];
    const armMat = dark;
    const propMat = new THREE.MeshStandardMaterial({
      color: 0xeaf1f7, roughness: 0.4, metalness: 0.2, transparent: true, opacity: 0.5, side: THREE.DoubleSide,
    });
    for (const [sx, sz] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) {
      const arm = new THREE.Mesh(new THREE.CylinderGeometry(0.022, 0.022, 0.18, 8), armMat);
      arm.rotation.z = Math.PI / 2;
      arm.position.set(sx * 0.3, 0.34, sz * 0.26);
      arm.rotation.y = Math.atan2(sx, sz);
      this.hull.add(arm);
      const hub = new THREE.Group();
      hub.position.set(sx * 0.42, 0.4, sz * 0.36);
      const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.04, 10), dark);
      hub.add(cap);
      const disc = new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.13, 0.008, 18), propMat);
      disc.position.y = 0.03;
      hub.add(disc);
      this.hull.add(hub);
      this.rotors.push(hub);
    }

    // a small skid underneath so it reads as hovering + casts a tidy shadow
    const skid = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.025, 0.42), dark);
    skid.position.y = 0.16;
    skid.castShadow = true;
    this.hull.add(skid);
  }
}
