"""AI Prompt Enhancer and Curator modules for Pexels CLI."""

from typing import List, Optional
from pydantic import BaseModel, Field
from pexels_cli.ai.provider import BaseAIProvider


class EnhancedPrompt(BaseModel):
    """Enhanced search keywords and style suggestions."""
    original_prompt: str
    primary_query: str = Field(description="Primary concise English query for Pexels")
    alternative_queries: List[str] = Field(description="List of alternative stock media search queries")
    style_keywords: List[str] = Field(description="Aesthetic and mood keywords (e.g. 'cinematic', 'minimalist')")
    recommended_color_palette: Optional[str] = Field(description="Suggested color filter if relevant")


async def enhance_prompt(ai_provider: BaseAIProvider, user_prompt: str) -> EnhancedPrompt:
    """Enhance a user prompt into optimized stock media search strategies."""
    system_prompt = (
        "You are an AI photo/video art director. Expand and refine the user's search prompt "
        "into effective search strategies for Pexels stock photos and videos."
    )
    return await ai_provider.generate_structured(
        prompt=f"User search prompt: '{user_prompt}'",
        schema=EnhancedPrompt,
        system_instruction=system_prompt,
    )


class CurationItem(BaseModel):
    """Single item in a project media curation plan."""
    role: str = Field(description="Role of media in project (e.g. 'Hero Banner', 'Background', 'Feature Icon')")
    search_query: str = Field(description="Specific Pexels search query for this role")
    orientation: Optional[str] = Field(description="Recommended orientation: landscape, portrait, square")
    description: str = Field(description="Why this shot fits the project brief")


class ProjectCurationPlan(BaseModel):
    """Curated list of media assets for a given project brief."""
    project_title: str = Field(description="Title of project brief")
    concept_summary: str = Field(description="Summary of visual creative direction")
    items: List[CurationItem] = Field(description="Required media assets for the project")


async def curate_project(ai_provider: BaseAIProvider, project_brief: str) -> ProjectCurationPlan:
    """Generate a structured stock media curation plan based on a project brief."""
    system_prompt = (
        "You are a creative director building a stock photography shot list for a client project brief. "
        "Break down the brief into specific media slots (e.g. hero image, team section, feature cards) "
        "and supply Pexels search queries for each."
    )
    return await ai_provider.generate_structured(
        prompt=f"Project brief: '{project_brief}'",
        schema=ProjectCurationPlan,
        system_instruction=system_prompt,
    )
