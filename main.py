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

# Apply the stream fix before importing any anipy_api modules
try:
    from stream_fix import apply_stream_fix, strict_encode
    fix_success = apply_stream_fix()
    logger.info(f"Stream fix application: {'Success' if fix_success else 'Failed'}")
    
    # Make strict_encode available globally
    builtins.strict_encode = strict_encode
    logger.info("Added strict_encode to builtins")
except Exception as e:
    logger.error(f"Error applying stream fix: {e}")
    logger.error(traceback.format_exc())

# Now import anipy_api modules
from anipy_api.provider import get_provider, LanguageTypeEnum
from anipy_api.anime import Anime

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
        
        # Check if it's a local variable error
        if "local variable 'strict_encode' referenced before assignment" in error_msg:
            logger.error("This is a local variable reference error")
            
            # Try to fix the issue on the fly
            try:
                from stream_fix import apply_stream_fix
                apply_stream_fix()
                logger.info("Re-applied stream fix during error handling")
                
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "Local variable 'strict_encode' referenced before assignment",
                        "details": error_msg,
                        "fix_attempted": True,
                        "message": "Please try your request again"
                    }
                )
            except Exception as e:
                logger.error(f"Error re-applying stream fix: {e}")
        
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
                
                # Check if it's in builtins
                has_builtin = hasattr(builtins, 'strict_encode')
                logger.info(f"strict_encode in builtins: {has_builtin}")
                
                # Try to determine where it's being called from
                tb = traceback.extract_tb(sys.exc_info()[2])
                calling_file = tb[-1].filename if tb else "unknown"
                calling_line = tb[-1].lineno if tb else "unknown"
                logger.info(f"Error occurred in file: {calling_file}, line: {calling_line}")
                
                # Try to fix the issue on the fly
                if not has_builtin:
                    builtins.strict_encode = strict_encode
                    logger.info("Re-added strict_encode to builtins")
                
                # Try to add it to the module where the error occurred
                if calling_file != "unknown":
                    module_name = None
                    for name, module in sys.modules.items():
                        try:
                            if hasattr(module, "__file__") and module.__file__ == calling_file:
                                module_name = name
                                if not hasattr(module, "strict_encode"):
                                    setattr(module, "strict_encode", strict_encode)
                                    logger.info(f"Added strict_encode to module: {name}")
                        except Exception:
                            pass
                
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "Encoder function not found in the right scope",
                        "details": error_msg,
                        "calling_file": calling_file,
                        "calling_line": calling_line,
                        "has_builtin": has_builtin,
                        "fix_attempted": True
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
    provider = get_provider("animekai")
    
    # Add strict_encode to the provider
    provider.strict_encode = strict_encode
    
    logger.info("Successfully initialized animekai provider")
