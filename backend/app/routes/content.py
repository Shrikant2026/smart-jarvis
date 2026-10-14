
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.ollama import generate_response

router = APIRouter(prefix="/content", tags=["Content Factory"])


class StoryRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=500)
    duration_seconds: int = Field(default=30, ge=15, le=90)
    scene_count: int = Field(default=3, ge=2, le=8)


@router.post("/story")
def generate_story(request: StoryRequest):
    prompt = f"""
You are the story-writing engine of a local AI Content Factory.

Create an original short-video story using these settings:
Topic: {request.topic}
Target duration: {request.duration_seconds} seconds
Number of scenes: {request.scene_count}

Return ONLY valid JSON with this exact structure:
{{
  "title": "Short catchy title",
  "hook": "Opening hook",
  "narration": "Complete narration for the target duration",
  "scenes": [
    {{
      "scene_number": 1,
      "duration_seconds": 10,
      "visual_prompt": "Detailed visual prompt for AI video generation",
      "narration": "Narration for this scene"
    }}
  ]
}}

Requirements:
- Include exactly {request.scene_count} scenes.
- Make scene durations add up to {request.duration_seconds} seconds.
- Keep the main character's appearance consistent across scenes.
- Write visual prompts suitable for a cinematic AI video generator.
- Do not include Markdown fences or text outside the JSON.
"""

    try:
        output = generate_response(prompt)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # Handle models that wrap JSON in Markdown fences.
    cleaned = output.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    try:
        story = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail="The local model returned invalid JSON. Retry the request.",
        ) from exc

    if not isinstance(story, dict) or not isinstance(story.get("scenes"), list):
        raise HTTPException(
            status_code=502,
            detail="The model returned an unexpected story structure.",
        )

    if len(story["scenes"]) != request.scene_count:
        raise HTTPException(
            status_code=502,
            detail="The model returned the wrong number of scenes. Retry the request.",
        )

    return story
