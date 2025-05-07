from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Union
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse, FileResponse
from urllib.parse import quote
import subprocess
import uuid
import os
import logging
import sys
import builtins

# Import our optimized secure encoder
from encoder import (
    strict_encode, 
    encode_string, 
    encode_bytes, 
    batch_encode, 
    benchmark,
    clear_caches
)

# Make strict_encode available globally
builtins.strict_encode = strict_encode

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log that we've made strict_encode available
logger.info("strict_encode function has been made globally available")

# Now import the anipy_api modules
from anipy_api.provider import get_provider, LanguageTypeEnum
from anipy_api.anime import Anime

router = APIRouter()

app = FastAPI()

# Whitelist frontend origins
origins = [
    "http://localhost:5173",
    "https://anipulse.pages.dev"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the provider after making strict_encode available
provider = get_provider("animekai")

@app.get("/", tags=["Status"])
def home():
    return {"msg": "Anipy Backend is running!"}

@app.get("/test-encoder", tags=["Diagnostics"])
def test_encoder():
    """
    Test if the encoder is working correctly.
    """
    try:
        # Test with a simple value and instructions
        value = 100
        instructions = "(n + 111) % 256;n ^ 217;~n & 255"
        result = strict_encode(value, instructions)
        
        # Test with the complex instructions from the error
        complex_instructions = "(n + 111) % 256;(n + 212) % 256;n ^ 217;(n + 214) % 256;(n + 151) % 256;~n & 255;~n & 255;~n & 255;(n - 1 + 256) % 256;(n - 96 + 256) % 256;~n & 255;~n & 255;(n - 206 + 256) % 256;~n & 255;(n + 116) % 256;n ^ 70;n ^ 147;(n + 190) % 256;n ^ 222;(n - 118 + 256) % 256;(n - 227 + 256) % 256;~n & 255;(n << 4 | (n & 0xFF) >> 4) & 255;(n + 22) % 256;~n & 255;(n + 94) % 256;(n + 146) % 256;~n & 255;(n - 206 + 256) % 256;(n - 62 + 256) % 256"
        complex_result = strict_encode(value, complex_instructions)
        
        # Check if the function is globally available
        has_global = hasattr(builtins, 'strict_encode')
        
        # Check if the function is available in the global namespace
        global_test = None
        try:
            # Try to evaluate strict_encode in a global context
            global_test = eval("strict_encode(100, '(n + 1) % 256')")
        except Exception as e:
            global_test = f"Error: {str(e)}"
        
        return {
            "status": "success",
            "simple_test": result,
            "complex_test": complex_result[:5],  # Just show the first 5 results
            "globally_available": has_global,
            "global_test": global_test,
            "encoder_version": "optimized"
        }
    except Exception as e:
        logger.error(f"Encoder test failed: {e}")
        return {"status": "error", "message": str(e)}

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

#Function to download anime using ffmpeg
@app.get("/download")
def download_hls_stream(
    hls_url: str = Query(..., description="Direct HLS .m3u8 URL for selected quality"),
    filename: str = Query("video.mp4", description="Desired download filename (optional)")
):
    try:
        # Generate a unique filename in a temporary location
        temp_filename = f"/tmp/{uuid.uuid4().hex}.mp4"

        # FFmpeg command to download and convert HLS to MP4
        command = [
            "ffmpeg",
            "-i", hls_url,
            "-c", "copy",
            "-bsf:a", "aac_adtstoasc",
            "-y",  # Overwrite output if it already exists
            temp_filename,
        ]

        subprocess.run(command, check=True)

        return FileResponse(
            path=temp_filename,
            filename=filename,
            media_type="video/mp4",
            headers={"Content-Disposition": f'attachment; filename="{quote(filename)}"'}
        )

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Video processing failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

if __name__ == "__main__":
    import uvicorn
    print("Starting FastAPI server on port 8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
