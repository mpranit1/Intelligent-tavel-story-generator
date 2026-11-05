// Wayfarer AI - Multimodal Travel Story Generator Client Application

let currentStory = null;
let currentSceneIndex = 0;
let masterAudio = null;
let sceneAudios = {};
let cinemaAudio = null;

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  // Initialize Lucide icons
  if (window.lucide) {
    lucide.createIcons();
  }

  setupEventListeners();
  loadPresets();
  setupAudioElements();
});

function setupAudioElements() {
  masterAudio = document.getElementById("master-audio-element");
  cinemaAudio = document.getElementById("cinema-audio-element");

  // Master audio listeners
  if (masterAudio) {
    masterAudio.addEventListener("timeupdate", () => {
      const slider = document.getElementById("master-audio-slider");
      const currLabel = document.getElementById("master-time-curr");
      const totalLabel = document.getElementById("master-time-total");

      if (masterAudio.duration && !isNaN(masterAudio.duration)) {
        const pct = (masterAudio.currentTime / masterAudio.duration) * 100;
        slider.value = pct;
        currLabel.textContent = formatTime(masterAudio.currentTime);
        totalLabel.textContent = formatTime(masterAudio.duration);
      }
    });

    masterAudio.addEventListener("ended", () => {
      updatePlayButtonIcon("btn-master-play", "icon-master-play", false);
    });

    const slider = document.getElementById("master-audio-slider");
    slider.addEventListener("input", (e) => {
      if (masterAudio.duration) {
        masterAudio.currentTime = (e.target.value / 100) * masterAudio.duration;
      }
    });
  }

  // Cinema audio listeners
  if (cinemaAudio) {
    cinemaAudio.addEventListener("ended", () => {
      // Auto-advance to next scene in cinema mode
      if (currentStory && currentStory.scenes && currentSceneIndex < currentStory.scenes.length - 1) {
        changeCinemaScene(currentSceneIndex + 1);
      } else {
        updatePlayButtonIcon("btn-cinema-play-pause", "icon-cinema-play", false);
        document.getElementById("cinema-audio-status").textContent = "Narration finished";
      }
    });
  }
}

function setupEventListeners() {
  const form = document.getElementById("story-form");
  const travelNotes = document.getElementById("travel-notes");
  const charCounter = document.getElementById("char-counter");
  const btnToggleKey = document.getElementById("btn-toggle-key");
  const geminiKeyInput = document.getElementById("gemini-key");

  // Character counter
  travelNotes.addEventListener("input", () => {
    const len = travelNotes.value.length;
    charCounter.textContent = `${len} character${len === 1 ? '' : 's'}`;
  });

  // Toggle API key visibility
  btnToggleKey.addEventListener("click", () => {
    if (geminiKeyInput.type === "password") {
      geminiKeyInput.type = "text";
      btnToggleKey.textContent = "Hide";
    } else {
      geminiKeyInput.type = "password";
      btnToggleKey.textContent = "Show";
    }
  });

  // Scroll to input button
  document.getElementById("btn-scroll-input").addEventListener("click", () => {
    document.getElementById("input-section").scrollIntoView({ behavior: "smooth" });
  });

  // Master Audio Play / Pause
  document.getElementById("btn-master-play").addEventListener("click", toggleMasterAudio);

  // Form submit
  form.addEventListener("submit", handleStoryGeneration);

  // Tab navigation
  document.getElementById("tab-scenes").addEventListener("click", () => switchTab("scenes"));
  document.getElementById("tab-itinerary").addEventListener("click", () => switchTab("itinerary"));
  document.getElementById("tab-export").addEventListener("click", () => switchTab("export"));

  // Cinema Mode triggers
  document.getElementById("btn-cinema-mode").addEventListener("click", openCinemaMode);
  document.getElementById("btn-close-cinema").addEventListener("click", closeCinemaMode);
  document.getElementById("btn-cinema-prev").addEventListener("click", () => {
    if (currentSceneIndex > 0) changeCinemaScene(currentSceneIndex - 1);
  });
  document.getElementById("btn-cinema-next").addEventListener("click", () => {
    if (currentStory && currentSceneIndex < currentStory.scenes.length - 1) {
      changeCinemaScene(currentSceneIndex + 1);
    }
  });
  document.getElementById("btn-cinema-play-pause").addEventListener("click", toggleCinemaAudio);

  // Lightbox close
  document.getElementById("btn-close-lightbox").addEventListener("click", closeLightbox);
  document.getElementById("image-lightbox").addEventListener("click", (e) => {
    if (e.target.id === "image-lightbox") closeLightbox();
  });

  // Export buttons
  document.getElementById("btn-download-md").addEventListener("click", downloadMarkdown);
  document.getElementById("btn-download-json").addEventListener("click", downloadJSON);
  document.getElementById("btn-print-story").addEventListener("click", () => window.print());
}

