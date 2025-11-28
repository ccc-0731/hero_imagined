import os
import uuid
import base64
import json
from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

app = Flask(__name__)
app.config['STATIC_OUTPUT'] = os.path.join(app.root_path, 'static', 'output')
os.makedirs(app.config['STATIC_OUTPUT'], exist_ok=True)

# Environment-configured models / keys
GOOGLE_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_TEXT_MODEL = os.getenv('GEMINI_TEXT_MODEL', 'gemini-2.5-flash')
GEMINI_IMAGE_MODEL = os.getenv('GEMINI_IMAGE_MODEL', "gemini-2.5-flash-image")
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')

def call_gemini_text(prompt, system=None):
	"""Call Google Gemini text API via google.genai library."""
	try:
		client = genai.Client(api_key=GOOGLE_API_KEY)
		response = client.models.generate_content(
			model=GEMINI_TEXT_MODEL,
			contents=prompt
		)
		text = response.text if response else ''
		return {'raw': text}
	except Exception as e:
		print(f'Gemini text error: {e}')
		return {'raw': f'Error: {str(e)}'}


def call_gemini_image(prompt, filename):
    """Call Gemini image generation via google.genai library."""
    out_path = os.path.join(app.config['STATIC_OUTPUT'], filename)
    try:
        client = genai.Client(api_key=GOOGLE_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_IMAGE_MODEL,
            contents=[prompt]
        )

        # --- FIXED IMAGE EXTRACTION (matches official docs) ---
        image_obj = None
        for part in response.parts:
            if part.inline_data is not None:
                image_obj = part.as_image()
                break  # first image only

        if image_obj is None:
            raise ValueError("No image returned from Gemini.")

        # Save it
        image_obj.save(out_path)

        return out_path

    except Exception as e:
        print(f"Gemini image error: {e}")
        raise

