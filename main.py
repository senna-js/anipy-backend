from fastapi import FastAPI, Query, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from typing import Union
import builtins
import sys
import logging
import traceback
import os
import re
import subprocess
import uuid
from urllib.parse import quote

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Apply the nuclear patch before importing any anipy_api modules
try:
    from nuclear_patch import apply_nuclear_patch, strict_encode
    fix_success = apply_nuclear_patch()
    logger.info(f"Nuclear patch application: {'Success' if fix_success else 'Failed'}")
    
    # Make strict_encode available globally
    builtins.strict_encode = strict_encode
    logger.info("Added strict_encode to builtins")
except Exception as e:
    logger.error(f"Error applying nuclear patch: {e}")
    logger.error(traceback.format_exc())

# Import the custom provider
try:
    from custom_provider import get_custom_provider, CustomAnime, LanguageTypeEnum
    logger.info("Successfully imported custom provider")
    
    # Use the custom provider instead of the built-in one
    use_custom_provider = True
except Exception as e:
    logger.error(f"Error importing custom provider: {e}")
    logger.error(traceback.format_exc())
    
    # Fall back to the built-in provider
    use_custom_provider = False
    
    # Import the built-in provider
    try:
        from anipy_api.provider import get_provider, LanguageTypeEnum
        from anipy_api.anime import Anime
        
        # Add strict_encode to the Anime class
        Anime.strict_encode = staticmethod(strict_encode)
        logger.info("Added strict_encode to Anime class")
    except Exception as e:
        logger.error(f"Error importing built-in provider: {e}")
        logger.error(traceback.format_exc())

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

# Custom exception handler for all exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_msg = str(exc)
    
    # Check if it's a strict_encode error
    if "strict_encode" in error_msg:
        logger.error(f"Encoder error: {error_msg}")
        
        # Check if it's a function not defined error
        if "Function 'strict_encode' not defined" in error_msg:
            logger.error("This is a function not defined error")
            
            # Try to fix the issue on the fly
            try:
                # Re-apply the nuclear patch
                from nuclear_patch import apply_nuclear_patch
                apply_nuclear_patch()
                logger.info("Re-applied nuclear patch during error handling")
                
                # Switch to the custom provider
                global use_custom_provider
                use_custom_provider = True
                logger.info("Switched to custom provider")
                
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "Function 'strict_encode' not defined",
                        "details": error_msg,
                        "fix_attempted": True,
                        "message": "Please try your request again"
                    }
                )
            except Exception as e:
                logger.error(f"Error re-applying nuclear patch: {e}")
        
        # Try to extract the encoding instructions from the error
        match = re.search(r'strict_encode$$(\d+), "(.*?)"$$', error_msg)
        if match:
            n_value = int(match.group(1))
            instructions = match.group(2)
            logger.info(f"Attempted to call strict_encode with n={n_value}, instructions='{instructions}'")
            
            # Test if our strict_encode function works with these instructions
            try:
                test_result = strict_encode(n_value, instructions)
                logger.info(f"Encoder test successful with sample value {n_value}: {test_result[:5]}...")
                
                # If we get here, our function works but isn't being found
                logger.error("The strict_encode function works but isn't being found in the right scope")
                
                # Switch to the custom provider
                global use_custom_provider
                use_custom_provider = True
                logger.info("Switched to custom provider")
                
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "Encoder function not found in the right scope",
                        "details": error_msg,
                        "fix_attempted": True,
                        "message": "Switched to custom provider, please try again"
                    }
                )
            except Exception as e:
                logger.error(f"Encoder test failed: {e}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "Encoder function test failed",
                        "details": str(e),
                        "original_error": error_msg
                    }
                )
    
    # For other errors
    logger.error(f"Unhandled exception: {error_msg}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={"error": error_msg}
    )

# Initialize provider
try:
    if use_custom_provider:
        provider = get_custom_provider()
        logger.info("Successfully initialized custom provider")
    else:
        provider = get_provider("animekai")
        
        # Add strict_encode to the provider
        provider.strict_encode = strict_encode
        
        logger.info("Successfully initialized animekai provider")
except Exception as e:
    logger.error(f"Failed to initialize provider: {e}")
    provider = None

@app.get("/", tags=["Status"])
def home():
    return {"msg": "Anipy Backend is running!", "provider": "custom" if use_custom_provider else "animekai"}

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
        
        # Check which modules have the function
        modules_with_function = []
        for module_name in sys.modules:
            if module_name.startswith('anipy_api'):
                module = sys.modules[module_name]
                if hasattr(module, 'strict_encode'):
                    modules_with_function.append(module_name)
        
        return {
            "status": "success",
            "simple_test": result,
            "complex_test": complex_result[:5],  # Just show the first 5 results
            "globally_available": has_global,
            "global_test": global_test,
            "modules_with_function": modules_with_function,
            "encoder_version": "nuclear_patch",
            "provider": "custom" if use_custom_provider else "animekai"
        }
    except Exception as e:
        logger.error(f"Encoder test failed: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/search/{query}", tags=["Search"])
