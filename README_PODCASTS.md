# Podcast Pipeline

Discovers, transcribes, and extracts expert quotes from quantum computing and AI/ML podcasts.

## Architecture

```
RSS Discovery  →  Dedup  →  Transcribe (AssemblyAI)  →  Extract Quotes (Claude)  →  BigQuery
```

| Stage | Module | Description |
|-------|--------|-------------|
| Config | `config/podcast_sources.py` | 13 podcast source definitions (6 quantum + 7 AI) |
| Config | `config/settings.py` | `PodcastConfig` — age window, chunk sizes, models |
| Discover | `fetchers/podcast.py` | RSS feed parsing, episode filtering |
| Transcribe | `fetchers/podcast.py` | AssemblyAI with speaker diarization |
| Extract | `processing/podcast_quote_extractor.py` | Domain-aware Claude-powered quote extraction |
| Store | `storage/bigquery.py` | `podcast_transcripts` + `podcast_quotes` tables |

## Enabled Podcasts

### Quantum Computing

| Podcast | Host(s) | RSS Source | Frequency |
|---------|---------|------------|-----------|
| The New Quantum Era | Sebastian Hassinger | Transistor.fm | Weekly |
| The Superposition Guy's Podcast | Yuval Boger | WordPress | Varies |
| The Quantum Divide | Dan Holme, Stephen DiAdamo | Transistor.fm | Varies |
| Impact Quantum | Candace Gillhoolley, Frank La Vigne | Captivate.fm | ~Weekly |
| IQT Quantum Dragon Podcast | Christopher Bishop | WordPress | ~Weekly |
| IEEE Quantum Podcast | IEEE | FeedBurner | Monthly |

### AI / ML

| Podcast | Host(s) | RSS Source | Frequency |
|---------|---------|------------|-----------|
| The Cognitive Revolution | Nathan Labenz | Simplecast | Weekly |
| Latent Space | swyx, Alessio Fanelli | Megaphone | Weekly |
| Practical AI | Daniel Whitenack, Chris Benson | Changelog | Weekly |
| The TWIML AI Podcast | Sam Charrington | Megaphone | Weekly |
| No Priors | Sarah Guo, Elad Gil | Megaphone | Weekly |
| Last Week in AI | Andrey Kurenkov, Jeremy Harris | Substack | Weekly |
| Hard Fork | Kevin Roose, Casey Newton | Simplecast | Weekly |

## Running

```bash
# All enabled podcasts (both domains)
python scripts/run_podcast.py --max-episodes 5

# Quantum podcasts only
python scripts/run_podcast.py --domain quantum --max-episodes 5

# AI podcasts only
python scripts/run_podcast.py --domain ai --max-episodes 5

# Single podcast
python scripts/run_podcast.py --podcasts new-quantum-era --max-episodes 2

# Discovery only (no transcription costs)
python scripts/run_podcast.py --skip-transcription --max-episodes 5

# List configured podcasts
python scripts/run_podcast.py --list-podcasts
```

## Configuration

Key settings in `PodcastConfig` (`config/settings.py`):

| Setting | Default | Description |
|---------|---------|-------------|
| `max_episode_age_days` | 14 | Lookback window (weekly Sunday runs) |
| `max_episodes_per_run` | 5 | Max episodes per podcast per run |
| `extraction_model` | claude-sonnet-4-6 | LLM for quote extraction |
| `chunk_size` | 30,000 | Characters per transcript chunk |
| `chunk_overlap` | 3,000 | Overlap between chunks |
| `dedup_similarity` | 0.85 | Quote dedup threshold |

## Dedup Logic

- **Episode-level:** `podcast_episode_exists()` checks `podcast_transcripts` table before transcribing
- **Quote-level:** Similarity-based dedup during extraction (configurable threshold)
- **Safe for re-runs:** Weekly schedule with 14-day window naturally overlaps; already-processed episodes are skipped

## Scheduling

Two Cloud Run Jobs run **weekly on Sundays** with 14-day lookback:

| Job | Domain | UTC Time | Podcasts |
|-----|--------|----------|----------|
| `quantum-podcasts` | quantum | Sunday 10:00 | 6 podcasts |
| `ai-podcasts` | ai | Sunday 10:30 | 7 podcasts |

The overlap ensures no episodes are missed.

## Costs

- **AssemblyAI transcription:** ~$0.37/hour of audio
- **Claude quote extraction:** ~$0.02-0.05 per episode (varies by length)
- Typical weekly run: 3-8 new episodes ≈ $2-5 total

## Database Tables

- **`podcast_transcripts`** — Full transcript, speaker info, metadata
- **`podcast_quotes`** — Individual quotes with speaker attribution, themes, relevance scoring

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ASSEMBLYAI_API_KEY` | Yes | AssemblyAI transcription |
| `ANTHROPIC_API_KEY` | Yes | Claude for quote extraction |
| `PODCAST_EXTRACTION_MODEL` | No | Override extraction model |
