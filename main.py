from fastapi import FastAPI, HTTPException
from get_search_youtube import get_query_searched_results
from get_channel_youtube import get_yt_channel_id
from get_playlist_youtube import get_yt_channel_videos_playlist
from get_videos_youtube import get_youtube_videos_details

# Create the FastAPI app
app = FastAPI()

# Query Search Endpoint
@app.get("/youtube/search")
def search_youtube(q: str, max_results: int = 5):
    try:
        data = get_query_searched_results(q, max_results)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Fetch Channel details Endpoint
@app.get("/youtube/channel")
def get_channel_details(channel_id: str):
    try:
        data = get_yt_channel_id(channel_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get Videos IDs from a Channels Playlist Endpoint
@app.get("/youtube/playlist")
def get_playlist_videos(playlist_id: str, max_results: int = 5):
    try:
        data = get_yt_channel_videos_playlist(playlist_id, max_results)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#Fetch Video Details Endpoint
@app.get("/youtube/video")
def get_video_details(video_id: str, max_results: int = 5):
    try: 
        data = get_youtube_videos_details(video_id, max_results)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Function to run the FastAPI server
def run_fastapi():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Run the FastAPI server in a separate thread
if __name__ == "__main__":
    import threading
    thread = threading.Thread(target=run_fastapi)
    thread.start()

    print("FastAPI server is running on http://127.0.0.1:8000")