"""Word-by-word subtitle renderer for YT-to-Shorts pipeline.

Same rendering approach as video-agent-pipeline-comfyui/tools/subtitle-creator:
  - Montserrat Bold/ExtraBold fonts
  - Emphasis detection (content words get bigger)
  - Frame-by-frame rendering with OpenCV + Pillow
  - Drop shadow + outline + main text
  - Piped to FFmpeg for H.264 encoding

Word-level timestamps come from YouTube JSON3 captions (no Deepgram needed).
"""

import json
import os
import re
import shutil
import subprocess

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# --- Configuration ---
from lib.config import FONTS_DIR as _FONTS_DIR

FONT_DIR = str(_FONTS_DIR)
FONT_EMPHASIS = os.path.join(FONT_DIR, "Montserrat-ExtraBold.ttf")
FONT_REGULAR = os.path.join(FONT_DIR, "Montserrat-Bold.ttf")

DEFAULT_FONT_SIZE = 76
EMPHASIS_FONT_SIZE = 110
TEXT_COLOR = "#FFFFFF"
EMPHASIS_COLOR = "#FFFF00"  # Yellow highlight for emphasis words (configurable via .env)
SHADOW_OFFSET = 6
SHADOW_COLOR = "#000000"
SHADOW_OPACITY = 180
OUTLINE_WIDTH = 5

# Position: 36% from top = just below the 608px slide area
SUBTITLE_Y_PERCENT = 0.36

# Named color shortcuts
COLOR_NAMES = {
    "yellow": "#FFFF00",
    "red": "#FF4D1F",
    "green": "#00FF00",
    "lime": "#E8F538",
    "cyan": "#22D3EE",
    "orange": "#FF8C00",
    "white": "#FFFFFF",
    "pink": "#FF69B4",
}

# Skip words (not emphasized)
SKIP_WORDS = {
    "a", "an", "the", "i", "me", "my", "you", "your", "he", "she", "it", "we", "they",
    "him", "her", "us", "them", "his", "its", "our", "their", "this", "that", "these",
    "those", "myself", "yourself", "in", "on", "at", "to", "for", "of", "with", "by",
    "from", "up", "about", "into", "over", "after", "through", "between", "under",
    "around", "before", "during", "without", "within", "and", "but", "or", "nor", "so",
    "yet", "if", "then", "than", "because", "while", "when", "where", "how", "what",
    "is", "am", "are", "was", "were", "be", "been", "being", "do", "does", "did",
    "has", "have", "had", "will", "would", "could", "should", "might", "may", "can",
    "shall", "must", "just", "like", "really", "very", "also", "too", "well", "here",
    "there", "now", "not", "no", "yes", "oh", "uh", "um", "gonna", "gotta", "wanna",
    "kinda", "sorta", "get", "got", "go", "say", "said", "tell", "told", "know",
    "think", "see", "look", "come", "came", "make", "take", "let", "put", "give",
    "want", "need",
}


def _find_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if path:
        return path
    for c in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
        if os.path.isfile(c):
            return c
    return ""


def _find_ffprobe() -> str:
    path = shutil.which("ffprobe")
    if path:
        return path
    for c in ["/opt/homebrew/bin/ffprobe", "/usr/local/bin/ffprobe"]:
        if os.path.isfile(c):
            return c
    return ""


# --- Word-level parsing from YouTube JSON3 ---

def parse_words_from_json3(json3_path: str, clip_start: float, clip_end: float) -> list:
    """Extract word-level timestamps from YouTube JSON3 captions for a clip window."""
    with open(json3_path) as f:
        data = json.load(f)

    words = []
    for event in data.get("events", []):
        base_ms = event.get("tStartMs", 0)
        dur_ms = event.get("dDurationMs", 0)
        segs = event.get("segs", [])

        for seg in segs:
            text = seg.get("utf8", "").strip()
            if not text or text == "\n":
                continue

            offset_ms = seg.get("tOffsetMs", 0)
            word_start_s = (base_ms + offset_ms) / 1000.0

            # Skip words outside clip range
            if word_start_s < clip_start or word_start_s >= clip_end:
                continue

            # Estimate word end (next word's start or segment end)
            word_end_s = (base_ms + dur_ms) / 1000.0

            # Clean text
            clean = re.sub(r"\[.*?\]", "", text).strip()
            clean = re.sub(r">>\s*", "", clean).strip()
            if not clean:
                continue

            # Split multi-word segments into individual words
            for w in clean.split():
                w = w.strip()
                if not w:
                    continue
                words.append({
                    "word": w.lower(),
                    "punctuated_word": w,
                    "start": word_start_s - clip_start,
                    "end": word_end_s - clip_start,
                })

    # Fix word end times: each word ends when the next one starts
    for i in range(len(words) - 1):
        if words[i + 1]["start"] > words[i]["start"]:
            words[i]["end"] = words[i + 1]["start"]

    # Ensure all words have positive duration
    for w in words:
        if w["end"] <= w["start"]:
            w["end"] = w["start"] + 0.3

    return words


