"""
API Data Loader for FlexiMORPv2.

Handles loading weather and resource data from various APIs and sources
for offshore renewable energy analysis.
"""

import numpy as np
import pandas as pd
import requests
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
import json
from datetime import datetime, timedelta
import time
import math

from ..config import SiteConfig
from ..models.technologies import ResourceData


@dataclass
class APIResponse:
    """Standardized API response container."""
    data: Any
    status_code: int
    message: str
    timestamp: datetime


class APIDataLoader:
    """
    Data loader for weather and resource APIs.
    
    Handles loading data from multiple sources including weather APIs,
    wave data services, and solar irradiance databases.
    """
    
    def __init__(self, config: SiteConfig):
        """
        Initialize API data loader.
        
        Args:
            config: Site configuration object
        """
        self.config = config
        self.cache = {}  # Simple memory cache
        self.api_endpoints = {
            'openweather': 'https://api.openweathermap.org/data/2.5',
            'metocean': 'https://api.metocean.co.nz/v1',
            'solcast': 'https://api.solcast.com.au',
            'era5': 'https://cds.climate.copernicus.eu/api/v2',
            'hindcast': 'https://marine.copernicus.eu/services-portfolio'
        }
        
        # Rate limiting parameters
        self.rate_limits = {
            'openweather': {'calls_per_minute': 60, 'last_call': 0},
            'metocean': {'calls_per_minute': 100, 'last_call': 0},
            'solcast': {'calls_per_minute': 50, 'last_call': 0}
        }
    
    def load_weather_data(self, 
                         coordinates: List[float], 
                         technologies: List[str],
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> ResourceData:
        """
        Load comprehensive weather and resource data.
        
        Args:
            coordinates: [latitude, longitude]
            technologies: List of technology names
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            ResourceData object with all required data
        """
        print(f"Loading weather data for coordinates: {coordinates}")
        
        # Set default date range (1 year)
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Create cache key
        cache_key = f"{coordinates[0]:.2f}_{coordinates[1]:.2f}_{start_date}_{end_date}"
        
        if cache_key in self.cache:
            print("Using cached weather data")
            return self.cache[cache_key]
        
        # Load data for each required parameter
        data_dict = {}
        
        # Wind data (needed for wind technology)
        if 'wind' in technologies:
            wind_data = self._load_wind_data(coordinates, start_date, end_date)
            data_dict.update(wind_data)
        
        # Solar data (needed for solar technology)
        if 'solar' in technologies:
            solar_data = self._load_solar_data(coordinates, start_date, end_date)
            data_dict.update(solar_data)
        
        # Wave data (needed for wave technology)
        if 'wave' in technologies:
            wave_data = self._load_wave_data(coordinates, start_date, end_date)
            data_dict.update(wave_data)
        
        # Temperature data (needed for all technologies)
        temp_data = self._load_temperature_data(coordinates, start_date, end_date)
        data_dict.update(temp_data)
        
        # Create timestamps
        timestamps = self._create_timestamps(start_date, end_date)
        data_dict['timestamps'] = timestamps
        
        # Ensure all arrays have the same length
        data_dict = self._synchronize_data_arrays(data_dict)
        
        # Create ResourceData object
        resource_data = ResourceData(
            wind_speed=data_dict.get('wind_speed', np.zeros(len(timestamps))),
            solar_irradiance=data_dict.get('solar_irradiance', np.zeros(len(timestamps))),
            wave_height=data_dict.get('wave_height', np.zeros(len(timestamps))),
            wave_period=data_dict.get('wave_period', np.zeros(len(timestamps))),
            temperature=data_dict.get('temperature', np.ones(len(timestamps)) * 15),  # Default 15°C
            timestamps=timestamps
        )
        
        # Cache the result
        self.cache[cache_key] = resource_data
        
        print(f"Loaded {len(timestamps)} data points")
        return resource_data
    
    def _load_wind_data(self, coordinates: List[float], start_date: str, end_date: str) -> Dict[str, np.ndarray]:
        """Load wind speed data from APIs or generate synthetic data."""
        
        # Try to load from configured API
        wind_config = self.config.technologies.get('wind')
        wind_api = wind_config.api_endpoint if wind_config else None
        
        if wind_api:
            try:
                return self._fetch_wind_from_api(coordinates, start_date, end_date, wind_api)
            except Exception as e:
                print(f"Failed to load wind data from API: {e}")
        
        # Generate synthetic wind data
        print("Generating synthetic wind data")
        return self._generate_synthetic_wind_data(coordinates, start_date, end_date)
    
    def _load_solar_data(self, coordinates: List[float], start_date: str, end_date: str) -> Dict[str, np.ndarray]:
        """Load solar irradiance data from APIs or generate synthetic data."""
        
        # Try to load from configured API
        solar_config = self.config.technologies.get('solar')
        solar_api = solar_config.api_endpoint if solar_config else None
        
        if solar_api:
            try:
                return self._fetch_solar_from_api(coordinates, start_date, end_date, solar_api)
            except Exception as e:
                print(f"Failed to load solar data from API: {e}")
        
        # Generate synthetic solar data
        print("Generating synthetic solar data")
        return self._generate_synthetic_solar_data(coordinates, start_date, end_date)
    
    def _load_wave_data(self, coordinates: List[float], start_date: str, end_date: str) -> Dict[str, np.ndarray]:
        """Load wave data from APIs or generate synthetic data."""
        
        # Try to load from configured API
        wave_config = self.config.technologies.get('wave')
        wave_api = wave_config.api_endpoint if wave_config else None
        
        if wave_api:
            try:
                return self._fetch_wave_from_api(coordinates, start_date, end_date, wave_api)
            except Exception as e:
                print(f"Failed to load wave data from API: {e}")
        
        # Generate synthetic wave data
        print("Generating synthetic wave data")
        return self._generate_synthetic_wave_data(coordinates, start_date, end_date)
    
    def _load_temperature_data(self, coordinates: List[float], start_date: str, end_date: str) -> Dict[str, np.ndarray]:
        """Load temperature data."""
        print("Generating synthetic temperature data")
        return self._generate_synthetic_temperature_data(coordinates, start_date, end_date)
    
    def _fetch_wind_from_api(self, coordinates: List[float], start_date: str, end_date: str, api_url: str) -> Dict[str, np.ndarray]:
        """Fetch wind data from external API."""
        
        # Example API call structure - this would need to be customized for each API
        params = {
            'lat': coordinates[0],
            'lon': coordinates[1],
            'start': start_date,
            'end': end_date,
            'variables': 'wind_speed'
        }
        
        response = self._make_api_request(api_url, params)
        
        if response.status_code == 200:
            # Parse API response (structure depends on specific API)
            data = response.data
            wind_speeds = np.array(data.get('wind_speed', []))
            return {'wind_speed': wind_speeds}
        else:
            raise Exception(f"API request failed: {response.message}")
    
    def _fetch_solar_from_api(self, coordinates: List[float], start_date: str, end_date: str, api_url: str) -> Dict[str, np.ndarray]:
        """Fetch solar data from external API."""
        
        params = {
            'lat': coordinates[0],
            'lon': coordinates[1],
            'start': start_date,
            'end': end_date,
            'variables': 'ghi,dni,dhi'  # Global, Direct, Diffuse Horizontal Irradiance
        }
        
        response = self._make_api_request(api_url, params)
        
        if response.status_code == 200:
            data = response.data
            irradiance = np.array(data.get('ghi', []))  # Global Horizontal Irradiance
            return {'solar_irradiance': irradiance}
        else:
            raise Exception(f"API request failed: {response.message}")
    
    def _fetch_wave_from_api(self, coordinates: List[float], start_date: str, end_date: str, api_url: str) -> Dict[str, np.ndarray]:
        """Fetch wave data from external API."""
        
        params = {
            'lat': coordinates[0],
            'lon': coordinates[1],
            'start': start_date,
            'end': end_date,
            'variables': 'wave_height,wave_period'
        }
        
        response = self._make_api_request(api_url, params)
        
        if response.status_code == 200:
            data = response.data
            wave_height = np.array(data.get('wave_height', []))
            wave_period = np.array(data.get('wave_period', []))
            return {'wave_height': wave_height, 'wave_period': wave_period}
        else:
            raise Exception(f"API request failed: {response.message}")
    
    def _make_api_request(self, url: str, params: Dict[str, Any]) -> APIResponse:
        """Make rate-limited API request."""
        
        # Apply rate limiting
        self._apply_rate_limit(url)
        
        try:
            response = requests.get(url, params=params, timeout=30)
            
            return APIResponse(
                data=response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
                status_code=response.status_code,
                message=response.reason,
                timestamp=datetime.now()
            )
        except requests.RequestException as e:
            return APIResponse(
                data=None,
                status_code=500,
                message=str(e),
                timestamp=datetime.now()
            )
    
    def _apply_rate_limit(self, url: str):
        """Apply rate limiting for API calls."""
        
        # Extract service name from URL
        service = 'default'
        for name, endpoint in self.api_endpoints.items():
            if endpoint in url:
                service = name
                break
        
        if service in self.rate_limits:
            rate_info = self.rate_limits[service]
            calls_per_minute = rate_info['calls_per_minute']
            last_call = rate_info['last_call']
            
            # Calculate minimum time between calls
            min_interval = 60.0 / calls_per_minute
            
            # Check if we need to wait
            current_time = time.time()
            time_since_last_call = current_time - last_call
            
            if time_since_last_call < min_interval:
                wait_time = min_interval - time_since_last_call
                print(f"Rate limiting: waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
            
            # Update last call time
            self.rate_limits[service]['last_call'] = time.time()
    
    def _generate_synthetic_wind_data(self, coordinates: List[float], start_date: str, end_date: str) -> Dict[str, np.ndarray]:
        """Generate realistic synthetic wind data."""
        
        timestamps = self._create_timestamps(start_date, end_date)
        num_points = len(timestamps)
        
        # Base wind speed depends on location (offshore typically higher)
        lat, lon = coordinates
        
        # Estimate base wind speed based on location
        if abs(lat) > 50:  # Higher latitudes = stronger winds
            base_wind = 8.5
        elif abs(lat) < 30:  # Lower latitudes = moderate winds
            base_wind = 6.5
        else:
            base_wind = 7.5
        
        # Generate wind speed with realistic patterns
        hours = np.arange(num_points)
        
        # Seasonal variation
        seasonal = 2.0 * np.sin(2 * np.pi * hours / (365.25 * 24)) + 1.0
        
        # Daily variation (weaker during day, stronger at night)
        daily = 1.5 * np.sin(2 * np.pi * hours / 24 + np.pi) + 1.0
        
        # Random weather patterns
        weather_noise = np.random.normal(0, 2.0, num_points)
        
        # Combine patterns
        wind_speeds = base_wind + seasonal + daily + weather_noise
        
        # Apply realistic constraints
        wind_speeds = np.clip(wind_speeds, 0, 30)  # 0-30 m/s range
        
        # Add some gusts and calms
        gust_probability = 0.05
        calm_probability = 0.03
        
        for i in range(num_points):
            if np.random.random() < gust_probability:
                wind_speeds[i] *= np.random.uniform(1.5, 2.5)  # Gust
            elif np.random.random() < calm_probability:
                wind_speeds[i] *= np.random.uniform(0.1, 0.5)  # Calm
        
        wind_speeds = np.clip(wind_speeds, 0, 35)
        
        return {'wind_speed': wind_speeds}
    
    def _generate_synthetic_solar_data(self, coordinates: List[float], start_date: str, end_date: str) -> Dict[str, np.ndarray]:
        """Generate realistic synthetic solar irradiance data."""
        
        timestamps = self._create_timestamps(start_date, end_date)
        num_points = len(timestamps)
        
        lat, lon = coordinates
        
        # Solar irradiance patterns
        irradiance = np.zeros(num_points)
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        
        for i, hour_offset in enumerate(range(num_points)):
            current_dt = start_dt + timedelta(hours=hour_offset)
            
            # Day of year for seasonal calculation
            day_of_year = current_dt.timetuple().tm_yday
            hour_of_day = current_dt.hour + current_dt.minute / 60.0
            
            # Solar elevation calculation (simplified)
            declination = 23.45 * np.sin(np.radians(360 * (284 + day_of_year) / 365))
            hour_angle = 15 * (hour_of_day - 12)
            
            solar_elevation = np.arcsin(
                np.sin(np.radians(declination)) * np.sin(np.radians(lat)) +
                np.cos(np.radians(declination)) * np.cos(np.radians(lat)) * np.cos(np.radians(hour_angle))
            )
            
            # Only positive elevations produce solar radiation
            if solar_elevation > 0:
                # Clear sky irradiance
                air_mass = 1 / np.sin(solar_elevation)
                clear_sky_irradiance = 1353 * (0.7 ** (air_mass ** 0.678))
                
                # Cloud factor (random weather)
                cloud_factor = np.random.uniform(0.3, 1.0)
                
                irradiance[i] = clear_sky_irradiance * cloud_factor * np.sin(solar_elevation)
            else:
                irradiance[i] = 0
        
        # Clip to realistic values
        irradiance = np.clip(irradiance, 0, 1200)  # W/m²
        
        return {'solar_irradiance': irradiance}
    
    def _generate_synthetic_wave_data(self, coordinates: List[float], start_date: str, end_date: str) -> Dict[str, np.ndarray]:
        """Generate realistic synthetic wave data."""
        
        timestamps = self._create_timestamps(start_date, end_date)
        num_points = len(timestamps)
        
        lat, lon = coordinates
        
        # Base wave conditions depend on location
        if abs(lat) > 50:  # Rough seas at high latitudes
            base_height = 2.5
            base_period = 8.0
        elif abs(lat) < 30:  # Calmer seas at low latitudes
            base_height = 1.5
            base_period = 6.0
        else:
            base_height = 2.0
            base_period = 7.0
        
        hours = np.arange(num_points)
        
        # Seasonal variation in wave conditions
        seasonal_height = 0.8 * np.sin(2 * np.pi * hours / (365.25 * 24) + np.pi) + 0.2
        seasonal_period = 1.5 * np.sin(2 * np.pi * hours / (365.25 * 24) + np.pi) + 0.5
        
        # Weather systems (storms create larger waves)
        storm_noise_height = np.random.normal(0, 0.5, num_points)
        storm_noise_period = np.random.normal(0, 1.0, num_points)
        
        # Generate wave heights and periods
        wave_heights = base_height + seasonal_height + storm_noise_height
        wave_periods = base_period + seasonal_period + storm_noise_period
        
        # Apply constraints
        wave_heights = np.clip(wave_heights, 0.5, 8.0)  # 0.5-8m significant wave height
        wave_periods = np.clip(wave_periods, 4.0, 15.0)  # 4-15s wave period
        
        # Add storm events
        storm_probability = 0.02
        for i in range(num_points):
            if np.random.random() < storm_probability:
                # Storm conditions
                wave_heights[i] *= np.random.uniform(2.0, 3.0)
                wave_periods[i] *= np.random.uniform(1.3, 1.8)
        
        wave_heights = np.clip(wave_heights, 0.5, 12.0)
        wave_periods = np.clip(wave_periods, 4.0, 20.0)
        
        return {
            'wave_height': wave_heights,
            'wave_period': wave_periods
        }
    
    def _generate_synthetic_temperature_data(self, coordinates: List[float], start_date: str, end_date: str) -> Dict[str, np.ndarray]:
        """Generate realistic synthetic temperature data."""
        
        timestamps = self._create_timestamps(start_date, end_date)
        num_points = len(timestamps)
        
        lat, lon = coordinates
        
        # Base temperature depends on latitude
        base_temp = 20 - abs(lat) * 0.5  # Roughly 20°C at equator, colder toward poles
        
        hours = np.arange(num_points)
        
        # Seasonal variation
        seasonal = 10 * np.sin(2 * np.pi * hours / (365.25 * 24) - np.pi/2)
        
        # Daily variation
        daily = 5 * np.sin(2 * np.pi * hours / 24 - np.pi/2)
        
        # Random weather variation
        weather_noise = np.random.normal(0, 3, num_points)
        
        # Combine patterns
        temperatures = base_temp + seasonal + daily + weather_noise
        
        # Apply realistic constraints for offshore conditions
        temperatures = np.clip(temperatures, -10, 40)  # °C
        
        return {'temperature': temperatures}
    
    def _create_timestamps(self, start_date: str, end_date: str) -> np.ndarray:
        """Create hourly timestamps between start and end dates."""
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        timestamps = []
        current_dt = start_dt
        
        while current_dt <= end_dt:
            timestamps.append(current_dt)
            current_dt += timedelta(hours=1)
        
        return np.array(timestamps)
    
    def _synchronize_data_arrays(self, data_dict: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """Ensure all data arrays have the same length."""
        
        if 'timestamps' not in data_dict:
            return data_dict
        
        target_length = len(data_dict['timestamps'])
        
        for key, array in data_dict.items():
            if key == 'timestamps':
                continue
                
            current_length = len(array)
            
            if current_length < target_length:
                # Pad with last value
                padding = np.full(target_length - current_length, array[-1] if len(array) > 0 else 0)
                data_dict[key] = np.concatenate([array, padding])
            elif current_length > target_length:
                # Truncate
                data_dict[key] = array[:target_length]
        
        return data_dict
    
    def validate_data_quality(self, resource_data: ResourceData) -> Dict[str, Any]:
        """Validate quality of loaded resource data."""
        
        validation_results = {
            'valid': True,
            'issues': [],
            'statistics': {}
        }
        
        # Check for missing data
        arrays_to_check = {
            'wind_speed': resource_data.wind_speed,
            'solar_irradiance': resource_data.solar_irradiance,
            'wave_height': resource_data.wave_height,
            'wave_period': resource_data.wave_period,
            'temperature': resource_data.temperature
        }
        
        for name, array in arrays_to_check.items():
            # Check for NaN values
            nan_count = np.isnan(array).sum()
            if nan_count > 0:
                validation_results['issues'].append(f"{name}: {nan_count} NaN values")
                validation_results['valid'] = False
            
            # Check for unrealistic values
            if name == 'wind_speed':
                if np.any(array < 0) or np.any(array > 50):
                    validation_results['issues'].append(f"{name}: unrealistic values (should be 0-50 m/s)")
                    validation_results['valid'] = False
            
            elif name == 'solar_irradiance':
                if np.any(array < 0) or np.any(array > 1500):
                    validation_results['issues'].append(f"{name}: unrealistic values (should be 0-1500 W/m²)")
                    validation_results['valid'] = False
            
            elif name == 'wave_height':
                if np.any(array < 0) or np.any(array > 20):
                    validation_results['issues'].append(f"{name}: unrealistic values (should be 0-20 m)")
                    validation_results['valid'] = False
            
            elif name == 'temperature':
                if np.any(array < -50) or np.any(array > 50):
                    validation_results['issues'].append(f"{name}: unrealistic values (should be -50 to 50°C)")
                    validation_results['valid'] = False
            
            # Calculate statistics
            validation_results['statistics'][name] = {
                'mean': float(np.mean(array)),
                'std': float(np.std(array)),
                'min': float(np.min(array)),
                'max': float(np.max(array)),
                'data_points': len(array)
            }
        
        return validation_results
    
    def export_data(self, resource_data: ResourceData, filepath: str, format: str = 'csv'):
        """Export resource data to file."""
        
        # Create DataFrame
        df = pd.DataFrame({
            'timestamp': resource_data.timestamps,
            'wind_speed': resource_data.wind_speed,
            'solar_irradiance': resource_data.solar_irradiance,
            'wave_height': resource_data.wave_height,
            'wave_period': resource_data.wave_period,
            'temperature': resource_data.temperature
        })
        
        if format.lower() == 'csv':
            df.to_csv(filepath, index=False)
        elif format.lower() == 'json':
            df.to_json(filepath, orient='records', date_format='iso')
        elif format.lower() == 'parquet':
            df.to_parquet(filepath, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        print(f"Data exported to {filepath}")
    
    def clear_cache(self):
        """Clear the data cache."""
        self.cache.clear()
        print("Data cache cleared")
