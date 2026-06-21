// Screenshot the live marimo notebook UI: load, click Run, wait for Mo to
// finish, then capture the two-column button-driven layout.
import { chromium } from "playwright";

const browser = await chromium.launch({
  args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
});
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
await page.goto("http://localhost:2719", { waitUntil: "networkidle" });
await page.waitForSelector("canvas", { timeout: 30000 }).catch(() => {});
await page.waitForTimeout(3500);

// click "Run My Code" and let the animation play out, then settle
const runBtn = page.getByRole("button", { name: /Run My Code/i });
await runBtn.click({ timeout: 10000 }).catch((e) => console.log("click failed:", e.message));
await page.waitForTimeout(11000);

await page.screenshot({ path: "test/layout.png", fullPage: false });
await browser.close();
console.log("wrote test/layout.png");
