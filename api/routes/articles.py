"""
Article API Routes
==================

Endpoints for browsing, filtering, and searching articles.
Powers the Explore page.
"""

from typing import Optional, List
from fastapi import APIRouter, Query

from api.dependencies import get_db

router = APIRouter()


@router.get("")
async def get_articles(
    hours: int = Query(168, description="Time window in hours"),
    limit: int = Query(100, description="Max results"),
    category: Optional[str] = Query(None, description="Filter by category"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    search: Optional[str] = Query(None, description="Text search query"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    domain: Optional[str] = Query(None, description="Filter by domain: quantum or ai"),
):
    """
    Get articles with optional filters.
    Main endpoint for the Explore page.
    """
    storage = get_db()

    if search:
        articles = await storage.search_articles(search, hours=hours, limit=limit, domain=domain)
    elif category:
        articles = await storage.get_articles_by_category(category, hours=hours, limit=limit, domain=domain)
    elif priority:
        articles = await storage.get_articles_by_priority(priority, hours=hours, limit=limit, domain=domain)
    else:
        articles = await storage.get_recent_articles(hours=hours, limit=limit, domain=domain)

    # Apply additional filters on the result set
    results = []
    for a in articles:
        if source_type and a.source_type != source_type:
            continue
        results.append(_article_to_dict(a))

    return {"articles": results, "count": len(results)}


@router.get("/categories")
async def get_category_counts(
    hours: int = Query(168, description="Time window in hours"),
    domain: Optional[str] = Query(None, description="Filter by domain: quantum or ai"),
):
    """Get article counts by category for the filter sidebar."""
    storage = get_db()
    articles = await storage.get_recent_articles(hours=hours, limit=5000, domain=domain)

    counts = {}
    for a in articles:
        cat = a.primary_category
        counts[cat] = counts.get(cat, 0) + 1

    return {"categories": counts, "total": len(articles)}


@router.get("/priorities")
async def get_priority_counts(
    hours: int = Query(168, description="Time window in hours"),
    domain: Optional[str] = Query(None, description="Filter by domain: quantum or ai"),
):
    """Get article counts by priority level."""
    storage = get_db()
    articles = await storage.get_recent_articles(hours=hours, limit=5000, domain=domain)

    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for a in articles:
        p = a.priority
        if p in counts:
            counts[p] += 1

    return {"priorities": counts, "total": len(articles)}


@router.get("/trends")
async def get_article_trends(
    domain: Optional[str] = Query(None, description="Filter by domain: quantum or ai"),
    days: int = Query(30, description="Time window in days"),
    top_n: int = Query(5, description="Number of top categories to return"),
):
    """
    Get article count trends over time by category.
    Returns daily counts for the top N categories.
    Powers the Explore analytics bar trend chart.
    """
    storage = get_db()
    hours = days * 24
    articles = await storage.get_recent_articles(hours=hours, limit=5000, domain=domain)

    # Count articles by category
    category_totals: dict[str, int] = {}
    for a in articles:
        cat = a.primary_category
        category_totals[cat] = category_totals.get(cat, 0) + 1

    # Get top N categories by volume
    top_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:top_n]
    top_cat_names = {c[0] for c in top_categories}

    # Build daily counts per category
    from collections import defaultdict
    daily_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for a in articles:
        if a.primary_category not in top_cat_names:
            continue
        if a.published_at:
            date_str = a.published_at.strftime("%Y-%m-%d")
            daily_counts[a.primary_category][date_str] += 1

    # Format response
    trends = []
    for cat in top_cat_names:
        data = [
            {"date": date, "count": count}
            for date, count in sorted(daily_counts[cat].items())
        ]
        trends.append({"category": cat, "data": data})

    return {"trends": trends}


@router.get("/concept-cloud")
async def get_concept_cloud(
    domain: Optional[str] = Query(None, description="Filter by domain: quantum or ai"),
    hours: int = Query(168, description="Time window in hours"),
):
    """
    Get weighted concept terms from recent articles.
    Aggregates companies, technologies, and use_case_domains.
    Powers the Explore analytics concept cloud.
    """
    storage = get_db()
    articles = await storage.get_recent_articles(hours=hours, limit=5000, domain=domain)

    # Aggregate term frequencies with type tracking
    term_counts: dict[str, int] = {}
    term_types: dict[str, str] = {}

    for a in articles:
        # Companies
        if a.companies_mentioned:
            items = a.companies_mentioned if isinstance(a.companies_mentioned, list) else [
                s.strip() for s in str(a.companies_mentioned).split(",") if s.strip()
            ]
            for item in items:
                if item and len(item) > 1:
                    term_counts[item] = term_counts.get(item, 0) + 1
                    term_types[item] = "company"

        # Technologies
        if a.technologies_mentioned:
            items = a.technologies_mentioned if isinstance(a.technologies_mentioned, list) else [
                s.strip() for s in str(a.technologies_mentioned).split(",") if s.strip()
            ]
            for item in items:
                if item and len(item) > 1:
                    term_counts[item] = term_counts.get(item, 0) + 1
                    term_types[item] = "technology"

        # Use case domains
        if a.use_case_domains:
            items = a.use_case_domains if isinstance(a.use_case_domains, list) else [
                s.strip() for s in str(a.use_case_domains).split(",") if s.strip()
            ]
            for item in items:
                if item and len(item) > 1:
                    term_counts[item] = term_counts.get(item, 0) + 1
                    term_types[item] = "use_case"

    # Sort by frequency and take top 80
    sorted_terms = sorted(term_counts.items(), key=lambda x: x[1], reverse=True)[:80]

    terms = [
        {"text": text, "weight": weight, "type": term_types.get(text, "topic")}
        for text, weight in sorted_terms
    ]

    return {"terms": terms}


@router.get("/themes")
async def get_article_themes(
    domain: Optional[str] = Query(None, description="Filter by domain: quantum or ai"),
    hours: int = Query(168, description="Time window in hours"),
    max_themes: int = Query(5, description="Max number of themes to return"),
):
    """
    Get algorithmically-extracted themes and talking points from recent articles.
    Clusters articles by category + entity overlap and generates theme summaries.
    Powers the Key Themes section on the Explore page.
    """
    from collections import defaultdict

    storage = get_db()
    articles = await storage.get_recent_articles(hours=hours, limit=5000, domain=domain)

    if not articles:
        return {"themes": [], "talking_points": []}

    # Group articles by primary_category
    by_category: dict[str, list] = defaultdict(list)
    for a in articles:
        by_category[a.primary_category].append(a)

    # Sort categories by article count descending, take top N
    sorted_cats = sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True)[:max_themes]

    # Human-readable category names
    cat_labels = {
        "hardware_milestone": "Hardware Milestones",
        "error_correction": "Error Correction",
        "algorithm_research": "Algorithm Research",
        "use_case_drug_discovery": "Drug Discovery Applications",
        "use_case_finance": "Finance & Optimization",
        "use_case_optimization": "Optimization Use Cases",
        "use_case_cybersecurity": "Cybersecurity & PQC",
        "use_case_energy_materials": "Energy & Materials",
        "use_case_ai_ml": "AI / ML Integration",
        "use_case_other": "Other Use Cases",
        "education_workforce": "Education & Workforce",
        "company_earnings": "Company Earnings",
        "funding_ipo": "Funding & IPO Activity",
        "partnership_contract": "Partnerships & Contracts",
        "personnel_leadership": "Leadership Changes",
        "policy_regulation": "Policy & Regulation",
        "geopolitics": "Geopolitics",
        "market_analysis": "Market Analysis",
        "skepticism_critique": "Skepticism & Critique",
        "ai_model_release": "AI Model Releases",
        "ai_product_launch": "AI Product Launches",
        "ai_infrastructure": "AI Infrastructure",
        "ai_safety_alignment": "AI Safety & Alignment",
        "ai_open_source": "Open Source AI",
        "ai_use_case_enterprise": "Enterprise AI",
        "ai_use_case_healthcare": "AI in Healthcare",
        "ai_use_case_finance": "AI in Finance",
        "ai_use_case_other": "AI Use Cases",
        "ai_research_breakthrough": "AI Research Breakthroughs",
    }

    themes = []
    all_talking_points = []

    for cat, cat_articles in sorted_cats:
        # Extract top companies across articles in this category
        company_counts: dict[str, int] = defaultdict(int)
        for a in cat_articles:
            if a.companies_mentioned:
                items = a.companies_mentioned if isinstance(a.companies_mentioned, list) else [
                    s.strip() for s in str(a.companies_mentioned).split(",") if s.strip()
                ]
                for c in items:
                    if c and len(c) > 1:
                        company_counts[c] += 1

        top_companies = [c for c, _ in sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:5]]

        # Build summary from top article takeaways
        takeaways = [a.key_takeaway for a in cat_articles if a.key_takeaway][:5]
        summary = takeaways[0] if takeaways else f"{len(cat_articles)} articles in this category"

        # Generate talking points from highest-relevance articles
        top_articles = sorted(cat_articles, key=lambda a: a.relevance_score or 0, reverse=True)[:3]
        for a in top_articles:
            if a.key_takeaway:
                all_talking_points.append(a.key_takeaway)

        # Collect article IDs for reference
        source_ids = [a.id for a in cat_articles[:20]]

        themes.append({
            "title": cat_labels.get(cat, cat.replace("_", " ").title()),
            "category": cat,
            "summary": summary,
            "article_count": len(cat_articles),
            "top_companies": top_companies,
            "categories": [cat],
            "source_ids": source_ids,
        })

    # Deduplicate and limit talking points
    seen = set()
    unique_points = []
    for tp in all_talking_points:
        if tp not in seen:
            seen.add(tp)
            unique_points.append(tp)
    talking_points = unique_points[:10]

    return {"themes": themes, "talking_points": talking_points}


@router.get("/{article_id}")
async def get_article_by_url(article_id: str):
    """Get a single article by URL (URL-encoded)."""
    from urllib.parse import unquote
    url = unquote(article_id)
    storage = get_db()
    article = await storage.get_article_by_url(url)
    if not article:
        return {"error": "Article not found"}, 404
    return _article_to_dict(article)


def _article_to_dict(article) -> dict:
    """Convert ClassifiedArticle to API response dict."""
    return {
        "id": article.id,
        "url": article.url,
        "title": article.title,
        "source_name": article.source_name,
        "source_type": article.source_type,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "summary": article.ai_summary or article.summary,
        "key_takeaway": article.key_takeaway,
        "category": article.primary_category,
        "priority": article.priority,
        "relevance_score": article.relevance_score,
        "sentiment": article.sentiment,
        "companies_mentioned": article.companies_mentioned,
        "technologies_mentioned": article.technologies_mentioned,
        "people_mentioned": article.people_mentioned,
        "use_case_domains": article.use_case_domains,
        "confidence": article.confidence,
        "domain": article.domain,
    }
