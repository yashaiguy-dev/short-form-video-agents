"""Configuration for YT-to-Shorts pipeline."""

import os
import shutil
from pathlib import Path

REEL_WIDTH = 1080
REEL_HEIGHT = 1920
TOP_HEIGHT = 608
BOTTOM_HEIGHT = 1312

GATHOS_IMAGE_WIDTH = 1344
GATHOS_IMAGE_HEIGHT = 768

DISSOLVE_DURATION = 0.5

BASE_DIR = Path(__file__).parent.parent
FONTS_DIR = BASE_DIR / "fonts"


def load_config(env_path: str = None, check_only: bool = False) -> dict:
    if env_path is None:
        env_path = str(BASE_DIR / ".env")

    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                env_vars[key.strip()] = value.strip().strip('"').strip("'")

    gathos_key = os.environ.get("GATHOS_IMAGE_API_KEY", env_vars.get("GATHOS_IMAGE_API_KEY", ""))
    if not gathos_key and not check_only:
        raise ValueError("GATHOS_IMAGE_API_KEY is required in .env")

    return {
        "gathos_api_key": gathos_key,
        "base_dir": str(BASE_DIR),
        "outputs_dir": str(BASE_DIR / "outputs"),
        "state_dir": str(BASE_DIR / "state"),
        "fonts_dir": str(FONTS_DIR),
        "subtitle_emphasis_color": env_vars.get("SUBTITLE_EMPHASIS_COLOR", "#FFFF00"),
    }


def check_setup() -> dict:
    """Verify all dependencies and configuration are in place."""
    results = {}

    cfg = load_config(check_only=True)

    # Python packages
    for pkg, import_name in [("yt-dlp", "yt_dlp"), ("opencv-python", "cv2"), ("numpy", "numpy"), ("Pillow", "PIL")]:
        try:
            __import__(import_name)
            results[pkg] = True
        except ImportError:
            results[pkg] = False

    # System tools
    results["ffmpeg"] = bool(shutil.which("ffmpeg") or os.path.isfile("/opt/homebrew/bin/ffmpeg") or os.path.isfile("/usr/local/bin/ffmpeg"))
    results["ffprobe"] = bool(shutil.which("ffprobe") or os.path.isfile("/opt/homebrew/bin/ffprobe") or os.path.isfile("/usr/local/bin/ffprobe"))
    yt_dlp_path = shutil.which("yt-dlp")
    if not yt_dlp_path:
        for c in ["/opt/homebrew/bin/yt-dlp", "/usr/local/bin/yt-dlp"]:
            if os.path.isfile(c):
                yt_dlp_path = c
                break
    results["yt-dlp-cli"] = bool(yt_dlp_path)

    # Fonts
    results["fonts"] = (FONTS_DIR / "Montserrat-Bold.ttf").is_file() and (FONTS_DIR / "Montserrat-ExtraBold.ttf").is_file()

    # API key
    results["gathos_api_key"] = bool(cfg.get("gathos_api_key"))

    # .env file
    results[".env"] = os.path.isfile(str(BASE_DIR / ".env"))

    return results