// ==========================================
// PRESETS LOADER
// ==========================================
async function loadPresets() {
  const container = document.getElementById("presets-container");
  try {
    const res = await fetch("/api/presets");
    const data = await res.json();
    container.innerHTML = "";

    data.presets.forEach(preset => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 border border-slate-700/60 text-xs text-slate-200 hover:text-amber-300 transition flex items-center gap-1.5 group";
      chip.innerHTML = `
        <span class="w-2 h-2 rounded-full bg-amber-400 group-hover:scale-125 transition-transform"></span>
        <span class="font-medium">${preset.name}</span>
        <span class="text-[10px] text-slate-400 opacity-75">(${preset.badge})</span>
      `;

      chip.addEventListener("click", () => {
        document.getElementById("travel-notes").value = preset.description;
        document.getElementById("tone-select").value = preset.tone;
        document.getElementById("voice-select").value = preset.voice;
        
        // Trigger char counter
        document.getElementById("char-counter").textContent = `${preset.description.length} characters`;

        // Highlight selected chip
        container.querySelectorAll("button").forEach(b => b.classList.remove("border-amber-500", "bg-amber-500/10"));
        chip.classList.add("border-amber-500", "bg-amber-500/10");
      });

      container.appendChild(chip);
    });

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    container.innerHTML = `<span class="text-xs text-slate-500">Failed to load preset trips.</span>`;
  }
}

// ==========================================
// STORY GENERATION PIPELINE
// ==========================================
async function handleStoryGeneration(e) {
  e.preventDefault();

  const notes = document.getElementById("travel-notes").value.trim();
  const tone = document.getElementById("tone-select").value;
  const duration = document.getElementById("duration-select").value;
  const voice = document.getElementById("voice-select").value;
  const geminiKey = document.getElementById("gemini-key").value.trim();

  if (!notes) return;

  // Show loading UI
  showLoading(true);
  startLoadingAnimation();

  // Pause any currently playing audio
  stopAllAudio();

  const payload = {
    description: notes,
    tone: tone,
    duration: duration,
    voice: voice,
    gemini_api_key: geminiKey || null
  };

  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Story generation failed.");
    }

    const story = await response.json();
    currentStory = story;

    renderStory(story);
    showLoading(false);

    // Scroll smoothly to results
    document.getElementById("results-section").scrollIntoView({ behavior: "smooth" });

  } catch (error) {
    alert("Error: " + error.message);
    showLoading(false);
  }
}

function showLoading(isLoading) {
  const loadingSec = document.getElementById("loading-section");
  const resultsSec = document.getElementById("results-section");
  const btnGen = document.getElementById("btn-generate");

  if (isLoading) {
    loadingSec.classList.remove("hidden");
    resultsSec.classList.add("hidden");
    btnGen.disabled = true;
    btnGen.classList.add("opacity-50", "cursor-not-allowed");
  } else {
    loadingSec.classList.add("hidden");
    resultsSec.classList.remove("hidden");
    btnGen.disabled = false;
    btnGen.classList.remove("opacity-50", "cursor-not-allowed");
  }
}

