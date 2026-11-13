import fs from 'fs';
import {geoMercator} from 'd3-geo';
import {feature} from 'topojson-client';
const [,, names, bbox, ptsJson, out] = process.argv;
const w = JSON.parse(fs.readFileSync('node_modules/world-atlas/countries-50m.json'));
const fc = feature(w, w.objects.countries);
const [x0,y0,x1,y1] = bbox.split(',').map(Number);
const proj = geoMercator().fitSize([975, 610], {type:"Feature", geometry:{type:"Polygon", coordinates:[[[x0,y1],[x1,y1],[x1,y0],[x0,y0],[x0,y1]]]}});
const want = names.split('|'); const states = [];
for (const f of fc.features) {
  const polys = f.geometry ? (f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates) : [];
  const rings = [];
  for (const p of polys) for (const r of p) { const q = r.map(c => proj(c)); if (q.length > 6 && q.some(([a,b]) => a>-50 && a<1025 && b>-50 && b<660)) rings.push(q); }
  if (rings.length && (want[0]==='x' || want.includes(f.properties.name))) states.push({name: f.properties.name, rings});
}
const pts = {}; for (const [k,v] of Object.entries(JSON.parse(ptsJson))) pts[k] = proj(v);
fs.writeFileSync(out, JSON.stringify({states, pts})); console.log(states.length, JSON.stringify(pts));
