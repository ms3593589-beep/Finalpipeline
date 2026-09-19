"""Unit tests for StateManager, idempotent publishing retry, and heartbeat freshness."""

import json
import unittest
from datetime import datetime, timezone, timedelta
from core.state import StateManager
from core import config


class TestStateManager(unittest.TestCase):
    def setUp(self):
        self.state_mgr = StateManager()
        # Ensure clean state file
        if config.RUN_STATE_FILE.exists():
            config.RUN_STATE_FILE.unlink()

    def tearDown(self):
        if config.RUN_STATE_FILE.exists():
            config.RUN_STATE_FILE.unlink()

    def test_idempotent_retry_flow(self):
        job_id = "test_job_1001"
        self.state_mgr.reset_run_state(job_id)

        # 1. Carousel successfully published
        self.state_mgr.update_run_state(
            stage="carousel_published",
            carousel_published=True,
            last_media_id="17900123456789"
        )
        self.state_mgr.record_published("17900123456789")

        # 2. Simulate pipeline resumption / retry after a crash during story publish
        resumed_state = self.state_mgr.get_run_state()
        self.assertTrue(resumed_state["carousel_published"])
        self.assertEqual(resumed_state["last_media_id"], "17900123456789")
        self.assertFalse(resumed_state["story_published"])

        # In pipeline logic: because carousel_published is True, carousel publishing step is bypassed
        # and only story publishing proceeds.
        self.state_mgr.update_run_state(stage="story_published", story_published=True)
        final_state = self.state_mgr.get_run_state()
        self.assertTrue(final_state["carousel_published"])
        self.assertTrue(final_state["story_published"])

    def test_heartbeat_update(self):
        # Set heartbeat file to 30 days ago
        old_time = datetime.now(timezone.utc) - timedelta(days=30)
        config.HEARTBEAT_FILE.write_text(old_time.isoformat() + "\n", encoding="utf-8")

        # 1. Old heartbeat updates and returns True
        self.assertTrue(self.state_mgr.check_and_update_heartbeat(max_age_days=25))
        
        # 2. Fresh heartbeat (updated just now) does not need update
        self.assertFalse(self.state_mgr.check_and_update_heartbeat(max_age_days=25))


if __name__ == "__main__":
    unittest.main()
