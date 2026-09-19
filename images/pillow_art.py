"""Generative offline procedural art provider using pure Pillow."""

import math
import random
from PIL import Image, ImageDraw, ImageFilter
from images.base import ImageProvider


class PillowArtProvider(ImageProvider):
    """Generates procedural sacred geometric mandalas, smooth multi-stop gradients, and textures."""

    def name(self) -> str:
        return "pillow"

    def is_available(self) -> bool:
        # Pure Python, always available with zero network or credential dependencies
        return True

    @staticmethod
    def _hex_to_rgb(hex_code: str):
        hex_code = hex_code.lstrip("#")
        return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

    def generate(
        self,
        prompt: str,
        seed: int,
        width: int = 1024,
        height: int = 1280
    ) -> Image.Image:
        """
        Procedurally renders a rich atmospheric background with geometric mandalas
        and aesthetic color harmonies seeded deterministically.
        """
        rng = random.Random(seed)

        # Curated harmonic palettes
        palettes = [
            ("#0D1B2A", "#1B263B", "#415A77", "#E0A96D"),  # Celestial Indigo & Gold
            ("#1A0933", "#3C096C", "#7B2CBF", "#FF9E00"),  # Mystic Purple & Amber
            ("#0B2545", "#134074", "#8DA9C4", "#EE6C4D"),  # Ocean Deep & Terracotta
            ("#1C1917", "#44403C", "#78716C", "#F59E0B"),  # Monolithic Stone & Warm Ochre
            ("#064E3B", "#047857", "#10B981", "#FBBF24"),  # Emerald Forest & Sun Gold
            ("#310E18", "#781D42", "#A32F5C", "#F6D860")   # Royal Jamdani & Zari Brass
        ]
        chosen_palette = rng.choice(palettes)
        c0 = self._hex_to_rgb(chosen_palette[0])
        c1 = self._hex_to_rgb(chosen_palette[1])
        c2 = self._hex_to_rgb(chosen_palette[2])
        accent = self._hex_to_rgb(chosen_palette[3])

        # Step 1: Smooth radial/linear blended gradient background
        img = Image.new("RGB", (width, height), c0)
        draw = ImageDraw.Draw(img)

        # Center of radial burst
        cx = width // 2 + rng.randint(-50, 50)
        cy = int(height * 0.45) + rng.randint(-50, 50)
        max_dist = math.hypot(width, height) * 0.75

        # Render concentric soft gradient circles
        steps = 45
        for s in range(steps, 0, -1):
            r = int(max_dist * (s / steps))
            t = s / steps
            # Blend between c2 (center) and c1 -> c0 (edges)
            if t < 0.5:
                blend_t = t * 2.0
                r_c = int(c2[0] * (1 - blend_t) + c1[0] * blend_t)
                g_c = int(c2[1] * (1 - blend_t) + c1[1] * blend_t)
                b_c = int(c2[2] * (1 - blend_t) + c1[2] * blend_t)
            else:
                blend_t = (t - 0.5) * 2.0
                r_c = int(c1[0] * (1 - blend_t) + c0[0] * blend_t)
                g_c = int(c1[1] * (1 - blend_t) + c0[1] * blend_t)
                b_c = int(c1[2] * (1 - blend_t) + c0[2] * blend_t)

            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(r_c, g_c, b_c))

        # Soften background
        img = img.filter(ImageFilter.GaussianBlur(radius=25))

        # Step 2: Overlay sacred geometry / mandala patterns
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)

        # Concentric geometric rings and lotus petal symmetry
        symmetry_points = rng.choice([8, 12, 16, 24])
        outer_radius = min(width, height) * 0.38

        # Draw mandala rings
        for ring_r in [int(outer_radius * 0.35), int(outer_radius * 0.65), int(outer_radius * 0.95)]:
            ring_color = (*accent, rng.randint(35, 75))
            draw_ov.ellipse([cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r], outline=ring_color, width=2)

        # Draw symmetric mandala rays and arcs
        for i in range(symmetry_points):
            angle = (2 * math.pi * i) / symmetry_points
            x1 = cx + math.cos(angle) * (outer_radius * 0.2)
            y1 = cy + math.sin(angle) * (outer_radius * 0.2)
            x2 = cx + math.cos(angle) * outer_radius
            y2 = cy + math.sin(angle) * outer_radius

            ray_color = (*accent, rng.randint(40, 90))
            draw_ov.line([(x1, y1), (x2, y2)], fill=ray_color, width=2)

            # Circular node accents at vertices
            dot_r = 4
            draw_ov.ellipse([x2 - dot_r, y2 - dot_r, x2 + dot_r, y2 + dot_r], fill=(*accent, 120))

        # Delicate diamond mesh / starlight points
        for _ in range(30):
            sx = rng.randint(int(width * 0.1), int(width * 0.9))
            sy = rng.randint(int(height * 0.1), int(height * 0.65))
            sr = rng.randint(2, 4)
            draw_ov.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=(255, 255, 255, rng.randint(40, 110)))

        # Composite overlay
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

        return img