function startLoadingAnimation() {
  const statusText = document.getElementById("loading-status-text");
  const steps = [
    { id: "step-narrative", text: "Analyzing travel notes & shaping narrative arc..." },
    { id: "step-itinerary", text: "Synthesizing day-by-day itinerary & insider tips..." },
    { id: "step-visuals", text: "Rendering atmospheric visual scene artwork..." },
    { id: "step-audio", text: "Synthesizing neural voiceover narration..." }
  ];

  let stepIdx = 0;
  const interval = setInterval(() => {
    if (stepIdx < steps.length) {
      statusText.textContent = steps[stepIdx].text;
      
      // Update step indicator cards
      steps.forEach((s, i) => {
        const el = document.getElementById(s.id);
        if (i <= stepIdx) {
          el.classList.add("border-amber-500", "bg-amber-500/20");
        } else {
          el.classList.remove("border-amber-500", "bg-amber-500/20");
        }
      });
      stepIdx++;
    } else {
      clearInterval(interval);
    }
  }, 1200);
}

// ==========================================
// RENDER STORY RESULTS
// ==========================================
function renderStory(story) {
  // Hero metadata
  document.getElementById("story-destination").textContent = story.destination;
  document.getElementById("story-duration").textContent = story.duration_label;
  document.getElementById("badge-date").textContent = story.generated_at;
  document.getElementById("story-title").textContent = story.title;
  document.getElementById("story-subtitle").textContent = story.subtitle;
  document.getElementById("story-summary").textContent = story.summary;

  // Vibe tag pills
  const vibeContainer = document.getElementById("vibe-tags-container");
  vibeContainer.innerHTML = "";
  (story.vibe_tags || []).forEach(tag => {
    const span = document.createElement("span");
    span.className = "text-[11px] px-2.5 py-0.5 rounded-full bg-slate-800 text-amber-300 border border-slate-700/60";
    span.textContent = `#${tag}`;
    vibeContainer.appendChild(span);
  });

  // Master Audio Setup
  if (story.full_audio_url) {
    masterAudio.src = story.full_audio_url;
    document.getElementById("master-audio-card").classList.remove("hidden");
    document.getElementById("audio-voice-badge").textContent = story.audio_voice.split("-")[2] || "Neural Voice";
  } else {
    document.getElementById("master-audio-card").classList.add("hidden");
  }

  // Badges count
  document.getElementById("count-scenes-badge").textContent = story.scenes.length;
  document.getElementById("count-days-badge").textContent = story.itinerary.length;

  // Render Tab 1: Visual Scenes & Narrative
  renderScenes(story.scenes);

  // Render Tab 2: Day-by-Day Itinerary
  renderItinerary(story.itinerary);

  // Re-initialize Lucide Icons
  if (window.lucide) {
    lucide.createIcons();
  }

  // Switch to first tab by default
  switchTab("scenes");
}

