import { Viewer } from "../js/viewer.js";
const el = document.getElementById("host");
const v = new Viewer(el);
v.setPuzzle({ name: "Gem Path", cols: 4, rows: 3, start: [0, 0], heading: "E",
  gems: [], goal: null, gaps: [[1,1],[2,1]], heights: {} });
window.__setExpr = (name) => { v.character.setExpression(name); if (v.character._exprTarget) v.character._expr = { ...v.character._exprTarget }; };
window.__ready = true;
