import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from services.models import TravelStoryRequest, TravelStoryResponse
from services.story_engine import generate_complete_travel_story, PRESETS
from services.tts_service import VOICE_OPTIONS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
AUDIO_DIR = os.path.join(STATIC_DIR, "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

app = FastAPI(
    title="Intelligent Travel Story Generator",
    description="Multimodal AI application converting travel memories into narrative, itinerary, visual scenes, captions, and audio narration.",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def root():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Intelligent Travel Story Generator API is running. static/index.html not found."}

@app.get("/api/presets")
async def get_presets():
    """Returns curated preset trips for instant 1-click loading."""
    return {"presets": PRESETS}

@app.get("/api/voices")
async def get_voices():
    """Returns available Edge TTS neural voice options."""
    return {"voices": VOICE_OPTIONS}

@app.post("/api/generate", response_model=TravelStoryResponse)
async def generate_story_endpoint(request: TravelStoryRequest):
    """
    Core multimodal pipeline:
    Receives travel description, synthesizes narrative, builds itinerary,
    generates visual scenes with prompt metadata, produces social captions,
    and renders neural audio narration.
    """
    if not request.description or len(request.description.strip()) < 10:
        raise HTTPException(status_code=400, detail="Please provide a more descriptive travel memory (at least 10 characters).")

    try:
        response = await generate_complete_travel_story(request)
        return response
    except Exception as e:
        print(f"[Error] Generation failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Story generation failed: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    print(f"Starting Intelligent Travel Story Generator server on http://localhost:{port}...")
    uvicorn.run("app:app", host="127.0.0.1", port=port, reload=True)
