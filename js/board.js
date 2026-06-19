// The world: low-poly grass/dirt tiles, water, walls, the typed/colored objects
// (gems, keys, balls, boxes, doors) and the goal ring -- all built from a puzzle.

import * as THREE from "three";
import { COLORS, TILE } from "./palette.js";
import { buildObject, buildWall } from "./objects.js";

function disposeObject(root) {
  root.traverse((child) => {
    if (child.geometry) child.geometry.dispose();
    if (child.material) {
      const mats = Array.isArray(child.material) ? child.material : [child.material];
      mats.forEach((m) => m.dispose());
    }
  });
}

export class Board {
  constructor(puzzle) {
    this.puzzle = puzzle;
    this.offset = { x: (puzzle.cols - 1) / 2, z: (puzzle.rows - 1) / 2 };
    this.group = new THREE.Group();
    this.gems = new Map(); // "col,row" -> { mesh, mat, base, collected }
    this.objects = new Map(); // "col,row" -> { type, color, group, base, float?, hinge?, lock?, lid? }
    this.goalRing = null;
    this._wallSet = new Set((puzzle.walls || []).map(([c, r]) => `${c},${r}`));
    this._build();
  }

  worldPos(col, row) {
    return new THREE.Vector3((col - this.offset.x) * TILE, 0, (row - this.offset.z) * TILE);
  }

  _build() {
    const p = this.puzzle;
    const gapSet = new Set((p.gaps || []).map(([c, r]) => `${c},${r}`));

    const grassMat = new THREE.MeshStandardMaterial({ color: COLORS.grass, roughness: 0.95, flatShading: true });
    const dirtMat = new THREE.MeshStandardMaterial({ color: COLORS.dirt, roughness: 1.0, flatShading: true });

    for (let r = 0; r < p.rows; r++) {
      for (let c = 0; c < p.cols; c++) {
        if (gapSet.has(`${c},${r}`)) continue;
        const pos = this.worldPos(c, r);
        const grass = new THREE.Mesh(new THREE.BoxGeometry(0.96, 0.2, 0.96), grassMat);
        grass.position.set(pos.x, -0.1, pos.z);
        grass.receiveShadow = true;
        grass.castShadow = true;
        this.group.add(grass);
        const dirt = new THREE.Mesh(new THREE.BoxGeometry(0.86, 0.55, 0.86), dirtMat);
        dirt.position.set(pos.x, -0.47, pos.z);
        dirt.receiveShadow = true;
        this.group.add(dirt);
      }
    }

    // water plane below
    const water = new THREE.Mesh(
      new THREE.PlaneGeometry(p.cols + 6, p.rows + 6),
      new THREE.MeshStandardMaterial({ color: COLORS.water, roughness: 0.4, metalness: 0.1, transparent: true, opacity: 0.92 })
    );
    water.rotation.x = -Math.PI / 2;
    water.position.y = -0.62;
    water.receiveShadow = true;
    this.group.add(water);

    // walls (stone blocks standing on the tiles)
    for (const [c, r] of p.walls || []) {
      const wall = buildWall();
      const pos = this.worldPos(c, r);
      wall.position.set(pos.x, 0, pos.z);
      this.group.add(wall);
    }

    // gems (the collectibles; kept in their own map for the collect animation)
    const gemGeo = new THREE.OctahedronGeometry(0.2, 0);
    for (const [c, r] of p.gems) {
      const mat = new THREE.MeshStandardMaterial({
        color: COLORS.gem, emissive: COLORS.gemEmissive, emissiveIntensity: 0.55,
        roughness: 0.15, metalness: 0.1, transparent: true, opacity: 1, flatShading: true,
      });
      const mesh = new THREE.Mesh(gemGeo, mat);
      const pos = this.worldPos(c, r);
      mesh.position.set(pos.x, 0.5, pos.z);
      mesh.castShadow = true;
      this.group.add(mesh);
      this.gems.set(`${c},${r}`, { mesh, mat, base: pos.clone(), collected: false });
    }

    // goal marker
    if (p.goal) {
      const [gc, gr] = p.goal;
      const pos = this.worldPos(gc, gr);
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(0.34, 0.05, 12, 28),
        new THREE.MeshStandardMaterial({ color: COLORS.goal, emissive: COLORS.goal, emissiveIntensity: 0.5, roughness: 0.4 })
      );
      ring.rotation.x = -Math.PI / 2;
      ring.position.set(pos.x, 0.06, pos.z);
      this.group.add(ring);
      this.goalRing = ring;
    }

