"""Gathos Image Generation API client for YT-to-Shorts pipeline."""

import base64
import json
import os
import time
import urllib.request
import urllib.error

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
BASE_URL = "https://gathos.com"


class GathosClient:
    def __init__(self, api_key: str, width: int = 1344, height: int = 768):
        self.api_key = api_key
        self.width = width
        self.height = height

    def _post(self, url: str, body: dict) -> dict:
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": UA,
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())

    def _get(self, url: str) -> dict:
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": UA,
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())

    def submit_image(self, prompt: str) -> str:
        for attempt in range(10):
            try:
                resp = self._post(
                    f"{BASE_URL}/api/v1/image-generation",
                    {"prompt": prompt, "width": self.width, "height": self.height},
                )
                return resp["job_id"]
            except urllib.error.HTTPError as e:
                if e.code in (429, 502, 503, 504):
                    wait = 15 * (attempt + 1)
                    print(f"  [gathos] HTTP {e.code}, backing off {wait}s", flush=True)
                    time.sleep(wait)
                    continue
                raise
            except Exception as e:
                wait = 10 * (attempt + 1)
                print(f"  [gathos] {type(e).__name__}, backing off {wait}s", flush=True)
                time.sleep(wait)
                continue
        raise RuntimeError("Gathos submission failed after 10 retries")

    def poll_job(self, job_id: str, timeout: int = 900) -> bytes:
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(5)
            try:
                r = self._get(f"{BASE_URL}/api/v1/image-generation/jobs/{job_id}")
            except urllib.error.HTTPError:
                continue
            status = r.get("status")
            if status == "completed":
                return base64.b64decode(r["result"]["image_base64"])
            elif status == "failed":
                raise RuntimeError(f"Gathos job failed: {r.get('error')}")
            else:
                pct = r.get("progress", 0)
                print(f"  [gathos] {job_id[:12]}... {status} ({pct}%)", flush=True)
        raise TimeoutError(f"Gathos job {job_id} timed out after {timeout}s")

    def generate_image(self, prompt: str, save_path: str) -> str:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        job_id = self.submit_image(prompt)
        print(f"  [gathos] submitted: {job_id[:12]}...", flush=True)
        image_data = self.poll_job(job_id)
        with open(save_path, "wb") as f:
            f.write(image_data)
        return save_path

    def generate_batch(self, prompts_and_paths: list, spacing: float = 8.0) -> list:
        jobs = {}
        for prompt, save_path in prompts_and_paths:
            if os.path.exists(save_path):
                print(f"  [gathos] {os.path.basename(save_path)} exists, skipping", flush=True)
                continue
            job_id = self.submit_image(prompt)
            jobs[save_path] = job_id
            print(f"  [gathos] {os.path.basename(save_path)} submitted: {job_id[:12]}...", flush=True)
            time.sleep(spacing)

        if not jobs:
            return []

        print(f"  [gathos] polling {len(jobs)} jobs...", flush=True)
        deadline = time.time() + 900
        pending = set(jobs.keys())
        results = []

        while pending and time.time() < deadline:
            time.sleep(5)
            for path in list(pending):
                try:
                    r = self._get(f"{BASE_URL}/api/v1/image-generation/jobs/{jobs[path]}")
                except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
                    continue
                status = r.get("status")
                if status == "completed":
                    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                    image_data = base64.b64decode(r["result"]["image_base64"])
                    with open(path, "wb") as f:
                        f.write(image_data)
                    print(f"  [gathos] {os.path.basename(path)} done", flush=True)
                    pending.discard(path)
                    results.append(path)
                elif status == "failed":
                    print(f"  [gathos] {os.path.basename(path)} FAILED: {r.get('error')}", flush=True)
                    pending.discard(path)

        if pending:
            print(f"  [gathos] TIMEOUT — still pending: {[os.path.basename(p) for p in pending]}", flush=True)

        return results
