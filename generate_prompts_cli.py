"""Standalone CLI script to execute News Ingestion & Gemini AI Prompt Planning (Steps 1 & 2)."""

import os
import sys
import json
import traceback
from pathlib import Path

from core import config
from core.news import NewsEngine
from core.planner import ContentPlanner
from core.telemetry import TelemetryClient

def main():
    print("=== STANDALONE NEWS & PROMPT GENERATOR (STEPS 1 & 2) ===")
    
    telemetry = TelemetryClient()
    news_engine = NewsEngine()
    planner = ContentPlanner()

    try:
        # 1. Fetch & Cluster News Candidates
        print("[NEWS-ENGINE] Ingesting Google News RSS feeds...")
        candidates = news_engine.collect_and_rank_stories()
        print(f"[NEWS-ENGINE] Found {len(candidates)} news story candidate clusters.")

        if not candidates:
            print("ERROR: No news candidates found.")
            telemetry.notify_warning("News Generator", "No news items fetched from RSS feeds.")
            sys.exit(1)

        # 2. Plan Top 9 Breaking News Stories with Gemini AI
        print("[CONTENT-PLANNER] Planning Top 9 breaking news stories with Gemini AI...")
        planned_stories = planner._plan_with_gemini(candidates, target_count=9)

        if not planned_stories:
            print("WARNING: LLM planning fallback triggered. Using top RSS items.")
            planned_stories = []
            for i, c in enumerate(candidates[:9]):
                headline = c.get("representative_title", f"News Story {i+1}")
                category = c.get("category", "TOP").upper()
                summary = c.get("description", headline)[:160]
                art_prompt = f"Editorial visual photo of {category.lower()} in India: {headline}"
                prompt = planner.format_infographic_prompt(
                    headline=headline,
                    category=category,
                    summary=summary,
                    art_prompt=art_prompt
                )
                planned_stories.append({
                    "title": headline,
                    "body": summary,
                    "category": category,
                    "image_prompt": prompt
                })

        print(f"[CONTENT-PLANNER] Successfully planned {len(planned_stories)} stories.")

        # 3. Format Copyable Prompts for Telegram Dispatch
        prompts_to_send = []
        for idx, story in enumerate(planned_stories):
            slide_num = idx + 1
            raw_prompt = story.get("image_prompt", "")
            prompts_to_send.append({
                "slide_index": slide_num,
                "formatted_index": f"{slide_num:02d}",
                "raw_prompt": raw_prompt
            })

        # 4. Dispatch 1-Tap Copyable Prompts to Telegram Main Chat
        print("[TELEMETRY] Dispatching 9 copyable prompt blocks to Telegram...")
        sent_count = telemetry.send_headlight_prompts(prompts_to_send)
        print(f"[TELEMETRY] Dispatched {sent_count}/{len(prompts_to_send)} prompts to Telegram successfully.")

        # 5. Save Generated Plan JSON locally
        out_dir = config.BASE_DIR / "state"
        out_dir.mkdir(parents=True, exist_ok=True)
        plan_file = out_dir / "latest_news_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump({"mode": "N", "slides": planned_stories}, f, indent=2, ensure_ascii=False)
        print(f"[SUCCESS] Plan saved to {plan_file}")

        # 6. Dispatch Admin Telemetry Summary to @Dailykeyupdatebot
        telemetry.send_admin_message(
            f"<b>📰 NEWS PROMPT GENERATOR EXECUTED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Status:</b> ✅ SUCCESS\n"
            f"<b>📸 Prompts Generated & Dispatched:</b> {len(prompts_to_send)}\n"
            f"<b>📲 Target Chat:</b> Main Telegram Bot",
            parse_mode="HTML"
        )

    except Exception as e:
        err_trace = traceback.format_exc()
        print(f"ERROR: {err_trace}", file=sys.stderr)
        telemetry.notify_error("NewsPromptGenerator", err_trace)
        sys.exit(1)

if __name__ == "__main__":
    main()