except Exception as e:
    logger.error(f"Failed to initialize provider: {e}")
    provider = None

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
            "encoder_version": "stream_fix"
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
        
        # Verify strict_encode is available before proceeding
        if not hasattr(builtins, 'strict_encode'):
            logger.error("strict_encode not found in builtins before episode retrieval")
            # Add it again just to be sure
            from stream_fix import strict_encode
            builtins.strict_encode = strict_encode
            logger.info("Re-added strict_encode to builtins")
        
        # Create anime object with detailed logging
        logger.info(f"Creating Anime object for ID: {anime_id}")
        try:
            # Create the anime object
            anime = Anime(provider, "", anime_id, [LanguageTypeEnum.SUB])
            logger.info("Successfully created Anime object")
        except Exception as e:
            logger.error(f"Error creating Anime object: {e}")
            
            # Check if it's a local variable error
            if "local variable 'strict_encode' referenced before assignment" in str(e):
                logger.error("This is a local variable reference error")
                
                # Try to fix the issue on the fly
                try:
                    from stream_fix import apply_stream_fix
                    apply_stream_fix()
                    logger.info("Re-applied stream fix")
                    
                    # Try again with the fixed function
                    try:
                        # Create the anime object
                        anime = Anime(provider, "", anime_id, [LanguageTypeEnum.SUB])
                        logger.info("Successfully created Anime object after fix")
                    except Exception as retry_e:
                        logger.error(f"Error creating Anime object after fix: {retry_e}")
                        return {"error": f"Failed to create anime object after fix: {str(retry_e)}"}
                except Exception as fix_e:
                    logger.error(f"Error re-applying stream fix: {fix_e}")
                    return {"error": f"Failed to fix local variable issue: {str(fix_e)}"}
            else:
                return {"error": f"Failed to create anime object: {str(e)}"}
        
        # Get episodes with detailed logging
        logger.info("Retrieving episodes...")
        try:
            # Get episodes
            episodes = anime.get_episodes(lang=LanguageTypeEnum.SUB)
            logger.info(f"Successfully retrieved {len(episodes)} episodes")
        except Exception as e:
            logger.error(f"Error retrieving episodes: {e}")
            
            # Check if it's a local variable error
            if "local variable 'strict_encode' referenced before assignment" in str(e):
                logger.error("This is a local variable reference error during episode retrieval")
                
                # Try to fix the issue on the fly
                try:
                    from stream_fix import apply_stream_fix
                    apply_stream_fix()
                    logger.info("Re-applied stream fix")
                    
                    # Try again with the fixed function
                    try:
                        # Get episodes
                        episodes = anime.get_episodes(lang=LanguageTypeEnum.SUB)
                        logger.info(f"Successfully retrieved {len(episodes)} episodes after fix")
                        return {"anime_id": anime_id, "episodes": episodes}
                    except Exception as retry_e:
                        logger.error(f"Error retrieving episodes after fix: {retry_e}")
                        return {"error": f"Failed to retrieve episodes after fix: {str(retry_e)}"}
                except Exception as fix_e:
                    logger.error(f"Error re-applying stream fix: {fix_e}")
                    return {"error": f"Failed to fix local variable issue: {str(fix_e)}"}
            
            return {"error": f"Failed to retrieve episodes: {str(e)}"}
        
        return {"anime_id": anime_id, "episodes": episodes}
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
        
        # Verify strict_encode is available before proceeding
        if not hasattr(builtins, 'strict_encode'):
            logger.error("strict_encode not found in builtins before stream retrieval")
            # Add it again just to be sure
            from stream_fix import strict_encode
            builtins.strict_encode = strict_encode
            logger.info("Re-added strict_encode to builtins")
        
        # Apply the stream fix again just to be sure
        try:
            from stream_fix import apply_stream_fix
            apply_stream_fix()
            logger.info("Re-applied stream fix before stream retrieval")
        except Exception as e:
            logger.error(f"Error re-applying stream fix: {e}")
        
        logger.info(f"🔍 Searching for anime: {anime_id}")
        results = provider.get_search(anime_id)

        # Match exactly by identifier
        target_result = next((r for r in results if r.identifier == anime_id), None)
        if not target_result:
            return {"error": "Exact anime match not found for this ID."}

        logger.info(f"Found anime: {target_result.name}")
        
        # Create anime object
        try:
            # Create the anime object
            anime_obj = Anime.from_search_result(provider, target_result)
            
            # Add strict_encode to the anime object
            anime_obj.strict_encode = strict_encode
            
            logger.info(f"Created anime object for: {anime_obj.name}")
        except Exception as e:
            logger.error(f"Error creating anime object: {e}")
            
            # Check if it's a local variable error
            if "local variable 'strict_encode' referenced before assignment" in str(e):
                logger.error("This is a local variable reference error")
                
                # Try to fix the issue on the fly
                try:
                    from stream_fix import apply_stream_fix
                    apply_stream_fix()
                    logger.info("Re-applied stream fix")
                    
                    # Try again with the fixed function
                    try:
                        # Create the anime object with explicit strict_encode
                        anime_obj = Anime.from_search_result(provider, target_result)
                        anime_obj.strict_encode = strict_encode
                        logger.info(f"Created anime object for: {anime_obj.name} after fix")
                    except Exception as retry_e:
                        logger.error(f"Error creating anime object after fix: {retry_e}")
                        return {"error": f"Failed to create anime object after fix: {str(retry_e)}"}
                except Exception as fix_e:
                    logger.error(f"Error re-applying stream fix: {fix_e}")
                    return {"error": f"Failed to fix local variable issue: {str(fix_e)}"}
            else:
                return {"error": f"Failed to create anime object: {str(e)}"}
        
        # Get episodes
        try:
            # Get episodes
            episodes = anime_obj.get_episodes(lang=language)
            logger.info(f"Got {len(episodes)} episodes")
        except Exception as e:
            logger.error(f"Error getting episodes: {e}")
            return {"error": f"Failed to get episodes: {str(e)}"}

        if episode not in episodes:
            return {"error": f"Episode {episode} is not available in {language.name}."}

        # Get videos
        try:
            logger.info(f"Getting videos for episode {episode}")
            
            # Add strict_encode to the anime object again just to be sure
            anime_obj.strict_encode = strict_encode
            
            # Get videos
            streams = anime_obj.get_videos(episode, language)
            logger.info(f"Got {len(streams) if streams else 0} streams")
        except Exception as e:
            logger.error(f"Error getting videos: {e}")
            
            # Check if it's a local variable error
            if "local variable 'strict_encode' referenced before assignment" in str(e):
                logger.error("This is a local variable reference error during video retrieval")
                
                # Try to fix the issue on the fly
                try:
                    from stream_fix import apply_stream_fix
                    apply_stream_fix()
                    logger.info("Re-applied stream fix")
                    
                    # Try again with the fixed function
                    try:
                        # Add strict_encode to the anime object
                        anime_obj.strict_encode = strict_encode
                        
                        # Get videos
                        streams = anime_obj.get_videos(episode, language)
                        logger.info(f"Got {len(streams) if streams else 0} streams after fix")
                    except Exception as retry_e:
                        logger.error(f"Error getting videos after fix: {retry_e}")
                        return {"error": f"Failed to get videos after fix: {str(retry_e)}"}
                except Exception as fix_e:
                    logger.error(f"Error re-applying stream fix: {fix_e}")
                    return {"error": f"Failed to fix local variable issue: {str(fix_e)}"}
            
            return {"error": f"Failed to get videos: {str(e)}"}

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
        logger.error(traceback.format_exc())
        return {"error": str(e)}

