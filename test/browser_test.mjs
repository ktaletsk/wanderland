// Headless render test: serves the repo, loads the real bundle in Chromium with
// software WebGL, feeds it a Python-produced timeline, and asserts the frontend
// builds the scene, plays to completion, and reports state back. Runs two
// fixtures: a solved run AND a "collected all gems but missed the goal" run,
// to prove the "Solved!" pill reflects the authoritative result.

import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const MIME = {
  ".html": "text/html",
  ".js": "text/javascript",
  ".mjs": "text/javascript",
  ".json": "application/json",
  ".css": "text/css",
};

const server = http.createServer((req, res) => {
  const urlPath = decodeURIComponent(req.url.split("?")[0]);
  const file = path.join(root, urlPath);
  if (!file.startsWith(root) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.writeHead(404).end("not found");
    return;
  }
  res.writeHead(200, { "Content-Type": MIME[path.extname(file)] || "application/octet-stream" });
  fs.createReadStream(file).pipe(res);
});

await new Promise((r) => server.listen(0, r));
const port = server.address().port;

const browser = await chromium.launch({
  args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
});

let ok = true;
const fail = (msg) => { ok = false; console.log("  ✗ " + msg); };
const pass = (msg) => console.log("  ✓ " + msg);

async function runFixture(fx) {
  const page = await browser.newPage();
  const consoleErrors = [];
  page.on("console", (m) => m.type() === "error" && consoleErrors.push(m.text()));
  page.on("pageerror", (e) => consoleErrors.push("pageerror: " + e.message));
  await page.goto(`http://localhost:${port}/test/harness.html?fx=${fx}`);
  await page.waitForFunction(() => window.__done !== undefined, { timeout: 15000 });
  const result = await page.evaluate(() => window.__done);
  await page.close();
  return { result, consoleErrors };
}

// --- fixture 1: a fully solved run ---
console.log("Headless render test — solved run:");
{
  const { result, consoleErrors } = await runFixture("fixture.json");
  if (result.fatal) fail("fatal: " + result.fatal);
  result.hasCanvas ? pass("canvas created") : fail("no canvas");
  result.webglOk ? pass("WebGL context acquired") : fail("WebGL unavailable");
  result.buttonArmed ? pass("in-scene Run button armed after load") : fail("Run button missing/disabled");
  result.noAutoplay ? pass("loading did NOT autoplay (waits for button)") : fail("autoplayed on load");
  result.errors && result.errors.length === 0 ? pass("no runtime errors") : fail("page errors: " + JSON.stringify(result.errors));
  consoleErrors.length === 0 ? pass("no console errors") : fail("console errors: " + JSON.stringify(consoleErrors));
  const s = result.state || {};
  s.finished ? pass("playback finished + state reported") : fail("no completion report");
  s.success === true ? pass("reported success=true") : fail("expected success=true, got " + s.success);
  result.statusText === "Solved!" ? pass(`HUD pill = "Solved!"`) : fail(`expected "Solved!", got "${result.statusText}"`);
  // second run exercised the "return home" glide, then replayed to the same end
  const s2 = result.secondState || {};
  s2.finished ? pass("second run (with return-home) completed") : fail("second run did not finish");
  s2.pose && s2.pose.col === result.expected.final.col && s2.pose.row === result.expected.final.row
    ? pass(`after return-home + replay, final pose matches (${s2.pose.col},${s2.pose.row})`)
    : fail(`second-run final pose wrong: ${JSON.stringify(s2.pose)}`);
}

// --- fixture 2: all gems collected, goal NOT reached -> must NOT say "Solved!" ---
console.log("\nHeadless render test — all gems but goal missed:");
{
  const { result, consoleErrors } = await runFixture("fixture_nogoal.json");
  if (result.fatal) fail("fatal: " + result.fatal);
  consoleErrors.length === 0 ? pass("no console errors") : fail("console errors: " + JSON.stringify(consoleErrors));
  const s = result.state || {};
  s.finished ? pass("playback finished") : fail("no completion report");
  result.expected.gems_collected === 2 && result.expected.success === false
    ? pass("fixture is: 2/2 gems, success=false")
    : fail("bad fixture: " + JSON.stringify(result.expected));
  s.success === false ? pass("reported success=false (despite 2/2 gems)") : fail("expected success=false, got " + s.success);
  result.statusText !== "Solved!"
    ? pass(`HUD pill is NOT "Solved!" (got "${result.statusText}")`)
    : fail(`BUG: HUD says "Solved!" but goal was not reached`);
}

await browser.close();
server.close();
console.log(ok ? "\nBROWSER TEST PASSED" : "\nBROWSER TEST FAILED");
process.exit(ok ? 0 : 1);
