"""Main orchestrator for YT-to-Shorts pipeline.

Stages:
  check      — verify all dependencies and configuration
  download   — yt-dlp downloads video + subtitles
  transcribe — parse subtitles into structured transcript
  slides     — Gathos generates editorial images per clip
  assembly   — FFmpeg cuts, composites, and outputs final clips
  subtitles  — burn bold white subtitles below the slide area

The 'select' stage is handled by the AI agent (reads transcript, writes clips.json).
"""

import argparse
import json
import os
import sys

from lib.config import load_config, check_setup
from lib.state import RunState
from lib.downloader import download_video
from lib.transcriber import transcribe
from lib.gathos_client import GathosClient
from lib.stitcher import cut_clip, create_slideshow, composite_clip, get_duration
from lib.subtitler import burn_subtitles


def stage_download(url: str, cfg: dict, state: RunState):
    """Download YouTube video and subtitles."""
    state.update_stage("download", status="in_progress")
    run_dir = os.path.join(cfg["outputs_dir"], state.run_id)

    result = download_video(url, run_dir)

    state.data["source_video"] = result["source_video"]
    state.data["captions_file"] = result["captions_file"]
    state.data["title"] = result["title"]
    state.data["video_duration"] = result["duration"]
    state.update_stage("download", status="complete")

    print(f"\n[pipeline] Download complete.", flush=True)
    print(f"  Video: {result['source_video']}", flush=True)
    print(f"  Captions: {result['captions_file'] or 'NONE'}", flush=True)


def stage_transcribe(cfg: dict, state: RunState):
    """Parse subtitles into structured transcript."""
    state.update_stage("transcribe", status="in_progress")

    captions_file = state.data.get("captions_file")
    if not captions_file:
        print("[transcribe] ERROR: No captions file found. Try a video with auto-captions.", flush=True)
        state.update_stage("transcribe", status="failed")
        sys.exit(1)

    run_dir = os.path.join(cfg["outputs_dir"], state.run_id)
    transcript_path = os.path.join(run_dir, "transcript.json")

    transcribe(captions_file, transcript_path)
    state.data["transcript_file"] = transcript_path
    state.update_stage("transcribe", status="complete")

    print(f"\n[pipeline] Transcript ready: {transcript_path}", flush=True)
    print("[pipeline] Next: AI agent reads transcript and writes clips.json", flush=True)


def stage_slides(cfg: dict, state: RunState):
    """Generate Gathos editorial images for each clip's slide segments."""
    state.update_stage("slides", status="in_progress")

    run_dir = os.path.join(cfg["outputs_dir"], state.run_id)
    clips_path = os.path.join(run_dir, "clips.json")

    if not os.path.exists(clips_path):
        print("[slides] ERROR: clips.json not found. Run clip selection first.", flush=True)
        state.update_stage("slides", status="failed")
        sys.exit(1)

    with open(clips_path) as f:
        clips_data = json.load(f)

    client = GathosClient(cfg["gathos_api_key"])
    prompts_and_paths = []

    for clip in clips_data["clips"]:
        cn = clip["clip_number"]
        for seg in clip.get("slide_segments", []):
            sn = seg["segment_number"]
            path = os.path.join(run_dir, f"clip_{cn:03d}_slide_{sn:02d}.png")
            prompts_and_paths.append((seg["image_prompt"], path))

    if not prompts_and_paths:
        print("[slides] ERROR: No slide prompts found in clips.json.", flush=True)
        state.update_stage("slides", status="failed")
        sys.exit(1)

    print(f"[slides] Generating {len(prompts_and_paths)} images via Gathos...", flush=True)
    results = client.generate_batch(prompts_and_paths, spacing=8.0)
    print(f"[slides] Done — {len(results)} images generated.", flush=True)

    for clip in clips_data["clips"]:
        cn = clip["clip_number"]
        for seg in clip.get("slide_segments", []):
            sn = seg["segment_number"]
            path = os.path.join(run_dir, f"clip_{cn:03d}_slide_{sn:02d}.png")
            if os.path.exists(path):
                state.mark_clip_asset(cn, f"slide_{sn}", path)

    state.update_stage("slides", status="complete")


