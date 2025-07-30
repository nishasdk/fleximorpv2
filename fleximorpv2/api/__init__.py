"""
API Integration Module for FlexiMORP v2
Handles data fetching from NREL, NASA, Copernicus, and OpenWeather APIs
"""

from .base_api import BaseAPIClient
from .nrel_api import NRELClient
from .nasa_api import NASAClient
from .copernicus_api import CopernicusClient
from .openweather_api import OpenWeatherClient
from .cache_manager import CacheManager

__all__ = [
    'BaseAPIClient',
    'NRELClient', 
    'NASAClient',
    'CopernicusClient',
    'OpenWeatherClient',
    'CacheManager'
]
