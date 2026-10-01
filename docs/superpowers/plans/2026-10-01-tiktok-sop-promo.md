# R&B SOP TikTok Promo Video Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce one 25–30 second 1080 × 1920 Thai-narrated, bilingual-captioned TikTok MP4 promoting R&B SOP Standard.

**Architecture:** Use a small, self-contained Python/Pillow renderer to animate the site's existing SOP imagery into timed vertical scenes and pipe frames to local FFmpeg. Generate Thai narration with `edge-tts` using `th-TH-PremwadeeNeural` at `+5%` speed, compose an original instrumental-only music bed, mix them with FFmpeg, and validate the finished MP4 with ffprobe plus visual/audio inspection. Keep all session outputs under `edit/`; do not edit or embed into website HTML.

**Tech Stack:** Python 3 standard library + installed Pillow, `edge-tts`, FFmpeg/ffprobe, website-owned JPG assets.

**Spec:** `docs/superpowers/specs/2026-10-01-tiktok-sop-promo-design.md`

## Global Constraints

- “9:16 vertical, 1080 × 1920, approximately 25–30 seconds, suitable for TikTok.”
- “Thai narration with concise bilingual Thai/English on-screen text.”
- “A tasteful instrumental-only music bed (for example, soft piano/plucked strings with light percussion), sourced from a properly licensed track or composed for this project. No lyrics.”
- “Do not add unsupported outcome statistics.”
- “Do not modify `index.html`, add a website embed, or deploy/publish the video as part of this work.”
- “Use only assets belonging to the website or media with a clear license; document soundtrack source/license alongside the final asset.”
- “Do not fabricate client endorsements, quantified savings/results, or product functionality not stated on the site.”
- Thai speech must pronounce the brand “อาร์แอนด์บี ทานโซลูชั่น” and spell SOP as “เอส โอ พี”; use `edge-tts`, voice `th-TH-PremwadeeNeural`, at `+5%` speed.
- Use `/Users/ittmacair/Library/Fonts/ThaiSansNeue-Bold.ttf` for corporate titles and `/Users/ittmacair/Library/Fonts/THSarabun Bold.ttf` for body/subtitle text; never rely on fallback fonts.
- Preserve the TikTok safe zones: top `y=0..260` empty, header starts at `y>=270`, right `x>860` empty, subtitles within `y=1200..1370`, bottom `y>1380` empty.
- Use non-linear cubic easing; keep the final frame visible for at least 1 second and total duration at least narration length plus 1 second.
- Composite subtitle text after all scene artwork and decorative overlays.
- Keep all session outputs in `edit/`, and append one session note to `edit/project.md`.
- The final file must be rendered and inspected for legibility, timing, safe areas, audio balance/sync, and duration.

## Review Focus

- Either SOP mockup missing/corrupt should stop production with a clear error instead of yielding a broken or incomplete video.
- Missing Thai font/system voice should be detected before rendering; Thai narration/captions must not silently fall back to unreadable text or silence.
- Changes to scene durations must keep total runtime within 25–30 seconds and align captions with narration.
- Text must remain readable inside TikTok safe margins at 1080 × 1920, including bilingual lines and the final CTA.
- FFmpeg or audio-mix failure must return a failure and must not leave a success-shaped partial MP4 at the final output path.

---

## File Structure

- Create `edit/render_sop_tiktok.py` — constants, asset/font preflight, scene timing, Pillow composition/animation, audio orchestration, FFmpeg encode, and fail-safe output handling.
- Create `edit/test_render_sop_tiktok.py` — standard-library unit tests for timeline, text/asset preflight, output-path failure behavior, and layout geometry.
- Create `edit/AUDIO-CREDITS.md` — document that the instrumental bed is original/synthesized for this video and identify the `edge-tts` voice used for narration; record any future substitution and its license/source.
- Create `edit/final.mp4` — final deliverable only after successful render and review.
- Create or append `edit/project.md` — one concise session record; if the file does not exist, create it.
- Read, do not modify: `assets/sop_suite_mockup.jpg`, `assets/sop_flowchart_mockup.jpg`, and the approved design spec.

### Task 1: Define and test the content timeline

**Files:**
- Create: `edit/render_sop_tiktok.py`
- Create: `edit/test_render_sop_tiktok.py`

