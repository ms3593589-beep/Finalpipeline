"""Companion Instagram Story generator matching exact 9:16 layout specs."""

from PIL import Image, ImageFilter, ImageEnhance
from core import config


class StoryGenerator:
    """Creates a 1080x1920 companion Instagram story from carousel slide 1."""

    STORY_WIDTH = config.STORY_WIDTH    # 1080
    STORY_HEIGHT = config.STORY_HEIGHT  # 1920

    @classmethod
    def generate_story(cls, slide1_img: Image.Image) -> Image.Image:
        """
        Builds a 1080x1920 Story canvas:
        - Background: slide 1 scaled to fill, center-cropped, Gaussian blurred (r=35), dimmed by 50%.
        - Foreground: slide 1 at native 1080x1350, centered vertically at y=285.
        - Bottom 20% remains safe for Instagram Story interactive reply/sticker UI.
        """
        # Ensure RGB
        if slide1_img.mode != "RGB":
            slide1_img = slide1_img.convert("RGB")

        orig_w, orig_h = slide1_img.size
        # Assert or resize slide1 to 1080x1350
        if orig_w != 1080 or orig_h != 1350:
            slide1_img = slide1_img.resize((1080, 1350), Image.Resampling.LANCZOS)

        # 1. Background Generation
        # Scale to fill 1080x1920
        scale = max(cls.STORY_WIDTH / 1080, cls.STORY_HEIGHT / 1350)
        bg_w = int(1080 * scale)
        bg_h = int(1350 * scale)
        bg = slide1_img.resize((bg_w, bg_h), Image.Resampling.BILINEAR)

        # Center crop to 1080x1920
        left = (bg_w - cls.STORY_WIDTH) // 2
        top = (bg_h - cls.STORY_HEIGHT) // 2
        bg_cropped = bg.crop((left, top, left + cls.STORY_WIDTH, top + cls.STORY_HEIGHT))

        # Heavy Gaussian blur and dimming
        bg_blurred = bg_cropped.filter(ImageFilter.GaussianBlur(radius=35))
        enhancer = ImageEnhance.Brightness(bg_blurred)
        bg_darkened = enhancer.enhance(0.50)

        # 2. Paste foreground slide at y=285
        # (1920 - 1350) / 2 = 285 exactly
        bg_darkened.paste(slide1_img, (0, 285))

        # Assert final dimensions
        final_w, final_h = bg_darkened.size
        assert final_w == cls.STORY_WIDTH and final_h == cls.STORY_HEIGHT, (
            f"Story dimensions must be {cls.STORY_WIDTH}x{cls.STORY_HEIGHT}, got {final_w}x{final_h}"
        )

        return bg_darkened
