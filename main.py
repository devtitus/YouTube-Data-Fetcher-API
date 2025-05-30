from fastapi import FastAPI, HTTPException, Request
from get_search_youtube import get_query_searched_results
from get_channel_youtube import get_yt_channel_id
from get_playlist_youtube import get_yt_channel_videos_playlist
from get_playlist_youtube_only_video_id import get_yt_channel_videos_playlist_only_video_id
from get_videos_youtube import get_youtube_videos_details
from redis_manager import logger, redis_manager
import time

# Create the FastAPI app
app = FastAPI()

# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Log the request details
    logger.info(
        f"Request: {request.method} {request.url.path} "
        f"- Status: {response.status_code} "
        f"- Duration: {process_time:.4f}s"
    )
    
    return response

# Health check endpoint
@app.get("/health")
def health_check():
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "redis_connected": redis_manager.connected
    }
    
    # Try to get the current API key to verify Redis is working
    if redis_manager.connected:
        try:
            key, index = redis_manager.get_current_api_key()
            health_status["current_key_index"] = index
        except Exception as e:
            health_status["status"] = "degraded"
            health_status["redis_error"] = str(e)
    
    return health_status

# Query Search Endpoint
@app.get("/youtube/search")
def search_youtube(q: str, max_results: int = 5):
    try:
        logger.info(f"Search request for query: '{q}' with max_results={max_results}")
        data = get_query_searched_results(q, max_results)
        return data
    except Exception as e:
        logger.error(f"Error in search endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Fetch Channel details Endpoint
@app.get("/youtube/channel")
def get_channel_details(channel_id: str):
    try:
        logger.info(f"Channel details request for channel_id: '{channel_id}'")
        data = get_yt_channel_id(channel_id)
        return data
    except Exception as e:
        logger.error(f"Error in channel endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Get Videos IDs from a Channels Playlist Endpoint
@app.get("/youtube/playlist")
def get_playlist_videos(playlist_id: str, max_results: int = 5):
    try:
        logger.info(f"Playlist videos request for playlist_id: '{playlist_id}' with max_results={max_results}")
        data = get_yt_channel_videos_playlist(playlist_id, max_results)
        return data
    except Exception as e:
        logger.error(f"Error in playlist endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
# Get Videos IDs from a Channels Playlist Endpoint
@app.get("/youtube/playlist_only_video_id")
def get_playlist_youtube_only_video_id(playlist_id: str, max_results: int = 5):
    try:
        logger.info(f"Playlist videos request for playlist_id: '{playlist_id}' with max_results={max_results}")
        data = get_yt_channel_videos_playlist_only_video_id(playlist_id, max_results)
        return data
    except Exception as e:
        logger.error(f"Error in playlist endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

#Fetch Video Details Endpoint
@app.get("/youtube/video")
def get_video_details(video_id: str, max_results: int = 5):
    try: 
        logger.info(f"Video details request for video_id: '{video_id}' with max_results={max_results}")
        data = get_youtube_videos_details(video_id, max_results)
        return data
    except Exception as e:
        logger.error(f"Error in video endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Function to run the FastAPI server
def run_fastapi():
    import uvicorn
    logger.info("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=5679)

# Run the FastAPI server in a separate thread
if __name__ == "__main__":
    import threading
    thread = threading.Thread(target=run_fastapi)
    thread.start()

    print("FastAPI server is running on http://127.0.0.1:5679")
    logger.info("FastAPI server is running on http://127.0.0.1:5679")