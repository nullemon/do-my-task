"""Turn your own story into ready-to-make episodes: shot list, picture and motion prompts, narration,
dialogue, captions, sound effects, music prompt and the Facebook caption. Uses Claude (your API credits).

  python story_to_episode.py my_story.txt                              # 1 episode, ~60 s, 80s American cartoon
  python story_to_episode.py my_story.txt --episodes 3 --style anime80s
  python story_to_episode.py my_story.txt --style "black ink stickman doodles on white paper" --look clean
  python story_to_episode.py --from-json episodes/series.json          # rebuild folders after editing the JSON

Writes series.json and one folder per episode (ep01, ...) into /workspace/episodes (or ./episodes) with episode.json and
shotlist.md. Follow shotlist.md, then run make_episode.py on the folder.
Needs ANTHROPIC_API_KEY set on the pod (RunPod: Edit Pod -> Environment Variables). Never paste the key in a chat.
"""
import argparse, json, os, sys

MODEL = 'claude-opus-5-5'
STYLES = {
    'american80s': ('1980s Saturday-morning cartoon, hand-painted gouache background, cel animation, flat colors, '
                    'bold black ink outlines, soft film grain, slightly faded colors', '80s-cartoon'),
    'anime80s': ('1980s anime cel, hand-painted watercolor background, soft pastel colors, film grain, VHS softness',
                 '80s-anime'),
}
NEGATIVE = ('3D render, glossy, smooth gradients, photorealistic, plastic skin, text, letters, watermark, '
            'extra fingers, deformed hands, blurry')

SYSTEM = """You are the head writer and director of a short animated series made for Facebook Reels: vertical 9:16,
watched mostly with the sound off, judged in the first two seconds. You turn the author's own story into episodes that
an AI image and video pipeline can produce at high quality, so it never looks like cheap AI content.

Story rules
- Keep the author's plot, characters, meaning and voice. Tighten and dramatize; never change what happens or add new
  major events. If the story is shorter than the requested runtime, slow down and show more; if longer, compress.
- Episode 1 opens with a hook in the first shot (a striking image plus a caption that raises a question).
- Every episode except the last ends on a cliffhanger. The last one lands the ending.
- Captions carry the story with the sound off: short (max 10 words), punchy, present tense or narration style.
- Narration and dialogue lines are short (max 14 words each) and sound natural spoken aloud.

Production rules (these keep the quality high)
- 12 to 15 shots per 60 seconds; each shot 3 to 6 seconds. The shot lengths add up to the requested runtime.
- kind "pan": a wide establishing or travelling shot. One still painting; the camera move (move: left, right, up, down,
  in, out) is done in code, so it is perfect. Use for places, journeys, moods.
- kind "still": a dramatic hold or reaction on one painting with a slow push-in (move "in" or "out").
- kind "animate": a character acting (talking, turning, running, reacting). Keep it to ONE simple action per shot,
  static camera. These go through an image-to-video model.
- At least 40 percent of shots are pan or still. 1980s TV cartoons used limited animation; so do we.
- Avoid what AI draws badly: close-ups of hands, crowds, fast spins, text or signs in the picture, many characters
  touching each other. Two characters per shot at most.

Prompt rules
- image_prompt is complete and self-contained: begin with the style words exactly as given, then the shot: who, pose
  or action frozen at its key moment, setting, time of day, lighting, camera angle and framing. Repeat every visible
  character's look description word for word from the characters list, so they stay identical across shots.
  Vertical 9:16 composition. No text, letters or logos in the picture.
- motion_prompt (animate shots only, else empty): what moves, in plain words, then "2D cel animation, limited
  animation, static camera". For pan and still shots leave it empty and set move.
- characters[].look is a precise, reusable visual description (age, build, face, hair, clothes and colours, one
  signature detail). Name the narrator character "Narrator" only if a narrator is needed; don't add it to characters.
- sfx is a short sound-effect description for a text-to-audio model (e.g. "distant thunder rumble"), or empty.
- music_prompt is for a text-to-music model: instrumental, genre and era, instruments, tempo in bpm, mood arc.
- facebook_caption: 1 to 2 lines with a hook and a question that invites comments; hashtags: 5 to 8, no spaces."""


