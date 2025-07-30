"""
Cache Manager for API Data

Handles caching of API responses with TTL, cleanup, and statistics
"""

import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Manages caching of API responses with TTL and cleanup
    """
    
    def __init__(self, 
                 base_path: str = "./cache", 
                 cache_ttl_hours: int = 24,
                 max_cache_size_mb: int = 500):
        """
        Initialize cache manager
        
        Args:
            base_path: Base directory for cache files
            cache_ttl_hours: Time-to-live for cache entries in hours
            max_cache_size_mb: Maximum cache size in MB
        """
        self.base_path = Path(base_path)
        self.ttl = timedelta(hours=cache_ttl_hours)
        self.max_cache_size = max_cache_size_mb * 1024 * 1024  # Convert to bytes
        
        # Create cache directories
        self.base_path.mkdir(exist_ok=True)
        for api_dir in ['nrel', 'nasa', 'copernicus', 'openweather']:
            (self.base_path / api_dir).mkdir(exist_ok=True)
        
        logger.info(f"Initialized cache manager at {self.base_path} with TTL: {cache_ttl_hours}h")
    
    def get_cache_key(self, 
                     api_name: str, 
                     endpoint: str, 
                     params: Dict[str, Any],
                     suffix: str = "") -> str:
        """
        Generate unique cache key from API parameters
        
        Args:
            api_name: Name of the API client
            endpoint: API endpoint
            params: Request parameters
            suffix: Additional identifier
            
        Returns:
            Unique cache key string
        """
        # Create a deterministic string from parameters
        param_str = json.dumps(params, sort_keys=True, separators=(',', ':'))
        combined_str = f"{api_name}_{endpoint}_{param_str}_{suffix}"
        
        # Generate hash to avoid filesystem issues with long names
        cache_hash = hashlib.md5(combined_str.encode()).hexdigest()
        
        return f"{api_name.lower()}_{endpoint.replace('/', '_')}_{cache_hash}"
    
    def is_cached_and_fresh(self, cache_key: str) -> bool:
        """
        Check if data is cached and still fresh
        
        Args:
            cache_key: Cache key to check
            
        Returns:
            True if cached and fresh, False otherwise
        """
        cache_file = self._get_cache_file_path(cache_key)
        
        if not cache_file.exists():
            return False
        
        # Check if file is still fresh
        try:
            mod_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            is_fresh = datetime.now() - mod_time < self.ttl
            
            if not is_fresh:
                logger.debug(f"Cache expired for {cache_key}")
                # Remove expired cache file
                cache_file.unlink(missing_ok=True)
                return False
            
            return True
            
        except OSError as e:
            logger.warning(f"Error checking cache file {cache_key}: {e}")
            return False
    
    def save_to_cache(self, cache_key: str, data: Dict[str, Any]):
        """
        Save data to cache
        
        Args:
            cache_key: Cache key
            data: Data to cache
        """
        cache_file = self._get_cache_file_path(cache_key)
        
        try:
            # Create directory if it doesn't exist
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Add metadata to cached data
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'cache_key': cache_key,
                'data': data
            }
            
            # Write to cache file
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved data to cache: {cache_key}")
            
            # Check cache size and cleanup if necessary
            self._cleanup_if_needed()
            
        except (OSError, json.JSONEncodeError) as e:
            logger.error(f"Failed to save cache {cache_key}: {e}")
    
    def load_from_cache(self, cache_key: str) -> Dict[str, Any]:
        """
        Load data from cache
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached data
            
        Raises:
            FileNotFoundError: If cache file doesn't exist
            ValueError: If cache file is corrupted
        """
        cache_file = self._get_cache_file_path(cache_key)
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            logger.debug(f"Loaded data from cache: {cache_key}")
            return cache_data['data']
            
        except (OSError, json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to load cache {cache_key}: {e}")
            # Remove corrupted cache file
            cache_file.unlink(missing_ok=True)
            raise ValueError(f"Corrupted cache file: {cache_key}")
    
    def clear_cache(self, pattern: str = None):
        """
        Clear cache files
        
        Args:
            pattern: Optional pattern to match cache keys (clears all if None)
        """
        try:
            if pattern is None:
                # Clear entire cache
                if self.base_path.exists():
                    shutil.rmtree(self.base_path)
                    self.base_path.mkdir(exist_ok=True)
                    for api_dir in ['nrel', 'nasa', 'copernicus', 'openweather']:
                        (self.base_path / api_dir).mkdir(exist_ok=True)
                logger.info("Cleared entire cache")
            else:
                # Clear files matching pattern
                cleared_count = 0
                for cache_file in self.base_path.rglob("*.json"):
                    if pattern in cache_file.name:
                        cache_file.unlink()
                        cleared_count += 1
                logger.info(f"Cleared {cleared_count} cache files matching pattern: {pattern}")
                
        except OSError as e:
            logger.error(f"Failed to clear cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            total_files = 0
            total_size = 0
            api_stats = {}
            
            for api_dir in self.base_path.iterdir():
                if api_dir.is_dir():
                    api_files = list(api_dir.glob("*.json"))
                    api_size = sum(f.stat().st_size for f in api_files)
                    
                    api_stats[api_dir.name] = {
                        'files': len(api_files),
                        'size_mb': api_size / (1024 * 1024)
                    }
                    
                    total_files += len(api_files)
                    total_size += api_size
            
            return {
                'total_files': total_files,
                'total_size_mb': total_size / (1024 * 1024),
                'max_size_mb': self.max_cache_size / (1024 * 1024),
                'usage_percent': (total_size / self.max_cache_size) * 100,
                'ttl_hours': self.ttl.total_seconds() / 3600,
                'api_breakdown': api_stats
            }
            
        except OSError as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {'error': str(e)}
    
    def _get_cache_file_path(self, cache_key: str) -> Path:
        """Get full path for cache file"""
        # Extract API name from cache key to organize into subdirectories
        api_name = cache_key.split('_')[0] if '_' in cache_key else 'misc'
        return self.base_path / api_name / f"{cache_key}.json"
    
    def _cleanup_if_needed(self):
        """Clean up cache if it exceeds size limit"""
        try:
            total_size = sum(
                f.stat().st_size 
                for f in self.base_path.rglob("*.json")
                if f.is_file()
            )
            
            if total_size > self.max_cache_size:
                logger.info(f"Cache size ({total_size / (1024*1024):.1f}MB) exceeds limit, cleaning up...")
                self._cleanup_old_files()
                
        except OSError as e:
            logger.error(f"Failed to check cache size: {e}")
    
    def _cleanup_old_files(self):
        """Remove oldest cache files to free space"""
        try:
            # Get all cache files with their modification times
            cache_files = []
            for cache_file in self.base_path.rglob("*.json"):
                if cache_file.is_file():
                    mod_time = cache_file.stat().st_mtime
                    cache_files.append((mod_time, cache_file))
            
            # Sort by modification time (oldest first)
            cache_files.sort(key=lambda x: x[0])
            
            # Remove oldest 25% of files
            files_to_remove = len(cache_files) // 4
            removed_count = 0
            
            for _, cache_file in cache_files[:files_to_remove]:
                try:
                    cache_file.unlink()
                    removed_count += 1
                except OSError:
                    continue
            
            logger.info(f"Cleaned up {removed_count} old cache files")
            
        except OSError as e:
            logger.error(f"Failed to cleanup old cache files: {e}")
    
    def get_cached_files_list(self) -> List[Dict[str, Any]]:
        """
        Get list of all cached files with metadata
        
        Returns:
            List of dictionaries with file information
        """
        cached_files = []
        
        try:
            for cache_file in self.base_path.rglob("*.json"):
                if cache_file.is_file():
                    stat = cache_file.stat()
                    mod_time = datetime.fromtimestamp(stat.st_mtime)
                    age_hours = (datetime.now() - mod_time).total_seconds() / 3600
                    
                    cached_files.append({
                        'filename': cache_file.name,
                        'api': cache_file.parent.name,
                        'size_kb': stat.st_size / 1024,
                        'modified': mod_time.isoformat(),
                        'age_hours': age_hours,
                        'expired': age_hours > (self.ttl.total_seconds() / 3600)
                    })
            
            # Sort by modification time (newest first)
            cached_files.sort(key=lambda x: x['modified'], reverse=True)
            
        except OSError as e:
            logger.error(f"Failed to list cached files: {e}")
        
        return cached_files
