"""End-to-end unit tests for pipeline dry run and slide count clamping."""

import json
import unittest
from pathlib import Path
from PIL import Image

from pipeline import PipelineCoordinator
from core import config


class TestDryRunPreview(unittest.TestCase):
    def setUp(self):
        self.coordinator = PipelineCoordinator(dry_run=True)

    def test_slide_count_clamp(self):
        # Test slide clamping (2 to 10 slides)
        meta_low = self.coordinator.execute(forced_slot="slot1")
        self.assertGreaterEqual(meta_low["total_slides"], 2)
        self.assertLessEqual(meta_low["total_slides"], 10)

    def test_dry_run_preview_generation(self):
        # Run offline dry run
        meta = self.coordinator.execute(forced_slot="slot1")
        
        preview_dir = config.MOCK_PREVIEW_DIR
        self.assertTrue(preview_dir.exists())

        # 1. Assert slides exist and match 1080x1350
        slide_count = meta["total_slides"]
        self.assertEqual(slide_count, 9)
        for idx in range(1, slide_count + 1):
            slide_file = preview_dir / f"slide_{idx}.jpg"
            self.assertTrue(slide_file.exists(), f"Missing {slide_file}")
            with Image.open(slide_file) as img:
                self.assertEqual(img.size, (1080, 1350))
                self.assertEqual(img.mode, "RGB")

        # 2. Assert story is not created when ENABLE_STORY_GENERATION is False
        story_file = preview_dir / "story.jpg"
        if getattr(config, "ENABLE_STORY_GENERATION", False):
            self.assertTrue(story_file.exists())
            with Image.open(story_file) as img:
                self.assertEqual(img.size, (1080, 1920))
                self.assertEqual(img.mode, "RGB")
        else:
            self.assertFalse(story_file.exists())

        # 3. Assert caption.txt exists and is <= 2200 chars
        caption_file = preview_dir / "caption.txt"
        self.assertTrue(caption_file.exists())
        caption_content = caption_file.read_text(encoding="utf-8")
        self.assertTrue(len(caption_content) > 50)
        self.assertLessEqual(len(caption_content), 2200)

        # 4. Assert metadata.json is complete
        metadata_file = preview_dir / "metadata.json"
        self.assertTrue(metadata_file.exists())
        with open(metadata_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["total_slides"], slide_count)
            self.assertIn("providers", data)
            self.assertIn("pillow", data["providers"])


if __name__ == "__main__":
    unittest.main()
