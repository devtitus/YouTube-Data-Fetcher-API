from typing import Dict
import requests
from config import API_KEYS, QUOTA_LIMIT

# Dictionary to track quota usage
quota_usage = {key: 0 for key in API_KEYS}

# Index to keep track of the current API key
current_key_index = 0

def get_next_api_key():
    global current_key_index
    current_key_index = (current_key_index + 1) % len(API_KEYS)
    return API_KEYS[current_key_index]

def make_youtube_api_request(url: str, params: Dict):
    global quota_usage

    while True:
        current_key = API_KEYS[current_key_index]
        if quota_usage[current_key] >= QUOTA_LIMIT:
            get_next_api_key()
            continue

        params['key'] = current_key
        response = requests.get(url, params=params)

        if response.status_code == 403 and 'quotaExceeded' in response.text:
            quota_usage[current_key] = QUOTA_LIMIT
            get_next_api_key()
        else:
            quota_usage[current_key] += 1  # Increment quota usage
            return response.json()