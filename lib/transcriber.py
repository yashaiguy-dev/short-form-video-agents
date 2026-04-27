"""Transcript parser for YouTube auto-generated subtitles.

Supports JSON3 (word-level) and VTT (segment-level) formats.
Outputs a structured transcript.json for AI clip selection.
"""

import json
import os
import re


def parse_json3(filepath: str) -> list:
    """Parse YouTube JSON3 subtitle format into timestamped segments."""
    with open(filepath) as f:
        data = json.load(f)

    events = data.get("events", [])
    segments = []

    for event in events:
        start_ms = event.get("tStartMs", 0)
        duration_ms = event.get("dDurationMs", 0)
        segs = event.get("segs", [])

        if not segs:
            continue

        text_parts = []
        for seg in segs:
            utf8 = seg.get("utf8", "")
            if utf8 and utf8.strip() != "\n":
                text_parts.append(utf8.strip())

        text = " ".join(text_parts).strip()
        if not text:
            continue

        segments.append({
            "start": round(start_ms / 1000.0, 2),
            "end": round((start_ms + duration_ms) / 1000.0, 2),
            "text": text,
        })

    return _merge_short_segments(segments)


def parse_vtt(filepath: str) -> list:
    """Parse VTT subtitle format into timestamped segments."""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    # Remove WEBVTT header and metadata
    content = re.sub(r"^WEBVTT.*?\n\n", "", content, flags=re.DOTALL)
    # Remove style blocks
    content = re.sub(r"STYLE\n.*?\n\n", "", content, flags=re.DOTALL)

    blocks = content.strip().split("\n\n")
    segments = []
    seen_texts = set()

    for block in blocks:
        lines = block.strip().split("\n")
        timestamp_line = None
        text_lines = []

        for line in lines:
            if "-->" in line:
                timestamp_line = line
            elif timestamp_line is not None:
                # Strip VTT tags like <c> </c> <00:01:23.456>
                clean = re.sub(r"<[^>]+>", "", line).strip()
                if clean:
                    text_lines.append(clean)

        if not timestamp_line or not text_lines:
            continue

        # Parse timestamps
        match = re.match(
            r"(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})",
            timestamp_line,
        )
        if not match:
            continue

        start = _vtt_time_to_seconds(match.group(1))
        end = _vtt_time_to_seconds(match.group(2))
        text = " ".join(text_lines).strip()

        # Deduplicate (VTT often has overlapping segments)
        if text not in seen_texts:
            seen_texts.add(text)
            segments.append({"start": round(start, 2), "end": round(end, 2), "text": text})

    return _merge_short_segments(segments)


def _vtt_time_to_seconds(time_str: str) -> float:
    parts = time_str.split(":")
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds


def _merge_short_segments(segments: list, min_duration: float = 1.0) -> list:
    """Merge very short segments into their neighbors for cleaner transcript."""
    if not segments:
        return segments

    merged = [segments[0].copy()]
    for seg in segments[1:]:
        prev = merged[-1]
        gap = seg["start"] - prev["end"]
        if gap < 0.5 and (prev["end"] - prev["start"]) < min_duration:
            prev["text"] = prev["text"] + " " + seg["text"]
            prev["end"] = seg["end"]
        else:
            merged.append(seg.copy())

    return merged


def transcribe(captions_file: str, output_path: str) -> list:
    """Parse captions file and write structured transcript.json.

    Returns the list of timestamped segments.
    """
    if captions_file.endswith(".json3"):
        segments = parse_json3(captions_file)
    elif captions_file.endswith(".vtt"):
        segments = parse_vtt(captions_file)
    else:
        raise ValueError(f"Unsupported subtitle format: {captions_file}")

    print(f"[transcribe] Parsed {len(segments)} segments", flush=True)

    total_words = sum(len(s["text"].split()) for s in segments)
    duration = segments[-1]["end"] if segments else 0
    print(f"[transcribe] Total: {total_words} words, {duration:.1f}s", flush=True)

    output = {
        "total_segments": len(segments),
        "total_words": total_words,
        "duration_seconds": duration,
        "segments": segments,
    }

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"[transcribe] Saved: {output_path}", flush=True)
    return segments
