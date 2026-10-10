"""Weather intelligence boundary."""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from app.core.config import settings
logger = logging.getLogger('annadata.weather')
CURRENT_FIELDS = ('temperature_2m','relative_humidity_2m','apparent_temperature','precipitation','precipitation_probability','weather_code','wind_speed_10m','cloud_cover','surface_pressure')
HOURLY_FIELDS = ('temperature_2m','relative_humidity_2m','precipitation','precipitation_probability','weather_code','wind_speed_10m','cloud_cover')
DAILY_FIELDS = ('weather_code','temperature_2m_max','temperature_2m_min','precipitation_sum','precipitation_probability_max','sunrise','sunset','wind_speed_10m_max')
MAX_HOURS = 48; MAX_DAYS = 7
class WeatherServiceError(Exception):
    def __init__(self, user_message: str, technical_detail: str = ''):
        super().__init__(user_message)
        self.user_message = user_message
        self.technical_detail = technical_detail
@dataclass
class WeatherSnapshot:
    source: str = 'Open-Meteo'
    latitude: float = 0.0
    longitude: float = 0.0
    observed_at: Optional[str] = None
    timezone: Optional[str] = None
    temperature_2m: Optional[float] = None
    relative_humidity_2m: Optional[float] = None
    apparent_temperature: Optional[float] = None
    precipitation: Optional[float] = None
    precipitation_probability: Optional[float] = None
    weather_code: Optional[int] = None
    wind_speed_10m: Optional[float] = None
    cloud_cover: Optional[float] = None
    surface_pressure: Optional[float] = None
    hourly: List[Dict[str, Any]] = field(default_factory=list)
    daily: List[Dict[str, Any]] = field(default_factory=list)
    @property
    def feels_like_2m(self) -> Optional[float]:
        return self.apparent_temperature
    @classmethod
    def from_openmeteo(cls, latitude: float, longitude: float, payload: Dict[str, Any]) -> 'WeatherSnapshot':
        current = payload.get('current') or {}
        hourly = payload.get('hourly') or {}
        daily = payload.get('daily') or {}
        snap = cls(source='Open-Meteo', latitude=float(payload.get('latitude', latitude)), longitude=float(payload.get('longitude', longitude)), timezone=payload.get('timezone'), observed_at=current.get('time') if isinstance(current, dict) else None, temperature_2m=current.get('temperature_2m') if isinstance(current, dict) else None, relative_humidity_2m=current.get('relative_humidity_2m') if isinstance(current, dict) else None, apparent_temperature=current.get('apparent_temperature') if isinstance(current, dict) else None, precipitation=current.get('precipitation') if isinstance(current, dict) else None, precipitation_probability=current.get('precipitation_probability') if isinstance(current, dict) else None, weather_code=current.get('weather_code') if isinstance(current, dict) else None, wind_speed_10m=current.get('wind_speed_10m') if isinstance(current, dict) else None, cloud_cover=current.get('cloud_cover') if isinstance(current, dict) else None, surface_pressure=current.get('surface_pressure') if isinstance(current, dict) else None)
        times = hourly.get('time', []) if isinstance(hourly, dict) else []
        htemp = hourly.get('temperature_2m', []) if isinstance(hourly, dict) else []
        hhum = hourly.get('relative_humidity_2m', []) if isinstance(hourly, dict) else []
        hprec = hourly.get('precipitation', []) if isinstance(hourly, dict) else []
        hprob = hourly.get('precipitation_probability', []) if isinstance(hourly, dict) else []
        hwc = hourly.get('weather_code', []) if isinstance(hourly, dict) else []
        hwind = hourly.get('wind_speed_10m', []) if isinstance(hourly, dict) else []
        hcloud = hourly.get('cloud_cover', []) if isinstance(hourly, dict) else []
        hlist: List[Dict[str, Any]] = []
        for i,t in enumerate(times[:MAX_HOURS]):
            def g(lst, idx): 
                try: return lst[idx] if idx < len(lst) else None
                except Exception: return None
            hlist.append({'time': t, 'temperature_2m': g(htemp,i), 'relative_humidity_2m': g(hhum,i), 'precipitation': g(hprec,i), 'precipitation_probability': g(hprob,i), 'weather_code': g(hwc,i), 'wind_speed_10m': g(hwind,i), 'cloud_cover': g(hcloud,i)})
        snap.hourly = hlist
        dtimes = daily.get('time', []) if isinstance(daily, dict) else []
        dwc = daily.get('weather_code', []) if isinstance(daily, dict) else []
        dmax = daily.get('temperature_2m_max', []) if isinstance(daily, dict) else []
        dmin = daily.get('temperature_2m_min', []) if isinstance(daily, dict) else []
        dpsum = daily.get('precipitation_sum', []) if isinstance(daily, dict) else []
        dppmax = daily.get('precipitation_probability_max', []) if isinstance(daily, dict) else []
        dsunr = daily.get('sunrise', []) if isinstance(daily, dict) else []
        dsuns = daily.get('sunset', []) if isinstance(daily, dict) else []
        dwmax = daily.get('wind_speed_10m_max', []) if isinstance(daily, dict) else []
        dlist: List[Dict[str, Any]] = []
        for i,t in enumerate(dtimes[:MAX_DAYS]):
            def g(lst, idx): 
                try: return lst[idx] if idx < len(lst) else None
                except Exception: return None
            dlist.append({'time': t, 'weather_code': g(dwc,i), 'temperature_2m_max': g(dmax,i), 'temperature_2m_min': g(dmin,i), 'precipitation_sum': g(dpsum,i), 'precipitation_probability_max': g(dppmax,i), 'sunrise': g(dsunr,i), 'sunset': g(dsuns,i), 'wind_speed_10m_max': g(dwmax,i)})
        snap.daily = dlist
        return snap
