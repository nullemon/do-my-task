import fs from 'fs';
import {geoAlbersUsa, geoPath} from 'd3-geo';
import {feature, mesh} from 'topojson-client';
const us = JSON.parse(fs.readFileSync('node_modules/us-atlas/states-10m.json'));
const proj = geoAlbersUsa().scale(1300).translate([487.5, 305]);
const states = feature(us, us.objects.states).features;
const out = {states: [], pts: {}};
for (const s of states) {
  const polys = s.geometry.type === 'Polygon' ? [s.geometry.coordinates] : s.geometry.coordinates;
  const P = [];
  for (const poly of polys) for (const ring of poly) {
    const r = ring.map(c => proj(c)).filter(Boolean);
    if (r.length > 2) P.push(r);
  }
  out.states.push({name: s.properties.name, rings: P});
}
const places = {Silverton: [-122.783, 45.005], Wolcott: [-87.042, 40.758], Portland: [-122.676, 45.523],
  Denver:[-104.99,39.74], Omaha:[-95.93,41.26], Boise:[-116.2,43.62], Cheyenne:[-104.82,41.14], SaltLake:[-111.89,40.76], DesMoines:[-93.61,41.59], ContinentalDivide:[-107.5,42.3]};
for (const [k,v] of Object.entries(places)) out.pts[k] = proj(v);
fs.writeFileSync('/home/claude/work/bobbie/usmap.json', JSON.stringify(out));
console.log(states.length, JSON.stringify(out.pts));
