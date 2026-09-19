"""Unit tests for evergreen weekday themes loader."""

import unittest
from core.themes import ThemeManager


class TestEvergreenThemes(unittest.TestCase):
    def test_evergreen_themes_loader(self):
        mgr = ThemeManager()
        
        # Test all 7 weekdays (0=Monday through 6=Sunday)
        for weekday in range(7):
            theme = mgr.get_theme_for_weekday(weekday)
            self.assertIn("theme", theme)
            self.assertIn("style_lock", theme)
            self.assertIn("narrative_concepts", theme)
            self.assertIn("prompt_keywords", theme)
            self.assertIn("hashtag_pool", theme)
            
            # Non-empty assertions
            self.assertTrue(len(theme["theme"]) > 0)
            self.assertTrue(len(theme["style_lock"]) > 10)
            self.assertTrue(len(theme["narrative_concepts"]) >= 3)
            self.assertTrue(len(theme["prompt_keywords"]) >= 3)
            self.assertTrue(len(theme["hashtag_pool"]) >= 10)
            
        # Verify wrap-around for weekday > 6
        self.assertEqual(mgr.get_theme_for_weekday(7), mgr.get_theme_for_weekday(0))


if __name__ == "__main__":
    unittest.main()
