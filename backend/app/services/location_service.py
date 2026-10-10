"""Reverse geocoding via OpenStreetMap Nominatim.

Design notes:
- Called only after the farmer has confirmed a location (never eagerly).
- Respects the Nominatim usage policy: a valid User-Agent and >= 1 request/second.
- Technical failures are logged on the backend; the farmer only ever sees a
  friendly, non-blocking message. A field without an area name is still usable.
- Only components actually present in the response are returned. Nothing is
  inferred or invented.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("annadata.location")

# Nominatim address keys are matched in order; the first present key wins.
LOCALITY_KEYS = (
    "village",
    "town",
    "hamlet",
    "municipality",
    "borough",
    "suburb",
    "neighbourhood",
    "quarter",
    "city",
    "locality",
)
SUB_DISTRICT_KEYS = ("subdistrict", "sub_district", "tehsil", "taluk", "mandal")
DISTRICT_KEYS = ("district", "state_district", "city_district", "county")
STATE_KEYS = ("state", "province", "region")
COUNTRY_KEYS = ("country",)

CACHE_MAX_ENTRIES = 500

_cache: dict[tuple[float, float], "ResolvedPlace"] = {}
_last_call_monotonic = 0.0
_lock = asyncio.Lock()


class LocationServiceError(Exception):
    """Raised when reverse geocoding cannot produce a usable result."""

    def __init__(self, user_message: str, technical_detail: str = ""):
        super().__init__(user_message)
        self.user_message = user_message
        self.technical_detail = technical_detail


@dataclass
class ResolvedPlace:
    address: Optional[str] = None
    locality: Optional[str] = None
    sub_district: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    source: str = "OpenStreetMap Nominatim"
    raw: dict = field(default_factory=dict)


def _first_present(address: dict, keys: tuple[str, ...]) -> Optional[str]:
    for key in keys:
        value = address.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _pick(place_name: Optional[str], max_length: int) -> Optional[str]:
    if not place_name:
        return None
    return place_name[:max_length]


def parse_address(address: dict, display_name: str = "") -> ResolvedPlace:
    """Map a Nominatim address object onto ANNADATA's administrative fields.

    Only keys actually returned by the service are stored; missing components
    stay None rather than being guessed.
    """
    district = _first_present(address, DISTRICT_KEYS)
    sub_district = _first_present(address, SUB_DISTRICT_KEYS)
    # Never repeat the district back as the locality.
    locality = None
    for key in LOCALITY_KEYS:
        value = address.get(key)
        if isinstance(value, str) and value.strip():
            candidate = value.strip()
            if not district or candidate.casefold() != district.casefold():
                locality = candidate
                break

    return ResolvedPlace(
        address=_pick(display_name, 512),
        locality=_pick(locality, 120),
        sub_district=_pick(sub_district, 120),
        district=_pick(district, 120),
        state=_pick(_first_present(address, STATE_KEYS), 120),
        country=_pick(_first_present(address, COUNTRY_KEYS), 80),
        raw={"display_name": display_name, "address": address},
    )


async def reverse_geocode(latitude: float, longitude: float) -> ResolvedPlace:
    """Resolve administrative area names for a confirmed coordinate."""
    global _last_call_monotonic

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise LocationServiceError(
            "Those coordinates are not valid. Please check the location.",
            f"out-of-range lat={latitude} lon={longitude}",
        )

    cache_key = (round(latitude, 5), round(longitude, 5))
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    async with _lock:
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached

        wait = settings.NOMINATIM_MIN_INTERVAL_SECONDS - (time.monotonic() - _last_call_monotonic)
        if wait > 0:
            await asyncio.sleep(wait)

        params = {
            "lat": f"{latitude:.7f}",
            "lon": f"{longitude:.7f}",
            "format": "jsonv2",
            "addressdetails": 1,
            "zoom": 18,
        }
        headers = {"User-Agent": settings.NOMINATIM_USER_AGENT, "Accept-Language": "en"}

        try:
            async with httpx.AsyncClient(
                timeout=settings.NOMINATIM_TIMEOUT_SECONDS, headers=headers
            ) as client:
                response = await client.get(f"{settings.NOMINATIM_BASE_URL}/reverse", params=params)
        except httpx.TimeoutException as exc:
            logger.warning("Reverse geocode timeout for %s,%s: %s", latitude, longitude, exc)
            _last_call_monotonic = time.monotonic()
            raise LocationServiceError(
                "We could not reach the location service. Your coordinates are saved - "
                "you can retry the area name lookup later.",
                f"timeout: {exc}",
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning("Reverse geocode network failure for %s,%s: %s", latitude, longitude, exc)
            _last_call_monotonic = time.monotonic()
            raise LocationServiceError(
                "We could not reach the location service right now. Your coordinates are saved - "
                "you can retry the area name lookup later.",
                f"network error: {exc}",
            ) from exc
        finally:
            _last_call_monotonic = time.monotonic()

        if response.status_code == 429 or response.status_code == 503:
            logger.warning("Reverse geocode rate limited (%s)", response.status_code)
            raise LocationServiceError(
                "The location service is busy right now. Please retry in a moment.",
                f"HTTP {response.status_code}",
            )

        if response.status_code != 200:
            logger.warning("Reverse geocode unexpected HTTP %s", response.status_code)
            raise LocationServiceError(
                "We could not look up the area name right now. Your coordinates are saved.",
                f"HTTP {response.status_code}",
            )

        try:
            payload = response.json()
        except ValueError as exc:
            logger.warning("Reverse geocode invalid JSON: %s", exc)
            raise LocationServiceError(
                "The location service returned an unexpected response. Please retry.",
                "invalid JSON response",
            ) from exc

        if not isinstance(payload, dict) or payload.get("error"):
            detail = payload.get("error") if isinstance(payload, dict) else "non-object response"
            logger.info("Reverse geocode produced no match: %s", detail)
            raise LocationServiceError(
                "We could not find an area name for these coordinates. "
                "Your field can still be saved with its location.",
                f"no match: {detail}",
            )

        address = payload.get("address")
        if not isinstance(address, dict) or not address:
            logger.info("Reverse geocode response missing address component")
            raise LocationServiceError(
                "Location coordinates were saved, but the area name could not be retrieved.",
                "missing address component",
            )

        resolved = parse_address(address, str(payload.get("display_name") or ""))
        if len(_cache) >= CACHE_MAX_ENTRIES:
            _cache.clear()
        _cache[cache_key] = resolved
        logger.info(
            "Reverse geocoded %s,%s -> %s",
            latitude,
            longitude,
            resolved.address or "(no display name)",
        )
        return resolved


async def check_service_reachable() -> dict:
    """Real connectivity check against the configured Nominatim instance."""
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(
            timeout=settings.NOMINATIM_TIMEOUT_SECONDS,
            headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
        ) as client:
            response = await client.get(f"{settings.NOMINATIM_BASE_URL}/status")
        latency_ms = int((time.monotonic() - started) * 1000)
        if response.status_code == 200:
            try:
                body = response.json()
                message = str(body.get("message") or "OK")
            except ValueError:
                message = "OK"
            return {"reachable": True, "latency_ms": latency_ms, "detail": message}
        logger.warning("Nominatim status returned HTTP %s", response.status_code)
        return {
            "reachable": False,
            "latency_ms": latency_ms,
            "detail": f"HTTP {response.status_code}",
        }
    except httpx.HTTPError as exc:
        logger.warning("Nominatim connectivity check failed: %s", exc)
        return {"reachable": False, "latency_ms": None, "detail": type(exc).__name__}
