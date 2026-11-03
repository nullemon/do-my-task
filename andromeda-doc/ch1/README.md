# CH1 — "THE SMUDGE" (0:00–1:00)

**Format:** 1920×1080, 24 fps, 1440 frames (exactly 60.0 s), silent master. Grain and vignette are added once at final assembly, so this master has none.
Output: `/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/andromeda/ch1.mp4`
(frames in `.../andromeda/ch1/frames/f_%04d.png`).

Today's sky, seen the way a good camera on a tripod would see it. A black ridge and one bare, wind-bent tree, under a real
north-east sky on a late-September evening (latitude 40° N, local sidereal time 19 h, about 21:00).
The Milky Way rises from the horizon through Perseus and Cassiopeia. Andromeda sits to its right, 28° above the horizon.

## Shots / timing (seconds from chapter start)

| t (s) | Picture | Narration beat |
|---|---|---|
| 0.0–2.0 | Opens on black. The brightest stars appear first, then thousands more. The Milky Way and airglow rise behind the tree (the frame is already a full sky by ~1.5 s) | 2.0 "Look up on a dark autumn night…" |
| 0–7 | Wide, locked-off feel: a slow sideways drift (~2.8 m) gives parallax between the tree, the near ridge and the far hazy ranges. The faint smudge of M31 is visible top-right | |
| 7–17 | Slow push (76° → 20° field of view) toward Andromeda. The tree slides out of frame. 8.3–15 s: a thin violet line traces the Andromeda figure (Alpheratz–δ–Mirach–Almach) and the classic star-hop Mirach → μ → ν → the smudge, which gets a thin circle. Caption **ANDROMEDA (M31)** at 9.6–14.6 | 7.5 "Near the constellation Andromeda, there's a faint smudge…" |
| 15–24 | Tighter (20° → 12.6°). It is still just the naked-eye smudge: a soft, elongated glow with a brighter core. Caption **≈ 2.5 MILLION LIGHT-YEARS** at 16.8–22.6 | 15.0 "It isn't a cloud. It isn't a star. It's another galaxy…" |
| 24.6–29 | "Long-exposure" reveal: the full ~3.2° disk fades up, with dust lanes, M32 and M110 | 24.0 "If your eyes could gather enough light…" |
| 25.8–33.4 | Six full-Moon outlines (0.52° each) appear one by one along the major axis and span the disk end to end. Caption **≈ 6 FULL MOONS WIDE** at 27.0–32.3 | "…about six full Moons wide." |
| 33–43 | Slow zoom (8.7° → 4.75° FOV) into the detailed galaxy. The camera rolls so the disk lies on a rising diagonal. Caption **LIGHT LEFT ≈ 2.5 MILLION YEARS AGO** at 35.0–41.6 | 33.0 "The light you're seeing left it two and a half million years ago…" |
| 43–51 | Detailed close-up, slow drift: dust lanes on the near (NW) side silhouetted against the bulge, blue star-forming arms, pink HII knots, NGC 206, M32 and M110 | 43.0 "It is the farthest thing most of us will ever see…" |
| 51–60 | The push quickens a little (3.85° → 2.85°) and the disk fills the frame. The galaxy brightens ~10%. Fade to black 58.4–60.0 | 51.0 "And it is coming toward us." |

## How it is built (fast on CPU)

- `gen_textures.py` (numpy only, ~2 min) bakes everything heavy into the shared cache `.../andromeda/textures/ch1_*`:
  - `ch1_mw.png` (16-bit): a gnomonic sky texture with the Milky Way, a galactic-coordinate model with star clouds,
    dust lanes and faint HII glows (Heart & Soul, California…). It also includes unresolved faint stars, atmospheric
    extinction, a zenith-to-horizon airglow gradient and the naked-eye M31 smudge.
  - `ch1_m31_{hi,mid,lo}.png`: a procedural M31 at 4096 / 2048 / 1024 px over 4.2°×2.4°. It has a Sérsic bulge with nucleus, an
    exponential disk inclined 75.5°, tightly wound arms, an off-centre 10-kpc ring, and dust lanes plus filaments, extincted
    more on the near (NW) side. It also has blue clusters, HII knots, NGC 206, globular-like dots, M32 and M110 at their real offsets. Tone
    mapping is an asinh stretch, as used for astrophotos. `ch1_m31_eye.png` is the blurred core only.
  - `ch1_stars.npz`: about 365k stars. The ~170 bright stars are real (BSC positions and magnitudes, rounded). Fainter stars are
    random but follow realistic number counts and Milky Way density, with deeper samples near M31 for the zoom.
  - `ch1_ring.png` (Moon/marker outline), `ch1_meta.json` (observer, plane frames, constellation lines).
