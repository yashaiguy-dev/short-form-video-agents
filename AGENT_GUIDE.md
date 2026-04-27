# YT-to-Shorts Pipeline — Agent Guide

Turn any YouTube video into multiple viral-ready vertical short clips (30-60s) with editorial top-screen imagery and bold animated subtitles.

## Output Format

```
┌─────────────────────────┐
│  Gathos Slides (608px)  │  Bold editorial illustrations (change every 3-4s)
├─────────────────────────┤
│                         │
│  Original Video         │  Center-cropped from YouTube
│  (1312px)               │  with original audio
│                         │
└─────────────────────────┘
     1080 x 1920 (9:16)
```

---

## Prerequisites — Setup (Run Once)

### Automatic Setup (Recommended for New Users)

**Mac/Linux:**
```bash
cd yt-to-shorts
bash setup.sh
```

**Windows:**
```cmd
cd yt-to-shorts
setup.bat
```

This installs all system tools (Python, FFmpeg, yt-dlp), all Python packages, and creates the `.env` file. The user only needs to add their Gathos API key manually.

If the user prefers manual setup, or if the auto-installer reports issues, use the steps below.

### System Dependencies

```bash
# macOS
brew install yt-dlp ffmpeg

# Linux (Ubuntu/Debian)
sudo apt install yt-dlp ffmpeg

# Windows (via winget)
winget install yt-dlp.yt-dlp Gyan.FFmpeg
# Or manually: pip3 install yt-dlp + download FFmpeg from https://ffmpeg.org/download.html
```

### Python Dependencies

```bash
cd yt-to-shorts
pip3 install -r requirements.txt
```

### API Key Setup

```bash
cp .env.example .env
# Edit .env and add your Gathos Image API key
# Get one at https://gathos.com
```

### Verify Setup

**Mac/Linux:**
```bash
PYTHONPATH=. python3 lib/pipeline.py --stage check
```

**Windows:**
```bash
set PYTHONPATH=. && python3 lib/pipeline.py --stage check
```

All items should show `[OK]`. Fix any `[MISSING]` items before proceeding.

---

## Pipeline Steps

### Step 1: Gather Requirements

