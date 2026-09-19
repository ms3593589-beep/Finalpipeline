"""Optional secondary image generator via Cloudflare Workers AI FLUX."""

import io
from typing import Optional
from PIL import Image

from core import config
from images.base import ImageProvider


class CloudflareFluxProvider(ImageProvider):
    """Generates images via Cloudflare Workers AI FLUX."""

    def __init__(self):
        self.account_id = config.CF_ACCOUNT_ID
        self.api_token = config.CF_API_TOKEN
        self.is_exhausted = False

    def name(self) -> str:
        return "cloudflare"

    def is_available(self) -> bool:
        return bool(self.account_id and self.api_token) and not self.is_exhausted

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
            url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run/@cf/black-forest-labs/flux-1-schnell"
            headers = {"Authorization": f"Bearer {self.api_token}"}
            payload = {
                "prompt": prompt,
                "num_steps": 4
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=45)
            if resp.status_code == 200:
                return Image.open(io.BytesIO(resp.content)).convert("RGB")
            elif resp.status_code in (401, 403, 402):
                self.is_exhausted = True
        except Exception:
            pass

        return None
