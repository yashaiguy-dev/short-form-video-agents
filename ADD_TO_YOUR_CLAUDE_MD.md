# Add This to Your CLAUDE.md

**GitHub:** [github.com/yashaiguy-dev/short-form-video-agents](https://github.com/yashaiguy-dev/short-form-video-agents)

If you use YT-to-Shorts alongside other projects, add the section below to your main `CLAUDE.md` file so your AI assistant knows how to find and run this pipeline from any directory.

Replace `/FULL/PATH/TO` with the actual path to your short-form-video-agents folder.

---

## Copy This Section

```markdown
## YT-to-Shorts Pipeline (YouTube Repurposing)

When the user asks to create short clips from a YouTube video, repurpose a YouTube video into shorts, clip a YouTube video, yt to shorts, or anything related to turning YouTube videos into short-form vertical clips:

1. Change to the `yt-to-shorts/` directory
2. Read `yt-to-shorts/AGENT_GUIDE.md`
3. Follow it step by step — all skills are inside `yt-to-shorts/skills/`
4. All Python commands must use `PYTHONPATH=/FULL/PATH/TO/yt-to-shorts` and run from that directory
5. The `.env` file with Gathos API key is at `yt-to-shorts/.env`

This works regardless of which directory the user is currently in.
```

---

## How It Works

When your AI assistant sees a request like "make me clips from this YouTube video", it:

1. Navigates to the yt-to-shorts folder
2. Reads the AGENT_GUIDE.md for step-by-step instructions
3. Runs the 8-stage pipeline (download → transcribe → select → prompts → images → assembly → subtitles)
4. Only pauses once — to show you clip selections for approval
5. Delivers final 9:16 vertical clips with editorial slides and animated subtitles

## Compatible AI Assistants

This works with any AI coding assistant that can read files and run terminal commands:
- Claude Code
- Cursor
- Qwen Code
- Gemini CLI
- Windsurf
- Any MCP-compatible assistant
