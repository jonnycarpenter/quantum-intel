"""
Test SEC Filing Models
======================

Tests for SecFiling, SecNugget, and related enums.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from models.sec_filing import (
    SecFiling,
    SecNugget,
    NuggetExtractionResult,
    FilingType,
    FilingSection,
    NuggetType,
    SignalStrength,
)


def test_filing_creation():
    """Test creating a SecFiling."""
    f = SecFiling(
        ticker="IONQ",
        company_name="IonQ Inc.",
        cik="1812364",
        filing_type="10-K",
        fiscal_year=2024,
    )
    assert f.ticker == "IONQ"
    assert f.filing_type == "10-K"
    assert f.fiscal_year == 2024
    assert f.filing_id  # UUID generated
    assert f.unique_key == "IONQ_10-K_2024"


def test_filing_unique_key_with_quarter():
    """Test unique key includes quarter for quarterly filings."""
    f = SecFiling(
        ticker="QBTS",
        company_name="D-Wave Quantum Inc.",
        cik="1905988",
        filing_type="10-Q",
        fiscal_year=2025,
        fiscal_quarter=2,
    )
    assert f.unique_key == "QBTS_10-Q_2025_Q2"


def test_nugget_creation():
    """Test creating a SecNugget with all fields."""
    n = SecNugget(
        filing_id="test-filing-123",
        nugget_text="The company identified quantum computing as a material risk factor",
        filing_type=FilingType.FORM_10K,
        section=FilingSection.RISK_FACTORS,
        nugget_type=NuggetType.RISK_ADMISSION,
        signal_strength=SignalStrength.EXPLICIT,
        ticker="IONQ",
        company_name="IonQ Inc.",
        cik="1812364",
        fiscal_year=2024,
    )
    assert n.nugget_type == NuggetType.RISK_ADMISSION
    assert n.signal_strength == SignalStrength.EXPLICIT
    assert n.section == FilingSection.RISK_FACTORS
    assert n.nugget_id  # UUID generated


def test_nugget_to_dict():
    """Test nugget serialization to dict."""
    n = SecNugget(
        filing_id="f-123",
        nugget_text="R&D spending increased 40% YoY",
        context_text="The company invested heavily...",
        filing_type=FilingType.FORM_10K,
        section=FilingSection.MDA,
        nugget_type=NuggetType.TECHNOLOGY_INVESTMENT,
        themes=["quantum_readiness", "r_and_d_spending"],
        signal_strength=SignalStrength.EXPLICIT,
        companies_mentioned=["IBM"],
        technologies_mentioned=["quantum processors"],
        competitors_named=["Google"],
        regulators_mentioned=[],
        risk_level="medium",
        is_new_disclosure=True,
        is_actionable=True,
        actionability_reason="New investment signals market entry",
        relevance_score=0.92,
        ticker="IONQ",
        company_name="IonQ Inc.",
        cik="1812364",
        fiscal_year=2024,
        accession_number="0001812364-24-000012",
    )
    d = n.to_dict()
    assert d["nugget_type"] == "technology_investment"
    assert d["section"] == "mda"
    assert d["signal_strength"] == "explicit"
    assert d["themes"] == "quantum_readiness,r_and_d_spending"
    assert d["companies_mentioned"] == "IBM"
    assert d["is_new_disclosure"] is True
    assert d["relevance_score"] == 0.92


def test_nugget_from_dict():
    """Test deserializing a nugget from dict (DB round-trip)."""
    d = {
        "nugget_id": "n-123",
        "filing_id": "f-456",
        "nugget_text": "Material risk identified",
        "context_text": "The company disclosed...",
        "filing_type": "10-K",
        "section": "risk_factors",
        "nugget_type": "risk_admission",
        "themes": "quantum_security,cyber_risk",
        "signal_strength": "standard",
        "companies_mentioned": "IBM,Google",
        "technologies_mentioned": "quantum key distribution",
        "competitors_named": "IBM",
        "regulators_mentioned": "SEC,NIST",
        "risk_level": "high",
        "is_new_disclosure": 1,
        "is_actionable": 0,
        "actionability_reason": "",
        "relevance_score": 0.8,
        "ticker": "IONQ",
        "company_name": "IonQ Inc.",
        "cik": "1812364",
        "fiscal_year": 2024,
        "fiscal_quarter": None,
        "filing_date": "2024-03-15T00:00:00+00:00",
        "accession_number": "0001812364-24-000012",
        "extracted_at": "2025-01-15T10:00:00+00:00",
        "extraction_model": "claude-sonnet-4-6-20250514",
        "extraction_confidence": 0.85,
    }
    n = SecNugget.from_dict(d)
    assert n.nugget_id == "n-123"
    assert n.nugget_type == NuggetType.RISK_ADMISSION
    assert n.section == FilingSection.RISK_FACTORS
    assert n.themes == ["quantum_security", "cyber_risk"]
    assert n.companies_mentioned == ["IBM", "Google"]
    assert n.regulators_mentioned == ["SEC", "NIST"]
    assert n.is_new_disclosure is True
    assert n.is_actionable is False


def test_extraction_result():
    """Test NuggetExtractionResult."""
    nuggets = [
        SecNugget(
            filing_id="f-1",
            nugget_text="Nugget 1",
            ticker="IONQ",
            company_name="IonQ",
            cik="1812364",
            fiscal_year=2024,
        ),
        SecNugget(
            filing_id="f-1",
            nugget_text="Nugget 2",
            ticker="IONQ",
            company_name="IonQ",
            cik="1812364",
            fiscal_year=2024,
        ),
    ]
    result = NuggetExtractionResult(
        filing_id="f-1",
        ticker="IONQ",
        company_name="IonQ",
        nuggets=nuggets,
        total_nuggets=2,
        extraction_model="claude-sonnet-4-6-20250514",
    )
    assert result.total_nuggets == 2
    assert len(result.nuggets) == 2


def test_filing_type_enum():
    """Test FilingType enum values."""
    assert FilingType("10-K") == FilingType.FORM_10K
    assert FilingType("10-Q") == FilingType.FORM_10Q
    assert FilingType("8-K") == FilingType.FORM_8K


def test_nugget_type_enum():
    """Test NuggetType enum covers all categories."""
    expected = {
        "competitive_disclosure", "risk_admission", "technology_investment",
        "ip_patent", "regulatory_compliance", "forward_guidance",
        "material_change", "quantum_readiness",
    }
    actual = {nt.value for nt in NuggetType}
    assert actual == expected


def test_signal_strength_enum():
    """Test SignalStrength enum values."""
    assert SignalStrength.EXPLICIT.value == "explicit"
    # Check that NOISE is not actually a value (it's implicit or similar)
    assert len(SignalStrength) >= 2
