# Clip Slide Prompter Skill

You are generating **editorial illustration prompts** for the top-screen visual slides of each short clip. These slides appear in the top 608px of a 1080x1920 vertical video, with the original YouTube footage in the bottom 1312px.

## Input

Read `outputs/{run_id}/clips.json` (written by the clip-selector skill).

## Design System

Use this default dark editorial palette for all slides:

| Role       | Hex       |
|------------|-----------|
| background | `#0B0F14` |
| primary    | `#FF4D1F` |
| accent     | `#E8F538` |
| text       | `#FCFCFC` |
| grid       | `#1A2029` |

## CRITICAL: Slide Timing Rules

**Each slide MUST show for 3-4 seconds MAX.** This is the single most important rule. Slides that stay on screen for 7+ seconds kill engagement.

### Formula (MANDATORY)

```
num_slides = round(clip_duration / 3.5)
```

| Clip Duration | Required Slides |
|---------------|-----------------|
| 20s           | 6 slides        |
| 25s           | 7 slides        |
| 30s           | 9 slides        |
| 35s           | 10 slides       |
| 40s           | 11 slides       |
| 45s           | 13 slides       |
| 50s           | 14 slides       |
| 55s           | 16 slides       |
| 60s           | 17 slides       |

**If you generate fewer slides than the table shows, you are doing it WRONG.** Count your slides before writing the JSON.

### How to Segment

1. Read the clip's `narration` text and the `duration` field
2. Calculate: `num_slides = round(duration / 3.5)` — minimum 5, even for short clips
3. Split the narration into that many segments at natural thought boundaries
4. Each segment: **5-12 words** (maps to ~3-4 seconds at 2.5 words/sec)
5. The `weight` is the word count of the segment — used to calculate display duration

### Image Prompt Format

Every image prompt MUST follow this exact template:

```
A wide 16:9 bold editorial illustration on #0B0F14 background with subtle grid pattern in #1A2029. [SPECIFIC VISUAL METAPHOR — a concrete scene, object, icon, or diagram rendered in #FF4D1F and #E8F538]. Huge headline in bold geometric sans-serif ALL CAPS, color #FCFCFC: '[2-4 WORD HEADLINE]'. [Accent detail — underline bar, glow, or decorative element in #E8F538]. High contrast, editorial magazine aesthetic, designer-grade typography, clean composition.
```

### Visual Metaphor Rules

The visual metaphor is the MOST important part. It must be:
- **Specific and concrete** — not "symbolic iconography" but "a cracked trust meter with the needle at zero"
- **Unique to the narration content** — each slide gets a different visual idea
- **Vivid and descriptive** — 1-2 sentences describing exactly what the viewer sees
- **Using the palette colors** — primary and accent colors referenced by hex value
- **NEVER** describe the speaker or reference the video itself
- One dominant visual element, not a busy scene — this is seen at thumbnail size

### Headline Rules

- **2-4 words MAXIMUM** — ALL CAPS
- Captures the **core idea** — not the first 4 words of narration, but the KEY POINT
- Think "magazine cover headline" — punchy, provocative, memorable

### Examples of GREAT Slide Prompts

Narration: "Stop using Gamma for your presentations. They all look the same."
```
"A wide 16:9 bold editorial illustration on #0B0F14 background with subtle grid pattern in #1A2029. Massive red X mark in #FF4D1F slashing diagonally across two generic AI presentation thumbnails arranged in a grid — each showing a bland gradient with a fake pie chart. Huge headline in bold geometric sans-serif ALL CAPS, color #FCFCFC: 'STOP USING GAMMA'. Small #E8F538 underline accent bar below headline. High contrast, editorial magazine aesthetic, designer-grade typography, clean composition."
```

Narration: "Your credibility is gone before you even start talking."
```
"A wide 16:9 bold editorial illustration on #0B0F14 background with subtle grid pattern in #1A2029. A cracked trust meter gauge in #FF4D1F, the needle snapping from high to zero, with a #FCFCFC dial face. Above it, a dotted #E8F538 trajectory line shows credibility plunging downward. Huge headline in bold geometric sans-serif ALL CAPS, color #FCFCFC: 'CREDIBILITY GONE'. High contrast, editorial magazine aesthetic, designer-grade typography."
```

### Examples of BAD Slide Prompts (never do this)

- Generic: "symbolic iconography illustrating the concept" — TOO VAGUE
- Text-only: "Center: bold ALL CAPS text: 'MOST STARTUPS FAIL'" — NO VISUAL
- Dark/empty: "Deep black background with geometric patterns" — BORING
- Narration as headline: "PEOPLE LOVE TO SAY" — NOT A KEY POINT

## Output

Update `clips.json` — add `slide_segments` array to each clip:

```json
{
  "clips": [
    {
      "clip_number": 1,
      "title": "...",
      "start_time": 45.0,
      "end_time": 87.5,
      "duration": 42.5,
      "narration": "Full text...",
      "hook": "...",
      "viral_score": 9,
      "slide_segments": [
        {
          "segment_number": 1,
          "text": "First 5-12 words of the narration...",
          "weight": 8,
          "image_prompt": "A wide 16:9 bold editorial illustration on #0B0F14 background with subtle grid pattern in #1A2029. ..."
        },
        {
          "segment_number": 2,
          "text": "Next 5-12 words...",
          "weight": 10,
          "image_prompt": "A wide 16:9 bold editorial illustration on #0B0F14 background..."
        }
      ]
    }
  ]
}
```

## Process

1. Read clips.json
2. For each clip:
   a. Calculate `num_slides = round(duration / 3.5)` (minimum 5)
   b. Split narration into exactly that many segments (5-12 words each)
   c. For each segment, write a bold editorial image prompt following the template
   d. **VERIFY**: Count your slide_segments — it MUST match the formula. If a 30s clip has fewer than 8 slides, add more.
3. Write the updated clips.json back (preserving all existing fields)
