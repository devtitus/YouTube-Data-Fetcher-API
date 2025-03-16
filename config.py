from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# List of API keys (loaded from environment variables)
API_KEYS = [
    os.getenv("API_KEY_1"),
    os.getenv("API_KEY_2"),
    os.getenv("API_KEY_3"),
    os.getenv("API_KEY_4"),
    os.getenv("API_KEY_5"),
    os.getenv("API_KEY_6"),
    os.getenv("API_KEY_7"),
    os.getenv("API_KEY_8"),
    os.getenv("API_KEY_9"),
    os.getenv("API_KEY_10"),
    os.getenv("API_KEY_11"),
    os.getenv("API_KEY_12"),
]

# Quota limit per API key
QUOTA_LIMIT = 10000