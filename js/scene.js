// Renderer, scene, lighting, camera and orbit controls -- the "stage" Mo and
// the board are placed on.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { COLORS, TILE } from "./palette.js";

export function createStage(el) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  el.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(COLORS.sky);
  scene.fog = new THREE.Fog(COLORS.sky, 14, 34);

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

  addLights(scene);

  return { renderer, scene, camera, controls };
}

function addLights(scene) {
  scene.add(new THREE.HemisphereLight(COLORS.sky, COLORS.grassDark, 0.95));

  const sun = new THREE.DirectionalLight(0xfff1d6, 1.5);
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

  scene.add(new THREE.AmbientLight(0xffffff, 0.25));
}

// Frame the camera to fit a board of the given dimensions.
export function frameCamera(camera, controls, cols, rows) {
  const radius = Math.max(cols, rows) * TILE;
  camera.position.set(radius * 0.7 + 1.4, radius * 0.78 + 3.0, radius * 1.0 + 2.6);
  controls.target.set(0, 0, 0);
  controls.update();
}
