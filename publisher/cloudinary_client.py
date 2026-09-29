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
            
            cloudinary.config(cloudinary_url=config.CLOUDINARY_URL)
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
            
            cloudinary.config(cloudinary_url=config.CLOUDINARY_URL)
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

    def cleanup_expired_assets(self, retention_days: int = getattr(config, "CLEANUP_RETENTION_DAYS", 7)) -> int:
        """Deletes Cloudinary assets older than the specified retention window (default 7 days)."""
        if not self.is_available():
            return 0

        deleted_count = 0
        try:
            import datetime
            import cloudinary
            import cloudinary.api
            import cloudinary.uploader

            cloudinary.config(cloudinary_url=config.CLOUDINARY_URL)
            cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=retention_days)

            # Retrieve resources under the igpipe prefix
            result = cloudinary.api.resources(type="upload", prefix="igpipe/", max_results=500)
            resources = result.get("resources", [])

            for res in resources:
                created_at_str = res.get("created_at")
                if created_at_str:
                    # Cloudinary format: ISO 8601 string, e.g. 2026-09-27T11:20:00Z
                    created_at = datetime.datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    if created_at < cutoff_date:
                        pid = res.get("public_id")
                        cloudinary.uploader.destroy(pid)
                        deleted_count += 1
        except Exception:
            pass

        return deleted_count

    def cleanup_all(self, job_id: str, force_immediate: bool = False):
        """Deletes staged images. If force_immediate is False, runs 7-day retention cleanup."""
        if not self.is_available():
            return

        if force_immediate:
            try:
                import cloudinary
                import cloudinary.api
                import cloudinary.uploader

                cloudinary.config(cloudinary_url=config.CLOUDINARY_URL)
                for pid in self.uploaded_public_ids:
                    try:
                        cloudinary.uploader.destroy(pid)
                    except Exception:
                        pass

                try:
                    cloudinary.api.delete_resources_by_prefix(f"igpipe/{job_id}/")
                except Exception:
                    pass
            except Exception:
                pass
            finally:
                self.uploaded_public_ids.clear()
        else:
            # Keep images for 7 days by default, cleaning up older expired assets
            self.cleanup_expired_assets(retention_days=getattr(config, "CLEANUP_RETENTION_DAYS", 7))
            self.uploaded_public_ids.clear()

