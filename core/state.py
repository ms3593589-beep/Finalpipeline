"""Pipeline state and idempotency manager."""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List

from core import config


class StateManager:
    """Handles persistent state, idempotency checkpoints, and heartbeat tracking."""

    def __init__(self):
        config.STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.state_file = config.RUN_STATE_FILE
        self.last_id_file = config.LAST_PROCESSED_ID_FILE
        self.heartbeat_file = config.HEARTBEAT_FILE
        self.news_history_file = config.NEWS_HISTORY_FILE

    def get_run_state(self) -> Dict[str, Any]:
        """Loads current run state or returns initial template."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "job_id": "",
            "stage": "idle",
            "carousel_published": False,
            "story_published": False,
            "last_media_id": "",
            "timestamp": ""
        }

    def update_run_state(self, **kwargs) -> Dict[str, Any]:
        """Atomically updates run state fields."""
        state = self.get_run_state()
        state.update(kwargs)
        state["timestamp"] = datetime.now(timezone.utc).isoformat()
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        return state

    def reset_run_state(self, job_id: str) -> Dict[str, Any]:
        """Initializes a new job run state."""
        return self.update_run_state(
            job_id=job_id,
            stage="planned",
            carousel_published=False,
            story_published=False,
            last_media_id=""
        )

    def get_last_processed_id(self) -> str:
        """Reads the ID of the last successfully published post."""
        if self.last_id_file.exists():
            return self.last_id_file.read_text(encoding="utf-8").strip()
        return "INIT_START"

    def record_published(self, post_id: str):
        """Updates last_processed_id.txt only after a verified publish."""
        self.last_id_file.write_text(post_id.strip() + "\n", encoding="utf-8")

    def check_and_update_heartbeat(self, max_age_days: int = 25) -> bool:
        """
        Refreshes heartbeat.txt if older than max_age_days or missing.
        Keeps GitHub Actions cron active on dormant repositories.
        """
        now = datetime.now(timezone.utc)
        needs_update = True
        if self.heartbeat_file.exists():
            try:
                content = self.heartbeat_file.read_text(encoding="utf-8").strip()
                last_time = datetime.fromisoformat(content)
                if now - last_time < timedelta(days=max_age_days):
                    needs_update = False
            except Exception:
                needs_update = True

        if needs_update:
            self.heartbeat_file.write_text(now.isoformat() + "\n", encoding="utf-8")
            return True
        return False

    def load_news_history(self, max_age_days: int = 3) -> List[Dict[str, Any]]:
        """Loads and cleans rolling news headline history (last N days)."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        history = []
        if self.news_history_file.exists():
            try:
                with open(self.news_history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        ts = datetime.fromisoformat(item.get("timestamp", ""))
                        if ts >= cutoff:
                            history.append(item)
            except Exception:
                pass
        return history

    def append_news_history(self, headlines: List[str]):
        """Records newly published news headlines with UTC timestamps."""
        history = self.load_news_history()
        now_str = datetime.now(timezone.utc).isoformat()
        for h in headlines:
            history.append({"headline": h, "timestamp": now_str})
        with open(self.news_history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
