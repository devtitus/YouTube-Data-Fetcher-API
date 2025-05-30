from typing import Dict
import requests
import logging
from redis_manager import redis_manager, logger

def make_youtube_api_request(url: str, params: Dict):
    """
    Make a request to the YouTube API with proper key rotation and quota management
    """
    # Get the current API key from Redis
    current_key, key_index = redis_manager.get_current_api_key()
    
    while True:
        # Add the API key to the request parameters
        params['key'] = current_key
        
        # Log the request
        endpoint = url.split('/')[-1]
        logger.info(f"Request to {endpoint} using API key index {key_index}")
        
        # Make the request
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            # Request was successful, increment the usage counter
            # Different endpoints have different quota costs
            quota_cost = 1
            if 'search' in url:
                quota_cost = 100  # Search endpoint costs 100 quota units
                
            redis_manager.increment_usage(key_index, quota_cost)
            return response.json()
            
        elif response.status_code == 403 and 'quotaExceeded' in response.text:
            # Quota exceeded, mark this key as exhausted and get a new one
            logger.warning(f"Quota exceeded for API key index {key_index}")
            next_key_index = redis_manager.mark_key_quota_exceeded(key_index)
            
            # Update the current key and index
            current_key = redis_manager.get_current_api_key()[0]
            key_index = next_key_index
            
            logger.info(f"Switched to API key index {key_index}")
        else:
            # Other error occurred
            error_msg = f"API request failed with status {response.status_code}: {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)