"""
Case Study API Routes
=====================

Endpoints for browsing, filtering, and searching case studies.
Powers the Case Studies page.
"""

from typing import Optional
from fastapi import APIRouter, Query

from api.dependencies import get_db

router = APIRouter()


@router.get("")
async def get_case_studies(
    domain: Optional[str] = Query(None, description="Filter by domain: quantum or ai"),
    company: Optional[str] = Query(None, description="Filter by company"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    readiness_level: Optional[str] = Query(None, description="Filter by readiness level"),
    outcome_type: Optional[str] = Query(None, description="Filter by outcome type"),
    search: Optional[str] = Query(None, description="Text search query"),
    limit: int = Query(100, description="Max results"),
):
    """
    Get case studies with optional filters.
    Powers the Case Studies page.
    """
    storage = get_db()

    if search:
        case_studies = await storage.search_case_studies(
            search, domain=domain, limit=limit
        )
    else:
        case_studies = await storage.get_case_studies(
            domain=domain,
            company=company,
            industry=industry,
            source_type=source_type,
            limit=limit,
        )

    # Post-filter for readiness_level and outcome_type (not on storage ABC)
    results = []
    for cs in case_studies:
        if readiness_level and cs.readiness_level != readiness_level:
            continue
        if outcome_type and cs.outcome_type != outcome_type:
            continue
        results.append(cs.to_display_dict())

    # Sort by relevance descending
    results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

    return {"case_studies": results, "count": len(results)}


@router.get("/stats")
async def get_case_study_stats(
    domain: Optional[str] = Query(None, description="Filter by domain"),
):
    """Summary statistics for dashboard cards."""
    storage = get_db()
    case_studies = await storage.get_case_studies(domain=domain, limit=500)

    companies = set()
    industries = set()
    readiness_counts: dict[str, int] = {}
    outcome_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    quantified = 0

    for cs in case_studies:
        if cs.company:
            companies.add(cs.company)
        if cs.industry:
            industries.add(cs.industry)
        if cs.readiness_level:
            readiness_counts[cs.readiness_level] = readiness_counts.get(cs.readiness_level, 0) + 1
        if cs.outcome_type:
            outcome_counts[cs.outcome_type] = outcome_counts.get(cs.outcome_type, 0) + 1
        if cs.source_type:
            source_counts[cs.source_type] = source_counts.get(cs.source_type, 0) + 1
        if cs.outcome_quantified:
            quantified += 1

    return {
        "total": len(case_studies),
        "quantified_outcomes": quantified,
        "unique_companies": len(companies),
        "unique_industries": len(industries),
        "by_readiness": readiness_counts,
        "by_outcome_type": outcome_counts,
        "by_source_type": source_counts,
        "companies": sorted(companies),
        "industries": sorted(industries),
    }
