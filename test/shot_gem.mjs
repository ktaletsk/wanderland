import http from "node:http"; import fs from "node:fs"; import path from "node:path";
import { fileURLToPath } from "node:url"; import { chromium } from "playwright";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const MIME={".html":"text/html",".js":"text/javascript",".json":"application/json",".css":"text/css"};
const server=http.createServer((q,s)=>{const f=path.join(root,decodeURIComponent(q.url.split("?")[0]));
 if(!fs.existsSync(f)||fs.statSync(f).isDirectory())return s.writeHead(404).end();
 s.writeHead(200,{"Content-Type":MIME[path.extname(f)]||"application/octet-stream"});fs.createReadStream(f).pipe(s);});
await new Promise(r=>server.listen(0,r));const port=server.address().port;
const b=await chromium.launch({args:["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader","--ignore-gpu-blocklist"]});

// HOVER: run to completion (Mo settles ON the gem), capture when done
{
  const p=await b.newPage({viewport:{width:720,height:560},deviceScaleFactor:2});
  await p.goto(`http://localhost:${port}/test/shot.html?fx=fixture_hover.json`);
  await p.waitForFunction(()=>window.__ready===true,{timeout:15000});
  await p.waitForTimeout(300);
  await p.evaluate(()=>window.__play(2));
  await p.waitForFunction(()=>/Run Again/.test(document.querySelector(".wanderland-run-btn")?.textContent||""),{timeout:15000});
  await p.waitForTimeout(700); // let the gem ease up over his head
  await p.locator("#host").screenshot({path:"test/gem_hover.png"});
  await p.close();
}
// COLLECT: short program (1 move + collect), burst around the jump
{
  const p=await b.newPage({viewport:{width:720,height:560},deviceScaleFactor:2});
  await p.goto(`http://localhost:${port}/test/shot.html?fx=fixture_collect2.json`);
  await p.waitForFunction(()=>window.__ready===true,{timeout:15000});
  await p.waitForTimeout(300);
  await p.evaluate(()=>window.__play(1));
  const start=Date.now();
  for (const at of [700, 850, 1000, 1150, 1300]) {
    await p.waitForTimeout(Math.max(0, at-(Date.now()-start)));
    await p.locator("#host").screenshot({path:`test/gem_c_${at}.png`});
  }
  await p.close();
}
await b.close();server.close();console.log("done");
