"""
OpenWeather API Client

Provides access to OpenWeather's current weather and forecast data:
- Current weather conditions
- 5-day weather forecasts
- Historical weather data
- Marine weather data
- Weather alerts and warnings
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging

from .base_api import BaseAPIClient, APIError

logger = logging.getLogger(__name__)


class OpenWeatherClient(BaseAPIClient):
    """
    OpenWeather API client for current and forecast weather data
    """
    
    def __init__(self, api_key: str, cache_ttl_hours: int = 3):  # Short cache for current data
        """
        Initialize OpenWeather API client
        
        Args:
            api_key: OpenWeather API key
            cache_ttl_hours: Cache TTL (default 3 hours for weather data)
        """
        super().__init__(
            api_key=api_key,
            base_url="https://api.openweathermap.org/data/2.5",
            cache_ttl_hours=cache_ttl_hours,
            rate_limit_per_minute=60  # Free tier limit
        )
        
        logger.info("Initialized OpenWeather API client")
    
    def _get_auth_params(self) -> Dict[str, str]:
        """Get OpenWeather API authentication parameters"""
        return {'appid': self.api_key}
    
    def get_current_weather(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Get current weather conditions
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Current weather data
        """
        endpoint = "weather"
        
        params = {
            'lat': lat,
            'lon': lon,
            'units': 'metric'
        }
        
        try:
            data = self.fetch_with_cache(endpoint, params, f"current_{lat}_{lon}")
            processed = self._process_current_weather(data, lat, lon)
            return processed
            
        except Exception as e:
            logger.error(f"Failed to fetch current weather for {lat}, {lon}: {e}")
            return self._get_fallback_current_weather(lat, lon)
    
    def get_forecast(self, lat: float, lon: float, days: int = 5) -> Dict[str, Any]:
        """
        Get weather forecast
        
        Args:
            lat: Latitude
            lon: Longitude
            days: Number of forecast days (max 5 for free tier)
            
        Returns:
            Weather forecast data
        """
        endpoint = "forecast"
        
        params = {
            'lat': lat,
            'lon': lon,
            'units': 'metric',
            'cnt': min(days * 8, 40)  # 3-hour intervals, max 40 for free tier
        }
        
        try:
            data = self.fetch_with_cache(endpoint, params, f"forecast_{lat}_{lon}_{days}d")
            processed = self._process_forecast_data(data, lat, lon, days)
            return processed
            
        except Exception as e:
            logger.error(f"Failed to fetch forecast for {lat}, {lon}: {e}")
            return self._get_fallback_forecast(lat, lon, days)
    
    def get_marine_weather(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Get marine weather conditions (requires marine subscription)
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Marine weather data
        """
        # Note: Marine API requires paid subscription
        # For demo, we'll estimate from regular weather data
        
        current_weather = self.get_current_weather(lat, lon)
        
        # Estimate marine conditions from weather data
        marine_data = {
            'location': {'latitude': lat, 'longitude': lon},
            'timestamp': datetime.now().isoformat(),
            'data_source': 'OpenWeather (estimated)',
            'quality_flag': 'estimated'
        }
        
        if 'wind_speed_ms' in current_weather:
            wind_speed = current_weather['wind_speed_ms']
            
            # Estimate wave conditions from wind (simplified)
            if wind_speed < 5:
                wave_height = 0.5
                sea_state = 'calm'
            elif wind_speed < 10:
                wave_height = 1.5
                sea_state = 'slight'
            elif wind_speed < 15:
                wave_height = 2.5
                sea_state = 'moderate'
            else:
                wave_height = 4.0
                sea_state = 'rough'
            
            marine_data.update({
                'wind_speed_ms': wind_speed,
                'wind_direction_deg': current_weather.get('wind_direction_deg', 0),
                'estimated_wave_height_m': wave_height,
                'sea_state': sea_state,
                'wave_energy_potential': 'low' if wave_height < 2 else 'medium' if wave_height < 3 else 'high'
            })
        
        return marine_data
    
    def get_weather_alerts(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Get weather alerts and warnings
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Weather alerts data
        """
        endpoint = "onecall"
        
        params = {
            'lat': lat,
            'lon': lon,
            'exclude': 'minutely,hourly,daily',  # Only get alerts
            'units': 'metric'
        }
        
        try:
            data = self.fetch_with_cache(endpoint, params, f"alerts_{lat}_{lon}")
            alerts = self._process_alerts_data(data, lat, lon)
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to fetch weather alerts for {lat}, {lon}: {e}")
            return self._get_fallback_alerts(lat, lon)
    
    def get_operational_conditions(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Get current operational conditions for renewable energy systems
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Operational conditions assessment
        """
        current = self.get_current_weather(lat, lon)
        forecast = self.get_forecast(lat, lon, days=1)
        
        conditions = {
            'location': {'latitude': lat, 'longitude': lon},
            'timestamp': datetime.now().isoformat(),
            'data_source': 'OpenWeather',
            'assessment_period': '24h forecast'
        }
        
        # Assess operational conditions
        wind_speed = current.get('wind_speed_ms', 0)
        temperature = current.get('temperature_c', 15)
        visibility = current.get('visibility_km', 10)
        
        # Wind turbine operational assessment
        if wind_speed < 3:
            wind_status = 'below_cut_in'
        elif wind_speed < 25:
            wind_status = 'operational'
        else:
            wind_status = 'above_cut_out'
        
        # Solar panel operational assessment
        cloud_cover = current.get('cloud_cover_percent', 50)
        if cloud_cover < 25:
            solar_status = 'excellent'
        elif cloud_cover < 50:
            solar_status = 'good'
        elif cloud_cover < 75:
            solar_status = 'fair'
        else:
            solar_status = 'poor'
        
        # Overall system assessment
        weather_desc = current.get('weather_description', '').lower()
        if any(term in weather_desc for term in ['storm', 'thunderstorm', 'severe']):
            system_status = 'maintenance_required'
        elif wind_speed > 20 or temperature < -10 or temperature > 40:
            system_status = 'caution'
        else:
            system_status = 'normal_operation'
        
        conditions.update({
            'current_conditions': current,
            'wind_turbine_status': wind_status,
            'solar_panel_status': solar_status,
            'system_status': system_status,
            'operational_capacity_estimate': {
                'wind': 0 if wind_status != 'operational' else min(1.0, wind_speed / 15),
                'solar': (100 - cloud_cover) / 100,
                'wave': min(0.8, wind_speed / 20)  # Estimated from wind
            },
            'forecast_24h': forecast.get('daily_summary', {}),
            'maintenance_recommendations': self._get_maintenance_recommendations(current, forecast)
        })
        
        return conditions
    
    def _process_current_weather(self, data: Dict[str, Any], lat: float, lon: float) -> Dict[str, Any]:
        """Process current weather data"""
        processed = {
            'location': {'latitude': lat, 'longitude': lon},
            'timestamp': datetime.now().isoformat(),
            'data_source': 'OpenWeather Current'
        }
        
        # Extract main weather data
        main = data.get('main', {})
        wind = data.get('wind', {})
        clouds = data.get('clouds', {})
        weather = data.get('weather', [{}])[0]
        
        processed.update({
            'temperature_c': main.get('temp', 15),
            'feels_like_c': main.get('feels_like', 15),
            'humidity_percent': main.get('humidity', 50),
            'pressure_hpa': main.get('pressure', 1013),
            'wind_speed_ms': wind.get('speed', 0),
            'wind_direction_deg': wind.get('deg', 0),
            'wind_gust_ms': wind.get('gust', 0),
            'cloud_cover_percent': clouds.get('all', 0),
            'visibility_km': data.get('visibility', 10000) / 1000,
            'weather_main': weather.get('main', 'Clear'),
            'weather_description': weather.get('description', 'clear sky')
        })
        
        return processed
    
    def _process_forecast_data(self, data: Dict[str, Any], lat: float, lon: float, days: int) -> Dict[str, Any]:
        """Process forecast data"""
        processed = {
            'location': {'latitude': lat, 'longitude': lon},
            'forecast_days': days,
            'data_source': 'OpenWeather Forecast',
            'forecasts': []
        }
        
        forecast_list = data.get('list', [])
        
        # Group by day
        daily_data = {}
        for item in forecast_list:
            dt = datetime.fromtimestamp(item['dt'])
            day_key = dt.strftime('%Y-%m-%d')
            
            if day_key not in daily_data:
                daily_data[day_key] = []
            
            daily_data[day_key].append({
                'datetime': dt.isoformat(),
                'temperature_c': item['main']['temp'],
                'wind_speed_ms': item['wind']['speed'],
                'cloud_cover_percent': item['clouds']['all'],
                'weather': item['weather'][0]['description']
            })
        
        # Calculate daily summaries
        for day, hourly_data in daily_data.items():
            temps = [h['temperature_c'] for h in hourly_data]
            winds = [h['wind_speed_ms'] for h in hourly_data]
            clouds = [h['cloud_cover_percent'] for h in hourly_data]
            
            daily_summary = {
                'date': day,
                'temp_min_c': min(temps),
                'temp_max_c': max(temps),
                'temp_avg_c': np.mean(temps),
                'wind_avg_ms': np.mean(winds),
                'wind_max_ms': max(winds),
                'cloud_avg_percent': np.mean(clouds),
                'hourly_data': hourly_data
            }
            
            processed['forecasts'].append(daily_summary)
        
        # Overall summary
        if processed['forecasts']:
            all_winds = [f['wind_avg_ms'] for f in processed['forecasts']]
            all_clouds = [f['cloud_avg_percent'] for f in processed['forecasts']]
            
            processed['daily_summary'] = {
                'avg_wind_speed_ms': np.mean(all_winds),
                'avg_cloud_cover_percent': np.mean(all_clouds),
                'wind_variability': np.std(all_winds),
                'weather_stability': 'stable' if np.std(all_clouds) < 20 else 'variable'
            }
        
        return processed
    
    def _process_alerts_data(self, data: Dict[str, Any], lat: float, lon: float) -> Dict[str, Any]:
        """Process weather alerts data"""
        alerts_data = {
            'location': {'latitude': lat, 'longitude': lon},
            'timestamp': datetime.now().isoformat(),
            'data_source': 'OpenWeather Alerts',
            'active_alerts': [],
            'alert_summary': 'no_alerts'
        }
        
        alerts = data.get('alerts', [])
        
        for alert in alerts:
            alert_info = {
                'sender': alert.get('sender_name', 'Weather Service'),
                'event': alert.get('event', 'Weather Alert'),
                'description': alert.get('description', ''),
                'start': datetime.fromtimestamp(alert.get('start', 0)).isoformat(),
                'end': datetime.fromtimestamp(alert.get('end', 0)).isoformat(),
                'severity': self._classify_alert_severity(alert.get('event', ''))
            }
            
            alerts_data['active_alerts'].append(alert_info)
        
        if alerts:
            severities = [a['severity'] for a in alerts_data['active_alerts']]
            if 'high' in severities:
                alerts_data['alert_summary'] = 'high_risk'
            elif 'medium' in severities:
                alerts_data['alert_summary'] = 'medium_risk'
            else:
                alerts_data['alert_summary'] = 'low_risk'
        
        return alerts_data
    
    def _classify_alert_severity(self, event: str) -> str:
        """Classify alert severity"""
        event_lower = event.lower()
        
        if any(term in event_lower for term in ['severe', 'extreme', 'hurricane', 'tornado']):
            return 'high'
        elif any(term in event_lower for term in ['storm', 'warning', 'gale']):
            return 'medium'
        else:
            return 'low'
    
    def _get_maintenance_recommendations(self, current: Dict[str, Any], forecast: Dict[str, Any]) -> List[str]:
        """Generate maintenance recommendations"""
        recommendations = []
        
        wind_speed = current.get('wind_speed_ms', 0)
        temperature = current.get('temperature_c', 15)
        humidity = current.get('humidity_percent', 50)
        
        if wind_speed > 20:
            recommendations.append("High wind conditions - consider turbine shutdown if >25 m/s")
        
        if temperature < -10:
            recommendations.append("Low temperature - check for ice formation on blades")
        
        if temperature > 35:
            recommendations.append("High temperature - monitor inverter cooling systems")
        
        if humidity > 80:
            recommendations.append("High humidity - check electrical connections for corrosion")
        
        # Check forecast
        forecast_summary = forecast.get('daily_summary', {})
        if forecast_summary.get('weather_stability') == 'variable':
            recommendations.append("Variable weather forecast - increase monitoring frequency")
        
        if not recommendations:
            recommendations.append("Normal conditions - routine maintenance schedule")
        
        return recommendations
    
    def _get_fallback_current_weather(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fallback current weather data"""
        return {
            'location': {'latitude': lat, 'longitude': lon},
            'temperature_c': 15,
            'wind_speed_ms': 7,
            'cloud_cover_percent': 40,
            'weather_description': 'partly cloudy',
            'data_source': 'estimated',
            'quality_flag': 'low'
        }
    
    def _get_fallback_forecast(self, lat: float, lon: float, days: int) -> Dict[str, Any]:
        """Fallback forecast data"""
        forecasts = []
        for i in range(days):
            date = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
            forecasts.append({
                'date': date,
                'temp_min_c': 10,
                'temp_max_c': 20,
                'wind_avg_ms': 8,
                'cloud_avg_percent': 50
            })
        
        return {
            'location': {'latitude': lat, 'longitude': lon},
            'forecasts': forecasts,
            'daily_summary': {
                'avg_wind_speed_ms': 8,
                'avg_cloud_cover_percent': 50,
                'weather_stability': 'stable'
            },
            'data_source': 'estimated',
            'quality_flag': 'low'
        }
    
    def _get_fallback_alerts(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fallback alerts data"""
        return {
            'location': {'latitude': lat, 'longitude': lon},
            'active_alerts': [],
            'alert_summary': 'no_alerts',
            'data_source': 'estimated',
            'quality_flag': 'low'
        }