**Interfaces:**
- Produces `SCENES`, an ordered list of scene records with `start_s`, `end_s`, `th`, and `en` fields, and `total_duration_s() -> float`.
- Produces `validate_timeline(scenes) -> None`, raising `ValueError` for empty/non-positive, overlapping, out-of-order, or out-of-range timelines.
- Produces `NARRATION_TH: str`, the approved Thai voiceover script consumed by Task 2.
- Consumes the approved six storyboard beats and final CTA from the design spec.

- [ ] **Step 1: Write failing timeline tests.** Test the six approved beats, contiguous increasing boundaries, a total in `[25, 30]`, non-empty Thai/English copy, and rejection of overlap, zero-length, and missing scenes.
- [ ] **Step 2: Run `python3 -m unittest edit.test_render_sop_tiktok -v`.** Expected: import/test failure because the module and timeline functions do not yet exist.
- [ ] **Step 3: Add exact scene timing and copy.** Use the storyboard windows `0–3`, `3–7`, `7–13`, `13–19`, `19–24`, and `24–30` seconds; write concise bilingual captions and a Thai narration script that expresses only site-backed benefits and the free-consultation CTA.
- [ ] **Step 4: Implement `total_duration_s()` and `validate_timeline()` minimally.** Reject non-contiguous bounds and content that would render an empty caption.
- [ ] **Step 5: Run the timeline tests.** Expected: all pass; runtime is exactly 30 seconds.
- [ ] **Step 6: Commit the content/timeline slice.**

```bash
git add edit/render_sop_tiktok.py edit/test_render_sop_tiktok.py docs/superpowers/plans/2026-10-01-tiktok-sop-promo.md
git commit -m "feat: define SOP TikTok promo timeline"
```

### Task 2: Create original Thai narration and instrumental audio

**Files:**
- Modify: `edit/render_sop_tiktok.py`
- Create: `edit/AUDIO-CREDITS.md`
- Test: `edit/test_render_sop_tiktok.py`

**Interfaces:**
- Produces `preflight_audio_tools() -> None`, `render_audio(output_dir: Path) -> tuple[Path, Path]` returning voice/music WAV paths, and `mix_audio(voice_path: Path, music_path: Path, output_path: Path, duration_s: float) -> Path`.
- Consumes `NARRATION_TH`; uses `python3 -m edge_tts --voice th-TH-PremwadeeNeural --rate=+5% --text ... --write-media ...` and local FFmpeg, without adding a project dependency.
- Produces an original, no-vocals instrumental bed; no third-party track licensing is needed.

- [ ] **Step 1: Add tests for tool preflight and audio command failure.** Mock subprocess calls to assert a missing Thai voice/FFmpeg raises a clear exception and a failed `say`/FFmpeg process is not treated as success.
- [ ] **Step 2: Run the focused tests and confirm the missing behavior fails.**
- [ ] **Step 3: Implement preflight.** Check `python3 -m edge_tts` and `ffmpeg`; verify `th-TH-PremwadeeNeural` is listed by the Edge TTS service, and fail with an actionable message if not.
- [ ] **Step 4: Generate narration from the Thai script.** Render `NARRATION_TH` with `python3 -m edge_tts --voice th-TH-PremwadeeNeural --rate=+5% --text ... --write-media ...` into a temporary MP3, convert to mono 48 kHz WAV with FFmpeg, and measure speech length. Do not speed speech beyond the required `+5%`.
- [ ] **Step 5: Synthesize the instrumental bed locally.** Produce a gentle, lyric-free piano/plucked-string-style original motif with a quiet light pulse, 48 kHz stereo WAV, 30-second duration, and fade-in/out. Avoid copying an existing song or melody.
- [ ] **Step 6: Mix narration over the bed with FFmpeg.** Duck music under speech, preserve headroom, fade the bed at the end, and output AAC-ready stereo audio at 48 kHz. Fail the render if narration is absent or audio duration is outside scene tolerance.
- [ ] **Step 7: Add `AUDIO-CREDITS.md`.** State that the instrumental was procedurally composed for this video and the voice uses `edge-tts` voice `th-TH-PremwadeeNeural`; record TTS source/engine and date without claiming an external license.
- [ ] **Step 8: Run unit tests and a short audio preflight render.** Listen to the complete Thai script/music mix and adjust only for intelligibility, clipping, and duration; expected peak remains below 0 dBFS.
- [ ] **Step 9: Commit the audio-generation slice.**

```bash
git add edit/render_sop_tiktok.py edit/test_render_sop_tiktok.py edit/AUDIO-CREDITS.md
git commit -m "feat: generate narrated instrumental promo audio"
```

### Task 3: Animate the vertical storyboard and render MP4

