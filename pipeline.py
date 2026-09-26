"""Main CLI entrypoint and orchestrator for Autonomous Instagram Dual-Slot Carousel Pipeline."""

import argparse
import hashlib
import json
import os
import shutil
import sys
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

from core import config
from core.budget import BudgetGuard
from core.news import NewsEngine
from core.planner import ContentPlanner
from core.scheduler import PipelineScheduler
from core.state import StateManager
from core.telemetry import TelemetryClient

from images.cloudflare import CloudflareFluxProvider
from images.huggingface import HuggingFaceProvider
from images.normalize import ImageNormalizer
from images.overlay import OverlayRenderer
from images.pillow_art import PillowArtProvider
from images.pollinations import PollinationsProvider

from caption import CaptionGenerator
from story import StoryGenerator


class PipelineCoordinator:
    """Orchestrates planning, generation, rendering, staging, publishing, and telemetry."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.state_mgr = StateManager()
        self.budget_guard = BudgetGuard()
        self.telemetry = TelemetryClient()
        self.scheduler = PipelineScheduler()
        self.planner = ContentPlanner()
        self.normalizer = ImageNormalizer()
        self.overlay_renderer = OverlayRenderer()
        self.story_gen = StoryGenerator()
        self.caption_gen = CaptionGenerator()
        self.news_engine = NewsEngine()

        # Providers
        self.pollinations = PollinationsProvider()
        self.cloudflare = CloudflareFluxProvider()
        self.huggingface = HuggingFaceProvider()
        self.pillow_art = PillowArtProvider()

    def _get_provider_chain(self) -> list:
        """Returns ordered active providers based on config."""
        provider_map = {
            "pollinations": self.pollinations,
            "cloudflare": self.cloudflare,
            "huggingface": self.huggingface,
            "pillow": self.pillow_art
        }
        chain = []
        for name in config.IMAGE_PROVIDER_ORDER:
            if name in provider_map:
                chain.append(provider_map[name])
        if self.pillow_art not in chain:
            chain.append(self.pillow_art)
        return chain

    def run_live_smoke(self) -> bool:
        """Performs a live smoke test against Pollinations.ai without publishing."""
        print("=== RUNNING LIVE SMOKE TEST ===")
        if not config.POLLINATIONS_API_KEY:
            print("ERROR: POLLINATIONS_API_KEY environment variable is missing!")
            return False

        balance, model_prices = self.budget_guard.check_pollinations_account()
        active_model = self.pollinations.discover_active_model()
        print(f"Pollinations Balance: {balance:.2f}")
        print(f"Available Model Prices: {model_prices}")
        print(f"Selected Model: {active_model}")

        test_prompt = "Sacred temple carved out of black basalt rock, dawn light, mist"
        seed = 42
        print(f"Generating test slide with prompt: '{test_prompt}'...")
        img = self.pollinations.generate(test_prompt, seed=seed, width=1024, height=1280)
        if img is None:
            print("ERROR: Pollinations generation failed or provider returned None.")
            return False

        norm_img = self.normalizer.normalize(img)
        assert norm_img.size == (1080, 1350), f"Invalid normalized size {norm_img.size}"

        out_dir = config.BASE_DIR / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "smoke_slide.jpg"
        self.normalizer.save_optimized_jpeg(norm_img, out_path)
        print(f"SUCCESS: Smoke slide saved at {out_path} ({norm_img.size})")
        return True

    def execute(
        self,
        forced_slot: str = "auto",
        from_json_path: str = ""
    ) -> Dict[str, Any]:
        """Main execution flow for Daily News Edition (Mode N)."""
        job_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
        print(f"\n[IG-PIPELINE] Starting Daily News Job: {job_id} (Dry Run: {self.dry_run})")

        # 1. Update heartbeat
        if self.state_mgr.check_and_update_heartbeat():
            print("[IG-PIPELINE] Refreshed heartbeat.txt")

        # 2. Determine slot
        resolved_slot = self.scheduler.resolve_slot(forced_slot)
        print(f"[IG-PIPELINE] Resolved Slot: {resolved_slot.upper()}")

        # 3. Content Planning (Mode N: Daily Top News)
        plan = None
        mode = "N"

        if from_json_path and Path(from_json_path).exists():
            with open(from_json_path, "r", encoding="utf-8") as f:
                plan = json.load(f)
            mode = plan.get("mode", "N")[0].upper()
            print(f"[IG-PIPELINE] Loaded custom plan from {from_json_path} (Mode {mode})")
        else:
            # Check news availability
            if self.dry_run:
                # Mock news items for offline dry-run
                now_iso = datetime.now(timezone.utc)
                mock_news = [
                    {
                        "representative_title": f"India Unveils Milestone Clean Energy Initiative {i+1}",
                        "description": f"Comprehensive renewable expansion across states reaches record deployment milestones in 2026.",
                        "category": "Technology" if i % 2 == 0 else "Business",
                        "sources": {"The Hindu", "Indian Express"},
                        "latest_time": now_iso,
                        "score": 10.0 - i,
                        "is_sensitive": False
                    }
                    for i in range(8)
                ]
                stories = mock_news
            else:
                stories = self.news_engine.collect_and_rank_stories()

            mode, context = self.scheduler.determine_mode(resolved_slot, news_story_count=len(stories))
            edition_title = context.get("edition", "Daily News Edition")
            print(f"[IG-PIPELINE] Operating Mode: {mode} ({edition_title})")
            plan = self.planner.plan_news_edition(stories, edition_name=edition_title)

        slides = plan.get("slides", [])
        # Clamp slides strictly between 2 and 10
        total_slides = max(2, min(len(slides), config.MAX_AI_IMAGES_PER_POST))
        slides = slides[:total_slides]
        for idx, s in enumerate(slides):
            s["slide_index"] = idx + 1
            s["total_slides"] = total_slides

        print(f"[IG-PIPELINE] Slides planned: {total_slides}")

        # 4. Setup output directory
        target_dir = config.MOCK_PREVIEW_DIR if self.dry_run else (config.BASE_DIR / "output" / job_id)
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        # 5. Budget & Provider Allocation
        active_model = self.pollinations.discover_active_model()
        if self.dry_run:
            # Offline dry-run: all slides render through Pillow
            ai_allocation = [False] * total_slides
        else:
            ai_allocation = self.budget_guard.calculate_slide_allocation(total_slides, active_model)

        providers = self._get_provider_chain()
        provider_counts: Dict[str, int] = {}
        rendered_slide_paths = []
        slide_metadata = []

        # 6. Slide Generation & Rendering Loop
        for i, slide_info in enumerate(slides):
            slide_idx = i + 1
            prompt = slide_info["image_prompt"]
            seed = int(hashlib.md5(f"{job_id}_{slide_idx}".encode()).hexdigest(), 16) % 10000000

            use_ai = ai_allocation[i]
            img = None
            used_provider_name = "pillow"

            if use_ai and not self.dry_run:
                for prov in providers:
                    if prov.name() != "pillow" and prov.is_available():
                        try:
                            img = prov.generate(prompt, seed=seed)
                            if img:
                                used_provider_name = prov.name()
                                break
                        except Exception:
                            continue

            # Fallback to Pillow
            if img is None:
                img = self.pillow_art.generate(prompt, seed=seed)
                used_provider_name = "pillow"

            provider_counts[used_provider_name] = provider_counts.get(used_provider_name, 0) + 1

            # Normalize to 1080x1350
            norm_img = self.normalizer.normalize(img)

            # Apply overlay typography
            final_img = self.overlay_renderer.render_overlay(norm_img, slide_info)

            # Save slide JPEG
            slide_file = target_dir / f"slide_{slide_idx}.jpg"
            self.normalizer.save_optimized_jpeg(final_img, slide_file)
            rendered_slide_paths.append(str(slide_file))

            slide_metadata.append({
                "slide_index": slide_idx,
                "provider": used_provider_name,
                "title": slide_info.get("title", ""),
                "prompt": prompt
            })
            print(f"  [OK] Rendered slide {slide_idx}/{total_slides} [{used_provider_name.upper()}]")

        # 7. Companion Story Generation
        # Open first slide for story
        from PIL import Image
        with Image.open(rendered_slide_paths[0]) as s1:
            story_img = self.story_gen.generate_story(s1)
            story_file = target_dir / "story.jpg"
            story_img.save(story_file, format="JPEG", quality=92)
        print(f"  [OK] Companion story generated (1080x1920)")

        # 8. Caption Generation
        hook = f"TOP INDIA NEWS BRIEFING"
        headlines_summary = "\n".join(f"• {s['title']}" for s in slides)
        caption_text = self.caption_gen.generate_caption(
            hook=hook,
            micro_story=f"Today's key headlines and cultural developments across India:\n{headlines_summary}"
        )
        caption_file = target_dir / "caption.txt"
        caption_file.write_text(caption_text, encoding="utf-8")
        print(f"  [OK] Caption generated ({len(caption_text)} chars)")

        # 9. Metadata & State
        metadata = {
            "job_id": job_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "slot": resolved_slot,
            "mode": mode,
            "total_slides": total_slides,
            "providers": provider_counts,
            "slides": slide_metadata
        }
        metadata_file = target_dir / "metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        # 10. Record headlines in history (for Mode N)
        if mode == "N" and not self.dry_run:
            headlines = [s["title"] for s in slides]
            self.state_mgr.append_news_history(headlines)

        # 11. Publishing or Dry Run completion
        if self.dry_run:
            print(f"\n[IG-PIPELINE] Dry Run complete! Artifacts created in {target_dir}")
            return metadata

        # LIVE PUBLISHING
        from publisher.cloudinary_client import CloudinaryStager
        from publisher.meta_client import MetaPublisher

        stager = CloudinaryStager()
        meta = MetaPublisher()

        if not stager.is_available() or not meta.is_available():
            print("[IG-PIPELINE] WARNING: Cloudinary or Meta credentials missing. Skipping live publish.")
            return metadata

        run_state = self.state_mgr.get_run_state()
        carousel_id = run_state.get("last_media_id")
        story_id = ""

        try:
            # Stage assets to Cloudinary
            print("[IG-PIPELINE] Staging assets to Cloudinary...")
            child_urls = []
            for idx, spath in enumerate(rendered_slide_paths):
                url = stager.upload_slide(spath, job_id, idx + 1)
                if not url:
                    raise RuntimeError(f"Failed to stage slide {idx + 1} to Cloudinary")
                child_urls.append(url)

            story_url = stager.upload_story(str(story_file), job_id)
            if not story_url:
                raise RuntimeError("Failed to stage story to Cloudinary")

            # Check idempotency: publish carousel only if not already published
            if not run_state.get("carousel_published"):
                print("[IG-PIPELINE] Creating child containers on Meta...")
                child_ids = [meta.create_carousel_item(u) for u in child_urls]
                print(f"[IG-PIPELINE] Publishing parent carousel ({len(child_ids)} slides)...")
                carousel_id = meta.publish_carousel(child_ids, caption_text)
                self.state_mgr.update_run_state(
                    stage="carousel_published",
                    carousel_published=True,
                    last_media_id=carousel_id
                )
                self.state_mgr.record_published(carousel_id)
                print(f"[IG-PIPELINE] Carousel published successfully: {carousel_id}")

            # Publish companion story
            if not run_state.get("story_published"):
                print("[IG-PIPELINE] Publishing companion story...")
                story_id = meta.publish_story(story_url)
                self.state_mgr.update_run_state(stage="story_published", story_published=True)
                print(f"[IG-PIPELINE] Story published successfully: {story_id}")

            permalink = meta.get_media_permalink(carousel_id) if carousel_id else ""
            self.telemetry.notify_success(
                mode=mode,
                slot=resolved_slot,
                slide_count=total_slides,
                provider_breakdown=provider_counts,
                carousel_permalink=permalink,
                story_id=story_id
            )

        except Exception as e:
            err_trace = traceback.format_exc()
            print(f"[IG-PIPELINE] ERROR during publishing: {err_trace}", file=sys.stderr)
            self.telemetry.notify_error("Publishing", err_trace)
            raise
        finally:
            stager.cleanup_all(job_id)

        return metadata


def main():
    parser = argparse.ArgumentParser(description="Autonomous Instagram Daily News Pipeline (Mode N)")
    parser.add_argument("--dry-run", action="store_true", help="Perform offline execution without network or publishing")
    parser.add_argument("--live-smoke", action="store_true", help="Run live Pollinations smoke test (1 slide, no publish)")
    parser.add_argument("--slot", choices=["auto", "slot1"], default="auto", help="Forced slot execution")
    parser.add_argument("--from-json", type=str, default="", help="Load pre-scripted plan from JSON")

    args = parser.parse_args()

    # Check env variables if CLI flag not passed
    dry_run = args.dry_run or os.getenv("DRY_RUN", "false").lower() == "true"
    forced_slot = args.slot if args.slot != "auto" else os.getenv("FORCED_SLOT", "auto")

    coordinator = PipelineCoordinator(dry_run=dry_run)

    if args.live_smoke:
        success = coordinator.run_live_smoke()
        sys.exit(0 if success else 1)

    try:
        coordinator.execute(forced_slot=forced_slot, from_json_path=args.from_json)
    except Exception as e:
        sys.exit(1)


if __name__ == "__main__":
    main()
