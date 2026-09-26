"""Unit tests for ContentPlanner, Gemini AI integration, Number Guard, and fallbacks."""

import json
import unittest
from unittest.mock import patch, MagicMock

from core.planner import ContentPlanner
from core import config


class TestContentPlanner(unittest.TestCase):
    def setUp(self):
        self.planner = ContentPlanner()
        self.sample_stories = [
            {
                "representative_title": f"India Launches Advanced Weather Satellite {i+1}",
                "description": f"ISRO deployed satellite carrying 12 meteorological sensors for climate monitoring.",
                "category": "Technology" if i % 2 == 0 else "Nation",
                "sources": {"The Hindu", "PTI"},
                "is_sensitive": False
            }
            for i in range(12)
        ]

    def test_gemini_prompt_construction(self):
        prompt = self.planner._build_gemini_news_prompt(self.sample_stories, target_count=9)
        self.assertIn("exactly 9 most important", prompt)
        self.assertIn("candidate_id", prompt)
        self.assertIn("art_prompt", prompt)
        self.assertIn("India Launches Advanced Weather Satellite 1", prompt)

    @patch("core.planner.ContentPlanner.plan_with_llm")
    def test_gemini_plan_success_with_number_guard(self, mock_llm):
        mock_llm.return_value = {
            "stories": [
                {
                    "candidate_id": i,
                    "headline": f"Satellite Mission {i+1} Succeeds",
                    "summary": f"ISRO deployed satellite with 12 sensors successfully.",
                    "category": "TECH",
                    "art_prompt": "Futuristic rocket rising above cloud layer at sunset"
                }
                for i in range(9)
            ]
        }

        with patch.object(config, "GEMINI_API_KEY", "test_key"):
            plan = self.planner.plan_news_edition(self.sample_stories, edition_name="Morning Edition")

        self.assertEqual(len(plan["slides"]), 9)
        self.assertEqual(plan["slides"][0]["category"], "TECH")
        self.assertTrue(plan["slides"][0]["image_prompt"].endswith(ContentPlanner.ART_DIRECTIVE))
        self.assertIn("12 sensors", plan["slides"][0]["body"])

    @patch("core.planner.ContentPlanner.plan_with_llm")
    def test_gemini_hallucinated_number_guard_reverts(self, mock_llm):
        # LLM invents "999 sensors" which is NOT in the source ("12 meteorological sensors")
        mock_llm.return_value = {
            "stories": [
                {
                    "candidate_id": 0,
                    "headline": "Satellite Mission 1 Succeeds",
                    "summary": "ISRO deployed satellite with 999 sensors for total coverage.",
                    "category": "TECH",
                    "art_prompt": "Rocket in space"
                }
            ] + [
                {
                    "candidate_id": i,
                    "headline": f"News Headline {i+1}",
                    "summary": f"ISRO deployed satellite carrying 12 meteorological sensors for climate monitoring.",
                    "category": "NATION",
                    "art_prompt": "Clean landscape"
                }
                for i in range(1, 9)
            ]
        }

        with patch.object(config, "GEMINI_API_KEY", "test_key"):
            plan = self.planner.plan_news_edition(self.sample_stories, edition_name="Morning Edition")

        # The first slide summary with "999" must be reverted by Number Guard
        self.assertNotIn("999", plan["slides"][0]["body"])

    def test_heuristic_fallback_when_gemini_unavailable(self):
        with patch.object(config, "GEMINI_API_KEY", ""):
            plan = self.planner.plan_news_edition(self.sample_stories, edition_name="Morning Edition")

        self.assertEqual(len(plan["slides"]), 9)
        for idx, slide in enumerate(plan["slides"]):
            self.assertEqual(slide["slide_index"], idx + 1)
            self.assertEqual(slide["total_slides"], 9)
            self.assertTrue(slide["image_prompt"].endswith(ContentPlanner.ART_DIRECTIVE))
            self.assertTrue(len(slide["title"]) > 0)


if __name__ == "__main__":
    unittest.main()