function renderScenes(scenes) {
  const grid = document.getElementById("scenes-grid");
  grid.innerHTML = "";

  scenes.forEach((scene, index) => {
    const card = document.createElement("div");
    card.className = "glass-card rounded-2xl overflow-hidden flex flex-col justify-between";

    // Visual image with prompt toggle and zoom icon
    const imgHtml = `
      <div class="relative aspect-video w-full bg-slate-900 overflow-hidden group cursor-pointer" onclick="openLightbox('${scene.image_url}', '${escapeHtml(scene.title)}')">
        <img
          src="${scene.image_url}"
          alt="${escapeHtml(scene.title)}"
          loading="lazy"
          onerror="this.onerror=null; this.src='https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?auto=format&fit=crop&w=1200&q=80';"
          class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
        />
        <div class="absolute inset-0 bg-gradient-to-t from-slate-950/80 via-transparent to-black/20 opacity-90 group-hover:opacity-100 transition"></div>
        
        <!-- Scene Number Pill -->
        <span class="absolute top-3 left-3 text-[11px] font-bold px-2.5 py-1 rounded-full bg-slate-950/80 text-amber-400 border border-amber-500/40 backdrop-blur shadow">
          Scene ${scene.scene_id}
        </span>

        <!-- Zoom Icon Pill -->
        <span class="absolute top-3 right-3 p-1.5 rounded-full bg-slate-950/80 text-slate-300 opacity-0 group-hover:opacity-100 transition border border-slate-700">
          <i data-lucide="zoom-in" class="w-4 h-4"></i>
        </span>

        <!-- Scene Title Overlay -->
        <div class="absolute bottom-3 left-3 right-3">
          <h3 class="text-lg font-bold text-white font-serif-travel drop-shadow">${escapeHtml(scene.title)}</h3>
        </div>
      </div>
    `;

    // Narrative & Audio Controls
    const contentHtml = `
      <div class="p-5 space-y-4 flex-1 flex flex-col justify-between">
        <div class="space-y-3">
          <!-- Narrative text -->
          <p class="text-sm text-slate-200 leading-relaxed font-normal">
            ${escapeHtml(scene.narrative_text)}
          </p>

          <!-- AI Visual Prompt Accordion -->
          <details class="text-xs group">
            <summary class="cursor-pointer text-slate-400 hover:text-amber-400 transition flex items-center gap-1 select-none">
              <i data-lucide="camera" class="w-3.5 h-3.5 text-amber-400"></i>
              <span>Visual Prompt Details</span>
            </summary>
            <div class="mt-2 p-2.5 bg-slate-950/60 rounded-lg border border-slate-800 text-[11px] text-slate-300 italic font-mono leading-normal">
              "${escapeHtml(scene.visual_prompt)}"
            </div>
          </details>
        </div>

        <div class="space-y-3 pt-3 border-t border-slate-800">
          <!-- Audio Play Button for Scene -->
          ${scene.audio_url ? `
            <div class="flex items-center justify-between">
              <button
                onclick="toggleSceneAudio(${scene.scene_id}, '${scene.audio_url}')"
                id="btn-scene-audio-${scene.scene_id}"
                class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-amber-400 border border-slate-700 text-xs font-medium flex items-center gap-1.5 transition"
              >
                <i data-lucide="volume-2" id="icon-scene-audio-${scene.scene_id}" class="w-4 h-4"></i>
                <span id="text-scene-audio-${scene.scene_id}">Play Scene Narration</span>
              </button>
            </div>
          ` : ''}

          <!-- Ready-to-use Caption Card -->
          <div class="bg-slate-950/70 p-3 rounded-xl border border-slate-800/80 space-y-1.5">
            <div class="flex items-center justify-between">
              <span class="text-[10px] uppercase font-semibold text-slate-400 tracking-wider flex items-center gap-1">
                <i data-lucide="instagram" class="w-3 h-3 text-amber-400"></i> Social Caption
              </span>
              <button
                onclick="copyCaption(${scene.scene_id})"
                id="btn-copy-${scene.scene_id}"
                class="text-[11px] text-amber-400 hover:text-amber-300 font-medium flex items-center gap-1 transition"
              >
                <i data-lucide="copy" class="w-3 h-3"></i> Copy
              </button>
            </div>
            <p id="caption-text-${scene.scene_id}" class="text-xs text-slate-300 leading-normal">
              ${escapeHtml(scene.caption)}
            </p>
            <div class="text-[11px] text-amber-400/80 font-mono">
              ${(scene.hashtags || []).map(h => escapeHtml(h)).join(' ')}
            </div>
          </div>
        </div>
      </div>
    `;

    card.innerHTML = imgHtml + contentHtml;
    grid.appendChild(card);
  });
}

