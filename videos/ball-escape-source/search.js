// Offline seed search: finds a run with well-paced ring breaks. Prints candidates.
const fs=require('fs');const src=fs.readFileSync(__dirname+'/index.html','utf8');
const consts=src.match(/const W=1080[^\n]*\n[^\n]*\nconst BR[^\n]*\n/)[0];
const helpers=src.match(/const clamp=[\s\S]*?\nfunction rng[^\n]*\n/)[0];
const sim=src.match(/function simulate\(seed\)\{[\s\S]*?\n\}\n/)[0];
const simulate=new Function(consts+helpers+sim+'return simulate;')();
let found=0,stats={ok:0,four:0};
for(let s=1;s<150000&&found<10;s++){const S=simulate(s);if(!S.ok)continue;stats.ok++;
  const b=S.ev.filter(e=>e.type==='break').map(e=>e.t);if(b.length<4)continue;stats.four++;
  const n=S.ev.length-4;
  if(b[0]>1.2&&b[0]<3.3&&b[1]-b[0]>1.5&&b[2]-b[1]>1.5&&b[3]-b[2]>1.6&&b[3]>10.0&&b[3]<10.6&&n>=30&&n<=80){found++;console.log(s,n,b.map(x=>x.toFixed(2)).join(' '));}
}
console.log(stats);
