import fs from 'fs';
import {geoMercator} from 'd3-geo';
import {feature} from 'topojson-client';
const w = JSON.parse(fs.readFileSync('node_modules/world-atlas/countries-50m.json'));
const fc = feature(w, w.objects.countries);
const aus = fc.features.find(f => f.properties.name === 'Australia');
const proj = geoMercator().fitSize([975, 610], {type:"Feature", geometry:{type:"Polygon", coordinates:[[[112,-10],[155,-10],[155,-44],[112,-44],[112,-10]]]}});
const rings = [];
const polys = aus.geometry.type === 'Polygon' ? [aus.geometry.coordinates] : aus.geometry.coordinates;
for (const p of polys) for (const r of p) { const q = r.map(c => proj(c)); if (q.length > 8) rings.push(q); }
const pts = {Warwick: proj([152.03,-28.22]), Brisbane: proj([153.03,-27.47]), Sydney: proj([151.21,-33.87])};
fs.writeFileSync(process.argv[2], JSON.stringify({states:[{name:"Australia", rings}], pts}));
console.log(rings.length, JSON.stringify(pts));