function renderItinerary(days) {
  const container = document.getElementById("itinerary-days-container");
  container.innerHTML = "";

  days.forEach((day) => {
    const dayCard = document.createElement("div");
    dayCard.className = "glass-panel rounded-2xl p-6 space-y-6";

    // Day Header
    const dayHeader = `
      <div class="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-2">
        <div>
          <span class="text-xs font-bold uppercase tracking-wider text-amber-400">Day ${day.day_number}</span>
          <h3 class="text-xl font-bold text-white font-serif-travel">${escapeHtml(day.title)}</h3>
        </div>
        <span class="text-xs text-slate-400 italic bg-slate-900/80 px-3 py-1 rounded-full border border-slate-800 self-start sm:self-auto">
          ${escapeHtml(day.theme)}
        </span>
      </div>
    `;

    // Schedule Timeline items
    let itemsHtml = `<div class="space-y-4">`;
    day.items.forEach((item) => {
      itemsHtml += `
        <div class="flex flex-col md:flex-row gap-4 p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-slate-700 transition">
          <!-- Time & Location Pillar -->
          <div class="md:w-56 shrink-0 space-y-1">
            <span class="text-xs font-semibold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 inline-block">
              ${escapeHtml(item.time_of_day)}
            </span>
            <h4 class="text-sm font-bold text-white flex items-center gap-1.5 mt-1">
              <i data-lucide="map-pin" class="w-3.5 h-3.5 text-amber-400 shrink-0"></i>
              ${escapeHtml(item.location)}
            </h4>
          </div>

          <!-- Activity & Tips Column -->
          <div class="flex-1 space-y-2.5">
            <div>
              <p class="text-sm font-medium text-slate-100">${escapeHtml(item.activity)}</p>
              <p class="text-xs text-slate-400 mt-0.5">${escapeHtml(item.highlights)}</p>
            </div>

            <!-- Food Tip & Travel Pro Tip Grid -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1 text-xs">
              ${item.local_food_tip ? `
                <div class="p-2 rounded-lg bg-slate-950/50 border border-slate-800 text-slate-300 flex items-start gap-2">
                  <i data-lucide="utensils" class="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5"></i>
                  <span><strong class="text-amber-300 font-semibold">Tasting Note:</strong> ${escapeHtml(item.local_food_tip)}</span>
                </div>
              ` : ''}

              ${item.travel_tip ? `
                <div class="p-2 rounded-lg bg-slate-950/50 border border-slate-800 text-slate-300 flex items-start gap-2">
                  <i data-lucide="lightbulb" class="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5"></i>
                  <span><strong class="text-amber-300 font-semibold">Pro-Tip:</strong> ${escapeHtml(item.travel_tip)}</span>
                </div>
              ` : ''}
            </div>
          </div>
        </div>
      `;
    });
    itemsHtml += `</div>`;

    dayCard.innerHTML = dayHeader + itemsHtml;
    container.appendChild(dayCard);
  });
}

// ==========================================
// AUDIO PLAYBACK HANDLERS
// ==========================================
function toggleMasterAudio() {
  if (!masterAudio || !masterAudio.src) return;

  // Stop any individual scene audio
  stopSceneAudios();

  if (masterAudio.paused) {
    masterAudio.play();
    updatePlayButtonIcon("btn-master-play", "icon-master-play", true);
  } else {
    masterAudio.pause();
    updatePlayButtonIcon("btn-master-play", "icon-master-play", false);
  }
}

function toggleSceneAudio(sceneId, audioUrl) {
  // Pause master audio if playing
  if (masterAudio && !masterAudio.paused) {
    masterAudio.pause();
    updatePlayButtonIcon("btn-master-play", "icon-master-play", false);
  }

  // If another scene audio is playing, pause it
  Object.keys(sceneAudios).forEach(id => {
    if (parseInt(id) !== sceneId && sceneAudios[id] && !sceneAudios[id].paused) {
      sceneAudios[id].pause();
      updateSceneAudioButton(id, false);
    }
  });

  if (!sceneAudios[sceneId]) {
    sceneAudios[sceneId] = new Audio(audioUrl);
    sceneAudios[sceneId].addEventListener("ended", () => {
      updateSceneAudioButton(sceneId, false);
    });
  }

  const audio = sceneAudios[sceneId];
  if (audio.paused) {
    audio.play();
    updateSceneAudioButton(sceneId, true);
  } else {
    audio.pause();
    updateSceneAudioButton(sceneId, false);
  }
}

function stopSceneAudios() {
  Object.keys(sceneAudios).forEach(id => {
    if (sceneAudios[id]) {
      sceneAudios[id].pause();
      sceneAudios[id].currentTime = 0;
      updateSceneAudioButton(id, false);
    }
  });
}

function stopAllAudio() {
  if (masterAudio) {
    masterAudio.pause();
    updatePlayButtonIcon("btn-master-play", "icon-master-play", false);
  }
  if (cinemaAudio) {
    cinemaAudio.pause();
    updatePlayButtonIcon("btn-cinema-play-pause", "icon-cinema-play", false);
  }
  stopSceneAudios();
}

