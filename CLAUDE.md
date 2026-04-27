# YT-to-Shorts

When the user asks to create short clips from a YouTube video, repurpose a YouTube video, clip a YouTube video, or anything related to yt-to-shorts — read `AGENT_GUIDE.md` in this directory and follow it step by step.

All skills are in the `skills/` folder within this project. Do NOT reference external skills or commands — everything is self-contained here.

Always use `PYTHONPATH=.` when running Python commands from this directory.

## Key Rules

- **Slide timing**: Each editorial slide MUST show for 3-4 seconds. A 30s clip needs ~9 slides. Never generate fewer than the formula requires (`duration / 3.5`).
- **Subtitle color**: Ask the user which emphasis color they want. Pass it via `--subtitle-color` on the subtitles stage.
- **Loop mode**: When the user wants batch clips, run all stages in sequence. Only pause for clip selection approval.
- **Setup**: If the user is new, run `--stage check` first. Guide them through fixing any `[MISSING]` items.
