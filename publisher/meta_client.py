"""Meta Instagram Graph API client for carousel and story publication."""

import time
from typing import List, Dict, Any, Optional
from core import config


class MetaPublisher:
    """Publishes carousel posts and companion stories via Instagram Graph API."""

    def __init__(self):
        self.user_id = config.IG_USER_ID
        self.access_token = config.IG_ACCESS_TOKEN
        self.api_version = config.GRAPH_API_VERSION
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    def is_available(self) -> bool:
        return bool(self.user_id and self.access_token)

    def _poll_container_status(self, container_id: str, max_attempts: int = 20, interval_s: float = 5.0) -> bool:
        """
        Polls container status code.
        Handles FINISHED, IN_PROGRESS, ERROR, and EXPIRED.
        """
        import requests

        url = f"{self.base_url}/{container_id}"
        params = {
            "fields": "status_code",
            "access_token": self.access_token
        }

        for _ in range(max_attempts):
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("status_code")
                if status == "FINISHED":
                    return True
                elif status in ("ERROR", "EXPIRED"):
                    raise RuntimeError(f"Meta container {container_id} failed with terminal status: {status}")
            time.sleep(interval_s)

        raise TimeoutError(f"Meta container {container_id} timed out after {max_attempts * interval_s}s")

    def create_carousel_item(self, image_url: str) -> str:
        """Creates an individual child carousel container."""
        import requests

        url = f"{self.base_url}/{self.user_id}/media"
        payload = {
            "image_url": image_url,
            "is_carousel_item": "true",
            "access_token": self.access_token
        }
        resp = requests.post(url, data=payload, timeout=20)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to create carousel child item: {resp.text}")

        container_id = resp.json().get("id")
        self._poll_container_status(container_id)
        return container_id

    def publish_carousel(self, child_container_ids: List[str], caption: str) -> str:
        """
        Creates and publishes the parent CAROUSEL container.
        Returns published media_id.
        """
        import requests

        if not (2 <= len(child_container_ids) <= 10):
            raise ValueError(f"Instagram carousel requires 2-10 items, got {len(child_container_ids)}")

        # 1. Create parent container
        url = f"{self.base_url}/{self.user_id}/media"
        payload = {
            "media_type": "CAROUSEL",
            "children": ",".join(child_container_ids),
            "caption": caption,
            "access_token": self.access_token
        }
        resp = requests.post(url, data=payload, timeout=20)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to create carousel parent container: {resp.text}")

        parent_id = resp.json().get("id")
        self._poll_container_status(parent_id)

        # 2. Publish container
        pub_url = f"{self.base_url}/{self.user_id}/media_publish"
        pub_payload = {
            "creation_id": parent_id,
            "access_token": self.access_token
        }
        pub_resp = requests.post(pub_url, data=pub_payload, timeout=20)
        if pub_resp.status_code != 200:
            raise RuntimeError(f"Failed to publish carousel: {pub_resp.text}")

        return pub_resp.json().get("id")

    def publish_story(self, image_url: str) -> str:
        """
        Creates and publishes a companion Story container.
        Returns published media_id.
        """
        import requests

        # 1. Create story container
        url = f"{self.base_url}/{self.user_id}/media"
        payload = {
            "media_type": "STORIES",
            "image_url": image_url,
            "access_token": self.access_token
        }
        resp = requests.post(url, data=payload, timeout=20)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to create story container: {resp.text}")

        story_container_id = resp.json().get("id")
        self._poll_container_status(story_container_id)

        # 2. Publish story container
        pub_url = f"{self.base_url}/{self.user_id}/media_publish"
        pub_payload = {
            "creation_id": story_container_id,
            "access_token": self.access_token
        }
        pub_resp = requests.post(pub_url, data=pub_payload, timeout=20)
        if pub_resp.status_code != 200:
            raise RuntimeError(f"Failed to publish story: {pub_resp.text}")

        return pub_resp.json().get("id")

    def get_media_permalink(self, media_id: str) -> str:
        """Retrieves permalink for published post."""
        import requests

        url = f"{self.base_url}/{media_id}"
        params = {
            "fields": "permalink",
            "access_token": self.access_token
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json().get("permalink", "")
        except Exception:
            pass
        return ""
