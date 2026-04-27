"""Run state manager for YT-to-Shorts pipeline."""

import json
import os
import re
from datetime import datetime
from pathlib import Path


def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text.strip())
    return text[:40].rstrip("-")


class RunState:
    def __init__(self, state_dir: str):
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self.run_id: str = ""
        self.data: dict = {}

    def create_run(self, url: str, title: str = "") -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        slug = _slugify(title or "yt-clip")
        run_id = f"{timestamp}_{slug}"

        self.run_id = run_id
        self.data = {
            "run_id": run_id,
            "status": "in_progress",
            "url": url,
            "title": title,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "stages": {
                "download": {"status": "pending"},
                "transcribe": {"status": "pending"},
                "select": {"status": "pending"},
                "slides": {"status": "pending"},
                "assembly": {"status": "pending"},
            },
            "clip_assets": {},
        }
        self._save()
        return run_id

    def load_latest(self) -> bool:
        files = sorted(
            self._state_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not files:
            return False
        return self._load_file(files[0])

    def load_run(self, run_id: str) -> bool:
        path = self._state_dir / f"{run_id}.json"
        if not path.exists():
            return False
        return self._load_file(path)

    def update_stage(self, stage: str, **kwargs):
        self.data["stages"][stage].update(kwargs)
        self._save()

    def mark_clip_asset(self, clip_num: int, asset_type: str, path: str):
        key = str(clip_num)
        if key not in self.data["clip_assets"]:
            self.data["clip_assets"][key] = {}
        self.data["clip_assets"][key][asset_type] = path
        self._save()

    def _file_path(self) -> Path:
        return self._state_dir / f"{self.run_id}.json"

    def _save(self):
        self._file_path().write_text(json.dumps(self.data, indent=2))

    def _load_file(self, path: Path) -> bool:
        try:
            self.data = json.loads(path.read_text())
            self.run_id = self.data.get("run_id", path.stem)
            return True
        except (json.JSONDecodeError, OSError):
            return False
