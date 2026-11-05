import os
import asyncio
from typing import Optional, List, Dict, Any

AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

VOICE_OPTIONS = {
    "en-US-JennyNeural": "Jenny (US - Warm Storyteller)",
    "en-US-GuyNeural": "Guy (US - Adventurous & Dynamic)",
    "en-GB-SoniaNeural": "Sonia (UK - Sophisticated Documentary)",
    "en-GB-RyanNeural": "Ryan (UK - Engaging Storyteller)",
    "en-AU-NatashaNeural": "Natasha (AU - Friendly & Cheerful)",
}

def _sync_gtts_save(text: str, file_path: str):
    """Synchronous gTTS fallback executed in thread pool."""
    from gtts import gTTS
    tts = gTTS(text=text.strip(), lang='en', slow=False)
    tts.save(file_path)

async def generate_speech_file(text: str, filename: str, voice: str = "en-US-JennyNeural") -> Optional[str]:
    """
    Synthesize speech using edge-tts with timeout and gTTS fallback.
    Saves to static/audio/<filename> and returns the public URL path.
    """
    if not text or not text.strip():
        return None
    
    file_path = os.path.join(AUDIO_DIR, filename)
    public_url = f"/static/audio/{filename}"

    # If already cached and valid, reuse
    if os.path.exists(file_path) and os.path.getsize(file_path) > 1000:
        return public_url

    selected_voice = voice if voice in VOICE_OPTIONS else "en-US-JennyNeural"

    # Attempt Edge TTS with 12-second timeout
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text.strip(), selected_voice)
        await asyncio.wait_for(communicate.save(file_path), timeout=12.0)
        if os.path.exists(file_path) and os.path.getsize(file_path) > 500:
            return public_url
    except Exception as e:
        print(f"[TTS] Edge-TTS notice for '{filename}': {e}. Attempting gTTS fallback...")

    # Fallback to gTTS in thread
    try:
        await asyncio.wait_for(asyncio.to_thread(_sync_gtts_save, text, file_path), timeout=10.0)
        if os.path.exists(file_path) and os.path.getsize(file_path) > 500:
            return public_url
    except Exception as e2:
        print(f"[TTS] gTTS fallback warning for '{filename}': {e2}")

    # If 0-byte file was left behind, remove it
    if os.path.exists(file_path) and os.path.getsize(file_path) == 0:
        try:
            os.remove(file_path)
        except OSError:
            pass

    return None

async def generate_story_audio_tracks(story_id: str, scenes: list, full_narrative: str, voice: str) -> dict:
    """
    Generates audio tracks for each individual scene plus the full narrative track concurrently.
    Returns a dict mapping {scene_id: url} and "full": url.
    """
    results = {}
    
    # Task for full track
    full_filename = f"{story_id}_full.mp3"
    full_task = generate_speech_file(full_narrative, full_filename, voice)

    # Tasks for scene tracks
    scene_tasks = []
    scene_keys = []
    for scene in scenes:
        s_id = scene.get("scene_id") if isinstance(scene, dict) else scene.scene_id
        s_text = scene.get("narrative_text") if isinstance(scene, dict) else scene.narrative_text
        s_title = scene.get("title") if isinstance(scene, dict) else scene.title
        
        script = f"{s_title}. {s_text}"
        s_filename = f"{story_id}_scene_{s_id}.mp3"
        
        scene_keys.append(s_id)
        scene_tasks.append(generate_speech_file(script, s_filename, voice))

    # Run all speech synthesis tasks in parallel!
    all_results = await asyncio.gather(full_task, *scene_tasks, return_exceptions=True)

    # Store full audio
    full_res = all_results[0]
    results["full"] = full_res if isinstance(full_res, str) else None

    # Store scene audios
    for idx, key in enumerate(scene_keys):
        s_res = all_results[idx + 1]
        results[key] = s_res if isinstance(s_res, str) else None

    return results