- `script.py` (bpy, Cycles CPU, 4 spp, no denoise, no lights or bounces):
  - The sky is the world shader. Each texture is sampled through its own gnomonic projection of the ray direction.
    Only the layers that contribute in a frame are linked, so one shader evaluation covers the whole sky.
  - Stars are a mesh of camera-facing quads, rebuilt every frame from the catalogue. They stay the same size on screen
    at any zoom (a real lens/telescope look). The limiting magnitude deepens as the field narrows (~7.9 → ~14), capped by catalogue completeness
    so no edges show.
  - Silhouettes are three ridge strips plus a recursive bent tree, black emission. Moon rings and the marker are small textured planes.
    Constellation lines are thin strips rebuilt per frame for a constant ~2 px width. Captions are Inter Light text on a HUD
    that is scaled with the lens, so their size never changes.
  - Galaxy level of detail hands over at fixed screen-pixel/texture-pixel ratios (lo → mid → hi), so the textures are never
    magnified more than ~1.5× or minified more than ~2×.

```bash
/home/user/bpyenv/bin/python gen_textures.py                      # textures + catalogue (~2 min)
/home/user/bpyenv/bin/python -c "import sys; p='script.py'; sys.argv=['blender','--','--frames','48,240,1000']; exec(compile(open(p).read(),p,'exec'))"
# full render, two processes, resumable
for k in 1 2; do setsid nohup /home/user/bpyenv/bin/python -c "import sys; p='script.py'; sys.argv=['blender','--','--render','--skip-existing','--start','$k','--step','2','--threads','1']; exec(compile(open(p).read(),p,'exec'))" > render_$k.log 2>&1 & done
ffmpeg -framerate 24 -i frames/f_%04d.png -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p ch1.mp4
```

## Facts used (and how honest each picture is)

| Claim | Status |
|---|---|
| Andromeda (M31) is ≈ 2.5 million light-years away | Standard value (~765–785 kpc). The model uses 770 kpc |
| The light left ≈ 2.5 million years ago, "before our species existed" | Follows from the distance. *Homo sapiens* is ~300,000 years old |
| Full disk ≈ 3.2° × 1°, about 6 full Moons wide | Standard apparent size (~190′ × 60′). The full Moon is ~0.52°, and 6 × 0.52° = 3.1°. The rings are drawn at true angular scale on the sky |
| Mostly only the core is seen with the naked eye | True. The film shows only a soft core-dominated smudge until the "long-exposure" reveal |
| "Perhaps a trillion suns" | Common estimate (~1 trillion stars). Estimates vary |
| M32 and M110 | Placed at their real offsets from the nucleus (M32 ~24′ S, M110 ~36′ NW). M110 is drawn at its catalogue position angle (~170°) |
| The sky | Real for lat 40° N, LST 19 h, facing NE (az ≈ 46°). Andromeda, Cassiopeia, Perseus, Pegasus, Triangulum and the Double Cluster are where they really are. Fainter stars are statistical, not catalogue stars |
| "Coming toward us" | Radial velocity −301 km/s heliocentric (≈ −110 km/s relative to the Milky Way). The faster push in the last shot is a visual metaphor only |

**Honesty notes**
- The galaxy is a procedural impression of M31 built from its real structure (bulge, inclined dusty disk, ring, satellites).
  It is not a photograph or a simulation. Spiral details are stylised.
- In the "long exposure" and close-up shots, brightness and colour are stretched the way astrophotos are. The eye never sees colour in M31.
- The zoom ends at about a 2.9° field. That is a telescope or long-lens view, not a naked-eye view.
- The landscape is symbolic (one ridge, one tree). The Milky Way brightness and the airglow are kept at realistic, dark-site levels.

## Render log

- 1440 frames, Cycles CPU 4 spp, two single-thread processes (odd/even frames), wall time ~69 min on the shared 4-core machine
  (load average 6–8 from the other chapters). That is ~2.9 s of wall time per frame, ~5–6 s per frame per process. On an idle
  core, the same frame takes ~2–3 s single-threaded. The fixed per-frame overhead (Python + star mesh rebuild) is <0.2 s.
- Master: `ch1.mp4`, libx264 -crf 16 -preset slow, yuv420p, 1920×1080, 24 fps, 1440 frames = 60.000 s, no grain, no audio.
