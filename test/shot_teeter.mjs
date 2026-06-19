import http from "node:http"; import fs from "node:fs"; import path from "node:path";
import { fileURLToPath } from "node:url"; import { chromium } from "playwright";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const MIME={".html":"text/html",".js":"text/javascript",".json":"application/json",".css":"text/css"};
const server=http.createServer((q,s)=>{const f=path.join(root,decodeURIComponent(q.url.split("?")[0]));
 if(!fs.existsSync(f)||fs.statSync(f).isDirectory())return s.writeHead(404).end();
 s.writeHead(200,{"Content-Type":MIME[path.extname(f)]||"application/octet-stream"});fs.createReadStream(f).pipe(s);});
await new Promise(r=>server.listen(0,r));const port=server.address().port;
const b=await chromium.launch({args:["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader","--ignore-gpu-blocklist"]});
const p=await b.newPage({viewport:{width:760,height:580},deviceScaleFactor:2});
await p.goto(`http://localhost:${port}/test/shot.html?fx=fixture_teeter.json`);
await p.waitForFunction(()=>window.__ready===true,{timeout:15000});
await p.waitForTimeout(500);
await p.evaluate(()=>window.__play(1));
const host=p.locator("#host");
const start=Date.now();
for (const [label,at] of [["leanout",1200],["teeter",1500],["recover",1950]]) {
  await p.waitForTimeout(Math.max(0, at-(Date.now()-start)));
  await host.screenshot({path:`test/teeter_${label}.png`});
}
await b.close();server.close();console.log("wrote teeter_*.png");
