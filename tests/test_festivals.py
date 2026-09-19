"""Unit tests for festival active window mathematics and multi-year calendar."""

import unittest
from datetime import date
from core.festivals import FestivalEngine


class TestFestivalEngine(unittest.TestCase):
    def setUp(self):
        self.engine = FestivalEngine()

    def test_festival_active_window_math(self):
        # In festivals.json, Diwali 2026 is 2026-11-08
        diwali_date = date(2026, 11, 8)
        
        # T-10 days: 2026-10-29 -> Active
        t_minus_10 = date(2026, 10, 29)
        fest, diff = self.engine.get_active_festival(t_minus_10)
        self.assertIsNotNone(fest)
        self.assertEqual(diff, 10)
        
        # T-5 days: 2026-11-03 -> Active
        t_minus_5 = date(2026, 11, 3)
        fest, diff = self.engine.get_active_festival(t_minus_5)
        self.assertIsNotNone(fest)
        self.assertEqual(diff, 5)
        
        # T (peak day): 2026-11-08 -> Active
        fest, diff = self.engine.get_active_festival(diwali_date)
        self.assertIsNotNone(fest)
        self.assertEqual(diff, 0)
        
        # T+1 day: 2026-11-09 -> Active
        t_plus_1 = date(2026, 11, 9)
        fest, diff = self.engine.get_active_festival(t_plus_1)
        self.assertIsNotNone(fest)
        self.assertEqual(diff, -1)
        
        # T+2 days: 2026-11-10 -> Inactive for Diwali
        # (Check that Diwali is not the returned active festival with delta -2)
        t_plus_2 = date(2026, 11, 10)
        fest, diff = self.engine.get_active_festival(t_plus_2)
        if fest:
            self.assertNotEqual(fest.get("slug"), "diwali")

        # T-11 days: 2026-10-28 -> Inactive for Diwali
        t_minus_11 = date(2026, 10, 28)
        fest, diff = self.engine.get_active_festival(t_minus_11)
        if fest:
            self.assertNotEqual(fest.get("slug"), "diwali")

        # Year check
        self.assertTrue(self.engine.has_year_data(2026))
        self.assertTrue(self.engine.has_year_data(2027))
        self.assertFalse(self.engine.has_year_data(2035))


if __name__ == "__main__":
    unittest.main()