# --- Emphasis detection (same as ComfyUI pipeline) ---

def detect_emphasis(words: list) -> list:
    for w in words:
        clean = w["punctuated_word"].strip(".,!?;:\"'()[]{}…–—-").lower()
        w["emphasis"] = clean not in SKIP_WORDS and len(clean) >= 4
    return words


# --- Word grouping (same as ComfyUI pipeline) ---

def group_words_into_lines(words: list, max_chars: int = 25, max_words: int = 4) -> list:
    lines = []
    current_line = []
    current_len = 0

    for w in words:
        word_text = w["punctuated_word"]
        new_len = current_len + len(word_text) + (1 if current_line else 0)

        should_break = False
        if current_line:
            if new_len > max_chars or len(current_line) >= max_words:
                should_break = True
            elif w["start"] - current_line[-1]["end"] > 0.4:
                should_break = True
            elif current_line[-1]["punctuated_word"][-1] in ".!?":
                should_break = True

        if should_break and current_line:
            lines.append({
                "start": current_line[0]["start"],
                "end": current_line[-1]["end"],
                "words": current_line,
            })
            current_line = []
            current_len = 0

        current_line.append(w)
        current_len += len(word_text) + (1 if len(current_line) > 1 else 0)

    if current_line:
        lines.append({
            "start": current_line[0]["start"],
            "end": current_line[-1]["end"],
            "words": current_line,
        })

    return lines


# --- Frame-by-frame renderer (same as ComfyUI pipeline) ---

_font_cache = {}

def _get_font(path: str, size: int):
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _render_subtitle_on_frame(
    frame: np.ndarray,
    words: list,
    font_size: int,
    emphasis_size: int,
    text_color: str = TEXT_COLOR,
    emphasis_color: str = EMPHASIS_COLOR,
    y_percent: float = SUBTITLE_Y_PERCENT,
) -> np.ndarray:
    h, w = frame.shape[:2]
    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")

    fill_rgb = _hex_to_rgb(text_color)
    emph_rgb = _hex_to_rgb(emphasis_color)
    shadow_rgb = _hex_to_rgb(SHADOW_COLOR)

    try:
        font_regular = _get_font(FONT_REGULAR, font_size)
        font_emphasis = _get_font(FONT_EMPHASIS, emphasis_size)
    except OSError:
        font_regular = ImageFont.load_default()
        font_emphasis = font_regular

    max_line_width = int(w * 0.90)

    # Auto-scale to fit max 2 visual lines
    scale = 1.0
    for attempt in range(10):
        fs = int(font_size * scale)
        es = int(emphasis_size * scale)
        fr = _get_font(FONT_REGULAR, fs)
        fe = _get_font(FONT_EMPHASIS, es)
        sp_w = fr.getbbox(" ")[2]

        word_renders = []
        for wd in words:
            text = wd["punctuated_word"]
            is_emph = wd.get("emphasis", False)
            font = fe if is_emph else fr
            bbox = font.getbbox(text)
            tw = bbox[2] - bbox[0]
            font_ascent, font_descent = font.getmetrics()
            th = font_ascent + font_descent
            word_renders.append((text, font, tw, th, font_ascent, is_emph))

        visual_lines = []
        current_vline = []
        current_width = 0
        for wr in word_renders:
            word_w = wr[2]
            added_width = word_w + (sp_w if current_vline else 0)
            if current_vline and current_width + added_width > max_line_width:
                visual_lines.append(current_vline)
                current_vline = [wr]
                current_width = word_w
            else:
                current_vline.append(wr)
                current_width += added_width
        if current_vline:
            visual_lines.append(current_vline)

        if len(visual_lines) <= 2:
            break
        scale *= 0.85

    space_width = sp_w

    line_metrics = []
    for vline in visual_lines:
        max_asc = max(wr[4] for wr in vline)
        max_desc = max(wr[3] - wr[4] for wr in vline)
        total_h = max_asc + max_desc
        line_w = sum(wr[2] for wr in vline) + space_width * (len(vline) - 1)
        line_metrics.append({
            "ascent": max_asc, "descent": max_desc,
            "height": total_h, "width": line_w,
        })

    line_gap = int(font_size * 0.3)
    total_block_height = sum(m["height"] for m in line_metrics) + line_gap * (len(visual_lines) - 1)

    block_top = int(h * y_percent) - total_block_height // 2

    shadow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    text_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)

    y_cursor = block_top
    for line_idx, vline in enumerate(visual_lines):
        metrics = line_metrics[line_idx]
        x_start = (w - metrics["width"]) // 2
        x_cursor = x_start

        for text, font, tw, th, font_ascent, is_emph in vline:
            y_offset = y_cursor + (metrics["ascent"] - font_ascent)

            shadow_draw.text(
                (x_cursor + SHADOW_OFFSET, y_offset + SHADOW_OFFSET),
                text, font=font, fill=(*shadow_rgb, SHADOW_OPACITY),
            )

            outline_w = OUTLINE_WIDTH
            for dx in range(-outline_w, outline_w + 1):
                for dy in range(-outline_w, outline_w + 1):
                    if dx == 0 and dy == 0:
                        continue
                    text_draw.text(
                        (x_cursor + dx, y_offset + dy),
                        text, font=font, fill=(0, 0, 0, 220),
                    )

            word_color = emph_rgb if is_emph else fill_rgb
            text_draw.text(
                (x_cursor, y_offset),
                text, font=font, fill=(*word_color, 255),
            )

            x_cursor += tw + space_width

        y_cursor += metrics["height"] + line_gap

    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=3))
    pil_img = Image.alpha_composite(pil_img, shadow_layer)
    pil_img = Image.alpha_composite(pil_img, text_layer)

    return cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)


