"""Service-layer tests: reverse geocoding (real + failure modes) and weather."""

import httpx
import pytest

from app.services import location_service, weather_service

BANGALORE = (12.9716, 77.5946)


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self):
        if isinstance(self._json, Exception):
            raise self._json
        return self._json


class FakeAsyncClient(httpx.AsyncClient):
    """Synchronous stand-in for httpx.AsyncClient used in failure-mode tests."""

    def __init__(self, *, response=None, timeout=None, headers=None):
        self._response = response
        super().__init__(timeout=timeout, headers=headers)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args, **kwargs):
        return False

    async def get(self, *args, **kwargs):
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


@pytest.mark.network
@pytest.mark.asyncio
async def test_reverse_geocode_real_lookup():
    place = await location_service.reverse_geocode(*BANGALORE)
    assert place.state == "Karnataka"
    assert place.country == "India"
    assert place.district
    assert place.address


@pytest.mark.network
@pytest.mark.asyncio
async def test_weather_service_real_lookup():
    snap = await weather_service.fetch_current_weather(*BANGALORE)
    assert snap.source == "Open-Meteo"
    assert snap.temperature_2m is not None
    assert snap.longitude is not None


def _clear_location_cache():
    location_service._cache.clear()


@pytest.mark.asyncio
async def test_reverse_geocode_timeout_is_friendly(monkeypatch):
    _clear_location_cache()

    def raise_timeout(*args, **kwargs):
        return FakeAsyncClient(response=httpx.TimeoutException("slow service"))

    monkeypatch.setattr(location_service.httpx, "AsyncClient", raise_timeout)
    with pytest.raises(location_service.LocationServiceError) as exc_info:
        await location_service.reverse_geocode(*BANGALORE)
    assert "coordinates are saved" in exc_info.value.user_message


@pytest.mark.asyncio
async def test_reverse_geocode_rate_limited_is_friendly(monkeypatch):
    _clear_location_cache()

    def fake(*args, **kwargs):
        return FakeAsyncClient(response=FakeResponse(status_code=429))

    monkeypatch.setattr(location_service.httpx, "AsyncClient", fake)
    with pytest.raises(location_service.LocationServiceError) as exc_info:
        await location_service.reverse_geocode(*BANGALORE)
    assert "busy" in exc_info.value.user_message


@pytest.mark.asyncio
async def test_reverse_geocode_no_address_components(monkeypatch):
    _clear_location_cache()

    def fake(*args, **kwargs):
        return FakeAsyncClient(
            response=FakeResponse(status_code=200, json_data={"display_name": "Some place"})
        )

    monkeypatch.setattr(location_service.httpx, "AsyncClient", fake)
    with pytest.raises(location_service.LocationServiceError) as exc_info:
        await location_service.reverse_geocode(*BANGALORE)
    assert "area name" in exc_info.value.user_message


@pytest.mark.asyncio
async def test_reverse_geocode_invalid_json(monkeypatch):
    _clear_location_cache()

    def fake(*args, **kwargs):
        return FakeAsyncClient(response=FakeResponse(status_code=200, json_data=ValueError("bad json")))

    monkeypatch.setattr(location_service.httpx, "AsyncClient", fake)
    with pytest.raises(location_service.LocationServiceError):
        await location_service.reverse_geocode(*BANGALORE)


@pytest.mark.asyncio
async def test_weather_service_http_error_is_friendly(monkeypatch):
    def fake(*args, **kwargs):
        return FakeAsyncClient(response=FakeResponse(status_code=500))

    monkeypatch.setattr(weather_service.httpx, "AsyncClient", fake)
    with pytest.raises(weather_service.WeatherServiceError) as exc_info:
        await weather_service.fetch_current_weather(*BANGALORE)
    assert "later" in exc_info.value.user_message


def test_parse_address_maps_only_present_components():
    from app.services.location_service import parse_address

    bern = parse_address(
        {
            "town": "Münsingen",
            "state": "Bern",
            "country": "Switzerland",
        },
        "Münsingen, Bern, Switzerland",
    )
    assert bern.locality == "Münsingen"
    assert bern.state == "Bern"
    assert bern.country == "Switzerland"
    assert bern.sub_district is None  # never invented
    assert bern.district is None  # never invented

    bangalore = parse_address(
        {
            "suburb": "Ashokanagar",
            "state_district": "Bengaluru Urban",
            "state": "Karnataka",
            "country": "India",
        },
        "Ashokanagar, Bengaluru Urban, Karnataka, India",
    )
    assert bangalore.locality == "Ashokanagar"
    assert bangalore.district == "Bengaluru Urban"
    assert bangalore.sub_district is None  # not present in this response