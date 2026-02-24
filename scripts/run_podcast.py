"""
Podcast Pipeline Runner
=======================

Standalone script to run the podcast ingestion pipeline.
Discovers episodes → transcribes → extracts quotes → stores results.

Usage:
    python scripts/run_podcast.py
    python scripts/run_podcast.py --podcasts new_quantum_era --max-episodes 3
    python scripts/run_podcast.py --skip-extraction
    python scripts/run_podcast.py --list-podcasts
"""

import asyncio
import argparse
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config.settings import PodcastConfig
from config.podcast_sources import (
    ENABLED_PODCAST_SOURCES,
    ALL_PODCAST_SOURCES,
    PODCAST_SOURCE_MAP,
    PodcastSourceConfig,
)
from fetchers.podcast import PodcastFetcher
from processing.podcast_quote_extractor import PodcastQuoteExtractor
from storage import get_storage
from utils.logger import get_logger

logger = get_logger(__name__)


async def run_podcast_pipeline(
    podcast_ids: list[str] | None = None,
    max_episodes: int = 5,
    skip_extraction: bool = False,
    skip_transcription: bool = False,
    db_path: str = "data/quantum_intel.db",
):
    """
    Run the complete podcast pipeline.

    1. Discover new episodes via RSS
    2. Transcribe with AssemblyAI (speaker diarization)
    3. Extract quotes using Claude Sonnet
    4. Store in storage backend (SQLite or BigQuery)
    """
    config = PodcastConfig()
    storage = get_storage(db_path=db_path)
    fetcher = PodcastFetcher(
        assemblyai_api_key=config.assemblyai_api_key,
        max_episode_age_days=config.max_episode_age_days,
    )
    extractor = PodcastQuoteExtractor(
        model=config.extraction_model,
        temperature=config.extraction_temperature,
        max_tokens=config.extraction_max_tokens,
    )

    # Determine which podcasts to process
    if podcast_ids:
        sources = []
        for pid in podcast_ids:
            if pid in PODCAST_SOURCE_MAP:
                sources.append(PODCAST_SOURCE_MAP[pid])
            else:
                logger.warning(f"[PODCAST_PIPELINE] Unknown podcast ID: {pid}")
        if not sources:
            logger.error("[PODCAST_PIPELINE] No valid podcast IDs provided")
            await storage.close()
            return
    else:
        sources = ENABLED_PODCAST_SOURCES

    if not sources:
        logger.warning("[PODCAST_PIPELINE] No enabled podcast sources. Check config/podcast_sources.py")
        await storage.close()
        return

    logger.info(
        f"[PODCAST_PIPELINE] Starting pipeline for {len(sources)} podcast(s), "
        f"max {max_episodes} episodes each"
    )

    total_transcripts = 0
    total_quotes = 0

    for source in sources:
        logger.info(f"[PODCAST_PIPELINE] === Processing: {source.name} ===")

        # Step 1: Discover new episodes via RSS
        if not source.rss_url:
            logger.warning(
                f"[PODCAST_PIPELINE] No RSS URL for {source.name} — "
                "skipping discovery (manual audio URLs needed)"
            )
            continue

        try:
            episodes = await fetcher.discover_episodes(
                sources=[source],
                max_per_source=max_episodes,
            )
        except Exception as e:
            logger.error(f"[PODCAST_PIPELINE] Discovery failed for {source.name}: {e}")
            continue

        if not episodes:
            logger.info(f"[PODCAST_PIPELINE] No episodes found for {source.name}")
            continue

        logger.info(f"[PODCAST_PIPELINE] Found {len(episodes)} episodes for {source.name}")

        # Step 2: Filter out already-processed episodes
        new_episodes = []
        for ep in episodes:
            exists = await storage.podcast_episode_exists(
                podcast_id=source.podcast_id,
                episode_id=ep.episode_id,
            )
            if not exists:
                new_episodes.append(ep)
            else:
                logger.debug(f"[PODCAST_PIPELINE] Already processed: {ep.title}")

        if not new_episodes:
            logger.info(f"[PODCAST_PIPELINE] All episodes already processed for {source.name}")
            continue

        logger.info(
            f"[PODCAST_PIPELINE] {len(new_episodes)} new episodes "
            f"(skipped {len(episodes) - len(new_episodes)} existing)"
        )

        # Step 3: Transcribe and extract quotes
        for ep in new_episodes:
            if not ep.audio_url:
                logger.warning(f"[PODCAST_PIPELINE] No audio URL for: {ep.title}")
                continue

            if skip_transcription:
                logger.info(f"[PODCAST_PIPELINE] Skipping transcription for: {ep.title}")
                continue

            # Transcribe with AssemblyAI
            logger.info(f"[PODCAST_PIPELINE] Transcribing: {ep.title}")
            try:
                transcript = await fetcher.transcribe_episode(
                    episode=ep,
                )
            except Exception as e:
                logger.error(f"[PODCAST_PIPELINE] Transcription failed for {ep.title}: {e}")
                continue

            if not transcript or not transcript.full_text:
                logger.warning(f"[PODCAST_PIPELINE] Empty transcript for: {ep.title}")
                continue

            # Save transcript
            await storage.save_podcast_transcript(transcript)
            total_transcripts += 1
            logger.info(
                f"[PODCAST_PIPELINE] Transcript saved: {ep.title} "
                f"({transcript.char_count} chars, {transcript.word_count} words)"
            )

            if skip_extraction:
                logger.info(f"[PODCAST_PIPELINE] Skipping extraction for: {ep.title}")
                continue

            # Extract quotes
            try:
                result = await extractor.extract_quotes(transcript, domain=source.domain)
            except Exception as e:
                logger.error(f"[PODCAST_PIPELINE] Extraction failed for {ep.title}: {e}")
                continue

            if result.quotes:
                saved = await storage.save_podcast_quotes(result.quotes)
                total_quotes += saved
                logger.info(
                    f"[PODCAST_PIPELINE] {ep.title}: "
                    f"{saved} quotes saved (cost=${result.extraction_cost_usd:.4f})"
                )
            else:
                logger.warning(
                    f"[PODCAST_PIPELINE] No quotes extracted from: {ep.title}"
                    f"{f' — error: {result.error}' if result.error else ''}"
                )

    logger.info(
        f"[PODCAST_PIPELINE] Complete! "
        f"Transcripts: {total_transcripts}, Quotes: {total_quotes}, "
        f"Extraction cost: ${extractor.total_cost:.4f}"
    )

    await storage.close()


