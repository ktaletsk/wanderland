// Low-poly geometry for the world's objects: walls and the colored, typed
// things that live on a tile -- keys, balls, boxes and doors. Each builder
// returns a THREE.Group; doors/boxes stash animation handles on `userData` so
// the Viewer can swing or open them.

import * as THREE from "three";

// Object colours.
export const OBJ_COLORS = {
  red: 0xe2564c,
  green: 0x4cbf5a,
  blue: 0x4a8bdf,
  purple: 0xa55fd6,
  yellow: 0xf0c64a,
  grey: 0x9aa3ab,
};

export function objColor(name) {
  return OBJ_COLORS[name] ?? 0xcccccc;
}

export function buildWall(colors = {}) {
  const g = new THREE.Group();
  const stone = new THREE.MeshStandardMaterial({ color: colors.stone ?? 0x8b94a0, roughness: 0.95, flatShading: true });
  const light = new THREE.MeshStandardMaterial({ color: colors.stoneLight ?? 0xa9b2bd, roughness: 0.95, flatShading: true });
  stone.userData.themeRole = "stone";
  light.userData.themeRole = "stoneLight";
  const block = new THREE.Mesh(new THREE.BoxGeometry(0.94, 0.7, 0.94), stone);
  block.position.y = 0.35;
  block.castShadow = true;
  block.receiveShadow = true;
  g.add(block);
  // a couple of offset capstones for low-poly texture. They protrude above the
  // block top (0.7) -- never coplanar with it, which would z-fight.
  for (const [x, z, s] of [[0.18, -0.12, 0.4], [-0.16, 0.15, 0.3]]) {
    const cap = new THREE.Mesh(new THREE.BoxGeometry(s, 0.16, s), light);
    cap.position.set(x, 0.7, z); // bottom embedded at 0.62, top at 0.78
    cap.castShadow = true;
    g.add(cap);
  }
  return g;
}

export function buildKey(color) {
  const g = new THREE.Group();
  const mat = new THREE.MeshStandardMaterial({ color, roughness: 0.3, metalness: 0.65 });
  const bow = new THREE.Mesh(new THREE.TorusGeometry(0.07, 0.022, 10, 18), mat);
  bow.position.y = 0.11;
  const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.018, 0.2, 8), mat);
  shaft.position.y = -0.02;
  const tooth1 = new THREE.Mesh(new THREE.BoxGeometry(0.055, 0.03, 0.022), mat);
  tooth1.position.set(0.035, -0.1, 0);
  const tooth2 = new THREE.Mesh(new THREE.BoxGeometry(0.035, 0.03, 0.022), mat);
  tooth2.position.set(0.025, -0.055, 0);
  g.add(bow, shaft, tooth1, tooth2);
  g.children.forEach((m) => (m.castShadow = true));
  g.userData.float = true; // bobs + spins like a collectible
  return g;
}

export function buildBall(color) {
  const g = new THREE.Group();
  const ball = new THREE.Mesh(
    new THREE.SphereGeometry(0.18, 22, 16),
    new THREE.MeshStandardMaterial({ color, roughness: 0.5 })
  );
  ball.position.y = 0.19;
  ball.castShadow = true;
  ball.receiveShadow = true;
  g.add(ball);
  return g;
}

export function buildBox(color) {
  const g = new THREE.Group();
  const mat = new THREE.MeshStandardMaterial({ color, roughness: 0.6 });
  const body = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.28, 0.34), mat);
  body.position.y = 0.17;
  body.castShadow = true;
  g.add(body);
  const lid = new THREE.Mesh(
    new THREE.BoxGeometry(0.38, 0.07, 0.38),
    new THREE.MeshStandardMaterial({ color, roughness: 0.45, metalness: 0.1 })
  );
  lid.position.y = 0.33;
  lid.castShadow = true;
  g.add(lid);
  g.userData.lid = lid;
  return g;
}

// orientation: 'z' (panel spans north-south, blocks E-W travel) or 'x'.
export function buildDoor(color, state, orientation = "z", colors = {}) {
  const g = new THREE.Group();
  const frameMat = new THREE.MeshStandardMaterial({ color: colors.doorFrame ?? 0x6b7480, roughness: 0.9, flatShading: true });
  frameMat.userData.themeRole = "doorFrame";
  const doorMat = new THREE.MeshStandardMaterial({ color, roughness: 0.5 });
  const along = orientation === "x" ? "x" : "z";

  // two frame posts at the ends of the wall line
  for (const s of [-1, 1]) {
    const post = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.74, 0.12), frameMat);
    if (along === "z") post.position.set(0, 0.37, s * 0.43);
    else post.position.set(s * 0.43, 0.37, 0);
    post.castShadow = true;
    g.add(post);
  }

  // a hinge at one post; the panel hangs off it so it can swing open
  const hinge = new THREE.Group();
  if (along === "z") hinge.position.set(0, 0, -0.43);
  else hinge.position.set(-0.43, 0, 0);
  const len = 0.86;
  const panel = new THREE.Mesh(
    along === "z" ? new THREE.BoxGeometry(0.1, 0.6, len) : new THREE.BoxGeometry(len, 0.6, 0.1),
    doorMat
  );
  if (along === "z") panel.position.set(0, 0.32, len / 2);
  else panel.position.set(len / 2, 0.32, 0);
  panel.castShadow = true;
  hinge.add(panel);

  // lock plate for a locked door (a little brass box on the panel)
  let lock = null;
  if (state === "locked") {
    lock = new THREE.Mesh(
      new THREE.BoxGeometry(0.1, 0.12, 0.06),
      new THREE.MeshStandardMaterial({ color: 0xd9b34a, roughness: 0.35, metalness: 0.7 })
    );
    if (along === "z") lock.position.set(0.07, 0.32, len * 0.5);
    else lock.position.set(len * 0.5, 0.32, 0.07);
    hinge.add(lock);
  }
  g.add(hinge);

  g.userData = { hinge, panel, lock, orientation: along, openAngle: along === "z" ? Math.PI / 2 : -Math.PI / 2 };
  if (state === "open") hinge.rotation.y = g.userData.openAngle;
  return g;
}

// Dispatch by object dict ({type, color, state}). `orientation` only used by doors.
export function buildObject(obj, orientation, colors = {}) {
  const color = objColor(obj.color);
  switch (obj.type) {
    case "key":
      return buildKey(color);
    case "ball":
      return buildBall(color);
    case "box":
      return buildBox(color);
    case "door":
      return buildDoor(color, obj.state, orientation, colors);
    default:
      return new THREE.Group();
  }
}
