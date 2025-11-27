import os
import uuid
import base64
import json
from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

load_dotenv()

app = Flask(__name__)
app.config['STATIC_OUTPUT'] = os.path.join(app.root_path, 'static', 'output')
os.makedirs(app.config['STATIC_OUTPUT'], exist_ok=True)

# Environment-configured models / keys
GOOGLE_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_TEXT_MODEL = os.getenv('GEMINI_TEXT_MODEL', 'gemini-2.0-flash')
GEMINI_IMAGE_MODEL = os.getenv('GEMINI_IMAGE_MODEL', 'gemini-2.0-flash')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')

def call_gemini_text(prompt, system=None):
	"""Call Google Gemini text API via google.generativeai library."""
	try:
		import google.generativeai as genai
		genai.configure(api_key=GOOGLE_API_KEY)
		model = genai.GenerativeModel(GEMINI_TEXT_MODEL)
		response = model.generate_content(prompt)
		text = response.text if response else ''
		return {'raw': text}
	except Exception as e:
		print(f'Gemini text error: {e}')
		return {'raw': f'Error: {str(e)}'}

def call_gemini_image(prompt, filename):
	"""Call Gemini image generation via google.generativeai library."""
	out_path = os.path.join(app.config['STATIC_OUTPUT'], filename)
	try:
		client = genai.Client()
		genai.configure(api_key=GOOGLE_API_KEY)
		model = genai.GenerativeModel(GEMINI_IMAGE_MODEL)
		response = client.models.generate_content(
			model=GEMINI_IMAGE_MODEL,
			contents=[prompt],
			number_of_images=1,
			width=1024,
			height=768
		)
		if response and response.images:
			img = response.images[0]
			with open(out_path, 'wb') as f:
				f.write(img.data)
			return out_path
		else:
			raise RuntimeError('No image returned from Gemini')
	except Exception as e:
		print(f'Gemini image error: {e}')
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
            return out_path
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
	In a {detected_topic} setting, generate exactly 8-10 specific, creative questions to help design a character. 
	For each question, provide:
	1. The question (numbered)
	2. An inspirational example answer in brackets [like this]
	
	Format as a JSON object like: {{"questions": [{{"number": 1, "question": "...", "example": "..."}}]}}
	Make questions cover: age, appearance, powers, personality, fears, goals, quirks, backstory, etc."""
	
	char_resp = call_gemini_text(char_q_prompt)
	try:
		char_data = json.loads(char_resp.get('raw', '{}'))
		char_questions = char_data.get('questions', [])
	except:
		char_questions = []
	
	# Generate world building questions
	world_q_prompt = f"""Based on a {detected_topic} world for the hero: "{user_prompt}"
	Generate exactly 4-5 deep, world-building questions to flesh out the setting.
	For each question, provide:
	1. The question (numbered)
	2. An inspirational example answer in brackets [like this]
	
	Format as JSON like: {{"questions": [{{"number": 1, "question": "...", "example": "..."}}]}}
	Make questions cover: mythology, creatures, history, magic/tech, culture, landmarks, etc."""
	
	world_resp = call_gemini_text(world_q_prompt)
	try:
		world_data = json.loads(world_resp.get('raw', '{}'))
		world_questions = world_data.get('questions', [])
	except:
		world_questions = []
	
	return jsonify({
		'character_questions': char_questions,
		'world_questions': world_questions
	})


@app.route('/api/character', methods=['POST'])
def api_character():
	data = request.json or {}
	answers = data.get('answers', {})
	# Compose a prompt for Gemini
	prompt = 'Create a paragraph describing a complete character profile using these traits:\n'
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
	prompt = 'Based on the world type: ' + str(detected.get('topic','unknown')) + '\n'
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
	
	# Agent 3: Story Crafter
	prompt = f"Write an engaging ~1000-word short story about an adventure of this hero in the world. The story should be thought-provoking and demonstrate deep philosophical ideas tied to the human condition. Character:\n{character}\nWorld:\n{world}\nStyle: cinematic, slightly whimsical."
	resp = call_gemini_text(prompt)
	story = resp.get('raw') or json.dumps(resp)
	
	# Agent 4a.1: Generate background illustration prompt (world-focused, no character)
	bg_prompt_req = f"Generate a detailed visual description prompt for a Studio Ghibli-style fantasy world background. The prompt should describe the landscape, atmosphere, and environment based on this world description: {world}. Include details about colors, mood, and cinematic quality. Do not mention the character. Output only the visual prompt, no other text."
	bg_prompt_resp = call_gemini_text(bg_prompt_req)
	bg_prompt = bg_prompt_resp.get('raw', '').strip()
	
	# Agent 4a.1: Generate background illustration
	if bg_prompt:
		bg_fname = f"background_{uuid.uuid4().hex[:8]}.png"
		bg_img_path = call_gemini_image(bg_prompt, bg_fname)
		bg_img_url = url_for('static', filename=f'output/{os.path.basename(bg_img_path)}')
	else:
		bg_img_url = None
	
	# Agent 4a.2: Generate hero scene illustration prompt
	hero_prompt_req = f"Generate a detailed visual description prompt for a Studio Ghibli-style cinematic scene illustration. The prompt should depict a dramatic moment of the hero in action, showing their unique features and abilities in the fantasy world. Include copyright-safe descriptions and emphasize artistic style over specific references. Character: {character}. Story excerpt: {story[:300]}. Output only the visual prompt, no other text."
	hero_prompt_resp = call_gemini_text(hero_prompt_req)
	hero_prompt = hero_prompt_resp.get('raw', '').strip()
	
	# Agent 4a.2: Generate hero scene illustration
	images = []
	if hero_prompt:
		hero_fname = f"hero_scene_{uuid.uuid4().hex[:8]}.png"
		hero_img_path = call_gemini_image(hero_prompt, hero_fname)
		hero_img_url = url_for('static', filename=f'output/{os.path.basename(hero_img_path)}')
		images.append(hero_img_url)
	if bg_img_url:
		images.insert(0, bg_img_url)
	
	# Agent 4b: Generate BGM with lyrics (~30 seconds)
	# Extract hero name from character description for personalization
	hero_name = 'the hero'
	try:
		name_resp = call_gemini_text(f"Extract just the character's name from this description: {character}. Output only the name, nothing else.")
		hero_name = name_resp.get('raw', '').strip() or 'the hero'
	except:
		pass
	
	audio_file = f"bgm_{uuid.uuid4().hex[:8]}.mp3"
	audio_path, lyrics = generate_bgm_instrumental(world[:100], character[:100], hero_name, audio_file)
	audio_url = url_for('static', filename=f'output/{os.path.basename(audio_path)}')
	lyrics = ""

	# Agent 4c: Real-life analogy via Gemini
	analogy_prompt = f"You are a thoughtful mentor speaking directly to the user. Infer the user's personality from this hero story (where the user is the main character) and suggest how they can embark on meaningful 'adventures' of their own in real life. Keep it inspiring and practical:\n{story}"
	analogy_resp = call_gemini_text(analogy_prompt)
	analogy = analogy_resp.get('raw') or json.dumps(analogy_resp)

	return jsonify({'story': story, 'images': images, 'audio': audio_url, 'analogy': analogy, 'lyrics': lyrics})


if __name__ == '__main__':
	app.run(port=8001, debug=True)