def search_anime(query: str):
    try:
        if not provider:
            return {"error": "Provider not initialized"}
        
        results = provider.get_search(query)
        
        if use_custom_provider:
            return [
                {
                    "title": r.name,
                    "id": r.identifier,
                    "languages": [lang.name for lang in r.languages],
                }
                for r in results
            ]
        else:
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
        if not provider:
            return {"error": "Provider not initialized"}
        
        if use_custom_provider:
            # Use the custom provider
            try:
                # Search for the anime to get its details
                results = provider.get_search(anime_id)
                target_result = next((r for r in results if r.identifier == anime_id), None)
                if not target_result:
                    return {"error": "Anime not found with this ID."}
                
                # Create the anime object
                anime = CustomAnime.from_search_result(provider, target_result)
                
                # Get episodes
                episodes = anime.get_episodes(lang=LanguageTypeEnum.SUB)
                
                return {"anime_id": anime_id, "episodes": episodes}
            except Exception as e:
                logger.error(f"Error using custom provider: {e}")
                return {"error": f"Failed to get episodes with custom provider: {str(e)}"}
        else:
            # Use the built-in provider
            try:
                # Create anime object with detailed logging
                logger.info(f"Creating Anime object for ID: {anime_id}")
                
                # Create the anime object
                anime = Anime(provider, "", anime_id, [LanguageTypeEnum.SUB])
                
                # Add strict_encode to the anime object
                anime.strict_encode = strict_encode
                
                logger.info("Successfully created Anime object")
                
                # Get episodes with detailed logging
                logger.info("Retrieving episodes...")
                
                # Get episodes
                episodes = anime.get_episodes(lang=LanguageTypeEnum.SUB)
                logger.info(f"Successfully retrieved {len(episodes)} episodes")
                
                return {"anime_id": anime_id, "episodes": episodes}
            except Exception as e:
                logger.error(f"Error using built-in provider: {e}")
                
                # Check if it's a function not defined error
                if "Function 'strict_encode' not defined" in str(e):
                    logger.error("This is a function not defined error")
                    
                    # Switch to the custom provider
                    global use_custom_provider
                    use_custom_provider = True
                    logger.info("Switched to custom provider")
                    
                    # Try again with the custom provider
                    try:
                        # Search for the anime to get its details
                        results = provider.get_search(anime_id)
                        target_result = next((r for r in results if r.identifier == anime_id), None)
                        if not target_result:
                            return {"error": "Anime not found with this ID."}
                        
                        # Create the anime object
                        anime = CustomAnime.from_search_result(provider, target_result)
                        
                        # Get episodes
                        episodes = anime.get_episodes(lang=LanguageTypeEnum.SUB)
                        
                        return {"anime_id": anime_id, "episodes": episodes}
                    except Exception as retry_e:
                        logger.error(f"Error using custom provider: {retry_e}")
                        return {"error": f"Failed to get episodes with custom provider: {str(retry_e)}"}
                
                return {"error": f"Failed to get episodes: {str(e)}"}
    except Exception as e:
        logger.error(f"Episode error: {e}")
        logger.error(traceback.format_exc())
        return {"error": str(e)}