function updateSceneAudioButton(sceneId, isPlaying) {
  const btn = document.getElementById(`btn-scene-audio-${sceneId}`);
  const text = document.getElementById(`text-scene-audio-${sceneId}`);
  const icon = document.getElementById(`icon-scene-audio-${sceneId}`);

  if (!btn || !text || !icon) return;

  if (isPlaying) {
    btn.classList.add("bg-amber-500", "text-slate-950");
    btn.classList.remove("bg-slate-800", "text-amber-400");
    text.textContent = "Pause Narration";
    icon.setAttribute("data-lucide", "pause");
  } else {
    btn.classList.remove("bg-amber-500", "text-slate-950");
    btn.classList.add("bg-slate-800", "text-amber-400");
    text.textContent = "Play Scene Narration";
    icon.setAttribute("data-lucide", "volume-2");
  }
  if (window.lucide) lucide.createIcons();
}

function updatePlayButtonIcon(btnId, iconId, isPlaying) {
  const icon = document.getElementById(iconId);
  if (!icon) return;
  if (isPlaying) {
    icon.setAttribute("data-lucide", "pause");
  } else {
    icon.setAttribute("data-lucide", "play");
  }
  if (window.lucide) lucide.createIcons();
}

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

// ==========================================
// CINEMA MODE (FULLSCREEN PRESENTATION)
// ==========================================
function openCinemaMode() {
  if (!currentStory || !currentStory.scenes || currentStory.scenes.length === 0) return;

  stopAllAudio();
  const modal = document.getElementById("cinema-modal");
  modal.classList.remove("hidden");

  currentSceneIndex = 0;
  displayCinemaScene(currentSceneIndex);
}

function closeCinemaMode() {
  const modal = document.getElementById("cinema-modal");
  modal.classList.add("hidden");
  if (cinemaAudio) {
    cinemaAudio.pause();
  }
}

function changeCinemaScene(newIndex) {
  if (!currentStory || newIndex < 0 || newIndex >= currentStory.scenes.length) return;
  currentSceneIndex = newIndex;
  displayCinemaScene(currentSceneIndex);
}

function displayCinemaScene(idx) {
  const scene = currentStory.scenes[idx];
  if (!scene) return;

  document.getElementById("cinema-scene-counter").textContent = `Scene ${idx + 1} of ${currentStory.scenes.length}`;
  document.getElementById("cinema-image").src = scene.image_url;
  document.getElementById("cinema-title").textContent = scene.title;
  document.getElementById("cinema-narration").textContent = scene.narrative_text;

  // Cinema Prev/Next button states
  document.getElementById("btn-cinema-prev").disabled = idx === 0;
  document.getElementById("btn-cinema-prev").classList.toggle("opacity-40", idx === 0);
  document.getElementById("btn-cinema-next").disabled = idx === currentStory.scenes.length - 1;
  document.getElementById("btn-cinema-next").classList.toggle("opacity-40", idx === currentStory.scenes.length - 1);

  // Play narration for this scene if present
  if (scene.audio_url && cinemaAudio) {
    cinemaAudio.src = scene.audio_url;
    cinemaAudio.play().catch(e => console.log("Autoplay was prevented:", e));
    updatePlayButtonIcon("btn-cinema-play-pause", "icon-cinema-play", true);
    document.getElementById("cinema-audio-status").textContent = "Playing narration...";
  } else {
    document.getElementById("cinema-audio-status").textContent = "No audio track";
    updatePlayButtonIcon("btn-cinema-play-pause", "icon-cinema-play", false);
  }
}

function toggleCinemaAudio() {
  if (!cinemaAudio || !cinemaAudio.src) return;
  if (cinemaAudio.paused) {
    cinemaAudio.play();
    updatePlayButtonIcon("btn-cinema-play-pause", "icon-cinema-play", true);
    document.getElementById("cinema-audio-status").textContent = "Playing narration...";
  } else {
    cinemaAudio.pause();
    updatePlayButtonIcon("btn-cinema-play-pause", "icon-cinema-play", false);
    document.getElementById("cinema-audio-status").textContent = "Paused";
  }
}