Ask the user:
1. **YouTube URL** — "What video do you want to clip?"
2. **Number of clips** — "How many clips would you like?" (default: 5)
3. **Clip duration** — "How long should each clip be?" (default: 30-60 seconds)
4. **Subtitle color** — "What color for subtitle emphasis words?" (default: yellow — options: yellow, red, green, lime, cyan, orange, pink, white, or any #RRGGBB)

Then say: *"I'll do my best to find that many, but I'll only include clips with genuine viral potential. Quality over quantity — every clip I deliver will be engineered to perform."*

Store the subtitle color — you'll pass it as `--subtitle-color` when running the subtitles stage.

### Step 2: Download

**Mac/Linux:**
```bash
PYTHONPATH=. python3 lib/pipeline.py --stage download --url "YOUTUBE_URL"
```

**Windows:**
```bash
set PYTHONPATH=. && python3 lib/pipeline.py --stage download --url "YOUTUBE_URL"
```

This downloads the video + auto-generated captions. Outputs: `source.mp4`, `captions.en.json3` (or `.vtt`), `info.json`.

### Step 3: Transcribe

**Mac/Linux:**
```bash
PYTHONPATH=. python3 lib/pipeline.py --stage transcribe
```

**Windows:**
```bash
set PYTHONPATH=. && python3 lib/pipeline.py --stage transcribe
```

Parses captions into timestamped segments. Output: `transcript.json`.

### Step 4: Select Clips (AI — Interactive)

Read the transcript and follow `skills/clip-selector.md`:

1. Read `outputs/{run_id}/transcript.json`
2. Run every candidate through the 5 viral tests (Hook, Retention Loop, Emotion, Shareability, Completeness)
3. **Present your selections to the user** with WHY each clip is viral-worthy
4. **Wait for approval** — user may remove, adjust, or request changes
5. Only after approval, write `outputs/{run_id}/clips.json`

### Step 5: Generate Slide Prompts (AI)

Follow `skills/clip-slide-prompter.md`:

1. Break each clip's narration into slides — **one slide every 3-4 seconds** (this is critical for engagement)
2. Generate bold editorial illustration prompts for each slide
3. **VERIFY slide count**: a 30s clip needs ~9 slides, a 60s clip needs ~17 slides
4. Update `outputs/{run_id}/clips.json` with `slide_segments`

### Step 6: Generate Slide Images

**Mac/Linux:**
```bash
PYTHONPATH=. python3 lib/pipeline.py --stage slides
```

**Windows:**
```bash
set PYTHONPATH=. && python3 lib/pipeline.py --stage slides
```

Generates editorial images via Gathos API (~8s spacing per image). Outputs: `clip_001_slide_01.png`, etc.

### Step 7: Assembly

**Mac/Linux:**
```bash
PYTHONPATH=. python3 lib/pipeline.py --stage assembly
```

**Windows:**
```bash
set PYTHONPATH=. && python3 lib/pipeline.py --stage assembly
```

For each clip:
1. Cuts the segment from source video (ffmpeg)
2. Creates slideshow from Gathos images (with dissolve transitions)
3. Composites: slides top + video bottom = 1080x1920 vertical
4. Outputs: `outputs/{run_id}/clip_001_final.mp4`, etc.

### Step 8: Subtitles

**Mac/Linux:**
```bash
PYTHONPATH=. python3 lib/pipeline.py --stage subtitles --subtitle-color "COLOR"
```

**Windows:**
```bash
set PYTHONPATH=. && python3 lib/pipeline.py --stage subtitles --subtitle-color "COLOR"
```

Replace `COLOR` with the user's chosen emphasis color (e.g., `green`, `red`, `#E8F538`).

Outputs: `outputs/{run_id}/clip_001_subtitled.mp4`, etc. — these are the **FINAL deliverables**.

---

## Loop Mode (Batch Processing)

When the user says "generate N clips from this video", run all steps in sequence without stopping between stages. The only pause point is Step 4 (clip selection) where you present your picks and wait for approval. After approval, run Steps 5-8 back-to-back.

**Loop flow:**
1. Download → Transcribe → AI clip selection (**pause for approval**) → AI slide prompts → Generate images → Assembly → Subtitles
2. Present all final clips to the user with file paths

---

## Error Recovery

| Error | Cause | Fix |
|-------|-------|-----|
| `GATHOS_IMAGE_API_KEY not set` | Missing `.env` or empty key | `cp .env.example .env` and add your Gathos key |
| `yt-dlp not found` | Not installed | `brew install yt-dlp` (Mac) / `winget install yt-dlp.yt-dlp` (Win) |
| `ffmpeg not found` | Not installed | `brew install ffmpeg` (Mac) / `winget install Gyan.FFmpeg` (Win) |
| `No captions available` | Video has no auto-subs | Try a video with spoken content, or upload manual SRT |
| `No module named 'lib'` | Missing PYTHONPATH | Run with `PYTHONPATH=.` prefix (Mac/Linux) or `set PYTHONPATH=.` (Windows) |
| `ModuleNotFoundError: cv2` | opencv-python not installed | `pip3 install -r requirements.txt` |
| Gathos 429 (rate limit) | Too many requests | Pipeline auto-retries with backoff. Wait and re-run `--stage slides` |
| Gathos 502/503/504 | Server temporarily down | Pipeline auto-retries (10 attempts). Re-run `--stage slides` if it fails |
| Pipeline stops mid-run | Crash or timeout | Re-run the failed stage — existing files are skipped automatically |
| Subtitle rendering slow | Frame-by-frame OpenCV | Normal. ~2-3 min per 60s clip. No fix needed |
| `yt-dlp: ERROR` | YouTube format change | `pip3 install --upgrade yt-dlp` to get latest extractors |
| Slides look wrong | Prompt quality | Adjust prompts in `clips.json`, re-run `--stage slides` |
| Wrong number of slides | Slide formula off | Verify: `num_slides = round(duration / 3.5)`. Fix in `clips.json` |

**Resume behavior:** Every stage checks for existing output files. Re-running a stage skips clips that already have their files. Use `--run-id` to resume a specific run.

---

## Quick Reference

| Stage | Type | Command / Skill |
|-------|------|-----------------|
| check | Python | `python3 lib/pipeline.py --stage check` |
| download | Python | `python3 lib/pipeline.py --stage download --url URL` |
| transcribe | Python | `python3 lib/pipeline.py --stage transcribe` |
| select | AI | Follow `skills/clip-selector.md` |
| slides-ai | AI | Follow `skills/clip-slide-prompter.md` |
| slides | Python | `python3 lib/pipeline.py --stage slides` |
| assembly | Python | `python3 lib/pipeline.py --stage assembly` |
| subtitles | Python | `python3 lib/pipeline.py --stage subtitles --subtitle-color COLOR` |

**Note:** All Python commands require `PYTHONPATH=.` prefix (Mac/Linux) or `set PYTHONPATH=. &&` prefix (Windows).

## Configuration

`.env` file:
```
GATHOS_IMAGE_API_KEY=your_key_here
SUBTITLE_EMPHASIS_COLOR=yellow
```

The `--subtitle-color` CLI flag overrides the `.env` value for that run.

## Key Constants

| Setting | Value |
|---------|-------|
| Output resolution | 1080 x 1920 (9:16 vertical) |
| Top panel (slides) | 1080 x 608px |
| Bottom panel (video) | 1080 x 1312px |
| Slide duration | 3-4 seconds each |
| Slide formula | `round(clip_duration / 3.5)` |
| Video codec | H.264 (libx264), crf=23 |
| Audio codec | AAC 192kbps |
| Frame rate | 24 fps |
| Subtitle position | 36% from top (~691px) |
| Dissolve transition | Cross-fade between slides |

## File Structure

```
yt-to-shorts/
├── .env                        ← API key + defaults
├── .env.example                ← Template for new users
├── .gitignore                  ← Ignores outputs, state, .env
├── requirements.txt            ← Python dependencies
├── fonts/                      ← Bundled Montserrat fonts (portable)
│   ├── Montserrat-Bold.ttf
│   └── Montserrat-ExtraBold.ttf
├── lib/
│   ├── pipeline.py             ← Main orchestrator (CLI entry point)
│   ├── config.py               ← Configuration + setup checker
│   ├── downloader.py           ← yt-dlp wrapper
│   ├── transcriber.py          ← Subtitle parser (JSON3 + VTT)
│   ├── gathos_client.py        ← Gathos Image API client
│   ├── stitcher.py             ← FFmpeg assembler (cut, slideshow, composite)
│   ├── subtitler.py            ← Word-by-word subtitle renderer
│   └── state.py                ← Run state manager (resumable)
├── skills/
│   ├── clip-selector.md        ← AI skill: viral clip selection
│   └── clip-slide-prompter.md  ← AI skill: editorial slide prompts
├── outputs/{run_id}/           ← Generated files per run
│   ├── source.mp4              ← Downloaded YouTube video
│   ├── captions.en.json3       ← YouTube auto-captions (word-level)
│   ├── info.json               ← Video metadata
│   ├── transcript.json         ← Parsed transcript segments
│   ├── clips.json              ← Selected clips + slide prompts
│   ├── clip_001_slide_*.png    ← Gathos editorial images
│   ├── clip_001_cut.mp4        ← Raw video segment
│   ├── clip_001_slideshow.mp4  ← Slideshow from editorial images
│   ├── clip_001_final.mp4      ← Composited clip (no subtitles)
│   └── clip_001_subtitled.mp4  ← FINAL clip with animated subtitles
└── state/                      ← Run state files (JSON, resumable)
```

## Notes

- **No GPU required** — uses the original YouTube footage, not AI-generated video
- **No cloud server** — everything runs locally except Gathos API calls for images
- Gathos API generates the top-screen editorial images
- Each clip is independent — if one fails, others still work
- The pipeline is resumable — existing files are skipped on re-run
- Use `--run-id` to resume a specific run
- Fonts are bundled in `fonts/` — works on any machine, no external font paths needed
- Subtitle colors are configurable per-run via `--subtitle-color`
- Compatible with: Claude Code, Cursor, Qwen Code, Gemini CLI, Windsurf, any MCP-compatible assistant