def episode_schema():
    s = lambda **kw: {'type': 'string', **kw}
    obj = lambda props: {'type': 'object', 'properties': props, 'required': list(props), 'additionalProperties': False}
    shot = obj({
        'id': {'type': 'integer'}, 'seconds': {'type': 'number'},
        'kind': s(enum=['pan', 'still', 'animate']),
        'move': s(enum=['none', 'left', 'right', 'up', 'down', 'in', 'out']),
        'image_prompt': s(), 'motion_prompt': s(), 'narration': s(),
        'dialogue': {'type': 'array', 'items': obj({'character': s(), 'line': s()})},
        'caption': s(), 'sfx': s()})
    episode = obj({'number': {'type': 'integer'}, 'title': s(), 'logline': s(),
                   'shots': {'type': 'array', 'items': shot},
                   'facebook_caption': s(), 'hashtags': {'type': 'array', 'items': s()}})
    return obj({'series_title': s(),
                'characters': {'type': 'array', 'items': obj({'name': s(), 'look': s()})},
                'music_prompt': s(), 'episodes': {'type': 'array', 'items': episode}})


def ask_claude(story, style, n, seconds):
    try:
        import anthropic
    except ImportError:
        sys.exit('  !!  the Claude SDK is missing: /workspace/venv/bin/pip install anthropic')
    user = (f'Style words (start every image_prompt with these): {style}\n'
            f'Number of episodes: {n}\nRuntime per episode: about {seconds} seconds\n\n'
            f'The author\'s story:\n<story>\n{story}\n</story>')
    client = anthropic.Anthropic()
    try:
        with client.beta.messages.stream(
            model=MODEL, max_tokens=64000, system=SYSTEM,
            messages=[{'role': 'user', 'content': user}],
            thinking={'type': 'adaptive'},
            output_config={'effort': 'high', 'format': {'type': 'json_schema', 'schema': episode_schema()}},
            betas=['server-side-fallback-2026-07-01'], fallbacks='default',   # a declined request re-runs on a fallback model
        ) as stream:
            msg = stream.get_final_message()
    except anthropic.AuthenticationError:
        sys.exit('  !!  no valid Claude API key. On RunPod: Edit Pod -> Environment Variables -> ANTHROPIC_API_KEY.')
    except anthropic.RateLimitError:
        sys.exit('  !!  Claude rate limit reached; wait a minute and run again.')
    except anthropic.APIStatusError as e:
        sys.exit(f'  !!  Claude API error {e.status_code}: {e.message}')
    except anthropic.APIConnectionError:
        sys.exit('  !!  could not reach the Claude API (network).')
    if msg.stop_reason == 'refusal':
        sys.exit('  !!  Claude declined this story. Soften any graphic parts and try again.')
    if msg.stop_reason == 'max_tokens':
        sys.exit('  !!  the answer was cut off; ask for fewer episodes at a time (--episodes).')
    text = next(b.text for b in msg.content if b.type == 'text')
    u = msg.usage
    cost = (u.input_tokens * 4 + u.output_tokens * 20) / 1e6
    print(f'  ..  Claude used {u.input_tokens} input + {u.output_tokens} output tokens (about ${cost:.2f})')
    return json.loads(text)


