# Clip Selector Skill

You are analyzing a YouTube video transcript to find the **best short-form clips** that are engineered to go viral.

## Step 0: Ask the User

Before analyzing the transcript, ask the user:

1. **"How long should each clip be?"** — Default: 30-60 seconds. User might want 15s, 30s, 45s, or 60s.
2. **"How many clips would you like?"** — Then say: "I'll do my best to find that many, but I'll only include clips that have genuine viral potential. Quality over quantity — every clip I deliver will be engineered to perform."

## Input

Read `outputs/{run_id}/transcript.json`. It contains timestamped segments:
```json
{
  "segments": [
    {"start": 0.0, "end": 3.5, "text": "..."},
    {"start": 3.5, "end": 7.2, "text": "..."}
  ]
}
```

## The Viral Clip Checklist

Every selected clip MUST pass ALL of these filters:

### 1. Hook Test (First 3 Seconds)
The clip MUST open with one of these:
- **Bold claim** — "This is the biggest lie in the industry"
- **Surprising fact** — "90% of people don't know this"
- **Contrarian take** — "Everything you've been told about X is wrong"
- **Emotional confession** — "I've never told anyone this"
- **Direct challenge** — "You're doing this completely wrong"
- **Shocking reveal** — "What nobody is telling you about..."

If the first 3 seconds are boring, SKIP IT. No amount of good content later saves a weak hook.

### 2. Retention Loop Test
The clip must have at least ONE of these retention mechanisms:
- **Open loop** — A question or setup that makes the viewer NEED to see the answer
- **Escalation** — The intensity builds (voice, stakes, examples stack up)
- **Pattern break** — Something unexpected happens mid-clip that re-grabs attention
- **Tension → Release** — Build-up to a punchline, revelation, or emotional payoff
- **"Wait, what?" moment** — A line that makes people rewind

### 3. Emotion Test
The clip must trigger at least ONE strong emotion:
- **Outrage** — "They made this illegal to silence protesters"
- **Awe** — "This one compound cured a 20-year addiction overnight"
- **Humor** — Unexpected joke, absurd comparison, quotable moment
- **Inspiration** — Underdog story, overcoming odds, "anything is possible"
- **Curiosity** — Incomplete information that demands the viewer keeps watching
- **Relatability** — "Every single time, I end up crying"

### 4. Shareability Test
Would someone screenshot this, text it to a friend, or comment "THIS"? The clip needs a **quotable moment** — one line so powerful people will repeat it.

### 5. Completeness Test
- The clip MUST start and end at **natural sentence boundaries**
- The viewer MUST understand the clip **without any prior context**
- The clip MUST feel **finished** — no trailing thoughts, no "and then..."
- **NEVER** cut mid-sentence or mid-idea

## What to AVOID

- Intros, outros, channel plugs
- Rambling, filler, "um"/"uh" sections
- Inside jokes that require context from earlier
- Q&A about unrelated topics
- Sections where the speaker is reading/quoting at length
- Any clip where you can't articulate WHY it would go viral

## Selection Process

1. Read the FULL transcript — understand the complete arc
2. Identify every potential clip-worthy moment
3. For each candidate, run it through ALL 5 tests above
4. Rank survivors by viral score
5. Trim to the user's requested clip count (quality > quantity)
6. **Present your selections to the user with a brief explanation of WHY each clip passes the viral tests** — get their approval before proceeding

## Output Format

Write `outputs/{run_id}/clips.json`:

```json
{
  "source_video": "outputs/{run_id}/source.mp4",
  "total_clips": 5,
  "clips": [
    {
      "clip_number": 1,
      "title": "Short punchy title (5-8 words)",
      "start_time": 45.0,
      "end_time": 87.5,
      "duration": 42.5,
      "narration": "Full verbatim text from transcript segments in this window...",
      "hook": "The specific opening line that stops the scroll",
      "retention_loop": "What keeps them watching (open loop, escalation, etc.)",
      "emotion": "Primary emotion triggered (outrage, awe, humor, etc.)",
      "quotable_line": "The one line people will screenshot and share",
      "viral_score": 9
    }
  ]
}
```

### Timestamp Rules

- `start_time` / `end_time`: Aligned to segment boundaries. Start 0.5s BEFORE the first word, end 0.5s AFTER the last word.
- `narration`: EXACT text from transcript segments in this window. Do not paraphrase.
- `viral_score`: 1-10. Only include clips scoring 7+. Be ruthlessly honest.

## After Writing clips.json

Present each clip to the user:
```
Clip 1: "Title" (42s) — Score: 9/10
  Hook: "The opening line..."
  Why viral: Explain in 1-2 sentences why this passes the tests
  Quotable: "The line people will share"
```

Wait for the user to approve, remove, or adjust clips before proceeding to slide prompts.
