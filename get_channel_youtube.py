from youtube_api import make_youtube_api_request

# 1 Quota Cost
def get_yt_channel_id (channel_id: str):
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "id": channel_id,
        "part": "id,snippet,statistics,status,topicDetails,contentDetails,brandingSettings,localizations",  
        "type": "channel"
    } 
    return make_youtube_api_request(url, params)