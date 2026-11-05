import os
import re
import uuid
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from services.models import TravelStoryRequest, TravelStoryResponse, VisualScene, ItineraryDay, ItineraryItem
from services.image_service import generate_scene_image_url
from services.tts_service import generate_story_audio_tracks

# ==========================================
# PRESET EXPEDITIONS (for 1-click test drive)
# ==========================================
PRESETS = [
    {
        "id": "preset-kyoto",
        "name": "Autumn in Kyoto, Japan",
        "badge": "Cultural & Zen",
        "description": "We spent 4 days wandering through Kyoto in late November. At dawn, we walked through the vermilion torii gates of Fushimi Inari with morning mist clinging to the cedar trees. By midday, we strolled through the whispering Arashiyama bamboo forest and sampled warm matcha soft serve. We ended with a tranquil tea ceremony in a traditional wooden machiya overlooking an autumn rock garden.",
        "tone": "evocative",
        "duration": "4-5 Days",
        "voice": "en-US-JennyNeural"
    },
    {
        "id": "preset-amalfi",
        "name": "Sun-Drenched Amalfi Coast, Italy",
        "badge": "Romantic & Coastal",
        "description": "A 3-day road trip along the cliffside roads of the Amalfi Coast. We rented a vintage convertible in Sorrento, swam in the turquoise waters of Positano, tasted fresh handmade lemon granita, hiked the Path of the Gods high above the Mediterranean clouds, and enjoyed fresh seafood pasta under a pergola of lemon trees in Ravello at twilight.",
        "tone": "romantic",
        "duration": "Weekend Getaway",
        "voice": "en-GB-SoniaNeural"
    },
    {
        "id": "preset-iceland",
        "name": "Iceland Ring Road & Aurora",
        "badge": "Adventurous & Wild",
        "description": "An expedition across Southern Iceland. We stood beneath the thunderous spray of Skogafoss, walked on the jet-black basalt sands of Reynisfjara beach, explored crystal blue ice caves inside Vatnajökull glacier, and soaked in thermal hot springs at midnight while green ribbons of the Northern Lights danced across the sub-arctic sky.",
        "tone": "adventurous",
        "duration": "5-7 Days",
        "voice": "en-US-GuyNeural"
    },
    {
        "id": "preset-serengeti",
        "name": "Serengeti Safari & Great Migration",
        "badge": "Wildlife & Epic",
        "description": "Five days across Tanzania's endless golden plains. We took off in a hot air balloon at sunrise over herds of wildebeest crossing the Mara River, tracked a pride of lions resting on sunlit granite kopjes, listened to the calls of zebras around our canvas safari camp campfire, and stargazed beneath the Milky Way.",
        "tone": "adventurous",
        "duration": "5-7 Days",
        "voice": "en-GB-RyanNeural"
    }
]

