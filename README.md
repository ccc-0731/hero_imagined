# 🌟 Hero Imaginer & Storyteller

*A multimodal, agentic workflow for crafting your childhood dream hero — then telling, illustrating, and narrating their story.*

Welcome to **DreamHero Studio**, a full agent-powered creative pipeline that guides a user from a spark of imagination → to a fully illustrated cinematic story → to an audio narration → to real-life inspiration.

Built with **Flask**, **Python**, **Google Gemini**, **Anthropic Claude (v0.73.0)**, and **ElevenLabs**, this project combines text, image, and audio generation into one cohesive interactive experience.

---

## ✨ Overview

DreamHero Studio is a web-based system where a user can:

1. Describe the kind of hero they want to become
2. Design the character in depth
3. Build the world
4. Get a ~1000-word illustrated story
5. Receive narrated audio of that story
6. Receive a reflective, real-world message tailored to them

All powered through an **agentic workflow** with clean, modular APIs.

---

## 🚀 Architecture

DreamHero Studio consists of **five main agents**, each running sequentially with intermediate UIs and progress indicators.

### **Agent 1 — Story Detector**

**Model:** Google Gemini API
**Purpose:** Interprets the user’s initial dream-hero prompt.
**Input:** Single text field asking:

> *“What kind of hero do you want to become?”*
> (with examples like *woodland elf*, *cybernetic ranger*, etc.)

**Output:**

* The story’s **genre** (fantasy, sci-fi, etc.)
* A **concise setting summary** derived from the user input

This feeds into Agents 2a and 2b.

---

### **Agent 2 — Question Askers**

Two parallel agents displayed in **left/right columns** on the same page.

#### **Agent 2a — Character Designer**

**Model:** Google Gemini
**Behavior:**
Prompts the user to fill 8–10 fields:

* age
* physical appearance
* personality
* superpowers
* weapons
* fears
* motivation
* etc.
  **Output:** A finalized *character blueprint*.

#### **Agent 2b — World Builder**

**Model:** Google Gemini
**Behavior:**
Asks 3–5 long-form questions to enrich the world:

* mythical plants + creatures (fantasy)
* ancient legends
* technologies (sci-fi)
* major events
* cultural traits

**Output:** A finalized *world description*.

---

### **Agent 3 — Story Crafter**

**Model:** Google Gemini
**Input:**

* Finalized *character description*
* Finalized *world description*

**Output:**
A **1000-word story**, formatted like a real narrative.
Displayed at the top of the final page.

---

### **Agent 4 — Storyteller Suite**

These three agents activate simultaneously after Agent 3 finishes.

#### **Agent 4a — Image Illustrator**

**Model:** Google Gemini (image generation)
**Output:**

* A set of **Studio-Ghibli-styled**, soft, cinematic illustrations
* Guided by the story
* With built-in guardrails to avoid copyrighted aesthetics

#### **Agent 4b — Audio Narrator**

**Model:** ElevenLabs
**Output:**

* A downloadable **MP3 narration** of the entire story

#### **Agent 4c — Real-Life Reflection Agent**

**Model:** Google Gemini
**Output:**
A personalized message connecting the fantasy story to the user’s real-world aspirations — like a gentle mentor showing what “adventure” means in real life.

---

## 🧠 Tech Stack

### Core Framework

* **Python 3.10+**
* **Flask** web server

### LLM APIs

* **Google Gemini**
* **Anthropic Claude API v0.73.0** (used for orchestration / agent logic)

### Audio API

* **ElevenLabs**

### Frontend

* HTML / CSS / JS
* Buttons trigger AJAX fetch calls
* Each agent transition displays a **smooth progress bar** until output loads

---

## 🔐 Environment Variables

Create a `.env` file (or use system env vars):

```
GEMINI_API_KEY=your_key
CLAUDE_API_KEY=your_key
ELEVENLABS_API_KEY=your_key

# You can optionally configure which model each agent uses:
MODEL_STORY_DETECTOR=gemini-pro
MODEL_CHARACTER_DESIGNER=gemini-pro
MODEL_WORLD_BUILDER=gemini-pro
MODEL_STORY_CRAFTER=gemini-pro
MODEL_IMAGE_GEN=gemini-pro-vision
MODEL_ANALYSIS=gemini-pro

# Claude agent orchestration
CLAUDE_MODEL=claude-3-sonnet-20240229
```

---

## 📁 Project Structure

```
dreamhero/
│
├── app.py                # Flask server + route definitions
├── agents/
│   ├── agent1_detector.py
│   ├── agent2_character.py
│   ├── agent2_world.py
│   ├── agent3_story.py
│   ├── agent4_images.py
│   ├── agent4_audio.py
│   ├── agent4_reflection.py
│   └── orchestrator.py   # Claude v0.73.0 used for workflow logic
│
├── static/
│   ├── progress.js
│   ├── styles.css
│   └── ghibli_filters.css
│
├── templates/
│   ├── index.html
│   ├── character_world.html
│   └── final_story.html
│
└── README.md
```

---

## 🔧 Running Locally

Make sure your virtual environment is activated, then:

```bash
pip install -r requirements.txt
flask run --host=0.0.0.0 --port=5000
```

Visit:

```
http://localhost:5000
```

---

## 🪄 User Flow

1. **User inputs their dream hero prompt**
2. **Agent 1** classifies genre + setting
3. Page transitions (with progress bar)
4. **Agents 2a + 2b** ask creativity-boosting questions
5. User submits → progress bar
6. **Agent 3** crafts story
7. **Agents 4a–c** generate illustrations, MP3, and reflective message
8. Everything presented on one beautiful final page

---

## 🌈 Roadmap / Ideas

* Save user sessions for later revisiting
* Let user regenerate illustrations with different moods
* Optional “hardcore mode” that makes the story ~3000 words
* Shareable polished PDF export

---

## 🧚 Credits

Built with love, caffeine, and childhood nostalgia.
Powered by the finest AI tools of our era.
Made to remind people of the small heroic spark they’ve always had.

Let the adventures begin.
