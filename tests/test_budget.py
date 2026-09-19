"""Unit tests for BudgetGuard, zero-cost enforcement, and slide distribution."""

import unittest
from unittest.mock import patch
from core.budget import BudgetGuard
from core import config


class TestBudgetGuard(unittest.TestCase):
    def setUp(self):
        self.guard = BudgetGuard()

    def test_distribute_ai_slides_cover_and_closing_priority(self):
        total = 5
        
        # 1. Affordable = 0 -> All False (Pillow)
        alloc_0 = self.guard.distribute_ai_slides(total_slides=total, affordable=0)
        self.assertEqual(alloc_0, [False, False, False, False, False])

        # 2. Affordable = 1 -> Cover slide only
        alloc_1 = self.guard.distribute_ai_slides(total_slides=total, affordable=1)
        self.assertEqual(alloc_1, [True, False, False, False, False])

        # 3. Affordable = 2 -> Cover (index 0) and Closing (index 4)
        alloc_2 = self.guard.distribute_ai_slides(total_slides=total, affordable=2)
        self.assertEqual(alloc_2, [True, False, False, False, True])

        # 4. Affordable = 3 -> Cover (0), Closing (4), and first middle (1)
        alloc_3 = self.guard.distribute_ai_slides(total_slides=total, affordable=3)
        self.assertEqual(alloc_3, [True, True, False, False, True])

        # 5. Affordable = 5 -> All True
        alloc_5 = self.guard.distribute_ai_slides(total_slides=total, affordable=5)
        self.assertEqual(alloc_5, [True, True, True, True, True])

    @patch.object(BudgetGuard, "check_pollinations_account")
    def test_budget_guard_balance_scenarios(self, mock_account):
        config.POLLINATIONS_API_KEY = "sk_test_key"
        
        # Scenario A: Balance 0
        mock_account.return_value = (0.0, {"flux": 0.05})
        alloc = self.guard.calculate_slide_allocation(total_slides=6, chosen_model="flux")
        self.assertEqual(alloc, [False] * 6)

        # Scenario B: Balance for 3 slides (balance = 0.15, price = 0.05)
        mock_account.return_value = (0.15, {"flux": 0.05})
        alloc = self.guard.calculate_slide_allocation(total_slides=6, chosen_model="flux")
        self.assertEqual(alloc, [True, True, False, False, False, True])

        # Scenario C: Balance check fails (network error -> returns 0.0, {})
        mock_account.return_value = (0.0, {})
        alloc = self.guard.calculate_slide_allocation(total_slides=6, chosen_model="flux")
        self.assertEqual(alloc, [False] * 6)


if __name__ == "__main__":
    unittest.main()
