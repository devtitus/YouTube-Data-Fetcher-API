from youtube_api import make_youtube_api_request

# 100 Quota Cost
def get_query_searched_results(q: str, max_results: int = 5):
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "q": q,
        "part": "id,snippet",
        "maxResults": max_results,
        "type": "video"
    }
    return make_youtube_api_request(url, params)