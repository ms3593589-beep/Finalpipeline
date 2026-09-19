"""Optional secondary image generator via Hugging Face Inference API FLUX.1-schnell."""

import io
import time
from typing import Optional
from PIL import Image

from core import config
from images.base import ImageProvider


class HuggingFaceProvider(ImageProvider):
    """Generates images via Hugging Face Inference API."""

    def __init__(self):
        self.token = config.HF_TOKEN
        self.is_exhausted = False

    def name(self) -> str:
        return "huggingface"

    def is_available(self) -> bool:
        return bool(self.token) and not self.is_exhausted

    def generate(
        self,
        prompt: str,
        seed: int,
        width: int = 1024,
        height: int = 1280
    ) -> Optional[Image.Image]:
        if not self.is_available():
            return None

        try:
            import requests
            url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
            headers = {"Authorization": f"Bearer {self.token}"}
            payload = {
                "inputs": prompt,
                "parameters": {"seed": seed}
            }

            # Cold start retry loop (models can take 20-60s to load)
            for _ in range(3):
                resp = requests.post(url, headers=headers, json=payload, timeout=60)
                if resp.status_code == 200:
                    return Image.open(io.BytesIO(resp.content)).convert("RGB")
                elif resp.status_code == 503:
                    # Model loading, check estimated_time
                    est_time = resp.json().get("estimated_time", 15.0)
                    time.sleep(min(float(est_time), 20.0))
                    continue
                elif resp.status_code in (401, 403, 402):
                    self.is_exhausted = True
                    break
                else:
                    break
        except Exception:
            pass

        return None