def stage_assembly(cfg: dict, state: RunState):
    """Cut clips from source, create slideshows, composite final shorts."""
    state.update_stage("assembly", status="in_progress")

    run_dir = os.path.join(cfg["outputs_dir"], state.run_id)
    clips_path = os.path.join(run_dir, "clips.json")
    source_video = state.data.get("source_video")

    if not os.path.exists(clips_path):
        print("[assembly] ERROR: clips.json not found.", flush=True)
        sys.exit(1)
    if not source_video or not os.path.exists(source_video):
        print("[assembly] ERROR: Source video not found.", flush=True)
        sys.exit(1)

    with open(clips_path) as f:
        clips_data = json.load(f)

    final_clips = []

    for clip in clips_data["clips"]:
        cn = clip["clip_number"]
        start = clip["start_time"]
        end = clip["end_time"]
        print(f"\n[assembly] Processing clip {cn}: {clip.get('title', '')} ({start:.1f}s → {end:.1f}s)", flush=True)

        # Step 1: Cut clip from source video
        cut_path = os.path.join(run_dir, f"clip_{cn:03d}_cut.mp4")
        if not os.path.exists(cut_path):
            cut_clip(source_video, start, end, cut_path)
        else:
            print(f"  [cut] already exists: {os.path.basename(cut_path)}", flush=True)

        clip_duration = get_duration(cut_path)

        # Step 2: Gather slide images and calculate durations
        slide_segments = clip.get("slide_segments", [])
        slide_paths = []
        for seg in slide_segments:
            sn = seg["segment_number"]
            path = os.path.join(run_dir, f"clip_{cn:03d}_slide_{sn:02d}.png")
            if os.path.exists(path):
                slide_paths.append((path, seg.get("weight", 1)))

        if not slide_paths:
            print(f"  [assembly] WARNING: No slide images for clip {cn}, skipping composite.", flush=True)
            final_clips.append(cut_path)
            continue

        # Calculate per-slide durations based on weights
        total_weight = sum(w for _, w in slide_paths)
        slide_durations = [(w / total_weight) * clip_duration for _, w in slide_paths]
        image_paths = [p for p, _ in slide_paths]

        # Step 3: Create slideshow
        slideshow_path = os.path.join(run_dir, f"clip_{cn:03d}_slideshow.mp4")
        if not os.path.exists(slideshow_path):
            create_slideshow(image_paths, slide_durations, slideshow_path)
        else:
            print(f"  [slideshow] already exists", flush=True)

        # Step 4: Composite (slides top + video bottom)
        final_path = os.path.join(run_dir, f"clip_{cn:03d}_final.mp4")
        if not os.path.exists(final_path):
            composite_clip(slideshow_path, cut_path, final_path)
        else:
            print(f"  [composite] already exists", flush=True)

        final_clips.append(final_path)
        state.mark_clip_asset(cn, "final", final_path)

    state.update_stage("assembly", status="complete")

    print(f"\n{'='*60}", flush=True)
    print(f"[pipeline] Assembly DONE — {len(final_clips)} clips generated:", flush=True)
    for path in final_clips:
        if os.path.exists(path):
            dur = get_duration(path)
            print(f"  {path} ({dur:.1f}s)", flush=True)
    print(f"{'='*60}", flush=True)


