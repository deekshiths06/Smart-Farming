from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field as PydanticField

from app.api.auth import get_current_user
from app.models.user import User
from app.services import location_service

router = APIRouter()


class ReverseGeocodeRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    latitude: float = PydanticField(ge=-90, le=90)
    longitude: float = PydanticField(ge=-180, le=180)


@router.post("/reverse-geocode")
async def reverse_geocode(
    payload: ReverseGeocodeRequest, current_user: User = Depends(get_current_user)
):
    """Resolve administrative area names for confirmed coordinates.

    Always returns HTTP 200 with a `status` of `ok` or `unavailable` so a
    farmer is never blocked by an external service outage.
    """
    try:
        place = await location_service.reverse_geocode(payload.latitude, payload.longitude)
    except location_service.LocationServiceError as exc:
        return {"status": "unavailable", "message": exc.user_message, "location": None}

    return {
        "status": "ok",
        "message": None,
        "location": {
            "address": place.address,
            "locality": place.locality,
            "sub_district": place.sub_district,
            "district": place.district,
            "state": place.state,
            "country": place.country,
            "source": place.source,
        },
    }
