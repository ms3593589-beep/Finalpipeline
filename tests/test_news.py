"""Unit tests for NewsEngine: RSS parsing, clustering, scoring, and safety filters."""

import unittest
from datetime import datetime, timezone, timedelta
from core.news import NewsEngine
from core import config


class TestNewsEngine(unittest.TestCase):
    def setUp(self):
        self.engine = NewsEngine()

    def test_number_guard_validation(self):
        source = "India launched 104 satellites in a single PSLV rocket mission from Sriharikota."
        
        # Valid: exact numbers present
        valid_summary = "A milestone mission deployed 104 satellites successfully."
        self.assertTrue(self.engine.validate_number_guard(valid_summary, source))

        # Invalid: hallucinated number 200
        invalid_summary = "A milestone mission deployed 200 satellites."
        self.assertFalse(self.engine.validate_number_guard(invalid_summary, source))

    def test_skip_and_sensitive_keywords(self):
        # Harmful story should be skipped
        self.assertTrue(self.engine.is_skip_story("Police arrest suspect involved in sexual assault case"))
        self.assertFalse(self.engine.is_skip_story("India inaugurates world's largest renewable solar park"))

        # Sensitive story should be flagged for softening
        self.assertTrue(self.engine.is_sensitive_story("Tragic train collision and flood disaster in coastal area"))
        self.assertFalse(self.engine.is_sensitive_story("ISRO announces new lunar exploration roadmap"))

    def test_clustering_and_ranking(self):
        now = datetime.now(timezone.utc)
        raw_items = [
            # Story A across 3 outlets
            {"title": "ISRO launches Chandrayaan probe to moon", "description": "Lunar mission", "pub_time": now, "link": "", "source": "The Hindu", "category": "Technology"},
            {"title": "ISRO sends Chandrayaan probe toward the moon", "description": "Space exploration", "pub_time": now, "link": "", "source": "Indian Express", "category": "Technology"},
            {"title": "Chandrayaan probe successfully launched by ISRO", "description": "Historic launch", "pub_time": now, "link": "", "source": "NDTV", "category": "Technology"},
            
            # Story B in single outlet
            {"title": "Local municipal council announces new park garden", "description": "City updates", "pub_time": now - timedelta(hours=5), "link": "", "source": "Local Wire", "category": "Local"}
        ]

        clusters = self.engine.collect_and_rank_stories(raw_items=raw_items)
        
        # Story A should be clustered together and ranked top because of 3 distinct outlets
        self.assertGreaterEqual(len(clusters), 1)
        top = clusters[0]
        self.assertEqual(len(top["sources"]), 3)
        self.assertGreater(top["score"], 9.0)

    def test_history_headline_deduplication(self):
        history = [
            {"headline": "Supreme Court delivers landmark verdict on digital privacy rights", "timestamp": datetime.now(timezone.utc).isoformat()}
        ]
        
        # Very similar headline should be detected as in history
        similar_headline = "Landmark verdict on digital privacy rights delivered by Supreme Court"
        self.assertTrue(self.engine.is_headline_in_history(similar_headline, history))

        # Different headline should not match
        different_headline = "Indian cricket team secures championship series win"
        self.assertFalse(self.engine.is_headline_in_history(different_headline, history))


if __name__ == "__main__":
    unittest.main()