def stage_subtitles(cfg: dict, state: RunState):
    """Burn bold white subtitles into each clip, positioned below the slides."""
    state.update_stage("subtitles", status="in_progress") if "subtitles" in state.data.get("stages", {}) else None

    run_dir = os.path.join(cfg["outputs_dir"], state.run_id)
    clips_path = os.path.join(run_dir, "clips.json")
    captions_file = state.data.get("captions_file")

    if not os.path.exists(clips_path):
        print("[subtitles] ERROR: clips.json not found.", flush=True)
        sys.exit(1)
    if not captions_file or not os.path.exists(captions_file):
        print("[subtitles] ERROR: captions file not found.", flush=True)
        sys.exit(1)

    with open(clips_path) as f:
        clips_data = json.load(f)

    subtitled_clips = []

    for clip in clips_data["clips"]:
        cn = clip["clip_number"]
        start = clip["start_time"]
        end = clip["end_time"]
        final_path = os.path.join(run_dir, f"clip_{cn:03d}_final.mp4")
        sub_path = os.path.join(run_dir, f"clip_{cn:03d}_subtitled.mp4")

        if not os.path.exists(final_path):
            print(f"  [subtitles] clip_{cn:03d}_final.mp4 not found, skipping", flush=True)
            continue

        if os.path.exists(sub_path):
            print(f"  [subtitles] clip_{cn:03d}_subtitled.mp4 already exists, skipping", flush=True)
            subtitled_clips.append(sub_path)
            continue

        print(f"\n[subtitles] Processing clip {cn}: {clip.get('title', '')}", flush=True)

        # Full subtitle pipeline: parse words → emphasis → group → render frame-by-frame
        emph_color = cfg.get("subtitle_emphasis_color", "#FFFF00")
        burn_subtitles(final_path, captions_file, start, end, sub_path, emphasis_color=emph_color)
        subtitled_clips.append(sub_path)
        state.mark_clip_asset(cn, "subtitled", sub_path)

    state.data["status"] = "complete"
    state._save()

    print(f"\n{'='*60}", flush=True)
    print(f"[pipeline] DONE — {len(subtitled_clips)} subtitled clips:", flush=True)
    for path in subtitled_clips:
        if os.path.exists(path):
            dur = get_duration(path)
            print(f"  {path} ({dur:.1f}s)", flush=True)
    print(f"{'='*60}", flush=True)


def stage_check():
    """Verify all dependencies and configuration are in place."""
    results = check_setup()

    print("\n  YT-to-Shorts — Setup Check\n", flush=True)

    all_ok = True
    sections = [
        ("Python Packages", ["yt-dlp", "opencv-python", "numpy", "Pillow"]),
        ("System Tools", ["ffmpeg", "ffprobe", "yt-dlp-cli"]),
        ("Project Files", ["fonts", ".env"]),
        ("API Keys", ["gathos_api_key"]),
    ]

    for section_name, keys in sections:
        print(f"  {section_name}:", flush=True)
        for key in keys:
            ok = results.get(key, False)
            icon = "OK" if ok else "MISSING"
            print(f"    [{icon}] {key}", flush=True)
            if not ok:
                all_ok = False
        print(flush=True)

    if all_ok:
        print("  All checks passed! Ready to go.\n", flush=True)
    else:
        print("  Some checks failed. Fix the issues above and run again.", flush=True)
        print("  See README.md for setup instructions.\n", flush=True)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="YT-to-Shorts pipeline")
    parser.add_argument("--stage", required=True, choices=["check", "download", "transcribe", "slides", "assembly", "subtitles"])
    parser.add_argument("--url", help="YouTube URL (required for download stage)")
    parser.add_argument("--run-id", help="Resume a specific run")
    parser.add_argument("--subtitle-color", help="Subtitle emphasis color: yellow, red, green, lime, cyan, orange, pink, white, or #RRGGBB")
    args = parser.parse_args()

    if args.stage == "check":
        stage_check()
        return

    cfg = load_config()

    if args.subtitle_color:
        cfg["subtitle_emphasis_color"] = args.subtitle_color

    state = RunState(cfg["state_dir"])

    if args.stage == "download":
        if not args.url:
            print("ERROR: --url is required for download stage", flush=True)
            sys.exit(1)
        state.create_run(args.url)
        stage_download(args.url, cfg, state)
    else:
        if args.run_id:
            if not state.load_run(args.run_id):
                print(f"ERROR: Run {args.run_id} not found", flush=True)
                sys.exit(1)
        else:
            if not state.load_latest():
                print("ERROR: No runs found. Run download stage first.", flush=True)
                sys.exit(1)
        print(f"[pipeline] Resuming run: {state.run_id}", flush=True)

        if args.stage == "transcribe":
            stage_transcribe(cfg, state)
        elif args.stage == "slides":
            stage_slides(cfg, state)
        elif args.stage == "assembly":
            stage_assembly(cfg, state)
        elif args.stage == "subtitles":
            stage_subtitles(cfg, state)


if __name__ == "__main__":
    main()
