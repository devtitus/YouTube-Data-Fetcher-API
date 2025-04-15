# youtube_api.py
import requests
from queue import Queue
from config import API_KEYS

# Create a thread-safe queue of valid (non-empty) API keys
_key_queue = Queue()
for key in API_KEYS:
    if key:
        _key_queue.put(key)

def make_youtube_api_request(url, params):
    api_key = _key_queue.get()  # wait if all keys are in use
    returned = False
    try:
        params_with_key = params.copy()
        params_with_key["key"] = api_key

        print(f"📡 Requesting: {url} with key: {api_key[:6]}...")

        response = requests.get(url, params=params_with_key, timeout=10)
        print(f"✅ Response {response.status_code}: {response.text[:100]}...")

        if response.status_code == 403 and 'quotaExceeded' in response.text:
            _key_queue.put(api_key)
            returned = True
            if _key_queue.empty():
                raise Exception("All API keys quota exhausted.")
            return make_youtube_api_request(url, params)

        if response.status_code != 200:
            raise Exception(f"Error {response.status_code}: {response.text}")
        
        return response.json()

    finally:
        if not returned:
            _key_queue.put(api_key)
