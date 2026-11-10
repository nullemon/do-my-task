const {chromium}=require('playwright');const fs=require('fs');const path=require('path');
(async()=>{
  const mode=process.argv[2]||'preview';
  const b=await chromium.launch();const p=await b.newPage({viewport:{width:1080,height:1920}});
  const errs=[];p.on('pageerror',e=>errs.push(e.message));p.on('console',m=>{if(m.type()==='error')errs.push(m.text())});
  await p.goto('file://'+path.resolve('index.html'));
  await p.evaluate(async()=>{await document.fonts.load('800 40px B','गर्मी');await document.fonts.load('800 40px B','POV 58');await document.fonts.ready;});
  const times=mode==='preview'?[0.8,1.8,2.2,3.6,5.8,7.0,8.2,9.8,11.4]:[...Array(Math.round(12.5*30)).keys()].map(f=>f/30);
  const dir=mode==='preview'?'prev':'frames';fs.mkdirSync(dir,{recursive:true});
  for(let i=0;i<times.length;i++){
    const d=await p.evaluate(t=>{render(t);return document.getElementById('c').toDataURL(t>=0?'image/png':'');},times[i]);
    fs.writeFileSync(`${dir}/f${String(i).padStart(4,'0')}.png`,Buffer.from(d.split(',')[1],'base64'));
  }
  if(errs.length)console.log('ERRORS',errs.slice(0,5));
  await b.close();
})();
