from typing import Dict
import requests
import logging
from redis_manager import redis_manager, logger

def get_endpoint_quota_cost(url: str) -> int:
    """
    Get the quota cost for different YouTube API endpoints
    Based on Google's API quota documentation
    """
    if 'search' in url:
        return 100  # Search endpoint
    elif 'videos' in url:
        return 1    # Videos endpoint
    elif 'channels' in url:
        return 1    # Channels endpoint
    elif 'playlistItems' in url:
        return 1    # PlaylistItems endpoint
    elif 'playlists' in url:
        return 1    # Playlists endpoint
    else:
        return 1    # Default quota cost for unknown endpoints

def make_youtube_api_request(url: str, params: Dict):
    """
    Make a request to the YouTube API with proper key rotation and quota management
    """
    max_retries = 3  # Maximum number of retries across all keys
    retry_count = 0
    
    # Check if all keys are exhausted before starting
    if redis_manager.are_all_keys_exhausted():
        logger.error("All API keys have exceeded their quotas. Request cannot be processed.")
        key_status = redis_manager.get_key_status_summary()
        logger.info(f"API Key Status Summary: {key_status}")
        raise Exception("All API keys have exceeded their daily quotas. Please try again tomorrow or add more API keys.")
    
    while retry_count < max_retries:
        # Get the current API key from Redis
        current_key, key_index = redis_manager.get_current_api_key()
        
        if not current_key:
            raise Exception("No valid API keys available")
        
        # Add the API key to the request parameters
        params['key'] = current_key
        
        # Get quota cost for this endpoint
        quota_cost = get_endpoint_quota_cost(url)
        
        # Log the request
        endpoint = url.split('/')[-1]
        logger.info(f"Request to {endpoint} using API key index {key_index} (quota cost: {quota_cost})")
        
        try:
            # Add natural delay to avoid detection
            redis_manager.add_request_delay()
            
            # Make the request
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                # Request was successful, increment the usage counter
                redis_manager.increment_usage(key_index, quota_cost)
                return response.json()
                
            elif response.status_code == 403:
                response_data = response.json() if response.content else {}
                error_reason = response_data.get('error', {}).get('errors', [{}])[0].get('reason', '')
                
                if 'quotaExceeded' in error_reason or 'dailyLimitExceeded' in error_reason:
                    # Quota exceeded, mark this key as exhausted and get a new one
                    logger.warning(f"Quota exceeded for API key index {key_index}, reason: {error_reason}")
                    redis_manager.mark_key_quota_exceeded(key_index)
                    
                    # Check if all keys are now exhausted
                    if redis_manager.are_all_keys_exhausted():
                        key_status = redis_manager.get_key_status_summary()
                        logger.error(f"All API keys exhausted. Status: {key_status}")
                        raise Exception("All API keys have exceeded their daily quotas. Please try again tomorrow or add more API keys.")
                    
                    retry_count += 1
                    continue  # Try with the next key
                elif 'keyInvalid' in error_reason or 'accessNotConfigured' in error_reason:
                    # Invalid API key, mark as exhausted
                    logger.error(f"Invalid API key at index {key_index}, reason: {error_reason}")
                    redis_manager.mark_key_quota_exceeded(key_index)
                    retry_count += 1
                    continue  # Try with the next key
                else:
                    # Other 403 error
                    error_msg = f"API request forbidden with status {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
            else:
                # Other error occurred
                error_msg = f"API request failed with status {response.status_code}: {response.text}"
                logger.error(error_msg)
                retry_count += 1
                if retry_count >= max_retries:
                    raise Exception(error_msg)
                continue  # Retry with same or different key
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during API request: {e}")
            retry_count += 1
            if retry_count >= max_retries:
                raise Exception(f"Network error after {max_retries} retries: {e}")
            continue  # Retry
    
    raise Exception(f"API request failed after {max_retries} retries")