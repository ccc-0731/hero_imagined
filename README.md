# 🌟 Hero Imagined

*A multimodal, agentic workflow for crafting your childhood dream superhero — then telling, illustrating, and sharing their story.*

A full agent-powered creative pipeline that guides you from a spark of imagination → to a fully illustrated cinematic story → to an immersive audio experience → to real-life inspiration.

Built with **Flask**, **Python**, **Google Gemini** (text & image), and **ElevenLabs** (audio), this project combines text, image, and audio generation into one cohesive interactive experience.

---

## ✨ Overview

Hero Imagined is a web-based system where a user can:

1. **Describe** the kind of hero they want to become (Agent 1)
2. **Design** the character in depth (Agent 2a)
3. **Build** the world they inhabit (Agent 2b)
4. **Get** a ~1000-word illustrated story (Agent 3)
5. **Experience** studio Ghibli–styled cinematic illustrations (Agent 4a)
6. **Listen** to a 30-second BGM with custom lyrics about their adventure (Agent 4b)
7. **Reflect** on how to embark on real-world adventures (Agent 4c)

All powered through a clean, agentic workflow with real-time progress updates.

---

## 🚀 Architecture

Hero Imagined consists of **six main agents**, each running sequentially with intermediate UIs and animated progress bars.

### **Agent 1 — Story Detector**

**Model:** Google Gemini API
**Purpose:** Interprets the user's initial dream-hero prompt.
**Input:** Single text field asking:

> *"What kind of hero do you want to become?"*
> (with examples: *woodland elf in a fantasy realm*, *secret agent on a sci-fi mission*, etc.)

**Output:**

* The story's **genre** (fantasy, sci-fi, etc.)
* A **concise setting summary** extracted from user input

---

### **Agents 2 — Question Askers (Character Designer & World Builder)**

Two parallel agents displayed in **left/right columns** on the same page, sharing a unified **"Done" button**.

#### **Agent 2a — Character Designer**

**Model:** Google Gemini
**Input:** User fills 8–10 fields:

* Age
* World Setting
* Hair & Skin
* Superpower
* Weapon
* Personality
* Worst Fear
* Quirk
* Backstory

**Output:** A finalized *character blueprint* (text summary).

#### **Agent 2b — World Builder**

**Model:** Google Gemini
**Input:** 4 long-form questions:

* Describe key mythical plants/creatures (fantasy) or tech (sci-fi)
* History & mythology
* Legendary figures or heroes
* Technology/magic details

**Output:** A finalized *world description*.

**UI Feature:** Both forms share a single **"Done"** button at the bottom, which triggers story generation once both character and world are finalized.

---

### **Agent 3 — Story Crafter**

**Model:** Google Gemini
**Input:**

* Finalized *character description* (from Agent 2a)
* Finalized *world description* (from Agent 2b)

**Process:**
Composes a ~1000-word cinematic story prompt and calls Gemini.

**Output:**
A **1000-word story**, formatted like real narrative prose.
Displayed at the top of the final page.

---

### **Agent 4 — Storyteller Suite**

Three agents that activate after Agent 3 completes, appearing on the same final page.

#### **Agent 4a.1 — Background Illustrator**

**Model:** Google Gemini (image generation)
**Process:**
1. Helper agent generates a Studio-Ghibli-style visual prompt for the *world background* (landscape, atmosphere, no character)
2. Gemini image model generates the background image

**Output:** A cinematic background image (~1024×768)

#### **Agent 4a.2 — Hero Scene Illustrator**

**Model:** Google Gemini (image generation)
**Process:**
1. Helper agent generates a visual prompt for a *dramatic scene with the hero in action* (with copyright guardrails)
2. Gemini image model generates the scene illustration

**Output:** A cinematic hero illustration (~1024×768)

#### **Agent 4b — Audio BGM Generator**

**Model:** ElevenLabs (sound generation API) + Gemini (lyrics)
**Process:**
1. Helper agent (Gemini) generates short, poetic lyrics (~50–80 words) about the hero's adventure
2. ElevenLabs `sound-generation` endpoint creates a **30-second BGM** with the lyrics, styled to match the world's vibe

**Output:** A downloadable **MP3 file** (~30 seconds of epic, whimsical music with lyrics)

#### **Agent 4c — Real-Life Reflection**

**Model:** Google Gemini
**Process:**
Reads the full story and infers the user's personality, suggesting how they can find their own "adventures" in real life.

**Output:** A personalized, inspiring message connecting the fantasy narrative to real-world growth and mindset.

---

## 🧠 Tech Stack

### Backend

* **Python 3.10+**
* **Flask** web framework
* **google-generativeai** library (Gemini text & image)
* **requests** (for ElevenLabs HTTP calls)

### LLM APIs

* **Google Gemini 2.0 Flash** (text generation & image generation)
* **ElevenLabs Sound Generation API** (music generation)

### Frontend

