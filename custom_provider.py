"""
Custom Provider - A provider that doesn't rely on the problematic strict_encode function.
"""
import logging
import requests
import json
import re
from enum import Enum
from typing import List, Dict, Any, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define the LanguageTypeEnum
class LanguageTypeEnum(Enum):
    SUB = "sub"
    DUB = "dub"
    RAW = "raw"

# Define the SearchResult class
class SearchResult:
    def __init__(self, name: str, identifier: str, languages: List[LanguageTypeEnum]):
        self.name = name
        self.identifier = identifier
        self.languages = languages

# Define the Stream class
class Stream:
    def __init__(self, url: str, resolution: str, language: LanguageTypeEnum, referrer: str = None):
        self.url = url
        self.resolution = resolution
        self.language = language
        self.referrer = referrer

# Define the CustomProvider class
class CustomProvider:
    def __init__(self, base_url: str = "https://api.animekai.info"):
        self.base_url = base_url
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        self.session.headers.update(self.headers)
    
    def get_search(self, query: str) -> List[SearchResult]:
        """
        Search for anime by name.
        """
        try:
            url = f"{self.base_url}/api/anime/search"
            params = {"q": query}
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for item in data.get("results", []):
                name = item.get("title", "")
                identifier = item.get("id", "")
                
                # Determine available languages
                languages = []
                if item.get("hasSub", False):
                    languages.append(LanguageTypeEnum.SUB)
                if item.get("hasDub", False):
                    languages.append(LanguageTypeEnum.DUB)
                
                results.append(SearchResult(name, identifier, languages))
            
            return results
        except Exception as e:
            logger.error(f"Error searching for anime: {e}")
            return []
    
    def get_episodes(self, anime_id: str, language: LanguageTypeEnum = LanguageTypeEnum.SUB) -> List[Union[int, float]]:
        """
        Get episodes for an anime.
        """
        try:
            url = f"{self.base_url}/api/anime/{anime_id}/episodes"
            params = {"language": language.value}
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            episodes = []
            
            for episode in data.get("episodes", []):
                episode_number = episode.get("number")
                if episode_number is not None:
                    try:
                        # Try to convert to float first, then to int if possible
                        episode_number = float(episode_number)
                        if episode_number.is_integer():
                            episode_number = int(episode_number)
                        episodes.append(episode_number)
                    except (ValueError, TypeError):
                        pass
            
            return sorted(episodes)
        except Exception as e:
            logger.error(f"Error getting episodes: {e}")
            return []
    
    def get_streams(self, anime_id: str, episode: Union[int, float], language: LanguageTypeEnum = LanguageTypeEnum.SUB) -> List[Stream]:
        """
        Get streams for an episode.
        """
        try:
            url = f"{self.base_url}/api/anime/{anime_id}/episode/{episode}/streams"
            params = {"language": language.value}
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            streams = []
            
            for stream in data.get("streams", []):
                stream_url = stream.get("url", "")
                resolution = stream.get("quality", "unknown")
                referrer = stream.get("referrer", None)
                
                if stream_url:
                    streams.append(Stream(stream_url, resolution, language, referrer))
            
            return streams
        except Exception as e:
            logger.error(f"Error getting streams: {e}")
            return []
    
    def get_info(self, anime_id: str) -> Dict[str, Any]:
        """
        Get information about an anime.
        """
        try:
            url = f"{self.base_url}/api/anime/{anime_id}"
            response = self.session.get(url)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            logger.error(f"Error getting anime info: {e}")
            return {}

# Create a function to get the custom provider
def get_custom_provider() -> CustomProvider:
    """
    Get the custom provider.
    """
    return CustomProvider()

# Create a custom Anime class that uses the custom provider
class CustomAnime:
    def __init__(self, provider: CustomProvider, name: str, identifier: str, languages: List[LanguageTypeEnum]):
        self.provider = provider
        self.name = name
        self.identifier = identifier
        self.languages = languages
    
    @classmethod
    def from_search_result(cls, provider: CustomProvider, search_result: SearchResult):
        """
        Create an Anime object from a search result.
        """
        return cls(provider, search_result.name, search_result.identifier, search_result.languages)
    
    def get_episodes(self, lang: LanguageTypeEnum = LanguageTypeEnum.SUB) -> List[Union[int, float]]:
        """
        Get episodes for this anime.
        """
        return self.provider.get_episodes(self.identifier, lang)
    
    def get_videos(self, episode: Union[int, float], language: LanguageTypeEnum = LanguageTypeEnum.SUB) -> List[Stream]:
        """
        Get videos for an episode.
        """
        return self.provider.get_streams(self.identifier, episode, language)
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about this anime.
        """
        return self.provider.get_info(self.identifier)