def generate_bgm_instrumental(world_description, character_description, hero_name, filename):
    """
    Generate ~30 seconds of instrumental background music using ElevenLabs.
    Music is based on the worldbuilding and tone of the story.
    """
    out_path = os.path.join(app.config['STATIC_OUTPUT'], filename)

    try:
        # ---- Build a musical style prompt -------------------------------
        # No lyrics! Instrument-only. Just an atmospheric vibe prompt.
        music_prompt = (
            f"Instrumental cinematic fantasy theme for a hero named {hero_name}. "
            f"World: {world_description}. "
			f"Character: {character_description}. "
            f"Tone: emotional, adventurous, atmospheric, warm, slightly whimsical. "
            f"Focus on orchestral textures, light percussion, gentle strings."
        )

        # ---- ElevenLabs compose endpoint --------------------------------
        url = "https://api.elevenlabs.io/v1/music"
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }

        body = {
            # Use the correct field names from ElevenLabs docs
            "prompt": music_prompt,          # You can’t use both "prompt" + "text"
            "music_length_ms": 30000,        # 30 seconds in ms
            "output_format": "mp3_44100_128",
            "force_instrumental": True       # Ensures no vocals
        }

        # ---- POST request (stream audio chunks) -------------------------
        resp = requests.post(url, headers=headers, json=body, stream=True, timeout=90)

        if resp.status_code == 200:
            with open(out_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return out_path, ""
        else:
            raise RuntimeError(f"ElevenLabs error {resp.status_code}: {resp.text}")

    except Exception as e:
        print(f"BGM generation error: {e}")
        raise



@app.route('/')
def index():
	return render_template('index.html')


@app.route('/builder', methods=['POST'])
def builder():
	# Agent 1: Story Detector
	user_prompt = request.form.get('hero_prompt','').strip()
	guiding = "Infer the general type of fiction setting (e.g., fantasy, sci-fi, steampunk, etc.) from this user prompt. Respond with only the genre name."
	combined = f"{guiding}\nUser: {user_prompt}"
	detected_resp = call_gemini_text(combined)
	detected_topic = detected_resp.get('raw', '').strip() or 'fantasy'
	detected = {'topic': detected_topic}
	return render_template('builder.html', detected=detected, raw_prompt=user_prompt)


@app.route('/api/generate-questions', methods=['POST'])
def api_generate_questions():
	"""Generate dynamic character and world building questions based on user prompt and detected genre."""
	data = request.json or {}
	user_prompt = data.get('user_prompt', '')
	detected_topic = data.get('detected_topic', 'fantasy')
	
	# Generate character questions
	char_q_prompt = f"""Based on the user wanting to create a hero described as: "{user_prompt}"
In a {detected_topic} setting, generate 8-10 basic and generic questions to help design a character. The questions should be no longer than a sentence, and the answer is expected to be very brief.
For each question, provide:
1. The question (numbered)
2. An inspirational example answer in parenthesis, (e.g. like this, including the).

Format as a JSON object like: {{"questions": [{{"number": 1, "question": "...", "example": "..."}}]}}
Make questions cover: age, gender, appearance, powers, personality, fears, goals, quirks, backstory, etc.

IMPORTANT: Return ONLY valid JSON, no additional text before or after."""
	
	char_resp = call_gemini_text(char_q_prompt)
	char_questions = []
	try:
		raw_text = char_resp.get('raw', '').strip()
		print(f"[DEBUG] Raw character response: {raw_text[:200]}")
		
		# Try to extract JSON from the response
		import re
		json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
		if json_match:
			json_str = json_match.group(0)
			char_data = json.loads(json_str)
			char_questions = char_data.get('questions', [])
			print(f"[DEBUG] Parsed {len(char_questions)} character questions")
		else:
			print("[ERROR] No JSON found in character response")
	except Exception as e:
		print(f"[ERROR] Failed to parse character questions: {e}")
	
	# Generate world building questions
	world_q_prompt = f"""Based on a {detected_topic} world for the hero: "{user_prompt}"
Generate exactly 4-5 simple and generic world-building questions. The questions and expected answers should be no longer than a sentence.
For each question, provide:
1. The question (numbered)
2. An inspirational example answer in parenthesis, (e.g. like this, including the e.g.). 

Format as JSON like: {{"questions": [{{"number": 1, "question": "...", "example": "..."}}]}}
Make questions cover: mythology, creatures, history, magic/tech, culture, landmarks, etc.

IMPORTANT: Return ONLY valid JSON, no additional text before or after."""
	
	world_resp = call_gemini_text(world_q_prompt)
	world_questions = []
	try:
		raw_text = world_resp.get('raw', '').strip()
		print(f"[DEBUG] Raw world response: {raw_text[:200]}")
		
		# Try to extract JSON from the response
		import re
		json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
		if json_match:
			json_str = json_match.group(0)
			world_data = json.loads(json_str)
			world_questions = world_data.get('questions', [])
			print(f"[DEBUG] Parsed {len(world_questions)} world questions")
		else:
			print("[ERROR] No JSON found in world response")
	except Exception as e:
		print(f"[ERROR] Failed to parse world questions: {e}")
	
	print(f"[DEBUG] Final response: char={len(char_questions)}, world={len(world_questions)}")
	return jsonify({
		'character_questions': char_questions,
		'world_questions': world_questions
	})


@app.route('/api/character', methods=['POST'])
def api_character():
	data = request.json or {}
	answers = data.get('answers', {})
	# Compose a prompt for Gemini
	prompt = 'Create a paragraph describing a complete character profile using these traits, including giving the character a suitable name:\n'
	for k,v in answers.items():
		prompt += f"{k}: {v}\n"
	resp = call_gemini_text(prompt)
	# If Gemini returned a raw string, use it; otherwise serialize
	character_text = resp.get('raw') or json.dumps(resp)
	return jsonify({'character': character_text})


@app.route('/api/world', methods=['POST'])
def api_world():
	data = request.json or {}
	answers = data.get('answers', {})
	detected = data.get('detected', {})
	prompt = 'Based on the world type: ' + str(detected.get('topic','unknown')) + ', give the world a name and create a paragraph describe the setting of this world:\n'
	for k,v in answers.items():
		prompt += f"{k}: {v}\n"
	resp = call_gemini_text(prompt)
	world_text = resp.get('raw') or json.dumps(resp)
	return jsonify({'world': world_text})


@app.route('/generate_story', methods=['POST'])
def generate_story():
	data = request.json or {}
	character = data.get('character','')
	world = data.get('world','')
	
	result = {
		'story': None,
		'images': [],
		'audio': None,
		'analogy': None,
		'error': None
	}
	
	# ============================================
	# Step 1: Generate Story (CRITICAL - must succeed)
	# ============================================
	try:
		prompt = f"Write an engaging ~1000-word short story about an adventure of this hero in the world. The story should be thought-provoking and demonstrate deep philosophical ideas tied to the human condition. Character:\n{character}\nWorld:\n{world}\nStyle: cinematic, slightly whimsical."
		resp = call_gemini_text(prompt)
		story = resp.get('raw') or json.dumps(resp)
		result['story'] = story
		print("[SUCCESS] Story generated")
	except Exception as e:
		print(f"[CRITICAL ERROR] Story generation failed: {e}")
		result['error'] = f"Story generation failed: {str(e)}"
		return jsonify(result), 500
	
	# ============================================
	# Step 2: Extract Hero Name (Optional)
	# ============================================
	hero_name = 'the hero'
	try:
		name_resp = call_gemini_text(f"Extract just the character's name from this description: {character}. Output only the name, nothing else.")
		hero_name = name_resp.get('raw', '').strip() or 'the hero'
		print(f"[SUCCESS] Hero name extracted: {hero_name}")
	except Exception as e:
		print(f"[WARNING] Hero name extraction failed: {e}, using default")
		hero_name = 'the hero'
	
	# ============================================
	# Step 3: Generate Background Image Prompt (Optional)
	# ============================================
	bg_img_url = None
	try:
		bg_prompt_req = f"Generate a detailed visual description prompt for a Studio Ghibli-style fantasy world background. The prompt should describe the landscape, atmosphere, and environment based on this world description: {world}. Include details about colors, mood, and cinematic quality. Do not mention the character. Output only the visual prompt, no other text."
		bg_prompt_resp = call_gemini_text(bg_prompt_req)
		bg_prompt = bg_prompt_resp.get('raw', '').strip()
		
		# Step 3b: Generate background illustration (only if prompt was generated)
		if bg_prompt:
			bg_fname = f"background_{uuid.uuid4().hex[:8]}.png"
			bg_img_path = call_gemini_image(bg_prompt, bg_fname)
			bg_img_url = url_for('static', filename=f'output/{os.path.basename(bg_img_path)}')
			result['images'].append(bg_img_url)
			print("[SUCCESS] Background image generated")
		else:
			print("[WARNING] Background image prompt generation returned empty")
	except Exception as e:
		print(f"[WARNING] Background image generation failed: {e}, continuing without it")
	
	# ============================================
	# Step 4: Generate Hero Scene Image Prompt (Optional)
	# ============================================
	try:
		hero_prompt_req = f"Generate a detailed visual description prompt for a Studio Ghibli-style cinematic scene illustration. The prompt should depict a dramatic moment of the hero in action, showing their unique features and abilities in the fantasy world. Include copyright-safe descriptions and emphasize artistic style over specific references. Character: {character}. Story excerpt: {story[:300]}. Output only the visual prompt, no other text."
		hero_prompt_resp = call_gemini_text(hero_prompt_req)
		hero_prompt = hero_prompt_resp.get('raw', '').strip()
		
		# Step 4b: Generate hero scene illustration (only if prompt was generated)
		if hero_prompt:
			hero_fname = f"hero_scene_{uuid.uuid4().hex[:8]}.png"
			hero_img_path = call_gemini_image(hero_prompt, hero_fname)
			hero_img_url = url_for('static', filename=f'output/{os.path.basename(hero_img_path)}')
			result['images'].insert(0, hero_img_url)
			print("[SUCCESS] Hero scene image generated")
		else:
			print("[WARNING] Hero scene image prompt generation returned empty")
	except Exception as e:
		print(f"[WARNING] Hero scene image generation failed: {e}, continuing without it")
	
	# ============================================
	# Step 5: Generate BGM (Optional)
	# ============================================
	try:
		audio_file = f"bgm_{uuid.uuid4().hex[:8]}.mp3"
		audio_path, lyrics = generate_bgm_instrumental(world[:100], character[:100], hero_name, audio_file)
		audio_url = url_for('static', filename=f'output/{os.path.basename(audio_path)}')
		result['audio'] = audio_url
		print("[SUCCESS] BGM generated")
	except Exception as e:
		print(f"[WARNING] BGM generation failed: {e}, continuing without it")
		result['audio'] = None
	
	# ============================================
	# Step 6: Generate Real-life Analogy (Optional)
	# ============================================
	try:
		analogy_prompt = f"You are a thoughtful mentor speaking directly to the user. Infer the user's personality from this hero story (where the user is the main character) and suggest how they can embark on meaningful 'adventures' of their own in real life. Keep it inspiring and practical:\n{story}"
		analogy_resp = call_gemini_text(analogy_prompt)
		analogy = analogy_resp.get('raw') or json.dumps(analogy_resp)
		result['analogy'] = analogy
		print("[SUCCESS] Analogy generated")
	except Exception as e:
		print(f"[WARNING] Analogy generation failed: {e}, continuing without it")
		result['analogy'] = None
	
	return jsonify(result)


if __name__ == '__main__':
	app.run(port=8000, debug=True)
