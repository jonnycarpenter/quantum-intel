"""
Podcast Fetcher
===============

Discovers podcast episodes via RSS feeds and prepares them for transcription.
Also handles AssemblyAI transcription with speaker diarization.

Pipeline: RSS discovery → audio URL extraction → AssemblyAI transcription

Requires:
    - feedparser (RSS parsing)
    - assemblyai (transcription)
    - ASSEMBLYAI_API_KEY env var
"""

import asyncio
import hashlib
import os
import re
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

try:
    import assemblyai as aai
    HAS_ASSEMBLYAI = True
except ImportError:
    HAS_ASSEMBLYAI = False

from models.podcast import (
    PodcastEpisode,
    PodcastTranscript,
    EpisodeStatus,
    TranscriptSource,
)
from config.podcast_sources import PodcastSourceConfig, ENABLED_PODCAST_SOURCES
from utils.logger import get_logger

logger = get_logger(__name__)


class PodcastFetcher:
    """
    Fetches podcast episodes from RSS feeds and transcribes audio via AssemblyAI.

    Two-phase operation:
    1. discover_episodes() — parse RSS, return PodcastEpisode list with audio URLs
    2. transcribe_episode() — send audio to AssemblyAI, return PodcastTranscript
    """

    def __init__(
        self,
        assemblyai_api_key: Optional[str] = None,
        max_episode_age_days: int = 30,
    ):
        self.api_key = assemblyai_api_key or os.getenv("ASSEMBLYAI_API_KEY", "")
        self.max_episode_age_days = max_episode_age_days

        if HAS_ASSEMBLYAI and self.api_key:
            aai.settings.api_key = self.api_key
            logger.info("[PODCAST] AssemblyAI configured")
        elif not HAS_ASSEMBLYAI:
            logger.warning("[PODCAST] assemblyai package not installed — transcription disabled")
        else:
            logger.warning("[PODCAST] ASSEMBLYAI_API_KEY not set — transcription disabled")

    # =========================================================================
    # RSS Episode Discovery
    # =========================================================================

    async def discover_episodes(
        self,
        sources: Optional[List[PodcastSourceConfig]] = None,
        max_per_source: Optional[int] = None,
        since_days: Optional[int] = None,
    ) -> List[PodcastEpisode]:
        """
        Discover new episodes from RSS feeds.

        Args:
            sources: Podcast sources to check (defaults to ENABLED_PODCAST_SOURCES)
            max_per_source: Override per-source max_episodes
            since_days: Only return episodes published within N days

        Returns:
            List of PodcastEpisode with audio_url populated
        """
        if not HAS_FEEDPARSER:
            logger.error("[PODCAST] feedparser not installed. pip install feedparser")
            return []

        sources = sources or ENABLED_PODCAST_SOURCES
        all_episodes: List[PodcastEpisode] = []

        for source in sources:
            if not source.rss_url:
                logger.info(f"[PODCAST] Skipping {source.name} — no RSS URL")
                continue

            try:
                episodes = await self._parse_rss_feed(
                    source,
                    max_episodes=max_per_source or source.max_episodes,
                    since_days=since_days or self.max_episode_age_days,
                )
                all_episodes.extend(episodes)
                logger.info(
                    f"[PODCAST] {source.name}: discovered {len(episodes)} episodes"
                )
            except Exception as e:
                logger.error(f"[PODCAST] RSS error for {source.name}: {e}")

        logger.info(f"[PODCAST] Total episodes discovered: {len(all_episodes)}")
        return all_episodes

    async def _parse_rss_feed(
        self,
        source: PodcastSourceConfig,
        max_episodes: int = 20,
        since_days: int = 30,
    ) -> List[PodcastEpisode]:
        """Parse an RSS feed and extract episode data."""
        # feedparser is synchronous — run in executor to not block
        loop = asyncio.get_event_loop()
        feed = await loop.run_in_executor(None, feedparser.parse, source.rss_url)

        if feed.bozo and not feed.entries:
            logger.warning(f"[PODCAST] Bad RSS feed for {source.name}: {feed.bozo_exception}")
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
        episodes: List[PodcastEpisode] = []

        for entry in feed.entries[:max_episodes]:
            try:
                episode = self._rss_entry_to_episode(entry, source)
                if episode and episode.audio_url:
                    # Filter by date if we have a published date
                    if episode.published_at and episode.published_at < cutoff:
                        continue
                    episodes.append(episode)
            except Exception as e:
                logger.warning(f"[PODCAST] Error parsing entry: {e}")
                continue

        return episodes

    def _rss_entry_to_episode(
        self,
        entry: Any,
        source: PodcastSourceConfig,
    ) -> Optional[PodcastEpisode]:
        """Convert a feedparser entry to a PodcastEpisode."""
        # Extract audio URL from enclosures
        audio_url = None
        duration_seconds = None

        # Check enclosures (standard podcast RSS)
        for enclosure in getattr(entry, "enclosures", []):
            enc_type = enclosure.get("type", "")
            if "audio" in enc_type or enc_type == "":
                audio_url = enclosure.get("href") or enclosure.get("url")
                break

        # Fallback: check links for audio
        if not audio_url:
            for link in getattr(entry, "links", []):
                if link.get("type", "").startswith("audio/"):
                    audio_url = link.get("href")
                    break

        if not audio_url:
            return None

        # Parse published date
        published_at = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                import time
                published_at = datetime.fromtimestamp(
                    time.mktime(entry.published_parsed), tz=timezone.utc
                )
            except (ValueError, OverflowError, OSError):
                pass

        # Parse duration (iTunes format: HH:MM:SS or MM:SS or seconds)
        itunes_duration = getattr(entry, "itunes_duration", None)
        if itunes_duration:
            duration_seconds = self._parse_duration(itunes_duration)

        # Extract episode number
        episode_number = None
        itunes_episode = getattr(entry, "itunes_episode", None)
        if itunes_episode:
            try:
                episode_number = int(itunes_episode)
            except (ValueError, TypeError):
                pass

        season = None
        itunes_season = getattr(entry, "itunes_season", None)
        if itunes_season:
            try:
                season = int(itunes_season)
            except (ValueError, TypeError):
                pass

        # Try to extract guest name from title
        guest_name = self._extract_guest_from_title(entry.get("title", ""))

        # Generate deterministic episode_id from stable URL identifier
        # so the same episode is recognized across pipeline runs (dedup)
        stable_key = audio_url or entry.get("link") or entry.get("id") or entry.get("title", "")
        episode_id = hashlib.md5(
            f"{source.podcast_id}:{stable_key}".encode()
        ).hexdigest()

        return PodcastEpisode(
            episode_id=episode_id,
            podcast_id=source.podcast_id,
            podcast_name=source.name,
            title=entry.get("title", "Untitled"),
            description=self._clean_html(
                entry.get("summary", entry.get("description", ""))
            ),
            published_at=published_at,
            audio_url=audio_url,
            episode_url=entry.get("link"),
            duration_seconds=duration_seconds,
            season=season,
            episode_number=episode_number,
            guest_name=guest_name,
            hosts=source.hosts,
            status=EpisodeStatus.PENDING.value,
        )

    # =========================================================================
    # AssemblyAI Transcription
    # =========================================================================

    async def transcribe_episode(
        self,
        episode: PodcastEpisode,
    ) -> Optional[PodcastTranscript]:
        """
        Transcribe a podcast episode using AssemblyAI.

        AssemblyAI handles:
        - Audio download (from URL)
        - Speech-to-text
        - Speaker diarization (who said what)

        Returns PodcastTranscript or None on failure.
        """
        if not HAS_ASSEMBLYAI:
            logger.error("[PODCAST] assemblyai package not installed")
            return None

        if not self.api_key:
            logger.error("[PODCAST] ASSEMBLYAI_API_KEY not configured")
            return None

        if not episode.audio_url:
            logger.error(f"[PODCAST] No audio URL for {episode.unique_key}")
            return None

        logger.info(f"[PODCAST] Transcribing: {episode.unique_key}")

        try:
            # Configure transcription with speaker diarization
            config = aai.TranscriptionConfig(
                speaker_labels=True,        # Enable speaker diarization
                speakers_expected=None,      # Let AssemblyAI detect speaker count
                language_code="en",
                punctuate=True,
                format_text=True,
            )

            # Run transcription (blocking call — run in executor)
            loop = asyncio.get_event_loop()
            transcriber = aai.Transcriber()
            transcript_result = await loop.run_in_executor(
                None,
                lambda: transcriber.transcribe(episode.audio_url, config=config),
            )

            if transcript_result.status == aai.TranscriptStatus.error:
                logger.error(
                    f"[PODCAST] Transcription failed for {episode.unique_key}: "
                    f"{transcript_result.error}"
                )
                return None

            # Build formatted text with speaker labels
            formatted_text, speakers = self._format_speaker_text(
                transcript_result, episode
            )

            # Calculate cost (~$0.37/hour at AssemblyAI pricing)
            duration_hours = (episode.duration_seconds or 0) / 3600
            estimated_cost = round(duration_hours * 0.37, 4)

            transcript = PodcastTranscript(
                episode_id=episode.episode_id,
                podcast_id=episode.podcast_id,
                podcast_name=episode.podcast_name,
                episode_title=episode.title,
                episode_url=episode.episode_url,
                published_at=episode.published_at,
                full_text=transcript_result.text or "",
                formatted_text=formatted_text,
                word_count=len((transcript_result.text or "").split()),
                char_count=len(transcript_result.text or ""),
                duration_seconds=episode.duration_seconds,
                has_speaker_labels=bool(transcript_result.utterances),
                speaker_count=len(speakers),
                speakers=speakers,
                transcript_source=TranscriptSource.ASSEMBLYAI.value,
                transcription_cost_usd=estimated_cost,
                guest_name=episode.guest_name,
                guest_title=episode.guest_title,
                guest_company=episode.guest_company,
                hosts=episode.hosts,
            )

            logger.info(
                f"[PODCAST] Transcribed {episode.unique_key}: "
                f"{transcript.word_count} words, {transcript.speaker_count} speakers, "
                f"~${estimated_cost:.4f}"
            )
            return transcript

        except Exception as e:
            logger.error(f"[PODCAST] Transcription error for {episode.unique_key}: {e}")
            return None

    def _format_speaker_text(
        self,
        transcript_result: Any,
        episode: PodcastEpisode,
    ) -> Tuple[str, List[Dict[str, str]]]:
        """
        Format transcript with speaker labels.

        Attempts to map generic "Speaker A/B" labels to real names
        using episode metadata (host names, guest name).
        """
        utterances = getattr(transcript_result, "utterances", None)
        if not utterances:
            return transcript_result.text or "", []

        # Collect unique speakers
        speaker_labels = sorted(set(u.speaker for u in utterances))

        # Try to map speakers to names using heuristics
        speaker_map = self._build_speaker_map(speaker_labels, episode)

        # Build formatted text
        lines = []
        speakers_info = []
        seen_speakers = set()

        for utterance in utterances:
            label = utterance.speaker
            name = speaker_map.get(label, f"Speaker {label}")
            lines.append(f"{name}: {utterance.text}")

            if label not in seen_speakers:
                seen_speakers.add(label)
                role = "host" if name in (episode.hosts or []) else "guest"
                speakers_info.append({
                    "label": label,
                    "name": name,
                    "role": role,
                })

        formatted = "\n\n".join(lines)
        return formatted, speakers_info

    def _build_speaker_map(
        self,
        speaker_labels: List[str],
        episode: PodcastEpisode,
    ) -> Dict[str, str]:
        """
        Best-effort mapping of speaker labels to real names.

        Heuristics:
        - If 2 speakers: first is likely host, second is guest
        - Use episode metadata for host/guest names
        """
        speaker_map = {}
        hosts = episode.hosts or []
        guest = episode.guest_name

        if len(speaker_labels) == 2:
            # Common case: host + guest
            # AssemblyAI typically labels the first speaker as A
            if hosts:
                speaker_map[speaker_labels[0]] = hosts[0]
            if guest:
                speaker_map[speaker_labels[1]] = guest
            elif len(hosts) > 1:
                speaker_map[speaker_labels[1]] = hosts[1]
        elif len(speaker_labels) == 1:
            # Monologue or poor diarization
            if hosts:
                speaker_map[speaker_labels[0]] = hosts[0]
        else:
            # 3+ speakers: assign hosts first, rest are guests
            for i, label in enumerate(speaker_labels):
                if i < len(hosts):
                    speaker_map[label] = hosts[i]
                elif guest and i == len(hosts):
                    speaker_map[label] = guest
                # else leave as "Speaker X"

        return speaker_map

    # =========================================================================
    # Helpers
    # =========================================================================

    @staticmethod
    def _parse_duration(duration_str: str) -> Optional[int]:
        """Parse podcast duration string to seconds."""
        if not duration_str:
            return None
        try:
            # Pure seconds
            if duration_str.isdigit():
                return int(duration_str)

            parts = duration_str.split(":")
            if len(parts) == 3:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + int(s)
            elif len(parts) == 2:
                m, s = parts
                return int(m) * 60 + int(s)
        except (ValueError, TypeError):
            pass
        return None

    @staticmethod
    def _clean_html(text: str) -> str:
        """Strip HTML tags from text."""
        if not text:
            return ""
        clean = re.sub(r"<[^>]+>", "", text)
        clean = re.sub(r"\s+", " ", clean)
        return clean.strip()[:2000]  # Cap description length

    @staticmethod
    def _extract_guest_from_title(title: str) -> Optional[str]:
        """
        Try to extract guest name from episode title.

        Common patterns:
        - "Topic with Guest Name"
        - "Guest Name on Topic"
        - "Topic — Guest Name"
        - "Topic ft. Guest Name"
        """
        # "... with Guest Name"
        match = re.search(r"\bwith\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", title)
        if match:
            return match.group(1)

        # "... — Name" or "... - Name"  (em dash or hyphen before a name)
        match = re.search(r"[—–-]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s*$", title)
        if match:
            return match.group(1)

        # "... ft. Name" or "... feat. Name"
        match = re.search(r"\b(?:ft|feat)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", title)
        if match:
            return match.group(1)

        return None


async def fetch_new_episodes(
    sources: Optional[List[PodcastSourceConfig]] = None,
    max_age_days: int = 30,
) -> List[PodcastEpisode]:
    """
    Convenience function: discover episodes from enabled podcast sources.
    """
    fetcher = PodcastFetcher(max_episode_age_days=max_age_days)
    return await fetcher.discover_episodes(sources=sources)
