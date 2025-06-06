
from youtube_api import make_youtube_api_request

# 1 Quota Cost
def get_yt_channel_videos_playlist_only_video_id (playlist_id: str, max_results: int = 5):
    url = "https://www.googleapis.com/youtube/v3/playlistItems"
    params = {
        "part": "id, status, contentDetails",
        "playlistId": playlist_id,
        "maxResults": max_results,
    }
    return make_youtube_api_request(url, params)