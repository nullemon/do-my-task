// node render.js meta <file> | preview <dir> t1 t2.. | frames <dir> <start> <end>
const {chromium}=require('playwright');const fs=require('fs');const path=require('path');
(async()=>{
  const [mode,out,...rest]=process.argv.slice(2);
  const b=await chromium.launch();const p=await b.newPage({viewport:{width:1080,height:1920}});
  const errs=[];p.on('pageerror',e=>errs.push(e.message));
  await p.goto('file://'+path.resolve(__dirname,'index.html'));
  await p.evaluate(async()=>{await document.fonts.load('800 40px B','क्या आज़ाद');await document.fonts.load('800 40px B','123');await document.fonts.ready;});
  if(errs.length){console.log('ERRORS',errs);process.exit(1);}
  const meta=await p.evaluate(()=>window.META);
  if(mode==='meta')fs.writeFileSync(out,JSON.stringify(meta));
  else{fs.mkdirSync(out,{recursive:true});
    const jobs=mode==='preview'?rest.map((t,i)=>[i,+t]):Array.from({length:(+rest[1])-(+rest[0])},(_,i)=>[i+(+rest[0]),(i+(+rest[0]))/meta.FPS]);
    for(const [i,t] of jobs){const d=await p.evaluate(t=>{render(t);return document.getElementById('c').toDataURL('image/png');},t);
      fs.writeFileSync(`${out}/f${String(i).padStart(4,'0')}.png`,Buffer.from(d.split(',')[1],'base64'));}}
  if(errs.length){console.log('ERRORS',errs);process.exitCode=1;}
  await b.close();
})();
