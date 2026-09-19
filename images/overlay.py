"""Typography, branding, gradient scrim, and safe-zone overlay renderer."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont

from core import config


class OverlayRenderer:
    """Applies gradient scrims, headers, titles, summaries, and safe-zone typography."""

    def __init__(self):
        self.fonts_dir = config.FONTS_DIR
        self.fonts_dir.mkdir(parents=True, exist_ok=True)

    def _get_font(self, font_name: str, size: int) -> ImageFont.ImageFont:
        """Loads bundled TrueType font with fallback to system fonts or default."""
        search_paths = [
            self.fonts_dir / f"{font_name}.ttf",
            self.fonts_dir / f"{font_name}.otf",
            Path("C:/Windows/Fonts") / f"{font_name}.ttf",
            Path("C:/Windows/Fonts") / "arial.ttf",
            Path("C:/Windows/Fonts") / "segoeui.ttf",
            Path("/usr/share/fonts/truetype/dejavu") / "DejaVuSans.ttf",
            Path("/System/Library/Fonts") / "Helvetica.ttc"
        ]
        for p in search_paths:
            if p.exists():
                try:
                    return ImageFont.truetype(str(p), size)
                except Exception:
                    continue
        try:
            return ImageFont.load_default(size=size)
        except Exception:
            return ImageFont.load_default()

    def _create_scrim(self, width: int, height: int, top_stop: int, bottom_stop: int, max_alpha: int = 210) -> Image.Image:
        """Creates a smooth linear black gradient scrim in RGBA."""
        scrim = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(scrim)
        
        span = bottom_stop - top_stop
        if span <= 0:
            return scrim

        for y in range(top_stop, bottom_stop):
            ratio = (y - top_stop) / span
            # Ease-in curve for natural shading
            alpha = int(max_alpha * (ratio ** 1.5))
            draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))
            
        # Below bottom_stop, solid maximum alpha
        if bottom_stop < height:
            draw.rectangle([(0, bottom_stop), (width, height)], fill=(0, 0, 0, max_alpha))

        return scrim

    def _wrap_text(self, text: str, font: ImageFont.ImageFont, max_width: int) -> list:
        """Wraps text into lines that fit within max_width pixels."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = font.getbbox(test_line)
            line_w = bbox[2] - bbox[0]
            if line_w <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
        if current_line:
            lines.append(" ".join(current_line))
        return lines

    def render_overlay(
        self,
        base_img: Image.Image,
        slide_info: Dict[str, Any]
    ) -> Image.Image:
        """
        Renders complete typography and branding overlay onto the 1080x1350 canvas.
        Respects the 10% outer safe margin (108px X, 135px Y).
        """
        w, h = base_img.size
        assert w == 1080 and h == 1350, f"Expected 1080x1350 canvas, got {w}x{h}"

        margin_x = config.SAFE_MARGIN_X  # 108
        margin_y = config.SAFE_MARGIN_Y  # 135
        content_w = w - (2 * margin_x)    # 864 px

        # Fonts
        font_header = self._get_font("SegoeUI-Semibold", 24)
        font_badge = self._get_font("SegoeUI-Bold", 26)
        font_title = self._get_font("SegoeUI-Bold", 46)
        font_body = self._get_font("SegoeUI", 30)
        font_footer = self._get_font("SegoeUI-Italic", 22)
        font_brand = self._get_font("SegoeUI-Bold", 26)

        # Scrim: smooth gradient covering bottom 52% of image
        scrim = self._create_scrim(w, h, top_stop=int(h * 0.48), bottom_stop=int(h * 0.76), max_alpha=225)
        
        # Subtle top header scrim for readability
        top_scrim = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw_top = ImageDraw.Draw(top_scrim)
        for y in range(0, margin_y + 60):
            ratio = 1.0 - (y / (margin_y + 60))
            alpha = int(140 * ratio)
            draw_top.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))

        # Composite scrims onto base image
        img_rgba = base_img.convert("RGBA")
        img_rgba = Image.alpha_composite(img_rgba, top_scrim)
        img_rgba = Image.alpha_composite(img_rgba, scrim)

        draw = ImageDraw.Draw(img_rgba)

        # 1. Top Header Banner
        header_text = slide_info.get("header", "TOP INDIA NEWS")
        draw.text((margin_x, margin_y - 45), header_text, font=font_header, fill=(230, 230, 230, 255))

        # Slide index badge (n/N)
        idx = slide_info.get("slide_index", 1)
        total = slide_info.get("total_slides", 10)
        badge_text = f"{idx}/{total}"
        badge_bbox = font_badge.getbbox(badge_text)
        badge_w = badge_bbox[2] - badge_bbox[0]
        draw.text((w - margin_x - badge_w, margin_y - 48), badge_text, font=font_badge, fill=(255, 204, 0, 255))

        # 2. Bottom Content Block
        # Layout from bottom up to avoid overlapping safe margin
        bottom_anchor = h - margin_y

        # AI Label & Swipe / Brand
        ai_label = "[AI] Generated illustration"
        draw.text((margin_x, bottom_anchor - 20), ai_label, font=font_footer, fill=(180, 180, 180, 220))

        if idx < total:
            swipe_text = "Swipe next >>"
            sw_bbox = font_brand.getbbox(swipe_text)
            sw_w = sw_bbox[2] - sw_bbox[0]
            draw.text((w - margin_x - sw_w, bottom_anchor - 24), swipe_text, font=font_brand, fill=(255, 204, 0, 255))
        else:
            brand_text = config.BRAND_HANDLE
            br_bbox = font_brand.getbbox(brand_text)
            br_w = br_bbox[2] - br_bbox[0]
            draw.text((w - margin_x - br_w, bottom_anchor - 24), brand_text, font=font_brand, fill=(255, 255, 255, 255))

        # Sources / Category
        sources = slide_info.get("sources", "")
        category = slide_info.get("category", "")
        cat_src = f"[{category}] {sources}" if category else sources
        draw.text((margin_x, bottom_anchor - 65), cat_src[:75], font=font_footer, fill=(210, 210, 210, 230))

        # Body / Summary text
        body_text = slide_info.get("body", "")
        body_lines = self._wrap_text(body_text, font_body, content_w)[:3]
        line_spacing_body = 38
        body_block_h = len(body_lines) * line_spacing_body
        body_start_y = bottom_anchor - 85 - body_block_h

        curr_y = body_start_y
        for line in body_lines:
            draw.text((margin_x, curr_y), line, font=font_body, fill=(235, 235, 235, 255))
            curr_y += line_spacing_body

        # Headline / Title
        title_text = slide_info.get("title", "")
        title_lines = self._wrap_text(title_text, font_title, content_w)[:3]
        line_spacing_title = 56
        title_block_h = len(title_lines) * line_spacing_title
        title_start_y = body_start_y - 25 - title_block_h

        curr_y = title_start_y
        for line in title_lines:
            draw.text((margin_x, curr_y), line, font=font_title, fill=(255, 255, 255, 255))
            curr_y += line_spacing_title

        return img_rgba.convert("RGB")
