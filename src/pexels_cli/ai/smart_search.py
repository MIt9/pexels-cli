"""Smart Search AI module - separate natural language processors for photos and videos."""

from typing import Optional
from pydantic import BaseModel, Field
from pexels_cli.ai.provider import BaseAIProvider


class SmartPhotoSearchParams(BaseModel):
    """Pexels photo search parameters generated from natural language."""
    search_query: str = Field(
        description="Optimized concise English search query terms for stock photos"
    )
    orientation: Optional[str] = Field(
        default=None,
        description="Orientation: 'landscape', 'portrait', or 'square' if inferred, else null"
    )
    color: Optional[str] = Field(
        default=None,
        description="Hex color code (e.g. '#FF0000') or color name ('red', 'blue', etc.) if inferred, else null"
    )
    size: Optional[str] = Field(
        default=None,
        description="Size: 'large', 'medium', or 'small' if specified, else null"
    )
    explanation: str = Field(
        description="Short reasoning of how natural language was translated into photo search parameters"
    )


class SmartVideoSearchParams(BaseModel):
    """Pexels video search parameters generated from natural language."""
    search_query: str = Field(
        description="Optimized concise English search query terms for stock footage/videos"
    )
    orientation: Optional[str] = Field(
        default=None,
        description="Orientation: 'landscape', 'portrait', or 'square' if inferred, else null"
    )
    size: Optional[str] = Field(
        default=None,
        description="Size: 'large', 'medium', or 'small' if specified, else null"
    )
    explanation: str = Field(
        description="Short reasoning of how natural language was translated into video search parameters"
    )


async def build_smart_photo_params(
    ai_provider: BaseAIProvider, natural_prompt: str
) -> SmartPhotoSearchParams:
    """Use AI to analyze natural language prompt for PHOTO search."""
    system_prompt = (
        "You are an expert stock photography researcher for Pexels. "
        "Translate the user request into search parameters specifically for stock photos.\n"
        "Supported orientation values: 'landscape', 'portrait', 'square'.\n"
        "Supported color values: 'red', 'orange', 'yellow', 'green', 'turquoise', 'blue', 'violet', "
        "'pink', 'brown', 'black', 'gray', 'white' or hex codes like '#000000'.\n"
        "Supported size values: 'large', 'medium', 'small'.\n"
        "Keep search_query in simple, effective English search terms."
    )
    return await ai_provider.generate_structured(
        prompt=f"Photo request: '{natural_prompt}'",
        schema=SmartPhotoSearchParams,
        system_instruction=system_prompt,
    )


async def build_smart_video_params(
    ai_provider: BaseAIProvider, natural_prompt: str
) -> SmartVideoSearchParams:
    """Use AI to analyze natural language prompt for VIDEO search."""
    system_prompt = (
        "You are an expert stock videography researcher for Pexels. "
        "Translate the user request into search parameters specifically for HD/4K stock video footage.\n"
        "Supported orientation values: 'landscape', 'portrait', 'square'.\n"
        "Supported size values: 'large', 'medium', 'small'.\n"
        "Keep search_query in simple, effective English search terms."
    )
    return await ai_provider.generate_structured(
        prompt=f"Video request: '{natural_prompt}'",
        schema=SmartVideoSearchParams,
        system_instruction=system_prompt,
    )
