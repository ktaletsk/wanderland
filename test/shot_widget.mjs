// Close-up of the widget in the live notebook: wait for the program to load
// (Run armed), capture it, click Run, wait for completion, capture the result.
import { chromium } from "playwright";

const browser = await chromium.launch({
  args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
});
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 2 });
await page.goto("http://localhost:2719", { waitUntil: "networkidle" });

const widget = page.locator(".wanderland-pg").first();
await widget.waitFor({ timeout: 30000 });

// wait until the timeline is loaded and the button is armed ("Run My Code", enabled)
await page.waitForFunction(() => {
  const b = document.querySelector(".wanderland-run-btn");
  return b && !b.disabled && /Run My Code/.test(b.textContent);
}, { timeout: 30000 });
await page.waitForTimeout(800);
await widget.screenshot({ path: "test/widget_armed.png" });

// click Run and wait for the run to finish (button relabels to "Run Again")
await page.locator(".wanderland-run-btn").click();
await page.waitForFunction(() => {
  const b = document.querySelector(".wanderland-run-btn");
  return b && /Run Again/.test(b.textContent);
}, { timeout: 30000 });
await page.waitForTimeout(600);
await widget.screenshot({ path: "test/widget_done.png" });

const status = await page.locator(".wanderland-hud-status").textContent();
console.log("HUD status after run:", JSON.stringify(status));

await browser.close();
console.log("wrote test/widget_armed.png and test/widget_done.png");
