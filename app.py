import os
import uuid
import base64
import json
from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
import requests

app = Flask(__name__)
app.config['STATIC_OUTPUT'] = os.path.join(app.root_path, 'static', 'output')
os.makedirs(app.config['STATIC_OUTPUT'], exist_ok=True)

# Environment-configured models / keys
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GEMINI_TEXT_MODEL = os.getenv('GEMINI_TEXT_MODEL', 'gemini')
GEMINI_IMAGE_MODEL = os.getenv('GEMINI_IMAGE_MODEL', 'gemini-image')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')

def call_gemini_text(prompt, system=None):
	"""Call Google Gemini text API if configured, otherwise return a mock reply."""
	if not GOOGLE_API_KEY:
		# simple mock: return trimmed prompt with a 'detected' type
		if 'hero' in prompt.lower():
			return {'topic':'fantasy','setting':prompt.strip()}
		return {'topic':'general','setting':prompt.strip()}

	# Real-call placeholder: user should replace with proper Google Generative API usage
	url = 'https://generativeai.googleapis.com/v1beta2/models/{}/generate'.format(GEMINI_TEXT_MODEL)
	headers = {'Authorization': f'Bearer {GOOGLE_API_KEY}', 'Content-Type': 'application/json'}
	body = { 'prompt': { 'text': prompt } }
	resp = requests.post(url, headers=headers, json=body, timeout=30)
	resp.raise_for_status()
	data = resp.json()
	# attempt to extract text
	text = data.get('candidates',[{}])[0].get('output','')
	return {'raw': text}

def call_gemini_image(prompt, filename):
	"""Call Gemini image generation or write a placeholder SVG to the static output and return path."""
	out_path = os.path.join(app.config['STATIC_OUTPUT'], filename)
	if not GOOGLE_API_KEY:
		# Write a cute placeholder SVG (Ghibli-ish feeling prompt is used only for naming)
		svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="768">
  <rect width="100%" height="100%" fill="#f6ecd2"/>
  <text x="50%" y="50%" font-size="36" text-anchor="middle" fill="#6b4f4f">Illustration placeholder</text>
  <text x="50%" y="58%" font-size="20" text-anchor="middle" fill="#6b4f4f">{prompt[:80]}</text>
</svg>'''
		with open(out_path, 'w') as f:
			f.write(svg)
		return out_path

	# Real call placeholder: user must adapt to the actual Google Images API
	url = 'https://generativeai.googleapis.com/v1beta2/images:generate'
	headers = {'Authorization': f'Bearer {GOOGLE_API_KEY}', 'Content-Type': 'application/json'}
	body = {'prompt': prompt, 'model': GEMINI_IMAGE_MODEL, 'size':'1024x1024'}
	resp = requests.post(url, headers=headers, json=body, timeout=60)
	resp.raise_for_status()
	data = resp.json()
	# Expect base64-encoded image(s)
	b64 = data.get('data',[{}])[0].get('b64_encoded_image')
	if not b64:
		raise RuntimeError('No image returned from Gemini')
	with open(out_path, 'wb') as f:
		f.write(base64.b64decode(b64))
	return out_path

SILENT_MP3_B64 = (
	# 1-second silent mp3, tiny base64 payload used as fallback when ElevenLabs is not configured
	"SUQzAwAAAAAA/////wAAACwAAAAAAABdAAABAAAACwAAAAAA"
)

def generate_audio_from_text(text, filename):
	out_path = os.path.join(app.config['STATIC_OUTPUT'], filename)
	if ELEVENLABS_API_KEY:
		# Placeholder for real ElevenLabs API call
		url = 'https://api.elevenlabs.io/v1/text-to-speech/default'
		headers = {'xi-api-key': ELEVENLABS_API_KEY, 'Content-Type': 'application/json'}
		body = {'text': text}
		resp = requests.post(url, headers=headers, json=body, stream=True, timeout=60)
		if resp.status_code == 200:
			with open(out_path, 'wb') as f:
				for chunk in resp.iter_content(1024):
					f.write(chunk)
			return out_path
		else:
			# fall back to silent mp3 if ElevenLabs fails
			pass

	# write the silent mp3 fallback
	try:
		data = base64.b64decode(SILENT_MP3_B64 + '==')
		with open(out_path, 'wb') as f:
			f.write(data)
	except Exception:
		# as a last resort, create a tiny text file to indicate missing audio
		with open(out_path, 'wb') as f:
			f.write(b'')
	return out_path


@app.route('/')
def index():
	return render_template('index.html')


@app.route('/builder', methods=['POST'])
def builder():
	# Agent 1: Story Detector
	user_prompt = request.form.get('hero_prompt','').strip()
	guiding = "What kind of hero do you want to become?"
	combined = f"{guiding}\nUser: {user_prompt}"
	detected = call_gemini_text(combined)
	return render_template('builder.html', detected=detected, raw_prompt=user_prompt)


@app.route('/api/character', methods=['POST'])
def api_character():
	data = request.json or {}
	answers = data.get('answers', {})
	# Compose a prompt for Gemini
	prompt = 'Create a complete character profile using these traits:\n'
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
	prompt = f"Write an engaging ~1000-word short story about this hero. Character:\n{character}\nWorld:\n{world}\nStyle: cinematic, slightly whimsical, family-friendly."
	resp = call_gemini_text(prompt)
	story = resp.get('raw') or json.dumps(resp)

	# Generate 3 illustrations
	images = []
	for i in range(3):
		fname = f"illustration_{uuid.uuid4().hex[:8]}.svg" if not GOOGLE_API_KEY else f"illustration_{uuid.uuid4().hex[:8]}.png"
		img_path = call_gemini_image(f"Studio Ghibli style, cinematic, {story[:200]}", fname)
		images.append(url_for('static', filename=f'output/{os.path.basename(img_path)}'))

	# Generate audio (mp3)
	audio_file = f"story_{uuid.uuid4().hex[:8]}.mp3"
	audio_path = generate_audio_from_text(story, audio_file)
	audio_url = url_for('static', filename=f'output/{os.path.basename(audio_path)}')

	# Real-life analogy via Gemini
	analogy_prompt = f"Infer the user's personality from this story and suggest real-life parallels and steps for them to embark on their own adventures:\n{story}"
	analogy_resp = call_gemini_text(analogy_prompt)
	analogy = analogy_resp.get('raw') or json.dumps(analogy_resp)

	return jsonify({'story': story, 'images': images, 'audio': audio_url, 'analogy': analogy})


if __name__ == '__main__':
	app.run(port=8001, debug=True)