* HTML / CSS / JavaScript
* Fetch API for AJAX calls
* Animated progress bars during agent transitions
* Gradient text styling for polished UI

---

## 🔐 Environment Variables

Create a `.env` file in the project root:

```bash
GEMINI_API_KEY=your_google_api_key_here
GEMINI_TEXT_MODEL=gemini-2.0-flash
GEMINI_IMAGE_MODEL=gemini-2.0-flash
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
```

See `.env.example` for a template.

---

## 📁 Project Structure

```
hero_imagined/
├── app.py                          # Flask server & all routes
├── requirements.txt                 # Python dependencies
├── .env                            # ← Add your API keys here
├── .env.example                    # Template for .env
│
├── templates/
│   ├── base.html                   # Base template (layout, CSS/JS includes)
│   ├── index.html                  # Agent 1: story detector
│   └── builder.html                # Agents 2a/2b + 3 + 4: character, world, story, images, audio
│
├── static/
│   ├── js/
│   │   └── app.js                  # Client-side logic: fetch calls, progress bars, UI updates
│   │
│   ├── css/
│   │   └── style.css               # Gradient text, columns, progress bar, button styling
│   │
│   ├── images/
│   │   └── builder-bg.png          # ← Place your background image here for builder page
│   │
│   └── output/                     # Generated images, audio files (auto-created)
│
└── README.md
```

---

## 🚀 Installation & Setup

### 1. Clone or navigate to the project

```bash
cd ~/Desktop/GitHub/hero_imagined
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
# Edit .env with your keys:
# GEMINI_API_KEY=...
# ELEVENLABS_API_KEY=...
```

### 5. (Optional) Add a background image

Place your background image at `static/images/builder-bg.png` (or any image path). The CSS will use it as the builder section background.

### 6. Run the Flask server

```bash
python app.py
```

The server will start on `http://localhost:5000`.

---

## 🎯 User Flow

1. **Index Page (Agent 1):** User enters their hero idea (e.g., "woodland elf warrior")
2. **Builder Page (Agents 2a + 2b):** Side-by-side forms for character & world. Progress bar shows generation.
3. **Shared "Done" Button:** Submits both forms and triggers Agent 3
4. **Final Page (Agents 3 + 4):** Displays:
   - Generated story (Agent 3)
   - Background + hero scene illustrations (Agent 4a)
   - Audio player with 30-sec BGM (Agent 4b)
   - Real-world inspiration message (Agent 4c)

---

## 🎨 UI Features

* **Gradient Text:** Titles and subtitles use a polished gradient (`#f6a819` → `#f06d6d` → `#8b5cf6`)
* **Animated Progress Bars:** Smooth transitions as agents run
* **Column Layout:** Character and World builders side-by-side with shared submit button
* **Responsive Design:** Works on desktop browsers
* **Background Image Support:** Builder section can display a custom fantasy background

---

## ⚙️ Configuration

### Model Selection

You can override the default Gemini model by setting environment variables:

```bash
export GEMINI_TEXT_MODEL=gemini-2.0-flash-exp
export GEMINI_IMAGE_MODEL=gemini-2.0-flash-exp
```

### ElevenLabs Audio

The BGM generator uses ElevenLabs' `sound-generation` endpoint. Ensure your API key has access to this feature.

---

## 🔧 Troubleshooting

### "Google API key not found"

Make sure you've set `GEMINI_API_KEY` in your `.env` file or exported it:

```bash
export GEMINI_API_KEY=your_key
```

### Images not generating

Check:
1. Your `GEMINI_API_KEY` is correct and has image generation enabled
2. The `static/output/` directory exists and is writable
3. Check terminal logs for detailed error messages

### Audio file is silent

If ElevenLabs doesn't return audio, check:
1. `ELEVENLABS_API_KEY` is correct
2. Your account has access to sound-generation API
3. Check terminal logs for API error responses

---

## 📚 Resources

* [Google Gemini API Docs](https://ai.google.dev/docs)
* [ElevenLabs API Reference](https://elevenlabs.io/docs/api-reference)
* [Anthropic Claude Docs](https://docs.anthropic.com/)
* [Flask Documentation](https://flask.palletsprojects.com/)

---

## 🌈 Future Enhancements

* **Session persistence:** Save user stories for later revisiting
* **Regeneration:** Re-run individual agents with different parameters
* **Extended mode:** Generate 3000+ word epic stories
* **PDF export:** Polished downloadable story booklets
* **Social sharing:** Share stories with custom URLs
* **Voice selection:** Choose narrator voices for audio

---

## 🧚 Credits & Inspiration

This project celebrates childhood imagination and the timeless appeal of storytelling. It was inspired by:

1. **Personal Milestone:** Achieving a lifelong dream (lightsaber collection since age 9)
2. **Modern Creativity:** The emergence of accessible AI creative tools
3. **Shared Experience:** Everyone has a hero inside them waiting to be told

*Built with love for dreamers, creators, and adventurers of all ages.*
