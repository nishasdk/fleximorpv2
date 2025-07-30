"""
Base API Client with Caching Support

Provides common functionality for all API clients including:
- Request caching with TTL
- Rate limiting
- Error handling and retries
- Batch request processing
"""

import requests
import time
import hashlib
import logging
from typing import Dict, List, Any, Optional, Union
from abc import ABC, abstractmethod
from pathlib import Path
import json
from datetime import datetime, timedelta

from .cache_manager import CacheManager

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Custom exception for API-related errors"""
    pass


class RateLimitError(APIError):
    """Exception raised when API rate limit is exceeded"""
    pass


class BaseAPIClient(ABC):
    """
    Base class for all API clients with caching and rate limiting
    """
    
    def __init__(self, 
                 api_key: str,
                 base_url: str,
                 cache_ttl_hours: int = 24,
                 rate_limit_per_minute: int = 60,
                 max_retries: int = 3):
        """
        Initialize base API client
        
        Args:
            api_key: API authentication key
            base_url: Base URL for API endpoints
            cache_ttl_hours: Cache time-to-live in hours
            rate_limit_per_minute: Maximum requests per minute
            max_retries: Maximum number of retry attempts
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.max_retries = max_retries
        
        # Initialize cache manager
        self.cache_manager = CacheManager(cache_ttl_hours=cache_ttl_hours)
        
        # Rate limiting
        self.rate_limit = rate_limit_per_minute
        self.request_times = []
        
        # Request session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FlexiMORP-v2/1.0',
            'Accept': 'application/json'
        })
        
        logger.info(f"Initialized {self.__class__.__name__} with cache TTL: {cache_ttl_hours}h")
    
    def _check_rate_limit(self):
        """Check and enforce rate limiting"""
        now = time.time()
        
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        # Check if we're at the limit
        if len(self.request_times) >= self.rate_limit:
            sleep_time = 60 - (now - self.request_times[0])
            if sleep_time > 0:
                logger.warning(f"Rate limit reached, sleeping for {sleep_time:.1f} seconds")
                time.sleep(sleep_time)
        
        # Record this request
        self.request_times.append(now)
    
    def _make_request(self, 
                     endpoint: str, 
                     params: Dict[str, Any] = None, 
                     method: str = 'GET') -> Dict[str, Any]:
        """
        Make HTTP request with error handling and retries
        
        Args:
            endpoint: API endpoint (relative to base_url)
            params: Request parameters
            method: HTTP method
            
        Returns:
            Response data as dictionary
            
        Raises:
            APIError: For API-related errors
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        params = params or {}
        
        # Add API key to parameters
        params.update(self._get_auth_params())
        
        for attempt in range(self.max_retries + 1):
            try:
                # Check rate limit before making request
                self._check_rate_limit()
                
                # Make request
                if method.upper() == 'GET':
                    response = self.session.get(url, params=params, timeout=30)
                elif method.upper() == 'POST':
                    response = self.session.post(url, json=params, timeout=30)
                else:
                    raise APIError(f"Unsupported HTTP method: {method}")
                
                # Check response status
                if response.status_code == 429:  # Rate limited
                    if attempt < self.max_retries:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.warning(f"Rate limited, waiting {wait_time} seconds (attempt {attempt + 1})")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise RateLimitError("API rate limit exceeded")
                
                response.raise_for_status()
                
                # Parse JSON response
                try:
                    return response.json()
                except ValueError as e:
                    raise APIError(f"Invalid JSON response: {e}")
                
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(f"Request failed, retrying in {wait_time} seconds: {e}")
                    time.sleep(wait_time)
                    continue
                else:
                    raise APIError(f"Request failed after {self.max_retries} retries: {e}")
        
        raise APIError("Maximum retries exceeded")
    
    def fetch_with_cache(self, 
                        endpoint: str, 
                        params: Dict[str, Any] = None,
                        cache_key_suffix: str = "") -> Dict[str, Any]:
        """
        Fetch data with caching support
        
        Args:
            endpoint: API endpoint
            params: Request parameters
            cache_key_suffix: Additional cache key identifier
            
        Returns:
            Response data (from cache or API)
        """
        params = params or {}
        
        # Generate cache key
        cache_key = self.cache_manager.get_cache_key(
            api_name=self.__class__.__name__,
            endpoint=endpoint,
            params=params,
            suffix=cache_key_suffix
        )
        
        # Check cache first
        if self.cache_manager.is_cached_and_fresh(cache_key):
            logger.debug(f"Cache hit for {cache_key}")
            return self.cache_manager.load_from_cache(cache_key)
        
        # Make API request
        logger.debug(f"Cache miss for {cache_key}, making API request")
        data = self._make_request(endpoint, params)
        
        # Save to cache
        self.cache_manager.save_to_cache(cache_key, data)
        
        return data
    
    def batch_fetch(self, requests_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Batch fetch multiple requests efficiently
        
        Args:
            requests_list: List of request dictionaries with 'endpoint' and 'params' keys
            
        Returns:
            List of response data dictionaries
        """
        results = []
        
        for i, request_info in enumerate(requests_list):
            endpoint = request_info['endpoint']
            params = request_info.get('params', {})
            cache_suffix = request_info.get('cache_suffix', f"batch_{i}")
            
            try:
                result = self.fetch_with_cache(endpoint, params, cache_suffix)
                results.append(result)
                
                # Add small delay between requests to be nice to the API
                if i < len(requests_list) - 1:
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Batch request {i} failed: {e}")
                results.append({'error': str(e)})
        
        return results
    
    @abstractmethod
    def _get_auth_params(self) -> Dict[str, str]:
        """
        Get authentication parameters for API requests
        Must be implemented by subclasses
        
        Returns:
            Dictionary of authentication parameters
        """
        pass
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get current rate limit status
        
        Returns:
            Dictionary with rate limit information
        """
        now = time.time()
        recent_requests = [t for t in self.request_times if now - t < 60]
        
        return {
            'requests_last_minute': len(recent_requests),
            'rate_limit': self.rate_limit,
            'requests_remaining': max(0, self.rate_limit - len(recent_requests)),
            'reset_time': max(recent_requests) + 60 if recent_requests else now
        }
    
    def clear_cache(self, pattern: str = None):
        """
        Clear cached data
        
        Args:
            pattern: Optional pattern to match cache keys (clears all if None)
        """
        self.cache_manager.clear_cache(pattern)
        logger.info(f"Cleared cache for {self.__class__.__name__}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        return self.cache_manager.get_cache_stats()
