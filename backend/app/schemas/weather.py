from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class CurrentWeather(BaseModel):
    model_config = ConfigDict(extra='ignore')

    temperature_2m: Optional[float] = None
    feels_like_2m: Optional[float] = None
    relative_humidity_2m: Optional[float] = None
    precipitation: Optional[float] = None
    precipitation_probability: Optional[float] = None
    weather_code: Optional[int] = None
    wind_speed_10m: Optional[float] = None
    cloud_cover: Optional[float] = None
    surface_pressure: Optional[float] = None
    observed_at: Optional[str] = None


class HourlyWeatherPoint(BaseModel):
    model_config = ConfigDict(extra='ignore')

    time: Optional[str] = None
    temperature_2m: Optional[float] = None
    relative_humidity_2m: Optional[float] = None
    precipitation: Optional[float] = None
    precipitation_probability: Optional[float] = None
    weather_code: Optional[int] = None
    wind_speed_10m: Optional[float] = None
    cloud_cover: Optional[float] = None


class DailyWeatherPoint(BaseModel):
    model_config = ConfigDict(extra='ignore')

    time: Optional[str] = None
    weather_code: Optional[int] = None
    temperature_2m_max: Optional[float] = None
    temperature_2m_min: Optional[float] = None
    precipitation_sum: Optional[float] = None
    precipitation_probability_max: Optional[float] = None
    sunrise: Optional[str] = None
    sunset: Optional[str] = None
    wind_speed_10m_max: Optional[float] = None


class WeatherData(BaseModel):
    model_config = ConfigDict(extra='ignore')

    source: str = 'Open-Meteo'
    latitude: float
    longitude: float
    field_name: Optional[str] = None
    village: Optional[str] = None
    locality: Optional[str] = None
    sub_district: Optional[str] = None
    taluk: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    data_source: str = 'Open-Meteo'
    last_updated_at: Optional[str] = None
    is_current: bool = True
    current: Optional[CurrentWeather] = None
    hourly: List[HourlyWeatherPoint] = []
    daily: List[DailyWeatherPoint] = []


class WeatherInsightItem(BaseModel):
    model_config = ConfigDict(extra='ignore')

    title: str
    observation: str
    relevant_weather: str
    explanation: str
    limitation: str


class WeatherResponse(BaseModel):
    model_config = ConfigDict(extra='ignore')

    status: str
    message: Optional[str] = None
    field: Optional[dict] = None
    weather: Optional[WeatherData] = None
    insights: List[WeatherInsightItem] = []