// ==========================================
// LIGHTBOX & CAPTIONS
// ==========================================
function openLightbox(url, title) {
  const lightbox = document.getElementById("image-lightbox");
  const img = document.getElementById("lightbox-img");
  const cap = document.getElementById("lightbox-caption");

  img.src = url;
  cap.textContent = title;
  lightbox.classList.remove("hidden");
}

function closeLightbox() {
  document.getElementById("image-lightbox").classList.add("hidden");
}

function copyCaption(sceneId) {
  const scene = currentStory.scenes.find(s => s.scene_id === sceneId);
  if (!scene) return;

  const fullText = `${scene.caption}\n\n${(scene.hashtags || []).join(' ')}`;
  navigator.clipboard.writeText(fullText).then(() => {
    const btn = document.getElementById(`btn-copy-${sceneId}`);
    btn.innerHTML = `<i data-lucide="check" class="w-3 h-3 text-emerald-400"></i> Copied!`;
    if (window.lucide) lucide.createIcons();
    setTimeout(() => {
      btn.innerHTML = `<i data-lucide="copy" class="w-3 h-3"></i> Copy`;
      if (window.lucide) lucide.createIcons();
    }, 2000);
  });
}

// ==========================================
// TABS SWITCHER
// ==========================================
function switchTab(tabName) {
  const tabs = ["scenes", "itinerary", "export"];
  tabs.forEach(t => {
    const btn = document.getElementById(`tab-${t}`);
    const panel = document.getElementById(`panel-${t}`);

    if (t === tabName) {
      btn.className = "tab-btn px-4 py-2.5 rounded-t-lg font-semibold border-b-2 border-amber-500 text-amber-400 bg-slate-800/50 flex items-center gap-2 transition shrink-0";
      panel.classList.remove("hidden");
    } else {
      btn.className = "tab-btn px-4 py-2.5 rounded-t-lg font-semibold border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-2 transition shrink-0";
      panel.classList.add("hidden");
    }
  });
}

// ==========================================
// EXPORTS: MARKDOWN & JSON
// ==========================================
function downloadMarkdown() {
  if (!currentStory) return;

  let md = `# ${currentStory.title}\n`;
  md += `*${currentStory.subtitle}*\n\n`;
  md += `**Destination:** ${currentStory.destination} | **Duration:** ${currentStory.duration_label}\n\n`;
  md += `### Overview\n${currentStory.summary}\n\n`;
  md += `**Themes:** ${(currentStory.vibe_tags || []).join(', ')}\n\n`;
  md += `---\n\n## Visual Story Chapters\n\n`;

  currentStory.scenes.forEach(s => {
    md += `### Scene ${s.scene_id}: ${s.title}\n`;
    md += `![${s.title}](${s.image_url})\n\n`;
    md += `*Visual Prompt:* \`${s.visual_prompt}\`\n\n`;
    md += `${s.narrative_text}\n\n`;
    md += `> **Social Caption:** ${s.caption}\n`;
    md += `> ${(s.hashtags || []).join(' ')}\n\n`;
  });

  md += `---\n\n## Day-by-Day Itinerary\n\n`;
  currentStory.itinerary.forEach(d => {
    md += `### Day ${d.day_number}: ${d.title}\n`;
    md += `*Focus:* ${d.theme}\n\n`;
    d.items.forEach(item => {
      md += `- **${item.time_of_day} | ${item.location}**: ${item.activity}\n`;
      md += `  - *Highlights:* ${item.highlights}\n`;
      if (item.local_food_tip) md += `  - *Tasting Note:* ${item.local_food_tip}\n`;
      if (item.travel_tip) md += `  - *Pro-Tip:* ${item.travel_tip}\n`;
    });
    md += `\n`;
  });

  const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
  triggerDownload(blob, `${currentStory.destination.toLowerCase().replace(/[^a-z0-9]/g, '_')}_travel_story.md`);
}

function downloadJSON() {
  if (!currentStory) return;
  const jsonStr = JSON.stringify(currentStory, null, 2);
  const blob = new Blob([jsonStr], { type: "application/json;charset=utf-8" });
  triggerDownload(blob, `${currentStory.destination.toLowerCase().replace(/[^a-z0-9]/g, '_')}_story_data.json`);
}

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#032;");
}
