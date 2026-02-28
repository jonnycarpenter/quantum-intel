"""
Test Vertex AI Embeddings Store
=================================

Mock-based tests for VertexEmbeddingsStore. All GCP/Vertex AI
calls are mocked — no credentials or project needed.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock
from dataclasses import dataclass, field

from storage.embeddings_config import CONTENT_TYPE_CONFIG


# =============================================================================
# Helpers — fake model items
# =============================================================================

@dataclass
class FakeArticle:
    id: str = "art-1"
    url: str = "https://example.com/art"
    title: str = "Quantum Breakthrough"
    ai_summary: str = "Major hardware advance"
    summary: str = "Short summary"
    key_takeaway: str = "New qubit record"
    source_name: str = "Nature"
    primary_category: str = "hardware_milestone"
    priority: str = "high"
    relevance_score: float = 0.9
    domain: str = "quantum"
    published_at: datetime = None


@dataclass
class FakeSecNugget:
    nugget_id: str = "nug-1"
    nugget_text: str = "Risk factor disclosure"
    context_text: str = "Filed under Item 1A"
    ticker: str = "IONQ"
    company_name: str = "IonQ"
    filing_type: str = "10-K"
    nugget_type: str = "risk_factor"
    themes: str = "supply_chain"
    signal_strength: str = "strong"
    risk_level: str = "medium"
    relevance_score: float = 0.85
    domain: str = "quantum"
    filing_date: datetime = None


@dataclass
class FakeEarningsQuote:
    quote_id: str = "eq-1"
    quote_text: str = "Revenue grew 40% year over year"
    context_before: str = "Looking at financials"
    context_after: str = "We expect continued growth"
    ticker: str = "IONQ"
    company_name: str = "IonQ"
    speaker_name: str = "Peter Chapman"
    speaker_role: str = "ceo"
    quote_type: str = "guidance"
    themes: str = "revenue"
    sentiment: str = "positive"
    relevance_score: float = 0.9
    domain: str = "quantum"
    year: int = 2025
    quarter: int = 3


@dataclass
class FakePodcastQuote:
    quote_id: str = "pq-1"
    quote_text: str = "We achieved quantum advantage"
    context_before: str = "The host asked about progress"
    context_after: str = "This was a milestone moment"
    podcast_name: str = "Quantum Computing Report"
    episode_title: str = "Episode 42"
    speaker_name: str = "Dr. Smith"
    speaker_role: str = "researcher"
    quote_type: str = "insight"
    themes: str = "quantum_advantage"
    sentiment: str = "positive"
    relevance_score: float = 0.88
    published_at: str = "2025-06-01T00:00:00"


@dataclass
class FakeCaseStudy:
    case_study_id: str = "cs-1"
    source_type: str = "article"
    use_case_title: str = "Quantum Drug Discovery"
    use_case_summary: str = "Pharma co used quantum for drug screening"
    grounding_quote: str = "We reduced screening time by 60%"
    outcome_metric: str = "60% time reduction"
    company: str = "Pfizer"
    industry: str = "Pharma"
    technology_stack: list = field(default_factory=lambda: ["trapped_ion"])
    outcome_type: str = "efficiency"
    readiness_level: str = "pilot"
    relevance_score: float = 0.92
    domain: str = "quantum"
    extracted_at: datetime = None


# =============================================================================
# Fixtures
# =============================================================================

def _make_vertex_store(content_type="articles"):
    """Create a VertexEmbeddingsStore with fully mocked GCP."""
    # We need to mock imports before creating the class
    with patch("storage.vertex_embeddings.HAS_VERTEX", True), \
         patch("storage.vertex_embeddings.aiplatform"), \
         patch("storage.vertex_embeddings.bigquery") as mock_bq:

        from storage.vertex_embeddings import VertexEmbeddingsStore

        # Bypass __init__
        instance = object.__new__(VertexEmbeddingsStore)
        instance.project_id = "test-project"
        instance.dataset_id = "test_dataset"
        instance.location = "us-central1"
        instance.full_dataset = "test-project.test_dataset"
        instance.bq_client = MagicMock()
        instance._model = MagicMock()
        instance.content_type = content_type
        instance._config = CONTENT_TYPE_CONFIG[content_type]
        instance._bq_table_name = instance._config["bq_table"]
        instance._id_field = instance._config["id_field"]
        instance._source_type = instance._config["source_type"]

        return instance


@pytest.fixture
def vertex_articles():
    return _make_vertex_store("articles")


@pytest.fixture
def vertex_sec():
    return _make_vertex_store("sec_nuggets")


@pytest.fixture
def vertex_earnings():
    return _make_vertex_store("earnings_quotes")


@pytest.fixture
def vertex_podcasts():
    return _make_vertex_store("podcast_quotes")


@pytest.fixture
def vertex_cases():
    return _make_vertex_store("case_studies")


# =============================================================================
# Init tests
# =============================================================================

class TestInit:

    def test_invalid_content_type_raises(self):
        """Invalid content_type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown content type"):
            with patch("storage.vertex_embeddings.HAS_VERTEX", True), \
                 patch("storage.vertex_embeddings.aiplatform"), \
                 patch("storage.vertex_embeddings.bigquery"):
                from storage.vertex_embeddings import VertexEmbeddingsStore
                VertexEmbeddingsStore(
                    project_id="p",
                    content_type="invalid_type",
                )

    def test_valid_content_types(self):
        """All registered content types should be accepted."""
        for ct in CONTENT_TYPE_CONFIG:
            store = _make_vertex_store(ct)
            assert store.content_type == ct