# ==========================================
# INTELLIGENT RULE/TEMPLATE NLP ENGINE
# (Guarantees zero-dependency local generation)
# ==========================================
class IntelligentNLPStoryEngine:
    """
    Parses unstructured travel text into cohesive structured story elements:
    extracts destination, tone, key moments, generates sensory narrative,
    synchronized visual prompts, captions, and day-by-day itineraries.
    """

    DESTINATION_MAP = {
        "kyoto": {"country": "Japan", "region": "Kansai", "vibe": ["Zen", "Historic", "Autumn Leaves", "Traditional Tea"]},
        "japan": {"country": "Japan", "region": "East Asia", "vibe": ["Modern Metropolises", "Ancient Shrines", "Culinary Delights"]},
        "tokyo": {"country": "Japan", "region": "Kanto", "vibe": ["Neon Lights", "Subway Beats", "Culinary Adventure"]},
        "amalfi": {"country": "Italy", "region": "Campania", "vibe": ["Mediterranean Blue", "Cliffside Villas", "Lemon Orchards"]},
        "italy": {"country": "Italy", "region": "Southern Europe", "vibe": ["La Dolce Vita", "Artisan Gelato", "Historic Plazas"]},
        "iceland": {"country": "Iceland", "region": "Nordic", "vibe": ["Glacial Blue", "Volcanic Ash", "Aurora Borealis"]},
        "serengeti": {"country": "Tanzania", "region": "East Africa", "vibe": ["Golden Savanna", "Wildlife Odyssey", "Starry Campfires"]},
        "paris": {"country": "France", "region": "Ile-de-France", "vibe": ["Cobblestone Romance", "Patisserie Aromas", "Boulevard Lights"]},
        "swiss": {"country": "Switzerland", "region": "Alps", "vibe": ["Alpine Meadows", "Snow Peaks", "Emerald Lakes"]},
        "bali": {"country": "Indonesia", "region": "Southeast Asia", "vibe": ["Emerald Rice Terraces", "Temple Bells", "Ocean Sunsets"]},
        "bangkok": {"country": "Thailand", "region": "Southeast Asia", "vibe": ["Street Food Woks", "Golden Temples", "Floating Markets"]},
        "new york": {"country": "USA", "region": "East Coast", "vibe": ["Towering Skylines", "Broadway Sparkle", "Central Park Strolls"]}
    }

    @classmethod
    def detect_destination(cls, text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        for key, info in cls.DESTINATION_MAP.items():
            if key in text_lower:
                return {
                    "name": key.title() + (f", {info['country']}" if key.title() != info['country'] else ""),
                    "info": info
                }
        
        # Heuristic fallback: look for "in [City/Country]" or "to [City/Country]"
        match = re.search(r'\b(?:in|to|exploring|visiting|across)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)', text)
        if match:
            found = match.group(1).strip()
            return {
                "name": found,
                "info": {"country": found, "region": "World", "vibe": ["Wanderlust", "Discovery", "Local Flavors"]}
            }
        
        return {
            "name": "The Open Road",
            "info": {"country": "Wanderland", "region": "Globe", "vibe": ["Exploration", "Horizon", "Discovery"]}
        }

    @classmethod
    def parse_sentences(cls, text: str) -> List[str]:
        # Clean and split into meaningful sentences or clauses
        raw = re.split(r'[.!?\n]+', text)
        sentences = [s.strip() for s in raw if len(s.strip()) > 15]
        return sentences

    @classmethod
    def generate_story(cls, request: TravelStoryRequest) -> Dict[str, Any]:
        desc = request.description.strip()
        dest_meta = cls.detect_destination(desc)
        dest_name = dest_meta["name"]
        vibes = dest_meta["info"].get("vibe", ["Adventure", "Wanderlust", "Culture"])
        tone = (request.tone or "evocative").lower()

        sentences = cls.parse_sentences(desc)
        if not sentences:
            sentences = [
                f"We set foot in {dest_name} with hearts wide open to discovery.",
                f"Every corner revealed hidden alleyways, rich local aromas, and welcoming smiles.",
                f"The golden hour painted the skyline in breathtaking warm amber tones.",
                f"As night fell, we gathered under the starlight to savor local dishes and celebrate the journey."
            ]

        # Determine scenes count (3 to 5 scenes)
        num_scenes = min(max(len(sentences), 3), 5)
        # Partition sentences across scenes
        chunk_size = max(1, len(sentences) // num_scenes)
        scene_seeds = []
        for i in range(num_scenes):
            start = i * chunk_size
            end = (i + 1) * chunk_size if i < num_scenes - 1 else len(sentences)
            chunk = " ".join(sentences[start:end]) if start < len(sentences) else sentences[-1]
            scene_seeds.append(chunk if chunk else sentences[0])

        # Style tone decorators
        tone_prefixes = {
            "evocative": ["Whispers of", "Echoes Across", "The Golden Glow of", "Reflections in", "Twilight Over"],
            "adventurous": ["Conquering", "Into the Wild of", "The Trail to", "Chasing Horizons at", "Expedition Through"],
            "romantic": ["Sunset Strolls in", "Enchanting Moments at", "Love and Solitude in", "Starry Nights over", "Sweet Serenades in"],
            "luxury": ["Opulent Vistas of", "The Savor of", "Bespoke Elegance in", "Private Retreats of", "Unrivaled Grandeur at"],
            "playful": ["Getting Happily Lost in", "The Curious Streets of", "Sweet Feasts in", "Wacky Wonders of", "Dancing Through"]
        }
        prefixes = tone_prefixes.get(tone, tone_prefixes["evocative"])

        story_title = f"Chronicles of {dest_name}: A Journey of Soul and Senses"
        story_subtitle = f"A {tone.capitalize()} odyssey through {dest_name}"
        summary = (
            f"From the first dawn light to the quiet evening breezes, this journey through {dest_name} "
            f"unfolded into a vivid tapestry of unforgettable landscapes, intimate encounters, and enduring memories. "
            f"Here is the narrative of every step, flavor, and horizon encountered along the way."
        )

        scenes_data = []
        for idx, seed in enumerate(scene_seeds):
            scene_num = idx + 1
            prefix = prefixes[idx % len(prefixes)]
            
            # Extract key nouns/phrases from seed for visual and title
            words = [w.strip(",.;:()") for w in seed.split() if len(w) > 3 and w.lower() not in {"this", "that", "with", "from", "into", "were", "went", "visited"}]
            subject_phrase = " ".join(words[:4]) if words else dest_name

            scene_title = f"{prefix} {subject_phrase.title()}"
            
            # Enrich narrative text
            if tone == "evocative":
                narrative_body = f"{seed}. The ambient air carried the unmistakable spirit of {dest_name}, where time seemed to slow down, allowing every sensory detail—from the soft texture of stone underfoot to the delicate whispers of the wind—to etch itself into memory."
            elif tone == "adventurous":
                narrative_body = f"{seed}. Every pulse of adrenaline brought a deeper thrill of discovery, pushing beyond familiar boundaries into the rugged, untamed beauty of {dest_name}."
            elif tone == "romantic":
                narrative_body = f"{seed}. Hand in hand, the world shrank into this single spellbound moment, illuminated by the tender colors of the horizon and the timeless charm of {dest_name}."
            elif tone == "luxury":
                narrative_body = f"{seed}. Impeccable serenity and bespoke refinement met at every turn, turning each sight in {dest_name} into a celebration of life's finest pleasures."
            else:
                narrative_body = f"{seed}. Joy and serendipity followed every step, turning simple wanderings into unexpected delight and spontaneous laughter."

            # Construct visual prompt with photographic specifications
            visual_prompt = (
                f"{subject_phrase} in {dest_name}, detailed atmospheric scenery, "
                f"cinematic natural lighting, authentic travel documentary aesthetics, vibrant colors"
            )

            # Generate visual URL
            image_url = generate_scene_image_url(visual_prompt, dest_name, idx)

            # Captions and hashtags
            caption = f"Still dreaming about this moment in {dest_name}: {seed[:100]}... ✨"
            hashtags = [
                f"#{dest_name.replace(' ', '').replace(',', '')}",
                f"#{tone.capitalize()}Travel",
                "#TravelDiaries",
                "#WanderlustMoments",
                "#StoryOfMyTrip"
            ]

            scenes_data.append({
                "scene_id": scene_num,
                "title": scene_title,
                "narrative_text": narrative_body,
                "visual_prompt": visual_prompt,
                "image_url": image_url,
                "caption": caption,
                "hashtags": hashtags
            })

        # Generate structured Itinerary synchronized with the scenes
        itinerary_days = []
        times_of_day = ["Morning Exploration", "Midday Culture & Lunch", "Golden Hour Vistas", "Evening Dining & Solitude"]
        
        # Determine number of days
        num_days = max(2, min(len(scenes_data), 4))
        for day_i in range(num_days):
            day_num = day_i + 1
            ref_scene = scenes_data[day_i % len(scenes_data)]
            
            day_items = []
            for t_idx, time_slot in enumerate(times_of_day):
                if t_idx == 0:
                    activity = f"Sunrise arrival and opening walk through {ref_scene['title']}"
                    highlight = "Watch the morning light unveil the historic sights before crowds arrive."
                    food_tip = "Local bakery pastry and freshly brewed regional coffee or tea."
                    tip = "Carry a light sweater for the early morning breeze and comfortable walking shoes."
                elif t_idx == 1:
                    activity = f"Culinary tasting and artisan market discovery in central {dest_name}"
                    highlight = "Sampling iconic street delicacies and visiting local craftsmanship workshops."
                    food_tip = "Traditional specialty platter recommended by locals."
                    tip = "Keep local cash on hand for small stall vendors."
                elif t_idx == 2:
                    activity = f"Scenic viewpoint walk corresponding to {ref_scene['title']}"
                    highlight = "Golden hour panorama capturing the skyline and natural terrain."
                    food_tip = "Refreshing regional fruit drink or artisanal gelato."
                    tip = "Bring an extra camera battery—the lighting is ideal for portraits here."
                else:
                    activity = f"Intimate dinner and twilight walk under the lanterns of {dest_name}"
                    highlight = "Immersive storytelling, local hospitality, and tranquil night architecture."
                    food_tip = "Slow-cooked regional dinner paired with local beverages."
                    tip = "Reserve a terrace table in advance for prime twilight views."

                day_items.append({
                    "time_of_day": time_slot,
                    "location": f"{dest_name} Landmark #{t_idx+1}",
                    "activity": activity,
                    "highlights": highlight,
                    "local_food_tip": food_tip,
                    "travel_tip": tip
                })

            itinerary_days.append({
                "day_number": day_num,
                "title": f"Day {day_num}: {ref_scene['title']}",
                "theme": f"Immersive immersion in {dest_name}'s {vibes[day_i % len(vibes)]} atmosphere",
                "items": day_items
            })

        return {
            "title": story_title,
            "subtitle": story_subtitle,
            "destination": dest_name,
            "duration_label": f"{num_days} Days / {num_days-1} Nights",
            "summary": summary,
            "vibe_tags": vibes,
            "scenes": scenes_data,
            "itinerary": itinerary_days
        }


# ==========================================
# GEMINI API LLM INTEGRATION
# ==========================================
async def generate_with_gemini(request: TravelStoryRequest, api_key: str) -> Optional[Dict[str, Any]]:
    """
    Invokes Google Gemini SDK to synthesize rich consistent story, itinerary, scenes, and captions.
    """
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        prompt = f"""
You are an award-winning travel writer, itinerary planner, and creative visual director.
Convert the following user travel memories into a cohesive multimodal digital travel story.

USER TRAVEL DESCRIPTION:
\"\"\"{request.description}\"\"\"

SPECIFICATIONS:
- Desired Tone: {request.tone or 'evocative'}
- Desired Duration: {request.duration or 'auto'}
- Return a STRICT valid JSON object matching this schema:
{{
  "title": "Evocative travel story headline",
  "subtitle": "Poetic secondary subtitle",
  "destination": "Main City/Country",
  "duration_label": "e.g. 4 Days / 3 Nights",
  "summary": "Compelling narrative overview paragraph (80-120 words)",
  "vibe_tags": ["3 to 5 tags e.g. Coastal, Historic, Culinary"],
  "scenes": [
    {{
      "scene_id": 1,
      "title": "Scene title",
      "narrative_text": "Lyrical, vivid paragraph describing this moment (70-100 words)",
      "visual_prompt": "Precise cinematic photographic prompt describing visual composition, lighting, lens, colors, subject",
      "caption": "Engaging social media caption with emoji",
      "hashtags": ["#tag1", "#tag2", "#tag3"]
    }}
  ],
  "itinerary": [
    {{
      "day_number": 1,
      "title": "Day 1 headline",
      "theme": "Day focus",
      "items": [
        {{
          "time_of_day": "Morning / Afternoon / Golden Hour / Evening",
          "location": "Specific place name",
          "activity": "Activity description",
          "highlights": "What makes this unforgettable",
          "local_food_tip": "Specific local dish or drink to try",
          "travel_tip": "Insider practical advice"
        }}
      ]
    }}
  ]
}}

Ensure 3 to 5 visual scenes that strictly mirror the narrative sequence.
Respond ONLY with the raw JSON object. No Markdown code fences, no commentary.
"""

        # Choose fast Gemini model
        model_name = "gemini-2.5-flash"
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        text_content = response.text.strip()
        # Clean potential markdown wrapping if present
        if text_content.startswith("```json"):
            text_content = text_content[7:]
        if text_content.startswith("```"):
            text_content = text_content[3:]
        if text_content.endswith("```"):
            text_content = text_content[:-3]
        
        parsed = json.loads(text_content.strip())

        # Post-process scenes to attach image URLs
        dest = parsed.get("destination", "Wanderlust")
        for idx, scene in enumerate(parsed.get("scenes", [])):
            v_prompt = scene.get("visual_prompt", f"{dest} scenic view")
            scene["image_url"] = generate_scene_image_url(v_prompt, dest, idx)

        return parsed
    except Exception as e:
        print(f"[Gemini] Warning: Gemini API call failed ({e}). Falling back to local NLP engine.")
        return None


# ==========================================
# UNIFIED STORY GENERATOR FACADE
# ==========================================
async def generate_complete_travel_story(request: TravelStoryRequest) -> TravelStoryResponse:
    story_id = f"story_{uuid.uuid4().hex[:8]}"
    voice = request.voice or "en-US-JennyNeural"

    # 1. Determine whether to use Gemini or Local NLP
    api_key = request.gemini_api_key or os.environ.get("GEMINI_API_KEY")
    story_dict = None
    if api_key:
        story_dict = await generate_with_gemini(request, api_key)
    
    if not story_dict:
        story_dict = IntelligentNLPStoryEngine.generate_story(request)

    # 2. Extract full narrative for overall voiceover
    scenes_list = story_dict.get("scenes", [])
    full_narrative_parts = [story_dict.get("title", ""), story_dict.get("summary", "")]
    for s in scenes_list:
        full_narrative_parts.append(f"{s.get('title', '')}. {s.get('narrative_text', '')}")
    full_narrative = "\n\n".join(full_narrative_parts)

    # 3. Generate Audio Narration asynchronously
    audio_tracks = await generate_story_audio_tracks(
        story_id=story_id,
        scenes=scenes_list,
        full_narrative=full_narrative,
        voice=voice
    )

    # 4. Bind audio URLs into the scenes
    model_scenes: List[VisualScene] = []
    for s in scenes_list:
        s_id = s.get("scene_id")
        scene_obj = VisualScene(
            scene_id=s_id,
            title=s.get("title", f"Scene {s_id}"),
            narrative_text=s.get("narrative_text", ""),
            visual_prompt=s.get("visual_prompt", ""),
            image_url=s.get("image_url", ""),
            caption=s.get("caption", ""),
            hashtags=s.get("hashtags", []),
            audio_url=audio_tracks.get(s_id)
        )
        model_scenes.append(scene_obj)

    # 5. Build Itinerary models
    model_itinerary: List[ItineraryDay] = []
    for d in story_dict.get("itinerary", []):
        day_items = [
            ItineraryItem(
                time_of_day=item.get("time_of_day", ""),
                location=item.get("location", ""),
                activity=item.get("activity", ""),
                highlights=item.get("highlights", ""),
                local_food_tip=item.get("local_food_tip"),
                travel_tip=item.get("travel_tip")
            )
            for item in d.get("items", [])
        ]
        model_itinerary.append(
            ItineraryDay(
                day_number=d.get("day_number", 1),
                title=d.get("title", "Day Itinerary"),
                theme=d.get("theme", "Exploration"),
                items=day_items
            )
        )

    return TravelStoryResponse(
        id=story_id,
        title=story_dict.get("title", "Travel Story"),
        subtitle=story_dict.get("subtitle", "A journey to remember"),
        destination=story_dict.get("destination", "Wanderland"),
        duration_label=story_dict.get("duration_label", "Multiday Journey"),
        summary=story_dict.get("summary", ""),
        vibe_tags=story_dict.get("vibe_tags", ["Travel", "Discovery"]),
        scenes=model_scenes,
        itinerary=model_itinerary,
        full_audio_url=audio_tracks.get("full"),
        audio_voice=voice,
        generated_at=datetime.now().strftime("%B %d, %Y - %I:%M %p")
    )
