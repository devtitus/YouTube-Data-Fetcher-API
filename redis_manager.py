import redis
import logging
import time
import os
import pytz
from datetime import datetime
from typing import Tuple, Dict, Any, Optional, Union
from config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, REDIS_KEY_PREFIX, API_KEYS, KEY_ROTATION_THRESHOLD, QUOTA_LIMIT

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/youtube_api.log')
    ]
)
logger = logging.getLogger('youtube_api')

class RedisManager:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.connected = False
        try:
            self._connect_with_retry()
            self._initialize_keys()
            self.connected = True
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            logger.warning("Falling back to in-memory storage for API key management")
            # Initialize in-memory fallback storage
            self.current_key_index = 0
            self.quota_usage = {i: 0 for i in range(len(API_KEYS))}
            self.request_counts = {i: 0 for i in range(len(API_KEYS))}
            self.last_reset_times = {i: datetime.now(pytz.utc) for i in range(len(API_KEYS))}

    def _connect_with_retry(self, max_retries=15, retry_delay=10):
        """Connect to Redis with retry mechanism for Docker container startup"""
        retries = 0
        while retries < max_retries:
            try:
                logger.info(f"Attempting to connect to Redis at {REDIS_HOST}:{REDIS_PORT} (attempt {retries+1}/{max_retries})")
                # Only pass password if it's not None or empty
                redis_kwargs = {
                    'host': REDIS_HOST,
                    'port': REDIS_PORT,
                    'db': REDIS_DB,
                    'decode_responses': True,
                    'socket_timeout': 5,
                    'socket_connect_timeout': 5
                }
                
                if REDIS_PASSWORD and REDIS_PASSWORD.strip():
                    redis_kwargs['password'] = REDIS_PASSWORD
                    
                self.redis_client = redis.Redis(**redis_kwargs)
                # Test connection
                self.redis_client.ping()
                logger.info(f"Successfully connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
                return
            except (redis.ConnectionError, redis.TimeoutError) as e:
                retries += 1
                logger.warning(f"Failed to connect to Redis: {e}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
        
        logger.error(f"Failed to connect to Redis after {max_retries} attempts")
        raise Exception(f"Could not connect to Redis at {REDIS_HOST}:{REDIS_PORT}")

    def _safe_redis_get(self, key: str, default: Any = None) -> Any:
        """Safely get a value from Redis with proper type handling"""
        if not self.redis_client:
            return default
        try:
            result = self.redis_client.get(key)
            return result if result is not None else default
        except redis.RedisError:
            return default

    def _safe_redis_set(self, key: str, value: Any) -> bool:
        """Safely set a value in Redis"""
        if not self.redis_client:
            return False
        try:
            self.redis_client.set(key, value)
            return True
        except redis.RedisError as e:
            logger.error(f"Error setting Redis key {key}: {e}")
            return False

    def _safe_redis_incrby(self, key: str, amount: int = 1) -> int:
        """Safely increment a Redis key by amount"""
        if not self.redis_client:
            return 0
        try:
            result = self.redis_client.incrby(key, amount)
            return int(str(result)) if result is not None else 0
        except (redis.RedisError, ValueError, TypeError):
            return 0

    def _safe_redis_exists(self, key: str) -> bool:
        """Safely check if a Redis key exists"""
        if not self.redis_client:
            return False
        try:
            return bool(self.redis_client.exists(key))
        except redis.RedisError:
            return False

    def _initialize_keys(self):
        """Initialize API keys in Redis if they don't exist"""
        if not self.redis_client:
            return
            
        try:
            if not self._safe_redis_exists(f"{REDIS_KEY_PREFIX}current_key_index"):
                self._safe_redis_set(f"{REDIS_KEY_PREFIX}current_key_index", 0)
                
            # Initialize quota usage and reset dates for each key
            pt_date = self._get_current_pt_date()
            for i, key in enumerate(API_KEYS):
                quota_key = f"{REDIS_KEY_PREFIX}quota:{i}"
                request_count_key = f"{REDIS_KEY_PREFIX}requests:{i}"
                reset_key = f"{REDIS_KEY_PREFIX}last_reset_date:{i}"
                
                if not self._safe_redis_exists(quota_key):
                    self._safe_redis_set(quota_key, 0)
                
                if not self._safe_redis_exists(request_count_key):
                    self._safe_redis_set(request_count_key, 0)
                    
                if not self._safe_redis_exists(reset_key):
                    self._safe_redis_set(reset_key, pt_date)
                    
            logger.info(f"Redis initialized with {len(API_KEYS)} API keys and reset dates")
        except Exception as e:
            logger.error(f"Error initializing Redis keys: {e}")
            raise

    def get_current_api_key(self) -> Tuple[str, int]:
        """Get the current API key based on rotation strategy"""
        if not self.connected:
            # Fallback to in-memory storage
            return API_KEYS[self.current_key_index], self.current_key_index
            
        try:
            index_str = self._safe_redis_get(f"{REDIS_KEY_PREFIX}current_key_index", "0")
            index = int(str(index_str)) if index_str else 0
            
            # Ensure index is within bounds
            if index >= len(API_KEYS):
                index = 0
                self._safe_redis_set(f"{REDIS_KEY_PREFIX}current_key_index", 0)
            
            # Reset quota if needed (based on PT date)
            self._reset_quota_if_needed(index)
            
            return API_KEYS[index], index
        except (ValueError, IndexError) as e:
            logger.error(f"Error getting current API key: {e}")
            # Fallback to first key if Redis fails
            return API_KEYS[0], 0

    def _get_current_pt_date(self) -> str:
        """Get current date in Pacific Time - handles both PST and PDT automatically"""
        pt = pytz.timezone('America/Los_Angeles')
        return datetime.now(pytz.utc).astimezone(pt).strftime('%Y-%m-%d')
    
    def _get_current_pt_datetime(self) -> datetime:
        """Get current datetime in Pacific Time for more precise tracking"""
        pt = pytz.timezone('America/Los_Angeles')
        return datetime.now(pytz.utc).astimezone(pt)
    
    def _is_new_pt_day(self, last_reset_date_str: Optional[str]) -> bool:
        """Check if we've crossed into a new PT day more precisely"""
        if not last_reset_date_str or last_reset_date_str == 'unknown':
            return True
            
        try:
            current_pt_date = self._get_current_pt_date()
            return last_reset_date_str != current_pt_date
        except Exception as e:
            logger.error(f"Error checking PT date: {e}")
            return True  # Err on the side of caution

    def _reset_quota_if_needed(self, key_index: int):
        """Reset daily quota if we've crossed into a new PT date"""
        reset_key = f"{REDIS_KEY_PREFIX}last_reset_date:{key_index}"
        current_pt_date = self._get_current_pt_date()
        last_reset_date = self._safe_redis_get(reset_key)
        
        if self._is_new_pt_day(str(last_reset_date) if last_reset_date else None):
            quota_key = f"{REDIS_KEY_PREFIX}quota:{key_index}"
            request_count_key = f"{REDIS_KEY_PREFIX}requests:{key_index}"
            
            # Reset both quota and request count for the new day
            self._safe_redis_set(quota_key, 0)
            self._safe_redis_set(request_count_key, 0)
            self._safe_redis_set(reset_key, current_pt_date)
            logger.info(f"Reset daily quota and request count for API key index {key_index} (New PT date: {current_pt_date})")

    def increment_usage(self, key_index: int, quota_cost: int = 1) -> int:
        """Increment the usage count for a specific API key"""
        if not self.connected:
            # Fallback to in-memory storage
            # Reset daily quota if needed
            current_time = datetime.now(pytz.utc)
            if (current_time - self.last_reset_times[key_index]).days >= 1:
                self.quota_usage[key_index] = 0
                self.request_counts[key_index] = 0  # Reset request count on new day
                self.last_reset_times[key_index] = current_time
                logger.info(f"Reset daily quota and request count for API key index {key_index}")
            
            self.quota_usage[key_index] += quota_cost
            self.request_counts[key_index] += 1
            
            logger.info(f"API Key {key_index} - Request #{self.request_counts[key_index]} - Quota used: {self.quota_usage[key_index]}/{QUOTA_LIMIT}")
            
            # Conservative rotation logic to avoid flagging
            # Use fixed 90% threshold
            quota_threshold = 0.90  # Fixed 90% threshold
            request_threshold = 1000  # Fixed request threshold
            
            if (self.quota_usage[key_index] >= QUOTA_LIMIT * quota_threshold or
                self.request_counts[key_index] >= request_threshold):
                next_index = self.rotate_key()
                logger.info(f"Rotated key from {key_index} to {next_index} (Quota: {self.quota_usage[key_index]}, Requests: {self.request_counts[key_index]})")
            
            return self.quota_usage[key_index]
            
        try:
            # Reset quota if needed before incrementing
            self._reset_quota_if_needed(key_index)
            
            # Increment quota usage
            quota_key = f"{REDIS_KEY_PREFIX}quota:{key_index}"
            new_quota = self._safe_redis_incrby(quota_key, quota_cost)
            
            # Increment request count
            request_count_key = f"{REDIS_KEY_PREFIX}requests:{key_index}"
            new_request_count = self._safe_redis_incrby(request_count_key, 1)
            
            logger.info(f"API Key {key_index} - Request #{new_request_count} - Quota used: {new_quota}/{QUOTA_LIMIT}")
            
            # More conservative rotation with randomized thresholds
            import random
            quota_threshold = random.uniform(0.75, 0.85)  # Random between 75-85%
            request_threshold = random.randint(800, 1200)  # Random between 800-1200
            
            if (new_quota >= QUOTA_LIMIT * quota_threshold or
                new_request_count >= request_threshold):
                next_index = self.rotate_key()
                logger.info(f"Rotated key from {key_index} to {next_index} (Quota: {new_quota}, Requests: {new_request_count})")
                # DON'T reset request count - let it accumulate naturally for more realistic patterns
                
            return new_quota
        except Exception as e:
            logger.error(f"Error incrementing usage: {e}")
            return 0

    def rotate_key(self) -> int:
        """Rotate to the next available API key"""
        if not self.connected:
            # Fallback to in-memory storage
            current_index = self.current_key_index
            next_index = (current_index + 1) % len(API_KEYS)
            
            # Check if the next key has available quota
            attempts = 0
            while attempts < len(API_KEYS):
                if self.quota_usage[next_index] < QUOTA_LIMIT:
                    # Found a key with available quota
                    break
                    
                # Try the next key
                next_index = (next_index + 1) % len(API_KEYS)
                attempts += 1
                
            if attempts == len(API_KEYS):
                logger.error("All API keys have exceeded their quota!")
                
            # Update the current key index
            self.current_key_index = next_index
            logger.info(f"Rotated from API key {current_index} to {next_index}")
            
            return next_index
            
        try:
            current_index_str = self._safe_redis_get(f"{REDIS_KEY_PREFIX}current_key_index", "0")
            current_index = int(str(current_index_str)) if current_index_str else 0
            next_index = (current_index + 1) % len(API_KEYS)
            
            # Check if the next key has available quota
            attempts = 0
            while attempts < len(API_KEYS):
                quota_key = f"{REDIS_KEY_PREFIX}quota:{next_index}"
                current_quota_str = self._safe_redis_get(quota_key, "0")
                current_quota = int(str(current_quota_str)) if current_quota_str else 0
                
                if current_quota < QUOTA_LIMIT:
                    # Found a key with available quota
                    break
                    
                # Try the next key
                next_index = (next_index + 1) % len(API_KEYS)
                attempts += 1
                
            if attempts == len(API_KEYS):
                logger.error("All API keys have exceeded their quota!")
                
            # Update the current key index
            self._safe_redis_set(f"{REDIS_KEY_PREFIX}current_key_index", next_index)
            logger.info(f"Rotated from API key {current_index} to {next_index}")
            
            return next_index
        except Exception as e:
            logger.error(f"Error rotating key: {e}")
            return 0

    def mark_key_quota_exceeded(self, key_index: int) -> int:
        """Mark a key as having exceeded its quota"""
        if not self.connected:
            # Fallback to in-memory storage
            self.quota_usage[key_index] = QUOTA_LIMIT
            logger.warning(f"API Key {key_index} marked as quota exceeded")
            
            # Rotate to next key
            return self.rotate_key()
            
        try:
            quota_key = f"{REDIS_KEY_PREFIX}quota:{key_index}"
            self._safe_redis_set(quota_key, QUOTA_LIMIT)
            logger.warning(f"API Key {key_index} marked as quota exceeded")
            
            # Rotate to next key
            return self.rotate_key()
        except Exception as e:
            logger.error(f"Error marking key quota exceeded: {e}")
            return 0

    def are_all_keys_exhausted(self) -> bool:
        """Check if all API keys have exceeded their quotas"""
        if not self.connected:
            # Fallback to in-memory storage
            return all(usage >= QUOTA_LIMIT for usage in self.quota_usage.values())
        
        try:
            for i in range(len(API_KEYS)):
                quota_key = f"{REDIS_KEY_PREFIX}quota:{i}"
                current_quota_str = self._safe_redis_get(quota_key, "0")
                current_quota = int(str(current_quota_str)) if current_quota_str else 0
                if current_quota < QUOTA_LIMIT:
                    return False
            return True
        except Exception as e:
            logger.error(f"Error checking if all keys exhausted: {e}")
            return False
    
    def get_key_status_summary(self) -> Dict[int, Dict[str, Any]]:
        """Get a summary of all API key statuses for logging/monitoring"""
        if not self.connected:
            # Fallback to in-memory storage
            return {
                i: {
                    'quota_used': self.quota_usage.get(i, 0),
                    'requests_made': self.request_counts.get(i, 0),
                    'last_reset': self.last_reset_times.get(i, datetime.now(pytz.utc)).isoformat()
                }
                for i in range(len(API_KEYS))
            }
        
        try:
            status = {}
            for i in range(len(API_KEYS)):
                quota_key = f"{REDIS_KEY_PREFIX}quota:{i}"
                request_count_key = f"{REDIS_KEY_PREFIX}requests:{i}"
                reset_key = f"{REDIS_KEY_PREFIX}last_reset_date:{i}"
                
                quota_used_str = self._safe_redis_get(quota_key, "0")
                requests_made_str = self._safe_redis_get(request_count_key, "0")
                last_reset = self._safe_redis_get(reset_key, "unknown")
                
                status[i] = {
                    'quota_used': int(str(quota_used_str)) if quota_used_str else 0,
                    'requests_made': int(str(requests_made_str)) if requests_made_str else 0,
                    'last_reset': str(last_reset) if last_reset else 'unknown'
                }
            return status
        except Exception as e:
            logger.error(f"Error getting key status summary: {e}")
            return {}

    def log_quota_validation_check(self):
        """Log current quota status for manual validation against Google Console"""
        status = self.get_key_status_summary()
        logger.info("=== QUOTA VALIDATION CHECK ===")
        for key_index, stats in status.items():
            logger.info(f"Key {key_index}: {stats['quota_used']}/{QUOTA_LIMIT} quota used, "
                       f"{stats['requests_made']} requests made, "
                       f"last reset: {stats['last_reset']}")
        logger.info("Compare these numbers with Google API Console > Quotas page")
    
    def add_request_delay(self):
        """Add small random delays to make request patterns more natural"""
        import random
        import time
        
        # Random delay between 0.1 to 0.5 seconds
        delay = random.uniform(0.1, 0.5)
        time.sleep(delay)
        logger.debug(f"Added {delay:.2f}s delay for natural request pattern")

# Create a singleton instance
redis_manager = RedisManager()
