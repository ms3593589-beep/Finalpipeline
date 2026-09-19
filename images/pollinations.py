"""Pollinations.ai primary image generation provider with Bearer auth and error guards."""

import base64
import io
import time
import urllib.parse
from typing import Optional, List
from PIL import Image

from core import config
from images.base import ImageProvider


class PollinationsProvider(ImageProvider):
    """Primary image generator interfacing with Pollinations.ai."""

    def __init__(self):
        self.base_url = config.POLLINATIONS_BASE_URL.rstrip("/")
        self.api_key = config.POLLINATIONS_API_KEY
        self.is_exhausted = False
        self.last_request_time = 0.0
        self.active_model = None

    def name(self) -> str:
        return "pollinations"

    def is_available(self) -> bool:
        return bool(self.api_key) and not self.is_exhausted

    def _throttle(self):
        """Enforces minimum interval between consecutive API requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < config.POLLINATIONS_MIN_INTERVAL_S:
            time.sleep(config.POLLINATIONS_MIN_INTERVAL_S - elapsed)
        self.last_request_time = time.time()

    def discover_active_model(self) -> str:
        """Queries /image/models and selects first available preference match."""
        if self.active_model:
            return self.active_model

        default_model = config.IMAGE_MODEL_PREFERENCE[0]
        if not self.api_key:
            return default_model

        try:
            import requests
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = requests.get(f"{self.base_url}/image/models", headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                available_names = set()
                if isinstance(data, list):
                    for item in data:
                        name = item.get("name") or item.get("id")
                        if name:
                            available_names.add(name.lower())
                elif isinstance(data, dict):
                    for name in data.keys():
                        available_names.add(name.lower())

                for pref in config.IMAGE_MODEL_PREFERENCE:
                    clean_pref = pref.strip().lower()
                    if clean_pref in available_names:
                        self.active_model = clean_pref
                        return self.active_model
        except Exception:
            pass

        self.active_model = default_model
        return self.active_model

    def generate(
        self,
        prompt: str,
        seed: int,
        width: int = 1024,
        height: int = 1280
    ) -> Optional[Image.Image]:
        """
        Executes generation call with retries, status code handling, and backoff.
        Returns PIL.Image or None if provider is exhausted.
        """
        if self.is_exhausted or not self.api_key:
            return None

        import requests

        model = self.discover_active_model()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "InstagramCarouselPipeline/2.0"
        }

        # If prompt is short, use GET /image/{prompt}
        encoded_prompt = urllib.parse.quote(prompt.strip())
        if len(encoded_prompt) <= 1000:
            url = f"{self.base_url}/image/{encoded_prompt}"
            params = {
                "model": model,
                "width": width,
                "height": height,
                "seed": seed
            }
            return self._execute_request(url, headers, params=params, method="GET")

        # Long prompt: use POST /v1/images/generations
        url = f"{self.base_url}/v1/images/generations"
        payload = {
            "prompt": prompt,
            "model": model,
            "size": f"{width}x{height}",
            "response_format": "b64_json"
        }
        return self._execute_request(url, headers, json_body=payload, method="POST")

    def _execute_request(
        self,
        url: str,
        headers: dict,
        params: dict = None,
        json_body: dict = None,
        method: str = "GET"
    ) -> Optional[Image.Image]:
        import requests

        max_attempts = 3
        backoff_seconds = 4.0

        for attempt in range(max_attempts):
            self._throttle()
            try:
                if method == "GET":
                    resp = requests.get(url, headers=headers, params=params, timeout=90)
                else:
                    resp = requests.post(url, headers=headers, json=json_body, timeout=90)

                # Status Code Handling
                if resp.status_code == 200:
                    # Check if response is JSON (OpenAI compatible) or raw image bytes
                    content_type = resp.headers.get("Content-Type", "")
                    if "json" in content_type:
                        data = resp.json()
                        b64_str = data["data"][0]["b64_json"]
                        img_bytes = base64.b64decode(b64_str)
                        return Image.open(io.BytesIO(img_bytes)).convert("RGB")
                    else:
                        return Image.open(io.BytesIO(resp.content)).convert("RGB")

                elif resp.status_code in (401, 402):
                    # 401 Unauthorized or 402 Payment/Quota Required -> Mark exhausted for this run
                    self.is_exhausted = True
                    return None

                elif resp.status_code in (429, 503):
                    # Rate limit or service unavailable -> Honor Retry-After
                    retry_after = resp.headers.get("Retry-After")
                    wait_time = float(retry_after) if retry_after else backoff_seconds
                    time.sleep(wait_time)
                    backoff_seconds *= 2.0
                    continue

                elif resp.status_code == 502:
                    # Upstream error -> retry up to 2 times
                    time.sleep(2.0)
                    continue

                else:
                    # Other 4xx or 5xx -> fall through
                    return None

            except (requests.RequestException, IOError):
                time.sleep(2.0)
                continue

        return None
