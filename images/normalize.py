"""Normalizes any generated or imported image to exact Instagram 4:5 carousel specifications."""

import io
from PIL import Image, ImageFilter, ImageEnhance
from core import config


class ImageNormalizer:
    """Normalizes images to exact 1080x1350 4:5 aspect ratio with blurred canvas extension if needed."""

    TARGET_WIDTH = config.CAROUSEL_WIDTH   # 1080
    TARGET_HEIGHT = config.CAROUSEL_HEIGHT # 1350
    TARGET_RATIO = TARGET_WIDTH / TARGET_HEIGHT  # 0.80

    @classmethod
    def normalize(cls, img: Image.Image) -> Image.Image:
        """
        Converts image to RGB, scales/extends to exactly 1080x1350 without distortion,
        and ensures compliance with Meta Graph API aspect ratio constraints.
        """
        if img.mode != "RGB":
            img = img.convert("RGB")

        orig_w, orig_h = img.size
        orig_ratio = orig_w / orig_h

        # If already exactly 1080x1350
        if orig_w == cls.TARGET_WIDTH and orig_h == cls.TARGET_HEIGHT:
            return img

        # Close enough to 4:5 (within 1% tolerance): perform direct high-quality Lanczos resize
        if abs(orig_ratio - cls.TARGET_RATIO) < 0.02:
            return img.resize((cls.TARGET_WIDTH, cls.TARGET_HEIGHT), Image.Resampling.LANCZOS)

        # Non-4:5 image (e.g. 1:1 square, landscape 16:9, or portrait):
        # Create a background canvas of 1080x1350 using scaled blurred and darkened original
        # 1. Background
        scale_bg = max(cls.TARGET_WIDTH / orig_w, cls.TARGET_HEIGHT / orig_h)
        bg_w = int(orig_w * scale_bg)
        bg_h = int(orig_h * scale_bg)
        bg = img.resize((bg_w, bg_h), Image.Resampling.BILINEAR)

        # Center crop background to 1080x1350
        left_bg = (bg_w - cls.TARGET_WIDTH) // 2
        top_bg = (bg_h - cls.TARGET_HEIGHT) // 2
        bg_cropped = bg.crop((left_bg, top_bg, left_bg + cls.TARGET_WIDTH, top_bg + cls.TARGET_HEIGHT))

        # Apply heavy blur and darken background
        bg_blurred = bg_cropped.filter(ImageFilter.GaussianBlur(radius=30))
        enhancer = ImageEnhance.Brightness(bg_blurred)
        bg_darkened = enhancer.enhance(0.45)

        # 2. Foreground: scale to fit inside 1080x1350 while preserving aspect ratio
        scale_fg = min(cls.TARGET_WIDTH / orig_w, cls.TARGET_HEIGHT / orig_h)
        fg_w = int(orig_w * scale_fg)
        fg_h = int(orig_h * scale_fg)
        fg_resized = img.resize((fg_w, fg_h), Image.Resampling.LANCZOS)

        # Center foreground onto background
        offset_x = (cls.TARGET_WIDTH - fg_w) // 2
        offset_y = (cls.TARGET_HEIGHT - fg_h) // 2
        bg_darkened.paste(fg_resized, (offset_x, offset_y))

        # Final assertion on dimensions and ratio
        final_w, final_h = bg_darkened.size
        assert final_w == cls.TARGET_WIDTH and final_h == cls.TARGET_HEIGHT, (
            f"Normalized size must be {cls.TARGET_WIDTH}x{cls.TARGET_HEIGHT}, got {final_w}x{final_h}"
        )
        ratio = final_w / final_h
        assert 0.8 <= ratio <= 1.91, f"Aspect ratio {ratio} outside Meta allowed bounds [0.8, 1.91]"

        return bg_darkened

    @classmethod
    def save_optimized_jpeg(cls, img: Image.Image, output_path, quality: int = 92) -> int:
        """Saves image as progressive sRGB JPEG and returns file size in bytes."""
        normalized = cls.normalize(img)
        normalized.save(
            output_path,
            format="JPEG",
            quality=quality,
            optimize=True,
            progressive=True,
            subsampling=0
        )
        with open(output_path, "rb") as f:
            return len(f.read())
