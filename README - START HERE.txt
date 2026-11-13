TRUE DOG STORIES VIDEO KIT
==========================
1. Unzip this folder somewhere (e.g. Documents\DogStories).
2. Double-click setup.bat (Windows) or run ./setup.sh (Mac/Linux).
3. Open this folder in Claude Code.
4. Type:  Read PROMPT.md and set everything up. Then make the video for <dog / story number>.
   e.g.   Read PROMPT.md and set everything up. Then download the footage for stories 7-10 and make video 7 (Hachiko).

What's inside
- PROMPT.md: the full instructions (story rules, hook, layouts, voice, captions, rendering, thumbnails, upload text)
- STORIES.md: done / next stories, verified facts and fact-check warnings
- examples\: the target layouts (dog reel formats), our current baseline to improve on, thumbnails, finished frames, voice samples
- reference\: the working code from the first 6 videos (pipeline, each video's script, footage downloader, maps, tools)
- fonts\: Montserrat + Playfair Display (used in all videos)
- setup.bat / setup.sh: installs Python packages, ffmpeg, the Kokoro voice model and whisper

Note: the reference code ran in a cloud workspace, so file paths inside it start with /home/claude/...
Claude Code should turn it into a clean pipeline with relative paths (cases\<code>\, lib\).
