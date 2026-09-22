"""Pexels API HTTP Client implementation."""

import asyncio
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import httpx
from pydantic import BaseModel


BASE_URL_V1 = "https://api.pexels.com/v1"
BASE_URL_VIDEOS = "https://api.pexels.com/videos"


class PexelsClientError(Exception):
    """Custom exception for Pexels API errors."""
    pass


class PexelsClient:
    """Async & Sync Pexels API Client."""

    def __init__(self, api_key: str, timeout: float = 30.0):
        if not api_key:
            raise PexelsClientError(
                "Pexels API Key is missing. Set it via `pexels-cli config set-pexels-key <KEY>` "
                "or set the PEXELS_API_KEY environment variable."
            )
        self.api_key = api_key
        self.headers = {"Authorization": api_key}
        self.timeout = timeout

    async def _request(self, method: str, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send HTTP request to Pexels API."""
        # Clean params (remove None values)
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            try:
                response = await client.request(method, url, params=clean_params)
                if response.status_code == 401:
                    raise PexelsClientError("Unauthorized: Invalid Pexels API Key.")
                elif response.status_code == 429:
                    raise PexelsClientError("Rate limit exceeded. Please try again later.")
                elif response.status_code >= 400:
                    raise PexelsClientError(f"Pexels API error HTTP {response.status_code}: {response.text}")
                return response.json()
            except httpx.RequestError as e:
                raise PexelsClientError(f"HTTP connection failed: {e}")

    # --- Photos ---

    async def search_photos(
        self,
        query: str,
        orientation: Optional[str] = None,
        size: Optional[str] = None,
        color: Optional[str] = None,
        locale: Optional[str] = None,
        page: int = 1,
        per_page: int = 15,
    ) -> Dict[str, Any]:
        """Search photos on Pexels."""
        url = f"{BASE_URL_V1}/search"
        params = {
            "query": query,
            "orientation": orientation,
            "size": size,
            "color": color,
            "locale": locale,
            "page": page,
            "per_page": per_page,
        }
        return await self._request("GET", url, params)

    async def curated_photos(self, page: int = 1, per_page: int = 15) -> Dict[str, Any]:
        """Get curated photos from Pexels."""
        url = f"{BASE_URL_V1}/curated"
        params = {"page": page, "per_page": per_page}
        return await self._request("GET", url, params)

    async def get_photo(self, photo_id: int) -> Dict[str, Any]:
        """Get single photo details by ID."""
        url = f"{BASE_URL_V1}/photos/{photo_id}"
        return await self._request("GET", url)

    # --- Videos ---

    async def search_videos(
        self,
        query: str,
        orientation: Optional[str] = None,
        size: Optional[str] = None,
        locale: Optional[str] = None,
        page: int = 1,
        per_page: int = 15,
    ) -> Dict[str, Any]:
        """Search videos on Pexels."""
        url = f"{BASE_URL_VIDEOS}/search"
        params = {
            "query": query,
            "orientation": orientation,
            "size": size,
            "locale": locale,
            "page": page,
            "per_page": per_page,
        }
        return await self._request("GET", url, params)

    async def popular_videos(
        self,
        min_width: Optional[int] = None,
        min_height: Optional[int] = None,
        min_duration: Optional[int] = None,
        max_duration: Optional[int] = None,
        page: int = 1,
        per_page: int = 15,
    ) -> Dict[str, Any]:
        """Get popular videos from Pexels."""
        url = f"{BASE_URL_VIDEOS}/popular"
        params = {
            "min_width": min_width,
            "min_height": min_height,
            "min_duration": min_duration,
            "max_duration": max_duration,
            "page": page,
            "per_page": per_page,
        }
        return await self._request("GET", url, params)

    async def get_video(self, video_id: int) -> Dict[str, Any]:
        """Get single video details by ID."""
        url = f"{BASE_URL_VIDEOS}/videos/{video_id}"
        return await self._request("GET", url)

    # --- Collections ---

    async def featured_collections(self, page: int = 1, per_page: int = 15) -> Dict[str, Any]:
        """Get featured collections."""
        url = f"{BASE_URL_V1}/collections/featured"
        params = {"page": page, "per_page": per_page}
        return await self._request("GET", url, params)

    async def get_collection_media(
        self,
        collection_id: str,
        media_type: Optional[str] = None,
        sort: Optional[str] = None,
        page: int = 1,
        per_page: int = 15,
    ) -> Dict[str, Any]:
        """Get media from a specific collection."""
        url = f"{BASE_URL_V1}/collections/{collection_id}"
        params = {"type": media_type, "sort": sort, "page": page, "per_page": per_page}
        return await self._request("GET", url, params)

    # --- Downloader ---

    async def download_file(
        self,
        url: str,
        output_path: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Path:
        """Stream download a file with progress reporting."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("GET", url, follow_redirects=True) as response:
                response.raise_for_status()
                total_bytes = int(response.headers.get("content-length", 0))
                downloaded = 0
                with open(output_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total_bytes)
        return output_path
