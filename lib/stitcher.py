"""FFmpeg-based assembler for YT-to-Shorts pipeline.

Creates 9:16 vertical shorts with:
  - Top half (608px): Gathos editorial images with dissolve transitions
  - Bottom half (1312px): Original YouTube video (center-cropped)
  - Audio from the original YouTube video
"""

import os
import shutil
import subprocess

from lib.config import REEL_WIDTH, REEL_HEIGHT, TOP_HEIGHT, BOTTOM_HEIGHT, DISSOLVE_DURATION


def _find_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if path:
        return path
    for candidate in [
        "/opt/homebrew/bin/ffmpeg",
        "/opt/homebrew/Cellar/ffmpeg/8.1/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
    ]:
        if os.path.isfile(candidate):
            return candidate
    return ""


def _find_ffprobe() -> str:
    path = shutil.which("ffprobe")
    if path:
        return path
    for candidate in [
        "/opt/homebrew/bin/ffprobe",
        "/opt/homebrew/Cellar/ffmpeg/8.1/bin/ffprobe",
        "/usr/local/bin/ffprobe",
    ]:
        if os.path.isfile(candidate):
            return candidate
    return ""


def get_duration(path: str) -> float:
    ffprobe = _find_ffprobe()
    if not ffprobe:
        raise RuntimeError("ffprobe not found. Install ffmpeg.")
    cmd = [
        ffprobe, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return float(result.stdout.strip())
    raise RuntimeError(f"ffprobe failed: {result.stderr[:400]}")


def cut_clip(source_video: str, start: float, end: float, output_path: str) -> str:
    """Cut a segment from the source video using precise seeking."""
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    duration = end - start

    cmd = [
        ffmpeg, "-y",
        "-ss", str(start),
        "-i", source_video,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg cut failed: {result.stderr[:400]}")
    print(f"  [cut] {start:.1f}s → {end:.1f}s ({duration:.1f}s) → {os.path.basename(output_path)}", flush=True)
    return output_path


def create_slideshow(
    image_paths: list,
    durations: list,
    output_path: str,
    dissolve: float = None,
) -> str:
    """Create a video slideshow from images with dissolve transitions."""
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found")

    if dissolve is None:
        dissolve = DISSOLVE_DURATION

    n = len(image_paths)
    if n == 0:
        raise ValueError("No images for slideshow")

    w, h = REEL_WIDTH, TOP_HEIGHT
    scale_filter = (
        f"scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h},"
        f"format=yuv420p,setpts=PTS-STARTPTS"
    )

    if n == 1:
        total_dur = durations[0]
        cmd = [
            ffmpeg, "-y",
            "-loop", "1", "-t", str(total_dur),
            "-i", image_paths[0],
            "-vf", scale_filter,
            "-r", "24",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-movflags", "+faststart",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg slideshow (single) failed: {result.stderr[:400]}")
        return output_path

    inputs = []
    for i, img in enumerate(image_paths):
        inputs.extend(["-loop", "1", "-t", f"{durations[i]:.3f}", "-i", img])

    filter_parts = []
    for i in range(n):
        filter_parts.append(f"[{i}:v]{scale_filter}[v{i}]")

    prev = "v0"
    for i in range(1, n):
        cumulative = sum(durations[:i])
        offset = cumulative - i * dissolve
        offset = max(0, offset)
        out_label = f"xf{i}" if i < n - 1 else "vout"
        filter_parts.append(
            f"[{prev}][v{i}]xfade=transition=fade:duration={dissolve:.3f}:offset={offset:.3f}[{out_label}]"
        )
        prev = out_label

    filter_complex = ";".join(filter_parts)

    cmd = [
        ffmpeg, "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-r", "24",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-movflags", "+faststart",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg slideshow failed: {result.stderr[:600]}")
    return output_path


def composite_clip(
    slideshow_path: str,
    clip_video_path: str,
    output_path: str,
) -> str:
    """Composite a single clip: slides on top, video on bottom, audio from original.

    - Slideshow (top): REEL_WIDTH x TOP_HEIGHT
    - Video (bottom): center-cropped to fill REEL_WIDTH x BOTTOM_HEIGHT
    - Audio: from the original YouTube clip
    """
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found")

    clip_duration = get_duration(clip_video_path)
    w, h_bottom = REEL_WIDTH, BOTTOM_HEIGHT

    filter_complex = (
        f"[1:v]scale={w}:{h_bottom}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h_bottom}[bottom];"
        f"[0:v][bottom]vstack=inputs=2[out]"
    )

    cmd = [
        ffmpeg, "-y",
        "-i", slideshow_path,
        "-i", clip_video_path,
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", "24",
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(clip_duration),
        "-movflags", "+faststart",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg composite failed: {result.stderr[:600]}")
    print(f"  [composite] {os.path.basename(output_path)} ({clip_duration:.1f}s)", flush=True)
    return output_path
