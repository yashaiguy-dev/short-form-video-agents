"""YouTube video downloader using yt-dlp."""

import json
import os
import shutil
import subprocess


def _find_ytdlp() -> str:
    path = shutil.which("yt-dlp")
    if path:
        return path
    for candidate in [
        "/opt/homebrew/bin/yt-dlp",
        "/usr/local/bin/yt-dlp",
    ]:
        if os.path.isfile(candidate):
            return candidate
    raise RuntimeError("yt-dlp not found. Install with: pip3 install yt-dlp")


def download_video(url: str, output_dir: str) -> dict:
    """Download a YouTube video and its auto-generated subtitles.

    Returns dict with paths: source_video, captions_file (or None), video_title.
    """
    ytdlp = _find_ytdlp()
    os.makedirs(output_dir, exist_ok=True)

    video_path = os.path.join(output_dir, "source.mp4")
    info_path = os.path.join(output_dir, "info.json")

    # Step 1: Get video info (title, duration, etc.)
    print("[download] Fetching video info...", flush=True)
    cmd_info = [
        ytdlp, "--dump-json", "--no-download", url,
    ]
    result = subprocess.run(cmd_info, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp info failed: {result.stderr[:500]}")

    info = json.loads(result.stdout)
    title = info.get("title", "Untitled")
    duration = info.get("duration", 0)
    print(f"[download] Title: {title}", flush=True)
    print(f"[download] Duration: {duration}s", flush=True)

    with open(info_path, "w") as f:
        json.dump({"title": title, "duration": duration, "url": url}, f, indent=2)

    # Step 2: Download video (best quality <=1080p)
    if not os.path.exists(video_path):
        print("[download] Downloading video...", flush=True)
        # Ensure ffmpeg is in PATH for yt-dlp merging
        env = os.environ.copy()
        ffmpeg_dir = ""
        for candidate in ["/opt/homebrew/bin", "/usr/local/bin"]:
            if os.path.isfile(os.path.join(candidate, "ffmpeg")):
                ffmpeg_dir = candidate
                break
        if ffmpeg_dir and ffmpeg_dir not in env.get("PATH", ""):
            env["PATH"] = ffmpeg_dir + ":" + env.get("PATH", "")

        cmd_dl = [
            ytdlp,
            "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "--merge-output-format", "mp4",
            "-o", video_path,
            "--no-playlist",
            url,
        ]
        result = subprocess.run(cmd_dl, capture_output=True, text=True, timeout=600, env=env)
        if result.returncode != 0:
            raise RuntimeError(f"yt-dlp download failed: {result.stderr[:500]}")
        print(f"[download] Video saved: {video_path}", flush=True)
    else:
        print(f"[download] Video already exists: {video_path}", flush=True)

    # Step 3: Download auto-generated subtitles (JSON3 for word-level timestamps)
    captions_file = None
    print("[download] Extracting subtitles...", flush=True)
    cmd_subs = [
        ytdlp,
        "--write-auto-sub",
        "--sub-lang", "en",
        "--sub-format", "json3",
        "--skip-download",
        "-o", os.path.join(output_dir, "captions"),
        url,
    ]
    result = subprocess.run(cmd_subs, capture_output=True, text=True, timeout=120)

    # Look for the downloaded subtitle file
    for ext in [".en.json3", ".json3"]:
        candidate = os.path.join(output_dir, f"captions{ext}")
        if os.path.exists(candidate):
            captions_file = candidate
            break

    # Fallback: try VTT format
    if not captions_file:
        print("[download] JSON3 subs not found, trying VTT...", flush=True)
        cmd_vtt = [
            ytdlp,
            "--write-auto-sub",
            "--sub-lang", "en",
            "--sub-format", "vtt",
            "--skip-download",
            "-o", os.path.join(output_dir, "captions"),
            url,
        ]
        subprocess.run(cmd_vtt, capture_output=True, text=True, timeout=120)
        for ext in [".en.vtt", ".vtt"]:
            candidate = os.path.join(output_dir, f"captions{ext}")
            if os.path.exists(candidate):
                captions_file = candidate
                break

    if captions_file:
        print(f"[download] Subtitles saved: {captions_file}", flush=True)
    else:
        print("[download] WARNING: No auto-captions found for this video.", flush=True)

    return {
        "source_video": video_path,
        "captions_file": captions_file,
        "title": title,
        "duration": duration,
    }
