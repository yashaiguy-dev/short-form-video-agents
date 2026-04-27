# YT-to-Shorts

[![GitHub](https://img.shields.io/github/stars/yashaiguy-dev/short-form-video-agents?style=social)](https://github.com/yashaiguy-dev/short-form-video-agents)

Fully automated, AI-driven YouTube repurposing pipeline. Give your AI assistant a YouTube URL — it downloads the video, finds the most viral moments, generates editorial illustrations, and delivers ready-to-upload 9:16 vertical clips with animated subtitles.

---

## What It Does

Eight-stage pipeline, mostly automated:

| Stage | What Happens |
|-------|-------------|
| 1 — Download | yt-dlp downloads the video + auto-generated captions |
| 2 — Transcribe | Captions parsed into timestamped text segments |
| 3 — Clip Selection | AI finds the most viral-worthy moments (5 tests: Hook, Retention, Emotion, Shareability, Completeness) |
| 4 — Slide Prompts | AI generates bold editorial illustration prompts for each clip |
| 5 — Slide Images | Gathos API generates magazine-style editorial images |
| 6 — Assembly | FFmpeg cuts clips, creates slideshows, composites into 1080x1920 vertical |
| 7 — Subtitles | Word-by-word animated text burned onto each clip |
| 8 — Delivery | Final clips ready for TikTok, Reels, Shorts |

**One approval gate:** the AI pauses after clip selection to let you approve/adjust before processing.

---

## Quick Start

### Clone the Repo

```bash
git clone https://github.com/yashaiguy-dev/short-form-video-agents.git
cd short-form-video-agents
```

### Automatic Setup (Recommended)

Run one command to install everything:

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

The script auto-detects what's missing and installs: Python 3, FFmpeg, yt-dlp, all pip packages, and creates your `.env` file. The only manual step is adding your Gathos API key ([gathos.com](https://gathos.com)).

**No GPU or cloud server needed.** Everything runs locally.

### Manual Setup (if you prefer)

```bash
# 1. Install system tools
# macOS: brew install python ffmpeg yt-dlp
# Windows: winget install Python.Python.3.12 Gyan.FFmpeg yt-dlp.yt-dlp
# Linux: sudo apt install python3 python3-pip ffmpeg yt-dlp

# 2. Install Python packages
pip3 install -r requirements.txt

# 3. Configure API key
cp .env.example .env
# Edit .env and add your Gathos Image API key

# 4. Verify
PYTHONPATH=. python3 lib/pipeline.py --stage check
```

All items should show `[OK]`. See [AGENT_GUIDE.md](AGENT_GUIDE.md) for detailed platform-specific instructions.

---

## Usage

Open your AI assistant (Claude Code, Cursor, Gemini CLI, etc.) in this project folder and say:

> "Make me 5 short clips from this YouTube video: [URL]"

The assistant reads [AGENT_GUIDE.md](AGENT_GUIDE.md) and runs the full pipeline. It only pauses once — to show you the selected clips for approval.

### Examples

> "Make me 10 clips (30 seconds each) from this video, use green subtitles"

> "Find the 5 most viral moments from this podcast episode: [URL]"

> "Create 3 clips with lime emphasis and orange subtitles from: [URL]"

---

## Subtitle Colors

Customize the emphasis word color per run:

| Color | Value |
|-------|-------|
| Yellow (default) | `yellow` |
| Red | `red` |
| Green | `green` |
| Lime | `lime` |
| Cyan | `cyan` |
| Orange | `orange` |
| Pink | `pink` |
| White | `white` |
| Custom | Any hex: `#FF4D1F`, `#E8F538` |

Just tell your AI assistant: "Use green subtitles" or set `SUBTITLE_EMPHASIS_COLOR=green` in `.env`.

---

## Project Structure

```
yt-to-shorts/
├── .env                        # Your API key (gitignored)
├── .env.example                # Template
├── AGENT_GUIDE.md              # Instructions for AI assistants
├── ADD_TO_YOUR_CLAUDE_MD.md    # Integration guide for multi-project setups
├── CLAUDE.md                   # Self-contained AI trigger
├── README.md                   # This file
├── requirements.txt            # Python dependencies
├── fonts/                      # Bundled Montserrat fonts (portable)
├── lib/
│   ├── pipeline.py             # Main CLI orchestrator
│   ├── config.py               # Config loader + setup checker
│   ├── downloader.py           # yt-dlp wrapper
│   ├── transcriber.py          # Caption parser (JSON3 + VTT)
│   ├── gathos_client.py        # Gathos Image API client
│   ├── stitcher.py             # FFmpeg assembler (cut, slideshow, composite)
│   ├── subtitler.py            # Word-by-word subtitle renderer
│   └── state.py                # Run state manager (resumable)
├── skills/
│   ├── clip-selector.md        # AI skill: viral clip selection
│   └── clip-slide-prompter.md  # AI skill: editorial slide prompts
├── outputs/                    # Generated clips per run (gitignored)
└── state/                      # Run state files (gitignored)
```

---

## How Long Does It Take?

| Clips | Time |
|-------|------|
| 3 clips (30s) | ~10-15 minutes |
| 5 clips (45s) | ~20-30 minutes |
| 10 clips (30s) | ~35-50 minutes |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `GATHOS_IMAGE_API_KEY not set` | Create `.env` from `.env.example` and add your key |
| `yt-dlp not found` | Install: `brew install yt-dlp` (Mac) / `winget install yt-dlp.yt-dlp` (Windows) |
| `ffmpeg not found` | Install: `brew install ffmpeg` (Mac) / `winget install Gyan.FFmpeg` (Windows) |
| No captions available | Video has no auto-generated subtitles. Try a different video with spoken content |
| Pipeline stops halfway | Tell the AI to continue — state is saved and it resumes from where it stopped |
| `No module named 'lib'` | Run with `PYTHONPATH=.` from the yt-to-shorts directory |
| Windows PYTHONPATH | Use `set PYTHONPATH=. && python3 lib/pipeline.py --stage check` |
| yt-dlp download fails | Update: `pip3 install --upgrade yt-dlp` — YouTube changes their format regularly |

For detailed setup instructions, see [AGENT_GUIDE.md](AGENT_GUIDE.md).

---

## License

MIT
