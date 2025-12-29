# 🌟 Hero Imagined

*A multimodal, agentic workflow for crafting your childhood dream superhero — then telling, illustrating, and sharing their story.*

Hero Imagined guides you from a spark of imagination to a fully illustrated, downloadable storybook with an optional short soundtrack and practical, real-world inspiration.

Built with Flask and a set of small, cooperative agents that coordinate Google Gemini (text + image) and ElevenLabs (music), the project combines narrative, cinematic illustrations, and audio into a single interactive experience.

---


## 🔁 Agentic Workflow (high level)

1. Agent 1 — Story Detector
    - Model: Google Gemini (`google.genai`) — detects the user's intent and extracts a concise setting/genre from a single prompt describing the kind of hero they want to become.

2. Agents 2 — Interactive Questioning
    - Two parallel agents (displayed side-by-side): Character Designer and World Builder.
    - Character Designer collects attributes (age, appearance, superpower, quirks, backstory, etc.) and produces a character blueprint.
    - World Builder asks long-form questions about the setting (creatures/tech, history/myth, notable figures, mechanics of magic/technology) and produces a world description.

3. Agent 3 — Story Crafter
    - Takes the finalized character blueprint and world description and composes a cinematic ~1000-word story using Google Gemini.

4. Agent 4 — Storyteller Suite (post-story)
    - 4a — Hero Scene Illustrator
       - Generates a cinematic hero action scene (the hero in-frame). Output is `images[0]`.
    - 4a — Background Illustrator
       - Generates a landscape/mood background image (no character). Output is `images[1]`.
    - 4b — Audio BGM Generator (optional)
       - Gemini writes short lyrics; ElevenLabs (sound-generation) produces a ~60s BGM. Downloadable MP3 is provided.
    - 4c — Real-Life Reflection
       - Gemini analyzes the story and suggests real-world steps and inspiration; shown in a separate "In Real Life" panel.

---

## 🧭 User Flow / UI

- Index page: user types a short hero idea (Agent 1 runs).
- Builder page: two columns with the Character and World forms. A shared "Done" button submits both, triggering Agent 3 (story) and the Storyteller Suite (images + audio).
- Final page: shows story text, two generated images (background shown as UI background; hero scene shown in content), an audio player (if generated), and a separate "In Real Life" panel.
- Download: the user can download a multi-page PDF of the story. The PDF uses the world background as the translucent page background (25% opacity) and includes the hero scene illustration inline.

---

## 🧩 Tech Stack & Dependencies

- Python 3.10+
- Flask
- `google.genai` (Google Gemini for text + image)
- `requests`
- `reportlab` (PDF generation)
- `Pillow` (PIL) for image processing and opacity handling
- ElevenLabs SDK / HTTP API (optional audio generation)

Ensure `reportlab` and `Pillow` are listed in `requirements.txt`.

---

## 🔐 Environment variables

Create a `.env` file at project root and add your keys:

```bash
GEMINI_API_KEY=your_google_api_key_here
GEMINI_TEXT_MODEL=gemini-2.5-flash
GEMINI_IMAGE_MODEL=gemini-2.5-flash-image
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
```

---

## 📁 Project structure (overview)

```
hero_imagined/
├── app.py                # Flask server + routes implementing agents and PDF export
├── requirements.txt      # Python dependencies
├── .env                  # API keys (local)
├── templates/            # Html templates (index, builder, final)
└── static/
      ├── js/
      ├── css/
      └── output/          # Generated images & audio files
```

---

## 📌 PDF Generation Notes (Still in progress)

- The server expects generated images in the form `images = [background_url, hero_scene_url]`.
- The PDF generator:
   - Uses the second image (`images[1]`) as the page background and applies a 25% alpha so story text remains readable on top of the art. (Currently not really working)
   - Embeds the hero scene (`images[0]`) inside the PDF as an inline image with its own caption.
   - Falls back gracefully if images are missing (skips background or hero image if not available).

---

## 🚀 Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in your keys
python app.py
```

Open `http://localhost:8000` (or the port printed in the logs) and try the flow.

---

## ✨ Next steps / ideas

- Add login sessions and store data so users can revisit the story page.
- Refine the PDF generation for better readability
- Add a narrator to read the entire story
- Add user end logic to modify prompt for story style alignment

---

## 🧚 Credits & Inspiration

This project celebrates childhood imagination and the timeless appeal of storytelling. It was inspired by:

1. **Personal Milestone:** Achieving the dream of owning a lightsaber since age 9
2. **Modern Creativity:** The emergence of accessible AI creative tools (and CS 1100 homework requirements)
3. **Shared Experience:** Everyone has a hero inside them waiting to be told

*Built with love for dreamers, creators, and adventurers of all ages.*
-- Panda Chu & GitHub Copilot :)
