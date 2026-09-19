"""Base interface for all carousel image generation providers."""

from abc import ABC, abstractmethod
from typing import Optional
from PIL import Image


class ImageProvider(ABC):
    """Abstract base class for all pipeline image generation providers."""

    @abstractmethod
    def name(self) -> str:
        """Unique identifier name of provider."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if required credentials and network endpoints are configured."""
        pass

    @abstractmethod
    def generate(
        self,
        prompt: str,
        seed: int,
        width: int = 1024,
        height: int = 1280
    ) -> Optional[Image.Image]:
        """
        Generates an image from prompt and seed.
        Returns a PIL Image object or None on failure/exhaustion.
        """
        pass
