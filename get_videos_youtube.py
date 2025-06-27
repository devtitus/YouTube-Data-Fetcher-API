from youtube_api import make_youtube_api_request

# 1 Quota Cost
def get_youtube_videos_details(video_id: str):
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "id": video_id,
        "part": "id,snippet,contentDetails,localizations,player,statistics,status,liveStreamingDetails,topicDetails,recordingDetails",
    }
    return make_youtube_api_request(url, params)