async def fetch_full_weather(latitude: float, longitude: float) -> WeatherSnapshot:
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise WeatherServiceError('Those coordinates are not valid for a weather lookup.', f'out-of-range lat={latitude} lon={longitude}')
    params = {'latitude': f'{latitude:.6f}', 'longitude': f'{longitude:.6f}', 'current': ','.join(CURRENT_FIELDS), 'hourly': ','.join(HOURLY_FIELDS), 'daily': ','.join(DAILY_FIELDS), 'timezone': 'auto', 'forecast_days': MAX_DAYS, 'forecast_hours': MAX_HOURS}
    try:
        async with httpx.AsyncClient(timeout=settings.OPEN_METEO_TIMEOUT_SECONDS) as client:
            response = await client.get(f'{settings.OPEN_METEO_BASE_URL}/forecast', params=params)
    except httpx.TimeoutException as exc:
        logger.warning('Weather lookup timeout for %s,%s: %s', latitude, longitude, exc)
        raise WeatherServiceError('Weather data could not be fetched right now. Please try again later.', f'timeout: {exc}') from exc
    except httpx.HTTPError as exc:
        logger.warning('Weather lookup network failure: %s', exc)
        raise WeatherServiceError('Weather data could not be fetched right now. Please try again later.', f'network error: {exc}') from exc
    if response.status_code != 200:
        logger.warning('Weather lookup HTTP %s', response.status_code)
        raise WeatherServiceError('Weather data could not be fetched right now. Please try again later.', f'HTTP {response.status_code}')
    try:
        payload = response.json()
    except ValueError as exc:
        logger.warning('Weather lookup invalid JSON: %s', exc)
        raise WeatherServiceError('Weather service returned an unexpected response.', 'invalid JSON response') from exc
    try:
        return WeatherSnapshot.from_openmeteo(latitude, longitude, payload)
    except Exception as exc:
        logger.warning('Weather lookup payload parse error: %s', exc)
        raise WeatherServiceError('Weather service returned an unexpected response.', f'parse error: {exc}') from exc
async def fetch_current_weather(latitude: float, longitude: float) -> WeatherSnapshot:
    return await fetch_full_weather(latitude, longitude)
async def check_service_reachable() -> dict:
    started = datetime.now(timezone.utc).timestamp()
    try:
        async with httpx.AsyncClient(timeout=settings.OPEN_METEO_TIMEOUT_SECONDS) as client:
            response = await client.get(f'{settings.OPEN_METEO_BASE_URL}/forecast', params={'latitude': '0', 'longitude': '0', 'current': 'temperature_2m'})
        latency_ms = int((datetime.now(timezone.utc).timestamp() - started) * 1000)
        if response.status_code == 200:
            return {'reachable': True, 'latency_ms': latency_ms, 'detail': 'HTTP 200'}
        logger.warning('Open-Meteo check returned HTTP %s', response.status_code)
        return {'reachable': False, 'latency_ms': latency_ms, 'detail': f'HTTP {response.status_code}'}
    except httpx.HTTPError as exc:
        logger.warning('Open-Meteo connectivity check failed: %s', exc)
        return {'reachable': False, 'latency_ms': None, 'detail': type(exc).__name__}
