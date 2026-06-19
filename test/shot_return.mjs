// Visual proof of the "return home" glide: run once (Mo ends at the goal),
// then start a second run and capture a frame mid-arc as Mo floats home.
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const MIME = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".css": "text/css" };
const server = http.createServer((req, res) => {
  const file = path.join(root, decodeURIComponent(req.url.split("?")[0]));
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) return res.writeHead(404).end();
  res.writeHead(200, { "Content-Type": MIME[path.extname(file)] || "application/octet-stream" });
  fs.createReadStream(file).pipe(res);
});
await new Promise((r) => server.listen(0, r));
const port = server.address().port;

const browser = await chromium.launch({
  args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
});
const page = await browser.newPage({ viewport: { width: 760, height: 580 }, deviceScaleFactor: 2 });
await page.goto(`http://localhost:${port}/test/shot.html`);
await page.waitForFunction(() => window.__ready === true, { timeout: 15000 });
await page.waitForTimeout(700);

// 1) run fast so Mo ends up at the goal
await page.evaluate(() => window.__play(24));
await page.waitForTimeout(2500);
const host = page.locator("#host");
await host.screenshot({ path: "test/return_ended.png" }); // Mo left at his final pose

// 2) start a second run at normal speed and grab a frame mid return-home arc
await page.evaluate(() => window.__play(1));
await page.waitForTimeout(380);
await host.screenshot({ path: "test/return_midair.png" });

await browser.close();
server.close();
console.log("wrote test/return_ended.png and test/return_midair.png");
