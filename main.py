from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Union
from anipy_api.provider import get_provider, LanguageTypeEnum
from anipy_api.anime import Anime
import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse
from urllib.parse import quote
import subprocess
import httpx
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

YOUR_BACKEND_URL = "https://web-production-fee0.up.railway.app"

app = FastAPI()

# Whitelist frontend origins
origins = [
    "http://localhost:5173",
    "https://anipulse.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

provider = get_provider("animekai")

@app.get("/", tags=["Status"])
def home():
    return {"msg": "Anipy Backend is running!"}

@app.get("/search/{query}", tags=["Search"])
def search_anime(query: str):
    try:
        results = provider.get_search(query)
        return [
            {
                "title": r.name,
                "id": r.identifier,
                "languages": [lang.name for lang in r.languages],
            }
            for r in results
        ]
    except Exception as e:
        logger.error(f"Search error: {e}")
        return {"error": str(e)}

@app.get("/episodes/{anime_id}", tags=["Episodes"])
def get_episodes(anime_id: str):
    try:
        anime = Anime(provider, "", anime_id, [LanguageTypeEnum.SUB])
        episodes = anime.get_episodes(lang=LanguageTypeEnum.SUB)
        return {"anime_id": anime_id, "episodes": episodes}
    except Exception as e:
        logger.error(f"Episode error: {e}")
        return {"error": str(e)}

@app.get("/stream/{anime_id}/{episode}", tags=["Streaming"])
def get_streams(
    anime_id: str,
    episode: Union[int, float],
    language: LanguageTypeEnum = Query(default=LanguageTypeEnum.SUB)
):
    try:
        logger.info(f"🔍 Searching for anime: {anime_id}")
        results = provider.get_search(anime_id)

        # Match exactly by identifier
        target_result = next((r for r in results if r.identifier == anime_id), None)
        if not target_result:
            return {"error": "Exact anime match not found for this ID."}

        anime_obj = Anime.from_search_result(provider, target_result)
        episodes = anime_obj.get_episodes(lang=language)

        if episode not in episodes:
            return {"error": f"Episode {episode} is not available in {language.name}."}

        streams = anime_obj.get_videos(episode, language)

        if not streams:
            return {"error": "No streams found for this episode."}

        available_streams = [
            {
                "quality": stream.resolution,
                "url": stream.url,
                "language": stream.language.name,
                "referrer": stream.referrer
            }
            for stream in streams if stream and stream.url
        ]

        return {
            "anime": anime_obj.name,
            "episode": episode,
            "language": language.name,
            "available_streams": sorted(available_streams, key=lambda s: s["quality"], reverse=True)
        }

    except Exception as e:
        logger.error(f"Stream error: {e}")
        return {"error": str(e)}

@app.get("/anime-info/{anime_id}", tags=["Info"])
def get_anime_info(anime_id: str):
    try:
        results = provider.get_search(anime_id)
        target_result = next((r for r in results if r.identifier == anime_id), None)
        if not target_result:
            return {"error": "Anime not found with this ID."}

        anime = Anime.from_search_result(provider, target_result)
        info = anime.get_info()
        return {"info": info}

    except Exception as e:
        logger.error(f"Info error: {e}")
        return {"error": str(e)}





@app.get("/ffmpeg-check")
def check_ffmpeg():
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        return {"output": result.stdout.split('\n')[0]}
    except Exception as e:
        return {"error": str(e)}