def list_podcasts():
    """Print all configured podcast sources."""
    print("\nConfigured Podcast Sources:")
    print("=" * 70)
    for src in ALL_PODCAST_SOURCES:
        status = "ENABLED" if src.enabled else "DISABLED"
        rss_status = "RSS: YES" if src.rss_url else "RSS: NO"
        domain_label = src.domain.upper()
        print(f"  [{status}] [{domain_label}] {src.podcast_id}: {src.name}")
        print(f"           Host(s): {', '.join(src.hosts)}")
        print(f"           {rss_status} | {src.discovery_method}")
        if src.rss_url:
            print(f"           RSS: {src.rss_url}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Run podcast ingestion pipeline"
    )
    parser.add_argument(
        "--podcasts",
        type=str,
        help="Comma-separated podcast IDs (default: all enabled)",
    )
    parser.add_argument(
        "--max-episodes",
        type=int,
        default=3,
        help="Max episodes per podcast (default: 3)",
    )
    parser.add_argument(
        "--skip-extraction",
        action="store_true",
        help="Only transcribe, skip quote extraction",
    )
    parser.add_argument(
        "--skip-transcription",
        action="store_true",
        help="Only discover episodes, skip transcription",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="data/quantum_intel.db",
        help="SQLite database path",
    )
    parser.add_argument(
        "--list-podcasts",
        action="store_true",
        help="List all configured podcasts and exit",
    )

    args = parser.parse_args()

    if args.list_podcasts:
        list_podcasts()
        return

    podcast_ids = None
    if args.podcasts:
        podcast_ids = [p.strip() for p in args.podcasts.split(",")]

    asyncio.run(
        run_podcast_pipeline(
            podcast_ids=podcast_ids,
            max_episodes=args.max_episodes,
            skip_extraction=args.skip_extraction,
            skip_transcription=args.skip_transcription,
            db_path=args.db_path,
        )
    )


if __name__ == "__main__":
    main()
