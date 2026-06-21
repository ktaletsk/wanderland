// Renderer, scene, lighting, camera and orbit controls -- the "stage" Mo and
// the board are placed on.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { colorsForTheme, TILE } from "./palette.js";

export function createStage(el, theme = "light") {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  el.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0xffffff, 14, 34);

  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
  camera.position.set(6, 7, 8);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.enablePan = false;
  controls.minDistance = 4;
  controls.maxDistance = 22;
  controls.minPolarAngle = 0.25;
  controls.maxPolarAngle = Math.PI / 2.15;
  controls.target.set(0, 0, 0);

  const lights = addLights(scene);
  const stars = buildStars();
  scene.add(stars);
  const stage = { renderer, scene, camera, controls, lights, stars };
  setStageTheme(stage, theme);

  return stage;
}

function addLights(scene) {
  const hemi = new THREE.HemisphereLight(0xffffff, 0xffffff, 0.95);
  scene.add(hemi);

  const sun = new THREE.DirectionalLight(0xffffff, 1.5);
  sun.position.set(5, 9, 4);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  sun.shadow.bias = -0.0004;
  sun.shadow.normalBias = 0.02;
  const s = 9;
  sun.shadow.camera.left = -s;
  sun.shadow.camera.right = s;
  sun.shadow.camera.top = s;
  sun.shadow.camera.bottom = -s;
  sun.shadow.camera.near = 1;
  sun.shadow.camera.far = 30;
  scene.add(sun);

  const ambient = new THREE.AmbientLight(0xffffff, 0.25);
  scene.add(ambient);

  return { hemi, sun, ambient };
}

function seededRandom(seed) {
  const x = Math.sin(seed * 12.9898) * 43758.5453;
  return x - Math.floor(x);
}

function buildStars() {
  const count = 560;
  const positions = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    // A world-space star sphere centered on the board, so stars orbit with the
    // scene instead of staying pinned to the screen. It extends below the tile
    // plane because the camera usually looks down into the lower sky.
    const azimuth = seededRandom(i + 1) * Math.PI * 2;
    const u = seededRandom(i + 101);
    const elevation = -0.95 + Math.pow(u, 0.86) * 2.18;
    const radius = 28 + seededRandom(i + 201) * 18;
    const ground = Math.cos(elevation) * radius;
    positions[i * 3] = Math.cos(azimuth) * ground;
    positions[i * 3 + 1] = Math.sin(elevation) * radius;
    positions[i * 3 + 2] = Math.sin(azimuth) * ground;
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const mat = new THREE.PointsMaterial({
    color: 0xf4fbff,
    size: 2.1,
    sizeAttenuation: false,
    transparent: true,
    opacity: 0.9,
    depthTest: true,
    depthWrite: false,
    fog: false,
  });
  const stars = new THREE.Points(geo, mat);
  stars.renderOrder = -1;
  stars.frustumCulled = false;
  return stars;
}

export function setStageTheme(stage, theme) {
  const colors = colorsForTheme(theme);
  stage.renderer.toneMappingExposure = colors.exposure;
  stage.scene.background = new THREE.Color(colors.sky);
  stage.scene.fog.color.set(colors.fog);
  stage.lights.hemi.color.set(colors.hemiSky);
  stage.lights.hemi.groundColor.set(colors.hemiGround);
  stage.lights.sun.color.set(colors.sun);
  stage.lights.sun.intensity = colors.sunIntensity;
  stage.lights.ambient.color.set(colors.ambient);
  stage.lights.ambient.intensity = colors.ambientIntensity;
  stage.stars.visible = theme === "dark";
}

// Frame the camera to fit a board of the given dimensions.
export function frameCamera(camera, controls, cols, rows) {
  const radius = Math.max(cols, rows) * TILE;
  camera.position.set(radius * 0.7 + 1.4, radius * 0.78 + 3.0, radius * 1.0 + 2.6);
  controls.target.set(0, 0, 0);
  controls.update();
}
