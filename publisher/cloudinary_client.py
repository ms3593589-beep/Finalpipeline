"""Cloudinary asset staging client with automatic post-publish cleanup."""

from typing import List, Dict, Any, Optional
from core import config


class CloudinaryStager:
    """Uploads temporary public assets to Cloudinary for Meta Graph API consumption, then deletes them."""

    def __init__(self):
        self.configured = bool(config.CLOUDINARY_URL)
        self.uploaded_public_ids: List[str] = []

    def is_available(self) -> bool:
        return self.configured

    def upload_slide(self, image_path: str, job_id: str, slide_index: int) -> Optional[str]:
        """Uploads a single slide to Cloudinary and returns secure public URL."""
        if not self.is_available():
            return None

        try:
            import cloudinary
            import cloudinary.uploader
            
            public_id = f"igpipe/{job_id}/slide_{slide_index}"
            resp = cloudinary.uploader.upload(
                image_path,
                public_id=public_id,
                overwrite=True,
                resource_type="image"
            )
            self.uploaded_public_ids.append(public_id)
            return resp.get("secure_url")
        except Exception:
            return None

    def upload_story(self, image_path: str, job_id: str) -> Optional[str]:
        """Uploads companion story to Cloudinary and returns secure public URL."""
        if not self.is_available():
            return None

        try:
            import cloudinary
            import cloudinary.uploader
            
            public_id = f"igpipe/{job_id}/story"
            resp = cloudinary.uploader.upload(
                image_path,
                public_id=public_id,
                overwrite=True,
                resource_type="image"
            )
            self.uploaded_public_ids.append(public_id)
            return resp.get("secure_url")
        except Exception:
            return None

    def cleanup_all(self, job_id: str):
        """Deletes all staged images under the job's folder in Cloudinary."""
        if not self.is_available():
            return

        try:
            import cloudinary
            import cloudinary.api
            import cloudinary.uploader

            # Destroy tracked public IDs
            for pid in self.uploaded_public_ids:
                try:
                    cloudinary.uploader.destroy(pid)
                except Exception:
                    pass

            # Safety net: delete folder prefix
            try:
                cloudinary.api.delete_resources_by_prefix(f"igpipe/{job_id}/")
            except Exception:
                pass

        except Exception:
            pass
        finally:
            self.uploaded_public_ids.clear()
