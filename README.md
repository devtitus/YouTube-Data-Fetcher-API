# YouTube Data Fetcher API

## Project Overview

This is a FastAPI application that provides endpoints to fetch YouTube data including search results, channel details, playlist videos, and individual video details. The application uses Redis for API key management and implements request logging.

## Prerequisites

- Python 3.9+
- Docker (optional, for containerized deployment)
- YouTube Data API v3 keys
- Redis server

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/yt-fetch.git
cd yt-fetch
```

2. Create and activate virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate    # Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

1. Copy the environment template and update with your values:

```bash
cp env.example .env
```

2. Edit the `.env` file with your credentials:

```env
# YouTube API Keys
API_KEY_Proj-yt-app=your_youtube_api_key_here
# Add more keys as needed:
# API_KEY_1=another_api_key_here
# API_KEY_2=another_api_key_here

# Redis Configuration
REDIS_HOST=localhost  # Use 'redis' for Docker setup
REDIS_PORT=6379
REDIS_DB=0
# REDIS_PASSWORD=your_redis_password_here  # Uncomment if using auth
```

## Running the Application

Start the FastAPI server:

```bash
python main.py
```

The API will be accessible at:  
http://127.0.0.1:5679

## API Endpoints

| Endpoint                          | Method | Description                        |
| --------------------------------- | ------ | ---------------------------------- |
| `/health`                         | GET    | Service health check               |
| `/youtube/search`                 | GET    | Search YouTube videos              |
| `/youtube/channel`                | GET    | Get channel details                |
| `/youtube/playlist`               | GET    | Get playlist videos (full details) |
| `/youtube/playlist_only_video_id` | GET    | Get playlist video IDs only        |
| `/youtube/video`                  | GET    | Get video details                  |

## Docker Setup

1. Build and start containers:

```bash
docker-compose up --build
```

2. The API will be accessible at:  
   http://localhost:5679

## Notes

- Rotate YouTube API keys in Redis using the API key manager
- Check `docker-compose.yml` for Redis configuration
- Use `wait-for-redis.sh` to ensure Redis is ready before app startup in Docker
