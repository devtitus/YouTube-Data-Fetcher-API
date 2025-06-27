from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# List of API keys (loaded from environment variables)
API_KEYS_RAW = [
    # os.getenv("API_KEY_1"),
    # os.getenv("API_KEY_2"),
    # os.getenv("API_KEY_3"),
    # os.getenv("API_KEY_4"),
    # os.getenv("API_KEY_5"),
    # os.getenv("API_KEY_6"),
    # os.getenv("API_KEY_7"),
    # os.getenv("API_KEY_8"),
    # os.getenv("API_KEY_9"),
    # os.getenv("API_KEY_10"),
    # os.getenv("API_KEY_11"),
    # os.getenv("API_KEY_12"),
    os.getenv("API_KEY_Proj-yt-app")
]

# Filter out None/empty API keys and validate they exist
API_KEYS = [key for key in API_KEYS_RAW if key and key.strip()]

if not API_KEYS:
    raise ValueError("No valid API keys found. Please set at least one API key in your environment variables.")

# Quota limit per API key
QUOTA_LIMIT = 10000

# Number of requests before rotating to next key
KEY_ROTATION_THRESHOLD = 1000

# Redis configuration
# In Docker environment, use the service name as hostname
REDIS_HOST = os.getenv("REDIS_HOST", "redis")  # Default to 'redis' service in Docker
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_KEY_PREFIX = "youtube_api:"