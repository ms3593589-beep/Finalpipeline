"""Budget guard and Pollen balance tracker for zero-marginal-cost guarantees."""

import json
import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple
from core import config


class BudgetGuard:
    """Monitors Pollinations API balance, determines affordable AI slides, and tracks usage."""

    def __init__(self):
        self.usage_file = config.USAGE_FILE

    def get_usage_record(self) -> Dict[str, Any]:
        """Loads or initializes daily/monthly usage counts."""
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")
        record = {
            "date": today_str,
            "daily_ai_count": 0,
            "monthly_ai_count": 0,
            "last_known_balance": 0.0,
            "last_updated": now.isoformat()
        }

        if self.usage_file.exists():
            try:
                with open(self.usage_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    # Check day reset
                    if saved.get("date") == today_str:
                        record["daily_ai_count"] = saved.get("daily_ai_count", 0)
                    # Check month reset
                    if saved.get("date", "")[:7] == today_str[:7]:
                        record["monthly_ai_count"] = saved.get("monthly_ai_count", 0)
                    record["last_known_balance"] = saved.get("last_known_balance", 0.0)
            except Exception:
                pass
        return record

    def update_usage(self, ai_images_generated: int, current_balance: float = None):
        """Records generated image counts and current balance into usage.json."""
        record = self.get_usage_record()
        record["daily_ai_count"] += ai_images_generated
        record["monthly_ai_count"] += ai_images_generated
        if current_balance is not None:
            record["last_known_balance"] = current_balance
        record["last_updated"] = datetime.now(timezone.utc).isoformat()

        try:
            with open(self.usage_file, "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2)
        except Exception:
            pass

    def check_pollinations_account(self) -> Tuple[float, Dict[str, float]]:
        """
        Fetches current balance and per-model pricing from Pollinations.ai.
        Returns (balance, model_prices_dict).
        On any error or missing key, returns (0.0, {}) to guarantee no unintended spending.
        """
        if not config.POLLINATIONS_API_KEY:
            return 0.0, {}

        try:
            import requests
            headers = {"Authorization": f"Bearer {config.POLLINATIONS_API_KEY}"}
            
            # Fetch balance
            balance_resp = requests.get(
                f"{config.POLLINATIONS_BASE_URL}/account/balance",
                headers=headers,
                timeout=10
            )
            if balance_resp.status_code != 200:
                return 0.0, {}
            balance_data = balance_resp.json()
            balance = float(balance_data.get("balance", balance_data.get("pollen", 0.0)))

            # Fetch models and prices
            models_resp = requests.get(
                f"{config.POLLINATIONS_BASE_URL}/image/models",
                headers=headers,
                timeout=10
            )
            model_prices = {}
            if models_resp.status_code == 200:
                models_data = models_resp.json()
                # models_data can be a list of model objects or a dict
                if isinstance(models_data, list):
                    for item in models_data:
                        name = item.get("name") or item.get("id")
                        price = float(item.get("price", item.get("cost", 0.0)))
                        if name:
                            model_prices[name] = price
                elif isinstance(models_data, dict):
                    for name, details in models_data.items():
                        if isinstance(details, dict):
                            model_prices[name] = float(details.get("price", details.get("cost", 0.0)))
                        else:
                            model_prices[name] = float(details)

            return balance, model_prices
        except Exception:
            # Any failure defaults to 0 balance for safety
            return 0.0, {}

    def calculate_slide_allocation(self, total_slides: int, chosen_model: str) -> List[bool]:
        """
        Determines which slides should use AI generation vs. Pillow fallback.
        Returns a list of booleans of length total_slides, where True = AI, False = Pillow.
        Cover (slide 0) and Closing (slide N-1) slides receive priority.
        """
        if total_slides <= 0:
            return []

        # If offline or dry run without key, all Pillow
        if not config.POLLINATIONS_API_KEY:
            return [False] * total_slides

        balance, model_prices = self.check_pollinations_account()
        if balance <= 0 or not model_prices or chosen_model not in model_prices:
            return [False] * total_slides

        price = model_prices.get(chosen_model, 0.0)

        # If price is unknown or 0, check if free tier allows generation
        if price <= 0:
            # Free model: affordable up to post limits
            affordable = min(total_slides, config.MAX_AI_IMAGES_PER_POST)
        else:
            effective_balance = max(0.0, balance - config.POLLEN_RESERVE_BUFFER)
            affordable = math.floor(round(effective_balance / price, 6))
            affordable = min(affordable, total_slides, config.MAX_AI_IMAGES_PER_POST)

        return self.distribute_ai_slides(total_slides, affordable)

    @staticmethod
    def distribute_ai_slides(total_slides: int, affordable: int) -> List[bool]:
        """
        Distributes affordable AI slots across slides, prioritizing cover (index 0)
        and closing (index N-1) slides.
        """
        affordable = max(0, min(affordable, total_slides))
        allocation = [False] * total_slides

        if affordable == 0:
            return allocation
        if affordable >= total_slides:
            return [True] * total_slides

        # Priority 1: Cover slide
        allocation[0] = True
        remaining = affordable - 1

        # Priority 2: Closing slide
        if remaining > 0 and total_slides > 1:
            allocation[-1] = True
            remaining -= 1

        # Priority 3: Early middle slides
        for i in range(1, total_slides - 1):
            if remaining <= 0:
                break
            allocation[i] = True
            remaining -= 1

        return allocation
