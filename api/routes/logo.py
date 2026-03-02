"""
Logo API Route
==============

Proxy endpoint for fetching company logos from Logo.dev.
Keeps the API token server-side and adds aggressive cache headers.

Also provides an enrichment endpoint for bulk company → logo resolution.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from typing import List

from api.services.logo_service import logo_service, enrich_companies_with_logos

router = APIRouter()


@router.get("/{domain}")
async def get_company_logo(domain: str):
    """Proxy endpoint for fetching company logos from Logo.dev.

    Keeps the API token server-side and adds cache headers.
    Frontend calls: GET /api/logo/boeing.com
    """
    try:
        logo_bytes = await logo_service.fetch_logo(domain)

        if logo_bytes:
            return Response(
                content=logo_bytes,
                media_type="image/png",
                headers={
                    # Cache for 7 days — logos rarely change
                    "Cache-Control": "public, max-age=604800, immutable",
                    "X-Logo-Domain": domain,
                },
            )
        else:
            raise HTTPException(status_code=404, detail=f"Logo not found for {domain}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching logo: {str(e)}")


@router.post("/enrich")
async def enrich_logos(companies: List[str]):
    """Bulk resolve company names to logo-enriched objects.

    Request body: ["IonQ", "NVIDIA", "Google"]
    Returns: [{name, domain, logo_url}, ...]
    """
    return enrich_companies_with_logos(companies)
