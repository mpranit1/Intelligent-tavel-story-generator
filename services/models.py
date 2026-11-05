from pydantic import BaseModel, Field
from typing import List, Optional


class TravelStoryRequest(BaseModel):
    description: str = Field(..., description="User's raw travel description, notes, or memories")
    tone: Optional[str] = Field("evocative", description="Tone of the story: evocative, adventurous, romantic, luxury, playful")
    duration: Optional[str] = Field("auto", description="Trip duration preference: auto, weekend, short, extended")
    voice: Optional[str] = Field("en-US-JennyNeural", description="Neural voice for audio narration")
    gemini_api_key: Optional[str] = Field(None, description="Optional Gemini API key for cloud LLM inference")


class VisualScene(BaseModel):
    scene_id: int
    title: str
    narrative_text: str
    visual_prompt: str
    image_url: str
    caption: str
    hashtags: List[str] = Field(default_factory=list)
    audio_url: Optional[str] = None
    audio_duration: Optional[float] = None


class ItineraryItem(BaseModel):
    time_of_day: str
    location: str
    activity: str
    highlights: str
    local_food_tip: Optional[str] = None
    travel_tip: Optional[str] = None


class ItineraryDay(BaseModel):
    day_number: int
    title: str
    theme: str
    items: List[ItineraryItem] = Field(default_factory=list)


class TravelStoryResponse(BaseModel):
    id: str
    title: str
    subtitle: str
    destination: str
    duration_label: str
    summary: str
    vibe_tags: List[str] = Field(default_factory=list)
    scenes: List[VisualScene] = Field(default_factory=list)
    itinerary: List[ItineraryDay] = Field(default_factory=list)
    full_audio_url: Optional[str] = None
    audio_voice: str
    generated_at: str
