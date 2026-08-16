import os
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import HTTPError
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")
BASE = "https://www.googleapis.com/youtube/v3"

params = {
    "part": "id,snippet",
    "q": "myntra haul",
    "type": "video",
    "maxResults": 30,
    "relevanceLanguage": "en",
    "regionCode": "IN",
    "key": API_KEY
}
url = f"{BASE}/search?{urlencode(params)}"
try:
    with urlopen(url, timeout=30) as r:
        print("Success")
except HTTPError as e:
    print("HTTPError:", e.code)
    print(e.read().decode())
