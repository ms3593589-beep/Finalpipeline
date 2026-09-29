"""Unit tests for caption building and 5-tier hashtag pyramid enforcement."""

import unittest
from caption import CaptionGenerator
from core import config


class TestCaptionGenerator(unittest.TestCase):
    def setUp(self):
        self.generator = CaptionGenerator()

    def test_hashtag_pyramid_enforcement(self):
        suggestions = {
            "niche": ["#IndianTech", "#cleanenergy", "#solarpower", "#GreenFuture", "#techindia", "#EVRevolution", "#Extra1", "#Extra2"],
            "aesthetic": ["#VisualStory", "#cinematic"],  # short, needs backfill
            "cultural": ["#IncredibleIndia", "#VedicWisdom", "#Heritage", "#IncredibleIndia"], # has duplicates
            "utility": [],  # empty, needs total backfill
            "discovery": ["#ExplorePage", "#InstaGood", "#DailyBriefing", "#DiscoverNow", "#NewsDaily"]
        }
        
        backup_pool = ["#curatedindia", "#smartbrief", "#indiandigest", "#visualmedia", "#newsupdates"]
        pyramid = self.generator.build_hashtag_pyramid(suggestions, backup_pool)
        
        # 1. Total count assertion (6+6+5+6+5 = 28)
        expected_total = sum(config.HASHTAG_TIER_COUNTS.values())
        self.assertEqual(len(pyramid), expected_total)
        
        # 2. Deduplication check
        self.assertEqual(len(pyramid), len(set(pyramid)))
        
        # 3. Format and lowercase validation
        for tag in pyramid:
            self.assertTrue(tag.startswith("#"))
            self.assertEqual(tag, tag.lower())
            self.assertRegex(tag, r"^#[a-z0-9_]+$")

    def test_caption_length_and_structure(self):
        # Long micro-story to trigger character guard
        long_story = "India is advancing rapidly across key sectors. " * 60
        hook = "🇮🇳 TOP INDIA NEWS TODAY"
        
        caption = self.generator.generate_caption(
            hook=hook,
            micro_story=long_story
        )
        
        # 1. Assert length <= 2200
        self.assertLessEqual(len(caption), config.MAX_CAPTION_CHARS)
        
        # 2. Assert all structural sections exist
        self.assertIn("🇮🇳 TOP INDIA NEWS TODAY", caption)
        self.assertIn(f"Follow {config.BRAND_HANDLE}", caption)
        self.assertIn("Which story impact surprised you most?", caption)
        self.assertIn("📌 Save this edition", caption)
        self.assertIn("🎨 Imagery: Symbolic editorial AI-generated illustrations.", caption)
        self.assertIn("#", caption)


if __name__ == "__main__":
    unittest.main()
