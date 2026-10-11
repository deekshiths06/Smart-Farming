"""Crop catalogue response schemas.

The catalogue is a read-only reference list. ``model_supported`` records whether
the installed disease model documents this crop; it is the *only* signal the
client should use to decide if disease analysis can run.
"""

from pydantic import BaseModel


class CatalogueCropRead(BaseModel):
    key: str
    display_name: str
    category: str
    category_label: str
    synonyms: list[str]
    model_supported: bool


class CatalogueCategoryRead(BaseModel):
    key: str
    label: str
    count: int


class CatalogueSearchRead(BaseModel):
    items: list[CatalogueCropRead]
    total: int
    limit: int
    offset: int
    catalogue_size: int
    model_supported_count: int
    categories: list[CatalogueCategoryRead]