# =============================================================================
# Document text building tests
# =============================================================================

class TestBuildDocumentText:

    def test_articles(self, vertex_articles):
        text = vertex_articles._build_document_text(FakeArticle())
        assert "Quantum Breakthrough" in text
        assert "Major hardware advance" in text
        assert "New qubit record" in text

    def test_sec_nuggets(self, vertex_sec):
        text = vertex_sec._build_document_text(FakeSecNugget())
        assert "Risk factor disclosure" in text
        assert "Item 1A" in text

    def test_earnings_quotes(self, vertex_earnings):
        text = vertex_earnings._build_document_text(FakeEarningsQuote())
        assert "Revenue grew 40%" in text
        assert "Looking at financials" in text
        assert "continued growth" in text

    def test_podcast_quotes(self, vertex_podcasts):
        text = vertex_podcasts._build_document_text(FakePodcastQuote())
        assert "quantum advantage" in text

    def test_case_studies(self, vertex_cases):
        text = vertex_cases._build_document_text(FakeCaseStudy())
        assert "Drug Discovery" in text
        assert "drug screening" in text
        assert "60% time reduction" in text

    def test_empty_article(self, vertex_articles):
        """Article with empty fields still produces something."""
        art = FakeArticle(title="Title Only", ai_summary="", key_takeaway="")
        text = vertex_articles._build_document_text(art)
        assert "Title Only" in text


# =============================================================================
# Metadata building tests
# =============================================================================

class TestBuildMetadata:

    def test_articles_metadata(self, vertex_articles):
        meta = vertex_articles._build_metadata(FakeArticle())
        assert meta["article_id"] == "art-1"
        assert meta["domain"] == "quantum"
        assert meta["priority"] == "high"

    def test_sec_metadata(self, vertex_sec):
        meta = vertex_sec._build_metadata(FakeSecNugget())
        assert meta["nugget_id"] == "nug-1"
        assert meta["ticker"] == "IONQ"

    def test_earnings_metadata(self, vertex_earnings):
        meta = vertex_earnings._build_metadata(FakeEarningsQuote())
        assert meta["quote_id"] == "eq-1"
        assert meta["year"] == 2025

    def test_podcast_metadata(self, vertex_podcasts):
        meta = vertex_podcasts._build_metadata(FakePodcastQuote())
        assert meta["quote_id"] == "pq-1"
        assert meta["podcast_name"] == "Quantum Computing Report"

    def test_case_studies_metadata(self, vertex_cases):
        meta = vertex_cases._build_metadata(FakeCaseStudy())
        assert meta["case_study_id"] == "cs-1"
        assert meta["company"] == "Pfizer"