@app.get("/stream/{anime_id}/{episode}", tags=["Streaming"])
def get_streams(
    anime_id: str,
    episode: Union[int, float],
    language: LanguageTypeEnum = Query(default=LanguageTypeEnum.SUB)
):
    try:
        if not provider:
            return {"error": "Provider not initialized"}
        
        if use_custom_provider:
            # Use the custom provider
            try:
                # Search for the anime to get its details
                results = provider.get_search(anime_id)
                target_result = next((r for r in results if r.identifier == anime_id), None)
                if not target_result:
                    return {"error": "Anime not found with this ID."}
                
                # Create the anime object
                anime_obj = CustomAnime.from_search_result(provider, target_result)
                
                # Get episodes
                episodes = anime_obj.get_episodes(lang=language)
                
                if episode not in episodes:
                    return {"error": f"Episode {episode} is not available in {language.name}."}
                
                # Get videos
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
                logger.error(f"Error using custom provider: {e}")
                return {"error": f"Failed to get streams with custom provider: {str(e)}"}
        else:
            # Use the built-in provider
            try:
                logger.info(f"🔍 Searching for anime: {anime_id}")
                results = provider.get_search(anime_id)
                
                # Match exactly by identifier
                target_result = next((r for r in results if r.identifier == anime_id), None)
                if not target_result:
                    return {"error": "Exact anime match not found for this ID."}
                
                logger.info(f"Found anime: {target_result.name}")
                
                # Create the anime object with explicit strict_encode
                # First, ensure strict_encode is in the module's globals
                import anipy_api.anime
                anipy_api.anime.strict_encode = strict_encode
                
                # Create the anime object
                anime_obj = Anime.from_search_result(provider, target_result)
                
                # Add strict_encode to the anime object
                anime_obj.strict_encode = strict_encode
                
                logger.info(f"Created anime object for: {anime_obj.name}")
                
                # Get episodes
                episodes = anime_obj.get_episodes(lang=language)
                logger.info(f"Got {len(episodes)} episodes")
                
                if episode not in episodes:
                    return {"error": f"Episode {episode} is not available in {language.name}."}
                
                # Get videos
                logger.info(f"Getting videos for episode {episode}")
                
                # Add strict_encode to the anime object again just to be sure
                anime_obj.strict_encode = strict_encode
                
                # Get videos
                streams = anime_obj.get_videos(episode, language)
                logger.info(f"Got {len(streams) if streams else 0} streams")
                
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
                logger.error(f"Error using built-in provider: {e}")
                
                # Check if it's a function not defined error
                if "Function 'strict_encode' not defined" in str(e):
                    logger.error("This is a function not defined error")
                    
                    # Switch to the custom provider
                    global use_custom_provider
                    use_custom_provider = True
                    logger.info("Switched to custom provider")
                    
                    # Try again with the custom provider
                    try:
                        # Search for the anime to get its details
                        results = provider.get_search(anime_id)
                        target_result = next((r for r in results if r.identifier == anime_id), None)
                        if not target_result:
                            return {"error": "Anime not found with this ID."}
                        
                        # Create the anime object
                        anime_obj = CustomAnime.from_search_result(provider, target_result)
                        
                        # Get episodes
                        episodes = anime_obj.get_episodes(lang=language)
                        
                        if episode not in episodes:
                            return {"error": f"Episode {episode} is not available in {language.name}."}
                        
                        # Get videos
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
                    except Exception as retry_e:
                        logger.error(f"Error using custom provider: {retry_e}")
                        return {"error": f"Failed to get streams with custom provider: {str(retry_e)}"}
                
                return {"error": f"Failed to get streams: {str(e)}"}
    except Exception as e:
        logger.error(f"Stream error: {e}")
        logger.error(traceback.format_exc())
        return {"error": str(e)}

@app.get("/anime-info/{anime_id}", tags=["Info"])
def get_anime_info(anime_id: str):
    try:
        if not provider:
            return {"error": "Provider not initialized"}
        
        if use_custom_provider:
            # Use the custom provider
            try:
                # Search for the anime to get its details
                results = provider.get_search(anime_id)
                target_result = next((r for r in results if r.identifier == anime_id), None)
                if not target_result:
                    return {"error": "Anime not found with this ID."}
                
                # Create the anime object
                anime = CustomAnime.from_search_result(provider, target_result)
                
                # Get info
                info = anime.get_info()
                
                return {"info": info}
            except Exception as e:
                logger.error(f"Error using custom provider: {e}")
                return {"error": f"Failed to get anime info with custom provider: {str(e)}"}
        else:
            # Use the built-in provider
            try:
                results = provider.get_search(anime_id)
                target_result = next((r for r in results if r.identifier == anime_id), None)
                if not target_result:
                    return {"error": "Anime not found with this ID."}
                
                # Create the anime object
                anime = Anime.from_search_result(provider, target_result)
                
                # Add strict_encode to the anime object
                anime.strict_encode = strict_encode
                
                info = anime.get_info()
                return {"info": info}
            except Exception as e:
                logger.error(f"Error using built-in provider: {e}")
                
                # Check if it's a function not defined error
                if "Function 'strict_encode' not defined" in str(e):
                    logger.error("This is a function not defined error")
                    
                    # Switch to the custom provider
                    global use_custom_provider
                    use_custom_provider = True
                    logger.info("Switched to custom provider")
                    
                    # Try again with the custom provider
                    try:
                        # Search for the anime to get its details
                        results = provider.get_search(anime_id)
                        target_result = next((r for r in results if r.identifier == anime_id), None)
                        if not target_result:
                            return {"error": "Anime not found with this ID."}
                        
                        # Create the anime object
                        anime = CustomAnime.from_search_result(provider, target_result)
                        
                        # Get info
                        info = anime.get_info()
                        
                        return {"info": info}
                    except Exception as retry_e:
                        logger.error(f"Error using custom provider: {retry_e}")
                        return {"error": f"Failed to get anime info with custom provider: {str(retry_e)}"}
                
                return {"error": f"Failed to get anime info: {str(e)}"}
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