def shotlist_md(series, ep, style, negative):
    L = [f'# Episode {ep["number"]}: {ep["title"]}', '', f'_{ep["logline"]}_', '',
         '## How to make it', '',
         '1. **Characters (once per series):** make a model sheet for each with Z-Image or Qwen Image (prompts below). '
         'Keep the best one; later we train a LoRA from them so every shot matches.',
         '2. **Each shot:** make the picture with Z-Image (1088 x 1920) using its picture prompt, then save it into '
         f'this folder as `shotNN.png` (`python pick.py ep{ep["number"]:02d} NN` copies your latest result).',
         '   - **animate** shots: then animate that picture with *Wan 2.2 14B Image to Video* (720 x 1280, 5 s, '
         'turbo on for tries) using the motion prompt, and save it as `shotNN.mp4`.',
         '   - **pan / still** shots: the picture is all you need; the camera move is done in code.',
         '3. **Voices:** record each line on your phone and save as `voice/shotNN.m4a` (or one `narration.m4a`).',
         '4. **Music:** ACE-Step 1.5 XL Turbo with the music prompt below; save as `music.mp3`.',
         '5. **Sound effects (optional):** Stable Audio 3.0 with each shot\'s sound effect; save as `sfx/shotNN.wav`.',
         f'6. **Build it:** `python make_episode.py ep{ep["number"]:02d}`. Missing shots show as labelled cards, '
         'so you can preview any time.', '',
         '## Style (already inside every picture prompt)', '', f'`{style}`', '',
         '## Negative prompt (for every picture and video)', '', f'`{negative}`', '',
         '## Characters (model-sheet prompts)', '']
    for c in series['characters']:
        L += [f'**{c["name"]}**', '',
              f'`{style}, character model sheet of {c["look"]}, front view, side view, back view, four facial '
              f'expressions (happy, worried, angry, surprised), plain light background, full body`', '']
    L += ['## Music prompt (ACE-Step)', '', f'`{series["music_prompt"]}`', '', '## Shots', '']
    total = 0.0
    for s in ep['shots']:
        total += s['seconds']
        move = f' {s["move"]}' if s['move'] != 'none' else ''
        L += [f'### Shot {s["id"]:02d}  ({s["kind"]}{move}, {s["seconds"]:g} s)', '',
              f'- **Picture** (`shot{s["id"]:02d}.png`): {s["image_prompt"]}']
        if s['kind'] == 'animate' and s['motion_prompt']:
            L.append(f'- **Motion** (`shot{s["id"]:02d}.mp4`): {s["motion_prompt"]}')
        if s['narration']:
            L.append(f'- **Narrator:** "{s["narration"]}"')
        for d in s['dialogue']:
            L.append(f'- **{d["character"]}:** "{d["line"]}"')
        if s['caption']:
            L.append(f'- **Caption:** {s["caption"]}')
        if s['sfx']:
            L.append(f'- **Sound effect** (`sfx/shot{s["id"]:02d}.wav`): {s["sfx"]}')
        L.append('')
    L += [f'Total: about {total:.0f} seconds.', '', '## Facebook caption', '', ep['facebook_caption'], '',
          ' '.join('#' + h.lstrip('#') for h in ep['hashtags']), '']
    return '\n'.join(L)


def write_folders(series, out, style, look):
    os.makedirs(out, exist_ok=True)
    series.setdefault('style', style)
    series.setdefault('look', look)
    json.dump(series, open(os.path.join(out, 'series.json'), 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    for ep in series['episodes']:
        d = os.path.join(out, f'ep{ep["number"]:02d}')
        os.makedirs(os.path.join(d, 'voice'), exist_ok=True)
        os.makedirs(os.path.join(d, 'sfx'), exist_ok=True)
        data = dict(ep, title=ep['title'], look=series['look'], style=series['style'], negative=NEGATIVE,
                    characters=series['characters'], music_prompt=series['music_prompt'])
        json.dump(data, open(os.path.join(d, 'episode.json'), 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
        open(os.path.join(d, 'shotlist.md'), 'w', encoding='utf-8').write(
            shotlist_md(series, ep, series['style'], NEGATIVE))
        secs = sum(s['seconds'] for s in ep['shots'])
        print(f'  OK  {d}  ({len(ep["shots"])} shots, {secs:.0f} s): open shotlist.md')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('story', nargs='?', help='text file with your story')
    ap.add_argument('--style', default='american80s', help='american80s, anime80s, or your own style words')
    ap.add_argument('--look', help='finish for make_episode.py: 80s-cartoon, 80s-anime or clean (default: by style)')
    ap.add_argument('--episodes', type=int, default=1)
    ap.add_argument('--seconds', type=int, default=60, help='runtime per episode')
    ap.add_argument('--out', default='/workspace/episodes' if os.path.isdir('/workspace') else 'episodes')
    ap.add_argument('--from-json', help='rebuild the episode folders from an edited series.json (no Claude call)')
    ap.add_argument('--dry-run', action='store_true', help='print what would be sent to Claude')
    a = ap.parse_args()

    style, look = STYLES.get(a.style, (a.style, 'clean'))
    look = a.look or look
    if a.from_json:
        series = json.load(open(a.from_json, encoding='utf-8'))
        write_folders(series, os.path.dirname(os.path.abspath(a.from_json)), series.get('style', style),
                      series.get('look', look))
        return
    if not a.story:
        ap.error('give a story file (or --from-json)')
    story = open(a.story, encoding='utf-8').read().strip()
    if a.dry_run:
        print(SYSTEM, '\n---\n', f'style: {style}\nepisodes: {a.episodes}\nseconds: {a.seconds}\n\n{story[:500]}...')
        return
    print(f'  ..  Claude is writing {a.episodes} episode(s) of ~{a.seconds} s (takes a minute or two)')
    series = ask_claude(story, style, a.episodes, a.seconds)
    write_folders(series, a.out, style, look)


if __name__ == '__main__':
    main()
