# Using the AI studio by hand (no Claude Code needed)

Start ComfyUI (`ai-studio\start-comfyui.ps1`, or `cd D:\AI\ComfyUI_windows_portable` then `.\run_nvidia_gpu.bat`)
and open http://127.0.0.1:8188.

## Basics (same for every job)

- **Open a workflow:** Workflow → Browse Templates → type the template name → click it.
- **Your files:** drag a picture or video from File Explorer onto the **Load Image** / **Load Video** box
  (or click the box and choose a file).
- **Settings and prompts:** most templates have one big box with all the fields (prompt, width, height,
  length…). Edit them there. Double-click it to see the inside if you're curious; you don't need to.
- **Go:** the **Run** button (top right) or **Ctrl+Enter**. The first run is slow while models load.
- **Results:** shown in the Save box and saved to `D:\AI\ComfyUI_windows_portable\ComfyUI\output`.
- **For your 8 GB card:** keep videos small: **480 × 832** (vertical) and **81 frames** (~3 seconds).
  Lengths must be 4×n+1 (49, 81, 121). Close Chrome before long video jobs.
- **Same result again:** set the seed's "control after generate" to **fixed** and change only the prompt.

## 1. Make an image: "Z-Image-Turbo: Text to Image"

- **prompt:** e.g. *An old golden retriever mix with a reddish-gold coat, grey muzzle and a worn red collar,
  sitting in the rain at a gas station at night, holding a yellow-green tennis ball, stylized 3D animated
  film, cinematic lighting.*
- **width / height:** 768 × 1344 for vertical Reels.
- Run. Make several and keep the best Rusty; you'll reuse him below.

## 2. Edit a photo / swap an object: "Qwen Image 2.1: Image Edit"

- **First Load Image (image_1):** the picture you want to change.
- **Second Load Image (image_2, optional):** something to bring in (an object, outfit or character).
- **Prompt:** an instruction. Refer to pictures as `<image1>`, `<image2>`. Examples:
  - *Replace the tennis ball in `<image1>` with the red frisbee from `<image2>`.*
  - *Change the background of `<image1>` to a rainy highway at dawn. Keep the dog exactly the same.*
- Turning **refine_prompt** on (together with **thinking**) usually gives better results but takes longer.

## 3. Make a still picture move: "Wan 2.2 5B Video Generation"

- **Load Image:** the start frame (e.g. your best Rusty).
- **Positive prompt:** describe the motion and camera: *the dog slowly wags his tail and tilts his head,
  rain falls, the camera pushes in slowly.*
- **Wan22ImageToVideoLatent:** width **704**, height **1280** (vertical), length **49** for a first test,
  then **121** (5 s) once it works.

## 4. Motion transfer (like Genjutsu Motion Transfer): "Wan Animate 2 Distilled: Motion Transfer"

Your character performs the motion from a driving video.

- **Load Image (Reference Image):** who (e.g. Rusty). Background doesn't matter.
- **Load Video (Pose Video):** the motion (e.g. a phone clip of a real dog walking).
  **Match the framing** (full body ↔ full body). Mismatched framing is the #1 cause of bad results.
- **Character Prompt:** looks only, no motion words:
  *Character appearance description: an old golden retriever mix, reddish-gold coat, grey muzzle, worn red
  collar, stylized 3D animated film. Background description: a long empty highway at dawn, wet asphalt.*
- **Post Prompt:** the motion: *a dog walking along the road.*
- In the big box: width/height **480 × 832**, length **81**, and set the cache **device** to **cpu**
  (avoids running out of graphics memory).
- Output: the video plus a side-by-side with the driving clip.

## 5. Replace a character in a video: "SCAIL-2 Int8: Character Replacement"

- **Load Video:** the original clip (the person or animal to replace).
- **Load Image:** the new character.
- In the **Base** box:
  - **replace_mode:** on = replace the subject in the video; off = make your character perform the motion.
  - **sam3_video_object / sam3_image_object:** what to track, in plain words, e.g. `dog` and `dog`
    (default is `human`).
  - **prompt:** describe the final video.
  - width/height **512 × 896** (vertical), frame count **81**, **turbo_mode** on.
- One run makes the first ~3 seconds. Longer clips are made in segments with the **Extend** box
  (advanced; Claude Code can automate this).

## 6. Swap or remove an object in a video: "Wan2.1 VACE Inpainting"

Needs the `swap` pack (run the setup script again after `git pull`).

- **Load Video:** the clip to edit. **Load Image (optional):** a reference for what should appear.
- **sam3_mask_object:** the thing to change, in words, e.g. `tennis ball`.
- **prompt:** what should be there instead (*a red frisbee*), or, to remove it, describe the background.
- width/height at **480p**, **enable_turbo_mode** on.

## Good to know

- Results get close to Genjutsu on many shots, but not all. Your 8 GB card caps size and length;
  upscale the best results afterwards.
- Only swap or animate real people with their permission.
- Check each model's license before commercial use (see `CLAUDE.md`).
