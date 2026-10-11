"""Crop catalogue API.

A single authenticated, read-only endpoint that backs the searchable crop
selector. It searches the full ANNADATA catalogue (not just the crops the image
model knows) and clearly marks which crops the disease model actually supports.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.auth import get_current_user
from app.models.user import User
from app.schemas.catalogue import CatalogueSearchRead
from app.services import crop_catalogue

router = APIRouter()


@router.get("/crops", response_model=CatalogueSearchRead)
async def search_crops(
    q: str = Query(default="", max_length=80, description="Case-insensitive name/synonym search"),
    category: Optional[str] = Query(default=None, max_length=40),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
):
    """Search the crop catalogue with pagination.

    Returns the page of matches plus the total match count, the full catalogue
    size and the number of crops the disease model supports, so the client never
    confuses "in the catalogue" with "detectable by the model".
    """
    items, total = crop_catalogue.search(q, category, limit, offset)
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "catalogue_size": crop_catalogue.catalogue_size(),
        "model_supported_count": crop_catalogue.supported_size(),
        "categories": crop_catalogue.categories(),
    }