**Files:**
- Modify: `edit/render_sop_tiktok.py`
- Test: `edit/test_render_sop_tiktok.py`
- Read: `assets/sop_suite_mockup.jpg`, `assets/sop_flowchart_mockup.jpg`
- Create: `edit/final.mp4`

**Interfaces:**
- Produces `preflight_visual_assets() -> None`, `render_frame(time_s: float) -> PIL.Image.Image`, and `render_video(output_path: Path) -> Path`.
- `render_video` invokes the audio functions from Task 2, streams enough 1080 × 1920 RGB frames to cover the narration plus at least a 1-second final hold (total 25–30 seconds) to FFmpeg, muxes the final audio, and returns the final path only after encoding succeeds.

- [ ] **Step 1: Write failing frame/layout tests.** Assert the frame size/mode, timeline boundary scene selection, no out-of-bounds text/CTA boxes, visible branded colors, and a clear exception for missing/unreadable required JPGs or font.
- [ ] **Step 2: Run focused tests and confirm failure before implementation.**
- [ ] **Step 3: Implement source-asset/font preflight.** Load both SOP mockups, `/Users/ittmacair/Library/Fonts/ThaiSansNeue-Bold.ttf`, and `/Users/ittmacair/Library/Fonts/THSarabun Bold.ttf` before creating render output; raise a clear error if any required file is absent or unreadable.
- [ ] **Step 4: Compose the six scenes with Pillow.** Use the site's deep green and champagne palette, high-contrast backgrounds, subtle cards, restrained pan/zoom/parallax on the owned SOP mockups, animated checklist/workflow accents with cubic easing, and sequential reveals.
- [ ] **Step 5: Add scene transitions and captions.** Keep all important visuals/text left of `x=860`, leave `y=0..260` and `y>1380` clear, start the header below `y=270`, and composite Thai/English captions last within `y=1200..1370`. Hold the final “นัดหมายปรึกษาฟรี / Book a free consultation” end card for at least 1 second with the site’s public LINE identity.
- [ ] **Step 6: Stream frames to FFmpeg and encode.** Use H.264 MP4 (`yuv420p`, 1080 × 1920, 30 fps), mux Task 2 audio, and render to a temporary filename; atomically rename to `edit/final.mp4` only after FFmpeg exits successfully and verifies the file. Add a mocked-FFmpeg failure test that asserts the final path is absent and the temporary file is cleaned up.
- [ ] **Step 7: Run tests and render the MP4.** Expected: unit tests pass and output exists at `edit/final.mp4`.
- [ ] **Step 8: Verify media metadata.** Run `ffprobe -v error -show_entries format=duration:stream=codec_type,width,height,sample_rate -of json edit/final.mp4`; verify duration 25–30 s, vertical dimensions 1080 × 1920, video+audio streams, and audio sample rate 48 kHz.
- [ ] **Step 9: Create a contact sheet inside a temporary directory and listen/watch the MP4.** Inspect each scene and transition for Thai glyph rendering, spelling, readable text, safe margins, image crop, CTA, narration/music balance, clipping, and sync; let the temporary-directory cleanup remove only that contact sheet.
- [ ] **Step 10: Commit the renderer and approved final media.**

```bash
git add edit/render_sop_tiktok.py edit/test_render_sop_tiktok.py edit/AUDIO-CREDITS.md edit/final.mp4
git commit -m "feat: render R&B SOP TikTok promo video"
```

### Task 4: Final verification and delivery

**Files:**
- Verify: `edit/final.mp4`
- Verify: `edit/AUDIO-CREDITS.md`
- Verify unchanged: `index.html`, `showcase.html`, all source assets

- [ ] **Step 1: Run the complete unit suite.** Run `python3 -m unittest edit.test_render_sop_tiktok -v`; expected: all tests pass.
- [ ] **Step 2: Run the final `ffprobe` acceptance command.** Confirm a 25–30 second 9:16 1080 × 1920 MP4 with audio and video.
- [ ] **Step 3: Reinspect the final export.** Confirm Thai narration is understandable, instrumental music contains no voice/recognizable borrowed melody, no clipping or cut-off words, text remains within TikTok safe areas, and final CTA is legible.
- [ ] **Step 4: Check project scope.** Run `git status --short` and `git diff --check`; expected changed files are limited to `edit/` and the approved planning documents; website HTML remains unchanged.
- [ ] **Step 5: Deliver the MP4 path and summarize its verified format, length, audio, and any caveat.**
