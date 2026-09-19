"""Unit tests for companion Instagram Story generator."""

import unittest
from PIL import Image
from story import StoryGenerator


class TestStoryGenerator(unittest.TestCase):
    def test_story_canvas_dimensions_and_padding(self):
        # Create a test slide 1 (1080x1350) with distinctive solid color
        slide1 = Image.new("RGB", (1080, 1350), color=(220, 50, 50))
        
        story = StoryGenerator.generate_story(slide1)
        
        # 1. Assert dimensions and mode
        self.assertEqual(story.size, (1080, 1920))
        self.assertEqual(story.mode, "RGB")
        
        # 2. Assert foreground is at y=285
        # Pixel at (540, 300) should match foreground color (220, 50, 50)
        fg_pixel = story.getpixel((540, 300))
        self.assertEqual(fg_pixel, (220, 50, 50))
        
        # 3. Assert background differs from foreground (e.g. at y=50 top margin)
        # Background should be blurred & dimmed (approx half brightness)
        bg_pixel = story.getpixel((540, 50))
        self.assertNotEqual(bg_pixel, (220, 50, 50))
        self.assertTrue(bg_pixel[0] < 160, f"Expected dimmed background, got {bg_pixel}")


if __name__ == "__main__":
    unittest.main()
