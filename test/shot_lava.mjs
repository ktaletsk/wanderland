import http from "node:http"; import fs from "node:fs"; import path from "node:path";
import { fileURLToPath } from "node:url"; import { chromium } from "playwright";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const MIME={".html":"text/html",".js":"text/javascript",".json":"application/json",".css":"text/css"};
const server=http.createServer((q,s)=>{const f=path.join(root,decodeURIComponent(q.url.split("?")[0]));
 if(!fs.existsSync(f)||fs.statSync(f).isDirectory())return s.writeHead(404).end();
 s.writeHead(200,{"Content-Type":MIME[path.extname(f)]||"application/octet-stream"});fs.createReadStream(f).pipe(s);});
await new Promise(r=>server.listen(0,r));const port=server.address().port;
const b=await chromium.launch({args:["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader","--ignore-gpu-blocklist"]});
const p=await b.newPage({viewport:{width:680,height:560},deviceScaleFactor:2});
const errs=[]; p.on("pageerror",e=>errs.push(String(e)));
await p.goto(`http://localhost:${port}/test/shot.html?fx=fixture_lava.json`);
await p.waitForFunction(()=>window.__ready===true,{timeout:15000});
await p.waitForTimeout(500);
await p.locator("#host").screenshot({path:"test/lava_init.png"});   // lava tiles
await p.evaluate(()=>window.__play(0.6));
// move(520)+turn(380)+move(520) into lava ~ /0.6, then ~650ms die; capture mid-sink
await p.waitForTimeout(2700);
await p.locator("#host").screenshot({path:"test/lava_death.png"});
console.log("errors:", errs.length);
await b.close();server.close();