# --- Main subtitle burning pipeline ---

def burn_subtitles(
    video_path: str,
    json3_path: str,
    clip_start: float,
    clip_end: float,
    output_path: str,
    font_size: int = DEFAULT_FONT_SIZE,
    emphasis_size: int = EMPHASIS_FONT_SIZE,
    emphasis_color: str = EMPHASIS_COLOR,
) -> str:
    """Full pipeline: parse words → emphasis → group → render frame-by-frame.

    emphasis_color: color name or hex for emphasized words. Examples:
      "yellow", "red", "green", "lime", "cyan", "orange", "white", or any "#RRGGBB"
    """
    # Resolve named colors
    emphasis_color = COLOR_NAMES.get(emphasis_color.lower().strip(), emphasis_color)
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found")

    # 1. Parse word-level timestamps from YouTube captions
    words = parse_words_from_json3(json3_path, clip_start, clip_end)
    if not words:
        print("  [subtitles] WARNING: No words found in captions for this clip range", flush=True)
        shutil.copy2(video_path, output_path)
        return output_path

    print(f"  [subtitles] {len(words)} words parsed from captions", flush=True)

    # 2. Detect emphasis
    words = detect_emphasis(words)
    emphasized = sum(1 for w in words if w["emphasis"])
    print(f"  [subtitles] {emphasized}/{len(words)} words emphasized", flush=True)

    # 3. Group into subtitle lines
    subtitle_lines = group_words_into_lines(words)
    print(f"  [subtitles] {len(subtitle_lines)} subtitle lines", flush=True)

    # 4. Render frame-by-frame
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if os.path.exists(output_path):
        os.remove(output_path)

    cmd = [
        ffmpeg, "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{width}x{height}", "-pix_fmt", "bgr24",
        "-r", str(fps),
        "-i", "-",
        "-i", video_path,
        "-map", "0:v:0", "-map", "1:a:0?",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy", "-shortest",
        output_path,
    ]
    ffmpeg_proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )

    frame_idx = 0
    last_pct = -1

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = frame_idx / fps

        active_words = None
        for line in subtitle_lines:
            if line["start"] <= current_time <= line["end"]:
                active_words = line["words"]
                break

        if active_words:
            frame = _render_subtitle_on_frame(
                frame, active_words,
                font_size=font_size,
                emphasis_size=emphasis_size,
                emphasis_color=emphasis_color,
            )

        ffmpeg_proc.stdin.write(frame.tobytes())
        frame_idx += 1

        pct = int((frame_idx / total_frames) * 100)
        if pct != last_pct and pct % 10 == 0:
            print(f"  [subtitles] Rendering: {pct}%", flush=True)
            last_pct = pct

    cap.release()
    ffmpeg_proc.stdin.close()
    ffmpeg_proc.wait()

    if ffmpeg_proc.returncode != 0:
        stderr = ffmpeg_proc.stderr.read().decode()
        raise RuntimeError(f"FFmpeg encoding failed: {stderr[-500:]}")

    print(f"  [subtitles] Done → {os.path.basename(output_path)}", flush=True)
    return output_path