@app.get("/anime-info/{anime_id}", tags=["Info"])
def get_anime_info(anime_id: str):
    try:
        if not provider:
            return {"error": "Provider not initialized"}
        
        results = provider.get_search(anime_id)
        target_result = next((r for r in results if r.identifier == anime_id), None)
        if not target_result:
            return {"error": "Anime not found with this ID."}

        try:
            # Create the anime object
            anime = Anime.from_search_result(provider, target_result)
            
            # Add strict_encode to the anime object
            anime.strict_encode = strict_encode
            
            info = anime.get_info()
            return {"info": info}
        except Exception as e:
            logger.error(f"Error getting anime info: {e}")
            
            # Check if it's a local variable error
            if "local variable 'strict_encode' referenced before assignment" in str(e):
                logger.error("This is a local variable reference error")
                
                # Try to fix the issue on the fly
                try:
                    from stream_fix import apply_stream_fix
                    apply_stream_fix()
                    logger.info("Re-applied stream fix")
                    
                    # Try again with the fixed function
                    try:
                        # Create the anime object
                        anime = Anime.from_search_result(provider, target_result)
                        
                        # Add strict_encode to the anime object
                        anime.strict_encode = strict_encode
                        
                        info = anime.get_info()
                        return {"info": info}
                    except Exception as retry_e:
                        logger.error(f"Error getting anime info after fix: {retry_e}")
                        return {"error": f"Failed to get anime info after fix: {str(retry_e)}"}
                except Exception as fix_e:
                    logger.error(f"Error re-applying stream fix: {fix_e}")
                    return {"error": f"Failed to fix local variable issue: {str(fix_e)}"}
            
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
