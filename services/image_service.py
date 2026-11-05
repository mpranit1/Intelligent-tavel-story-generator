import urllib.parse
import random

# Curated fallback photography categories for fast offline/resilient fallback
CURATED_FALLBACKS = {
    "japan": [
        "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&w=1200&q=80", # Kyoto torii
        "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?auto=format&fit=crop&w=1200&q=80", # Tokyo neon
        "https://images.unsplash.com/photo-1545569341-9eb8b30979d9?auto=format&fit=crop&w=1200&q=80", # Bamboo grove
        "https://images.unsplash.com/photo-1528164344705-475426879c0d?auto=format&fit=crop&w=1200&q=80", # Sakura temple
    ],
    "italy": [
        "https://images.unsplash.com/photo-1533105079780-92b9be482077?auto=format&fit=crop&w=1200&q=80", # Amalfi coast
        "https://images.unsplash.com/photo-1516483638261-f4dbaf036963?auto=format&fit=crop&w=1200&q=80", # Cinque terre
        "https://images.unsplash.com/photo-1529260830199-42c24126f198?auto=format&fit=crop&w=1200&q=80", # Rome colosseum
        "https://images.unsplash.com/photo-1506461883276-594a12b11cf3?auto=format&fit=crop&w=1200&q=80", # Venice canals
    ],
    "iceland": [
        "https://images.unsplash.com/photo-1504893524553-b855bce32c67?auto=format&fit=crop&w=1200&q=80", # Waterfall
        "https://images.unsplash.com/photo-1517411032315-54ef2cb783bb?auto=format&fit=crop&w=1200&q=80", # Aurora borealis
        "https://images.unsplash.com/photo-1483375801503-374c5f66cb61?auto=format&fit=crop&w=1200&q=80", # Black sand beach
        "https://images.unsplash.com/photo-1529963183134-61a90db47eaf?auto=format&fit=crop&w=1200&q=80", # Glaciers
    ],
    "nature": [
        "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?auto=format&fit=crop&w=1200&q=80", # Road trip
        "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=80", # Tropical beach
        "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1200&q=80", # Mountain summit
        "https://images.unsplash.com/photo-1516426122078-c23e76319801?auto=format&fit=crop&w=1200&q=80", # Safari wildlife
    ],
    "city": [
        "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=1200&q=80", # Paris Eiffel
        "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?auto=format&fit=crop&w=1200&q=80", # London street
        "https://images.unsplash.com/photo-1477959858617-67f30bc75b82?auto=format&fit=crop&w=1200&q=80", # City skyline
        "https://images.unsplash.com/photo-1514933651103-005eec06c04b?auto=format&fit=crop&w=1200&q=80", # Cafe bistrot
    ]
}

def generate_scene_image_url(prompt: str, destination: str = "", scene_index: int = 0) -> str:
    """
    Creates an AI generative image URL via Pollinations AI with fallback metadata.
    Enriches the prompt with photographic aesthetic enhancers.
    """
    cleaned_prompt = prompt.strip().replace("\n", " ")
    enhanced_prompt = (
        f"award-winning travel documentary photography of {cleaned_prompt}, "
        f"cinematic golden lighting, highly detailed 35mm shot, national geographic magazine quality, 8k resolution"
    )
    
    encoded_prompt = urllib.parse.quote(enhanced_prompt)
    seed = random.randint(1000, 99999)
    # Pollinations AI direct image URL
    return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&nologo=true&seed={seed}"

def get_fallback_image(destination: str, scene_index: int = 0) -> str:
    dest_lower = destination.lower()
    for key, urls in CURATED_FALLBACKS.items():
        if key in dest_lower:
            return urls[scene_index % len(urls)]
    # Default to nature/city
    fallback_pool = CURATED_FALLBACKS["nature"] + CURATED_FALLBACKS["city"]
    return fallback_pool[scene_index % len(fallback_pool)]
