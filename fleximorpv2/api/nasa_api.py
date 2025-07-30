"""
NASA API Client

Provides access to NASA's environmental and meteorological data including:
- NASA POWER API (weather, solar irradiance, temperature)
- Earth Observation data
- Climate data for renewable energy analysis
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging

from .base_api import BaseAPIClient, APIError

logger = logging.getLogger(__name__)


class NASAClient(BaseAPIClient):
    """
    NASA API client for environmental and meteorological data
    """
    
    def __init__(self, api_key: str = None, cache_ttl_hours: int = 168):  # 1 week default cache
        """
        Initialize NASA API client
        
        Args:
            api_key: NASA API key (optional for POWER API)
            cache_ttl_hours: Cache TTL (default 1 week for climate data)
        """
        super().__init__(
            api_key=api_key or "DEMO_KEY",
            base_url="https://power.larc.nasa.gov/api",
            cache_ttl_hours=cache_ttl_hours,
            rate_limit_per_minute=1000  # NASA POWER has generous limits
        )
        
        # Alternative endpoints
        self.earth_api_base = "https://api.nasa.gov/planetary/earth"
        
        logger.info("Initialized NASA API client")
    
    def _get_auth_params(self) -> Dict[str, str]:
        """Get NASA API authentication parameters"""
        if self.api_key and self.api_key != "DEMO_KEY":
            return {'api_key': self.api_key}
        return {}
    
    def get_climate_data(self, 
                        lat: float, 
                        lon: float, 
                        start_date: str = "20190101",
                        end_date: str = "20211231",
                        parameters: List[str] = None) -> Dict[str, Any]:
        """
        Get climate data from NASA POWER API
        
        Args:
            lat: Latitude (-90 to 90)
            lon: Longitude (-180 to 180)
            start_date: Start date (YYYYMMDD format)
            end_date: End date (YYYYMMDD format)
            parameters: List of climate parameters to retrieve
            
        Returns:
            Climate data including temperature, humidity, wind, precipitation
        """
        if parameters is None:
            parameters = [
                'T2M',      # Temperature at 2m
                'T2M_MAX',  # Max temperature
                'T2M_MIN',  # Min temperature
                'RH2M',     # Relative humidity
                'WS10M',    # Wind speed at 10m
                'WD10M',    # Wind direction at 10m
                'PRECTOTCORR',  # Precipitation
                'PS',       # Surface pressure
                'ALLSKY_SFC_SW_DWN'  # Solar irradiance
            ]
        
        endpoint = "temporal/daily/point"
        
        params = {
            'parameters': ','.join(parameters),
            'community': 'RE',  # Renewable Energy community
            'longitude': lon,
            'latitude': lat,
            'start': start_date,
            'end': end_date,
            'format': 'JSON'
        }
        
        try:
            data = self.fetch_with_cache(
                endpoint, 
                params, 
                f"climate_{lat}_{lon}_{start_date}_{end_date}"
            )
            
            # Process the climate data
            processed_data = self._process_climate_data(data, lat, lon, start_date, end_date)
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Failed to fetch NASA climate data for {lat}, {lon}: {e}")
            # Return default/estimated data as fallback
            return self._get_default_climate_data(lat, lon, start_date, end_date)
    
    def get_ocean_conditions(self, 
                           lat: float, 
                           lon: float, 
                           start_date: str = "20190101",
                           end_date: str = "20211231") -> Dict[str, Any]:
        """
        Get ocean conditions for wave energy analysis
        
        Args:
            lat: Latitude
            lon: Longitude
            start_date: Start date (YYYYMMDD format)
            end_date: End date (YYYYMMDD format)
            
        Returns:
            Ocean conditions including wave height estimates, temperature
        """
        # NASA POWER doesn't have wave data, but we can get related parameters
        ocean_params = [
            'T2M',          # Air temperature (affects sea surface temp)
            'WS10M',        # Wind speed (primary driver of waves)
            'WD10M',        # Wind direction
            'PS',           # Pressure (affects storm systems)
            'PRECTOTCORR'   # Precipitation (weather patterns)
        ]
        
        endpoint = "temporal/daily/point"
        
        params = {
            'parameters': ','.join(ocean_params),
            'community': 'RE',
            'longitude': lon,
            'latitude': lat,
            'start': start_date,
            'end': end_date,
            'format': 'JSON'
        }
        
        try:
            data = self.fetch_with_cache(
                endpoint, 
                params, 
                f"ocean_{lat}_{lon}_{start_date}_{end_date}"
            )
            
            # Process and estimate ocean conditions
            processed_data = self._process_ocean_data(data, lat, lon)
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Failed to fetch ocean conditions for {lat}, {lon}: {e}")
            return self._get_default_ocean_data(lat, lon)
    
    def get_extreme_weather_stats(self, 
                                 lat: float, 
                                 lon: float, 
                                 years: int = 20) -> Dict[str, Any]:
        """
        Get extreme weather statistics for risk analysis
        
        Args:
            lat: Latitude
            lon: Longitude
            years: Number of years of data to analyze
            
        Returns:
            Extreme weather statistics and return periods
        """
        # Get long-term climate data for extremes analysis
        end_year = 2021
        start_year = max(1981, end_year - years + 1)  # NASA POWER starts from 1981
        
        start_date = f"{start_year}0101"
        end_date = f"{end_year}1231"
        
        extreme_params = [
            'T2M_MAX',      # Max temperature
            'T2M_MIN',      # Min temperature
            'WS10M_MAX',    # Max wind speed
            'PRECTOTCORR',  # Precipitation
            'PS'            # Pressure
        ]
        
        endpoint = "temporal/daily/point"
        
        params = {
            'parameters': ','.join(extreme_params),
            'community': 'RE',
            'longitude': lon,
            'latitude': lat,
            'start': start_date,
            'end': end_date,
            'format': 'JSON'
        }
        
        try:
            data = self.fetch_with_cache(
                endpoint, 
                params, 
                f"extremes_{lat}_{lon}_{years}y"
            )
            
            # Calculate extreme weather statistics
            stats = self._calculate_extreme_stats(data, years)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to fetch extreme weather data for {lat}, {lon}: {e}")
            return self._get_default_extreme_stats(lat, lon)
    
    def get_seasonal_patterns(self, 
                            lat: float, 
                            lon: float, 
                            years: int = 5) -> Dict[str, Any]:
        """
        Get seasonal patterns for resource planning
        
        Args:
            lat: Latitude
            lon: Longitude
            years: Number of years to analyze
            
        Returns:
            Seasonal patterns and monthly statistics
        """
        end_year = 2021
        start_year = end_year - years + 1
        
        start_date = f"{start_year}0101"
        end_date = f"{end_year}1231"
        
        seasonal_params = [
            'ALLSKY_SFC_SW_DWN',  # Solar irradiance
            'WS10M',              # Wind speed
            'T2M',                # Temperature
            'RH2M',               # Humidity
            'PRECTOTCORR'         # Precipitation
        ]
        
        endpoint = "temporal/monthly/point"
        
        params = {
            'parameters': ','.join(seasonal_params),
            'community': 'RE',
            'longitude': lon,
            'latitude': lat,
            'start': start_date,
            'end': end_date,
            'format': 'JSON'
        }
        
        try:
            data = self.fetch_with_cache(
                endpoint, 
                params, 
                f"seasonal_{lat}_{lon}_{years}y"
            )
            
            # Calculate seasonal patterns
            patterns = self._calculate_seasonal_patterns(data)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to fetch seasonal patterns for {lat}, {lon}: {e}")
            return self._get_default_seasonal_patterns(lat, lon)
    
    def _process_climate_data(self, data: Dict[str, Any], lat: float, lon: float, 
                            start_date: str, end_date: str) -> Dict[str, Any]:
        """Process raw climate data from NASA POWER"""
        try:
            properties = data.get('properties', {})
            parameter_data = properties.get('parameter', {})
            
            # Extract time series data
            processed = {
                'location': {'latitude': lat, 'longitude': lon},
                'date_range': {'start': start_date, 'end': end_date},
                'data_source': 'NASA POWER',
                'quality_flag': 'good'
            }
            
            # Process each parameter
            for param, values in parameter_data.items():
                if isinstance(values, dict):
                    # Calculate basic statistics
                    valid_values = [v for v in values.values() if v != -999.0]  # Filter missing data
                    if valid_values:
                        processed[param] = {
                            'mean': np.mean(valid_values),
                            'std': np.std(valid_values),
                            'min': np.min(valid_values),
                            'max': np.max(valid_values),
                            'count': len(valid_values)
                        }
            
            # Calculate derived metrics
            if 'T2M' in processed:
                processed['avg_temperature_c'] = processed['T2M']['mean']
            
            if 'WS10M' in processed:
                processed['avg_wind_speed_ms'] = processed['WS10M']['mean']
                # Estimate wind power density (W/m²)
                ws_mean = processed['WS10M']['mean']
                processed['wind_power_density'] = 0.5 * 1.225 * (ws_mean ** 3)  # Simplified
            
            if 'ALLSKY_SFC_SW_DWN' in processed:
                processed['avg_solar_irradiance'] = processed['ALLSKY_SFC_SW_DWN']['mean']
                # Estimate solar capacity factor
                ghi_mean = processed['ALLSKY_SFC_SW_DWN']['mean']  # kWh/m²/day
                processed['solar_capacity_factor_est'] = min(0.35, ghi_mean / 6.0 * 0.18)
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing NASA climate data: {e}")
            return self._get_default_climate_data(lat, lon, start_date, end_date)
    
    def _process_ocean_data(self, data: Dict[str, Any], lat: float, lon: float) -> Dict[str, Any]:
        """Process ocean conditions from available NASA data"""
        climate_data = self._process_climate_data(data, lat, lon, "", "")
        
        # Estimate wave conditions from wind data
        ocean_conditions = {
            'location': {'latitude': lat, 'longitude': lon},
            'data_source': 'NASA POWER (derived)',
            'quality_flag': 'estimated'
        }
        
        if 'WS10M' in climate_data:
            wind_speed = climate_data['WS10M']['mean']
            # Simplified wave height estimation from wind speed
            # H_s ≈ 0.2 * U²/g (where U is wind speed, g is gravity)
            significant_wave_height = 0.2 * (wind_speed ** 2) / 9.81
            
            ocean_conditions.update({
                'avg_wind_speed_ms': wind_speed,
                'estimated_wave_height_m': significant_wave_height,
                'wave_energy_potential': 'low' if significant_wave_height < 1.5 else 'medium' if significant_wave_height < 3.0 else 'high',
                'wave_power_density_estimate': min(50000, 500 * (significant_wave_height ** 2))  # kW/m (simplified)
            })
        
        return ocean_conditions
    
    def _calculate_extreme_stats(self, data: Dict[str, Any], years: int) -> Dict[str, Any]:
        """Calculate extreme weather statistics"""
        try:
            properties = data.get('properties', {})
            parameter_data = properties.get('parameter', {})
            
            stats = {
                'analysis_period_years': years,
                'data_source': 'NASA POWER',
                'extreme_events': {}
            }
            
            for param, values in parameter_data.items():
                if isinstance(values, dict):
                    valid_values = [v for v in values.values() if v != -999.0]
                    if valid_values:
                        # Calculate percentiles for extreme analysis
                        p95 = np.percentile(valid_values, 95)
                        p99 = np.percentile(valid_values, 99)
                        p1 = np.percentile(valid_values, 1)
                        p5 = np.percentile(valid_values, 5)
                        
                        stats['extreme_events'][param] = {
                            '1_percentile': p1,
                            '5_percentile': p5,
                            '95_percentile': p95,
                            '99_percentile': p99,
                            'return_period_estimate': f"{years}-year analysis"
                        }
            
            # Estimate design conditions
            if 'WS10M_MAX' in stats['extreme_events']:
                max_wind = stats['extreme_events']['WS10M_MAX']['99_percentile']
                stats['design_wind_speed_ms'] = max_wind * 1.1  # Add safety factor
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating extreme statistics: {e}")
            return self._get_default_extreme_stats(0, 0)
    
    def _calculate_seasonal_patterns(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate seasonal patterns from monthly data"""
        try:
            properties = data.get('properties', {})
            parameter_data = properties.get('parameter', {})
            
            patterns = {
                'data_source': 'NASA POWER',
                'monthly_averages': {},
                'seasonal_summary': {}
            }
            
            # Process monthly data for each parameter
            for param, monthly_values in parameter_data.items():
                if isinstance(monthly_values, dict):
                    # Group by month (assuming keys are in YYYYMM format)
                    monthly_groups = {}
                    for date_key, value in monthly_values.items():
                        if value != -999.0:  # Filter missing data
                            month = int(str(date_key)[-2:])  # Extract month
                            if month not in monthly_groups:
                                monthly_groups[month] = []
                            monthly_groups[month].append(value)
                    
                    # Calculate monthly averages
                    monthly_avg = {}
                    for month in range(1, 13):
                        if month in monthly_groups:
                            monthly_avg[month] = np.mean(monthly_groups[month])
                        else:
                            monthly_avg[month] = 0  # No data available
                    
                    patterns['monthly_averages'][param] = monthly_avg
                    
                    # Calculate seasonal statistics
                    seasons = {
                        'winter': [12, 1, 2],
                        'spring': [3, 4, 5],
                        'summer': [6, 7, 8],
                        'autumn': [9, 10, 11]
                    }
                    
                    seasonal_avg = {}
                    for season, months in seasons.items():
                        season_values = [monthly_avg[m] for m in months if m in monthly_avg]
                        seasonal_avg[season] = np.mean(season_values) if season_values else 0
                    
                    patterns['seasonal_summary'][param] = seasonal_avg
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error calculating seasonal patterns: {e}")
            return self._get_default_seasonal_patterns(0, 0)
    
    def _get_default_climate_data(self, lat: float, lon: float, start_date: str, end_date: str) -> Dict[str, Any]:
        """Fallback climate data when API fails"""
        # Estimate based on latitude
        if abs(lat) < 23.5:  # Tropical
            temp = 25
            wind = 6
            solar = 5.5
        elif abs(lat) < 50:  # Temperate
            temp = 12
            wind = 7
            solar = 4.0
        else:  # Polar
            temp = -5
            wind = 8
            solar = 2.5
        
        return {
            'location': {'latitude': lat, 'longitude': lon},
            'date_range': {'start': start_date, 'end': end_date},
            'avg_temperature_c': temp,
            'avg_wind_speed_ms': wind,
            'avg_solar_irradiance': solar,
            'wind_power_density': 300,
            'solar_capacity_factor_est': 0.18,
            'data_source': 'estimated',
            'quality_flag': 'low'
        }
    
    def _get_default_ocean_data(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fallback ocean data when API fails"""
        # Rough estimates based on location
        if abs(lat) > 50:  # High latitude seas
            wave_height = 2.5
            wave_power = 30000
        elif abs(lat) > 30:  # Mid latitude
            wave_height = 1.8
            wave_power = 15000
        else:  # Low latitude
            wave_height = 1.2
            wave_power = 8000
        
        return {
            'location': {'latitude': lat, 'longitude': lon},
            'estimated_wave_height_m': wave_height,
            'wave_power_density_estimate': wave_power,
            'wave_energy_potential': 'medium',
            'data_source': 'estimated',
            'quality_flag': 'low'
        }
    
    def _get_default_extreme_stats(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fallback extreme weather stats"""
        return {
            'analysis_period_years': 20,
            'design_wind_speed_ms': 35,  # Conservative estimate
            'extreme_events': {
                'max_temperature_c': 35,
                'min_temperature_c': -10,
                'max_wind_speed_ms': 30
            },
            'data_source': 'estimated',
            'quality_flag': 'low'
        }
    
    def _get_default_seasonal_patterns(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fallback seasonal patterns"""
        # Simplified seasonal patterns
        if lat > 0:  # Northern hemisphere
            solar_pattern = {1: 0.6, 2: 0.7, 3: 0.8, 4: 0.9, 5: 1.0, 6: 1.1,
                           7: 1.1, 8: 1.0, 9: 0.9, 10: 0.8, 11: 0.7, 12: 0.6}
            wind_pattern = {1: 1.1, 2: 1.0, 3: 0.9, 4: 0.8, 5: 0.8, 6: 0.8,
                          7: 0.8, 8: 0.8, 9: 0.9, 10: 1.0, 11: 1.1, 12: 1.1}
        else:  # Southern hemisphere (inverted)
            solar_pattern = {1: 1.1, 2: 1.0, 3: 0.9, 4: 0.8, 5: 0.7, 6: 0.6,
                           7: 0.6, 8: 0.7, 9: 0.8, 10: 0.9, 11: 1.0, 12: 1.1}
            wind_pattern = {1: 0.8, 2: 0.8, 3: 0.9, 4: 1.0, 5: 1.1, 6: 1.1,
                          7: 1.1, 8: 1.0, 9: 0.9, 10: 0.8, 11: 0.8, 12: 0.8}
        
        return {
            'monthly_averages': {
                'ALLSKY_SFC_SW_DWN': solar_pattern,
                'WS10M': wind_pattern
            },
            'seasonal_summary': {
                'ALLSKY_SFC_SW_DWN': {
                    'winter': 0.7, 'spring': 0.9, 'summer': 1.1, 'autumn': 0.9
                },
                'WS10M': {
                    'winter': 1.0, 'spring': 0.9, 'summer': 0.8, 'autumn': 1.0
                }
            },
            'data_source': 'estimated',
            'quality_flag': 'low'
        }
