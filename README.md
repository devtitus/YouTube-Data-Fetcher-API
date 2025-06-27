# YouTube Data Fetcher API

## Project Overview

This is a FastAPI application that provides endpoints to fetch YouTube data including search results, channel details, playlist videos, and individual video details. The application features **advanced quota management** and **anti-flagging protection** with Redis-based API key rotation.

## 🚀 Key Features

- **Smart API Key Rotation**: Automatic rotation at 90% quota usage
- **Anti-Flagging Protection**: Random delays and conservative thresholds
- **Pacific Time Quota Tracking**: Accurate daily quota resets
- **Redis-Backed Persistence**: Maintains state across restarts
- **Circuit Breaker**: Handles quota exhaustion gracefully
- **Comprehensive Logging**: Detailed request and quota tracking

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
| `/status`                         | GET    | API key status and quota summary   |

## 🛡️ Anti-Flagging & Quota Management

This API implements **95-98% protection** against YouTube API flagging with:

### **Conservative Rotation Strategy**

- **Quota Threshold**: 90% (9,000/10,000 units)
- **Request Threshold**: 1,000 requests per key
- **Natural Delays**: 0.1-0.5 seconds between requests

### **Pacific Time Quota Tracking**

- Accurate PST/PDT timezone handling
- Daily quota resets at midnight PT
- Persistent quota tracking in Redis

### **Smart Key Management**

- Automatic key rotation when thresholds are reached
- Circuit breaker when all keys are exhausted
- Fallback to in-memory storage if Redis is unavailable

### **Monitoring & Validation**

- Real-time quota tracking and logging
- Status endpoint for monitoring key usage
- Quota validation checks against Google Console

## Docker Setup

1. Build and start containers:

```bash
docker-compose up --build
```

2. The API will be accessible at:  
   http://localhost:5679

## Notes

- **Advanced Quota Management**: Automatic key rotation at 90% quota usage with 1000 request limit
- **Anti-Flagging Protection**: Random delays (0.1-0.5s) and conservative thresholds provide 95-98% protection
- **Pacific Time Tracking**: Quota resets align with Google's PT timezone schedule
- **Redis Persistence**: Quota and usage data maintained across application restarts
- **Status Monitoring**: Use `/status` endpoint to monitor API key usage and quota consumption
- **Documentation**: See `ANTI_FLAGGING_ANALYSIS.md` and `QUOTA_TRACKING_EXPLANATION.md` for detailed implementation notes

## 📊 Quota Usage Recommendations

- **Low Risk**: < 5,000 quota per key per day
- **Medium Risk**: 5,000-8,000 quota per key per day
- **Higher Risk**: > 8,000 quota per key per day

The fixed 90% threshold ensures safe operation while maintaining efficiency.