# =============================================================================
# Core operations tests
# =============================================================================

class TestIndexItems:

    @pytest.mark.asyncio
    async def test_index_items_empty(self, vertex_articles):
        result = await vertex_articles.index_items([])
        assert result == 0

    @pytest.mark.asyncio
    async def test_index_items_new(self, vertex_articles):
        """Index new items: embeds, checks existence, inserts."""
        article = FakeArticle()

        # Mock embedding generation
        mock_embedding = [0.1] * 768
        vertex_articles._run_sync = AsyncMock(side_effect=[
            [mock_embedding],        # _embed call
            [],                       # existence check (empty = none exist)
            [],                       # insert_rows_json (no errors)
        ])

        result = await vertex_articles.index_items([article])
        assert result == 1

    @pytest.mark.asyncio
    async def test_index_items_all_existing(self, vertex_articles):
        """All items already indexed returns 0."""
        article = FakeArticle()

        mock_embedding = [0.1] * 768
        vertex_articles._run_sync = AsyncMock(side_effect=[
            [mock_embedding],                    # _embed
            [{"article_id": "art-1"}],          # existence check (found!)
        ])

        result = await vertex_articles.index_items([article])
        assert result == 0

    @pytest.mark.asyncio
    async def test_index_articles_alias(self, vertex_articles):
        """index_articles is an alias for index_items."""
        vertex_articles.index_items = AsyncMock(return_value=5)
        result = await vertex_articles.index_articles([FakeArticle()])
        assert result == 5
        vertex_articles.index_items.assert_called_once()


class TestSearch:

    @pytest.mark.asyncio
    async def test_search_returns_results(self, vertex_articles):
        """Search returns SearchResults with correct structure."""
        mock_embedding = [0.1] * 768
        mock_row = {
            "article_id": "art-1",
            "title": "Quantum Breakthrough",
            "url": "https://example.com/art",
            "document_text": "Summary text",
            "distance": 0.15,
            "source_name": "Nature",
            "priority": "high",
        }

        vertex_articles._run_sync = AsyncMock(side_effect=[
            mock_embedding,    # query embedding
            [mock_row],        # vector search results
        ])

        results = await vertex_articles.search("quantum computing", n_results=5)
        assert results.total == 1
        assert results.query == "quantum computing"
        assert results.results[0].item_id == "art-1"
        assert results.results[0].title == "Quantum Breakthrough"
        assert results.results[0].score == pytest.approx(0.85, abs=0.01)

    @pytest.mark.asyncio
    async def test_search_empty(self, vertex_articles):
        """Search returns empty results when nothing found."""
        mock_embedding = [0.1] * 768
        vertex_articles._run_sync = AsyncMock(side_effect=[
            mock_embedding,
            [],
        ])

        results = await vertex_articles.search("nonexistent topic")
        assert results.total == 0
        assert results.results == []

    @pytest.mark.asyncio
    async def test_search_error_returns_empty(self, vertex_articles):
        """Search errors are caught and return empty results."""
        mock_embedding = [0.1] * 768
        vertex_articles._run_sync = AsyncMock(side_effect=[
            mock_embedding,
            Exception("BQ error"),
        ])

        results = await vertex_articles.search("test")
        assert results.total == 0


class TestCount:

    def test_count(self, vertex_articles):
        """count() delegates to BQ."""
        vertex_articles.bq_client.query.return_value.result.return_value = [{"cnt": 100}]
        assert vertex_articles.count() == 100

    def test_count_empty(self, vertex_articles):
        """count() returns 0 when no rows."""
        vertex_articles.bq_client.query.return_value.result.return_value = []
        assert vertex_articles.count() == 0
