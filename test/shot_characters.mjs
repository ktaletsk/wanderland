import http from "node:http"; import fs from "node:fs"; import path from "node:path";
import { fileURLToPath } from "node:url"; import { chromium } from "playwright";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const MIME={".html":"text/html",".js":"text/javascript",".json":"application/json",".css":"text/css"};
const server=http.createServer((q,s)=>{const f=path.join(root,decodeURIComponent(q.url.split("?")[0]));
 if(!fs.existsSync(f)||fs.statSync(f).isDirectory())return s.writeHead(404).end();
 s.writeHead(200,{"Content-Type":MIME[path.extname(f)]||"application/octet-stream"});fs.createReadStream(f).pipe(s);});
await new Promise(r=>server.listen(0,r));const port=server.address().port;
const b=await chromium.launch({args:["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader","--ignore-gpu-blocklist"]});
let bad=0;
for (const char of ["mo","rover"]) {
  const p=await b.newPage({viewport:{width:760,height:580},deviceScaleFactor:2});
  const errs=[];
  p.on("console",m=>{ if(m.type()==="error") errs.push(m.text()); });
  p.on("pageerror",e=>errs.push(String(e)));
  await p.goto(`http://localhost:${port}/test/shot.html?char=${char}`);
  await p.waitForFunction(()=>window.__ready===true,{timeout:15000});
  await p.waitForTimeout(500);
  await p.evaluate(()=>window.__play(3));      // play whole program fast
  await p.waitForTimeout(4500);
  await p.locator("#host").screenshot({path:`test/char_${char}.png`});
  const status = await p.evaluate(()=>document.querySelector(".wanderland-hud-status")?.textContent || "");
  console.log(`[${char}] errors=${errs.length} status="${status}"`, errs.slice(0,2));
  if (errs.length) bad++;
  await p.close();
}
await b.close();server.close();
console.log(bad? "CHARACTERS: FAIL" : "CHARACTERS: OK (both played clean)");
process.exit(bad?1:0);
