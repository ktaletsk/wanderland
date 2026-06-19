import http from "node:http"; import fs from "node:fs"; import path from "node:path";
import { fileURLToPath } from "node:url"; import { chromium } from "playwright";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const MIME={".html":"text/html",".js":"text/javascript",".json":"application/json",".css":"text/css"};
const server=http.createServer((q,s)=>{const f=path.join(root,decodeURIComponent(q.url.split("?")[0]));
 if(!fs.existsSync(f)||fs.statSync(f).isDirectory())return s.writeHead(404).end();
 s.writeHead(200,{"Content-Type":MIME[path.extname(f)]||"application/octet-stream"});fs.createReadStream(f).pipe(s);});
await new Promise(r=>server.listen(0,r));const port=server.address().port;
const b=await chromium.launch({args:["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader","--ignore-gpu-blocklist"]});
const p=await b.newPage({viewport:{width:760,height:600},deviceScaleFactor:2});
await p.goto(`http://localhost:${port}/test/shot_expr.html`);
await p.waitForFunction(()=>window.__ready===true,{timeout:15000});
await p.waitForTimeout(600);
for(const name of ["neutral","determined","happy","surprised"]){
  await p.evaluate(n=>window.__setExpr(n),name); await p.waitForTimeout(350);
  // crop to Mo's head region (upper-right of the board)
  await p.screenshot({path:`test/expr_${name}.png`, clip:{x:430,y:180,width:330,height:300}});
}
await b.close();server.close();console.log("wrote expr_*.png");
