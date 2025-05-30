import redis
import logging
import time
import os
import pytz
from datetime import datetime
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
        self.redis_client = None
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
                self.redis_client = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    db=REDIS_DB,
                    password=REDIS_PASSWORD,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5
                )
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

    def _initialize_keys(self):
        """Initialize API keys in Redis if they don't exist"""
        try:
            if not self.redis_client.exists(f"{REDIS_KEY_PREFIX}current_key_index"):
                self.redis_client.set(f"{REDIS_KEY_PREFIX}current_key_index", 0)
                
            # Initialize quota usage and reset dates for each key
            pt_date = self._get_current_pt_date()
            for i, key in enumerate(API_KEYS):
                quota_key = f"{REDIS_KEY_PREFIX}quota:{i}"
                request_count_key = f"{REDIS_KEY_PREFIX}requests:{i}"
                reset_key = f"{REDIS_KEY_PREFIX}last_reset_date:{i}"
                
                if not self.redis_client.exists(quota_key):
                    self.redis_client.set(quota_key, 0)
                
                if not self.redis_client.exists(request_count_key):
                    self.redis_client.set(request_count_key, 0)
                    
                if not self.redis_client.exists(reset_key):
                    self.redis_client.set(reset_key, pt_date)
                    
            logger.info(f"Redis initialized with {len(API_KEYS)} API keys and reset dates")
        except redis.RedisError as e:
            logger.error(f"Error initializing Redis keys: {e}")
            raise

    def get_current_api_key(self):
        """Get the current API key based on rotation strategy"""
        if not self.connected:
            # Fallback to in-memory storage
            return API_KEYS[self.current_key_index], self.current_key_index
            
        try:
            index = int(self.redis_client.get(f"{REDIS_KEY_PREFIX}current_key_index"))
            
            # Reset quota if needed (based on PT date)
            self._reset_quota_if_needed(index)
            
            return API_KEYS[index], index
        except redis.RedisError as e:
            logger.error(f"Error getting current API key: {e}")
            # Fallback to first key if Redis fails
            return API_KEYS[0], 0

    def _get_current_pt_date(self):
        """Get current date in Pacific Time"""
        pt = pytz.timezone('America/Los_Angeles')
        return datetime.now(pytz.utc).astimezone(pt).strftime('%Y-%m-%d')

    def _reset_quota_if_needed(self, key_index):
        """Reset daily quota if we've crossed into a new PT date"""
        reset_key = f"{REDIS_KEY_PREFIX}last_reset_date:{key_index}"
        current_pt_date = self._get_current_pt_date()
        last_reset_date = self.redis_client.get(reset_key)
        
        if last_reset_date != current_pt_date:
            quota_key = f"{REDIS_KEY_PREFIX}quota:{key_index}"
            self.redis_client.set(quota_key, 0)
            self.redis_client.set(reset_key, current_pt_date)
            logger.info(f"Reset daily quota for API key index {key_index}")

    def increment_usage(self, key_index, quota_cost=1):
        """Increment the usage count for a specific API key"""
        if not self.connected:
            # Fallback to in-memory storage
            # Reset daily quota if needed
            current_time = datetime.now(pytz.utc)
            if (current_time - self.last_reset_times[key_index]).days >= 1:
                self.quota_usage[key_index] = 0
                self.last_reset_times[key_index] = current_time
                logger.info(f"Reset daily quota for API key index {key_index}")
            
            self.quota_usage[key_index] += quota_cost
            self.request_counts[key_index] += 1
            
            logger.info(f"API Key {key_index} - Request #{self.request_counts[key_index]} - Quota used: {self.quota_usage[key_index]}/{QUOTA_LIMIT}")
            
            # Check if we need to rotate keys based on request count
            if self.request_counts[key_index] >= KEY_ROTATION_THRESHOLD:
                self.rotate_key()
                logger.info(f"Rotated key after {self.request_counts[key_index]} requests")
                # Reset request count for this key
                self.request_counts[key_index] = 0
            
            return self.quota_usage[key_index]
            
        try:
            # Reset quota if needed before incrementing
            self._reset_quota_if_needed(key_index)
            
            # Increment quota usage
            quota_key = f"{REDIS_KEY_PREFIX}quota:{key_index}"
            new_quota = self.redis_client.incrby(quota_key, quota_cost)
            
            # Increment request count
            request_count_key = f"{REDIS_KEY_PREFIX}requests:{key_index}"
            new_request_count = self.redis_client.incrby(request_count_key, 1)
            
            logger.info(f"API Key {key_index} - Request #{new_request_count} - Quota used: {new_quota}/{QUOTA_LIMIT}")
            
            # Check if we need to rotate keys based on request count
            if new_request_count >= KEY_ROTATION_THRESHOLD:
                self.rotate_key()
                logger.info(f"Rotated key after {new_request_count} requests")
                # Reset request count for this key
                self.redis_client.set(request_count_key, 0)
            
            return new_quota
        except redis.RedisError as e:
            logger.error(f"Error incrementing usage: {e}")
            return 0

    def rotate_key(self):
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
            current_index = int(self.redis_client.get(f"{REDIS_KEY_PREFIX}current_key_index"))
            next_index = (current_index + 1) % len(API_KEYS)
            
            # Check if the next key has available quota
            attempts = 0
            while attempts < len(API_KEYS):
                quota_key = f"{REDIS_KEY_PREFIX}quota:{next_index}"
                current_quota = int(self.redis_client.get(quota_key))
                
                if current_quota < QUOTA_LIMIT:
                    # Found a key with available quota
                    break
                    
                # Try the next key
                next_index = (next_index + 1) % len(API_KEYS)
                attempts += 1
                
            if attempts == len(API_KEYS):
                logger.error("All API keys have exceeded their quota!")
                
            # Update the current key index
            self.redis_client.set(f"{REDIS_KEY_PREFIX}current_key_index", next_index)
            logger.info(f"Rotated from API key {current_index} to {next_index}")
            
            return next_index
        except redis.RedisError as e:
            logger.error(f"Error rotating key: {e}")
            return 0

    def mark_key_quota_exceeded(self, key_index):
        """Mark a key as having exceeded its quota"""
        if not self.connected:
            # Fallback to in-memory storage
            self.quota_usage[key_index] = QUOTA_LIMIT
            logger.warning(f"API Key {key_index} marked as quota exceeded")
            
            # Rotate to next key
            return self.rotate_key()
            
        try:
            quota_key = f"{REDIS_KEY_PREFIX}quota:{key_index}"
            self.redis_client.set(quota_key, QUOTA_LIMIT)
            logger.warning(f"API Key {key_index} marked as quota exceeded")
            
            # Rotate to next key
            return self.rotate_key()
        except redis.RedisError as e:
            logger.error(f"Error marking key quota exceeded: {e}")
            return 0

# Create a singleton instance
redis_manager = RedisManager()