    this._buildObjects();
  }

  _doorOrientation(c, r) {
    // a door in a vertical wall line (walls N/S of it) spans north-south ('z')
    const vertical = this._wallSet.has(`${c},${r - 1}`) || this._wallSet.has(`${c},${r + 1}`);
    return vertical ? "z" : "x";
  }

  _addObject(c, r, obj) {
    const orientation = obj.type === "door" ? this._doorOrientation(c, r) : "z";
    const group = buildObject(obj, orientation);
    const pos = this.worldPos(c, r);
    group.position.set(pos.x, 0, pos.z);
    this.group.add(group);
    this.objects.set(`${c},${r}`, {
      type: obj.type,
      color: obj.color,
      group,
      base: pos.clone(),
      float: !!group.userData.float,
      hinge: group.userData.hinge || null,
      lock: group.userData.lock || null,
      lid: group.userData.lid || null,
    });
  }

  _buildObjects() {
    const objs = this.puzzle.objects || {};
    for (const key of Object.keys(objs)) {
      const obj = objs[key];
      if (obj.type === "gem") continue; // gems handled above
      const [c, r] = key.split(",").map(Number);
      this._addObject(c, r, obj);
    }
  }

  // Swap the object on a cell (used when a box is opened -> its contents, or null).
  replaceObject(c, r, obj) {
    const key = `${c},${r}`;
    const old = this.objects.get(key);
    if (old) {
      this.group.remove(old.group);
      disposeObject(old.group);
      this.objects.delete(key);
    }
    if (obj) this._addObject(c, r, obj);
    return this.objects.get(key) || null;
  }

  // Restore every gem to its uncollected state.
  resetGems() {
    for (const gem of this.gems.values()) {
      gem.mesh.visible = true;
      gem.mesh.scale.set(1, 1, 1);
      gem.mat.opacity = 1;
      gem.collected = false;
    }
  }

  // Remove + dispose a group that was detached from the objects map (e.g. an
  // item that was being carried, so resetObjects() can't see it).
  disposeDetached(group) {
    this.group.remove(group);
    disposeObject(group);
  }

  // Rebuild all objects to their initial state (after pickups/drops/toggles).
  resetObjects() {
    for (const e of this.objects.values()) {
      this.group.remove(e.group);
      disposeObject(e.group);
    }
    this.objects.clear();
    this._buildObjects();
  }

  // Per-frame idle motion: gems + keys float/spin, the goal ring rotates. The gem
  // on the character's cell (`occupied` = "col,row") rises above his head.
  tick(t, occupied = null) {
    for (const [key, gem] of this.gems) {
      if (gem.collected || !gem.mesh.visible) continue;
      gem.mesh.rotation.y = t * 1.2;
      const restY = key === occupied ? 1.32 : 0.5;
      const targetY = gem.base.y + restY + Math.sin(t * 2 + gem.base.x) * 0.06;
      gem.mesh.position.y += (targetY - gem.mesh.position.y) * 0.18;
    }
    for (const e of this.objects.values()) {
      if (!e.float || !e.group.visible || e.carried) continue;
      e.group.rotation.y = t * 1.1;
      e.group.position.y = 0.28 + Math.sin(t * 2 + e.base.x) * 0.05;
    }
    if (this.goalRing) this.goalRing.rotation.z = t * 0.6;
  }

  dispose() {
    disposeObject(this.group);
  }
}
