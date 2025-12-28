import os
import uuid
import base64
import json
import concurrent.futures
import markdown as md
from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.utils import ImageReader
from io import BytesIO
from PIL import Image as PILImage

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
            "music_length_ms": 60000,        # 60 seconds in ms
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


# ----------------------
# Helpers for agent workflow
# ----------------------
def run_with_timeout(fn, *args, timeout=60, **kwargs):
	"""Run function in a separate thread and raise TimeoutError if it exceeds timeout seconds."""
	with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
		future = ex.submit(fn, *args, **kwargs)
		try:
			return future.result(timeout=timeout)
		except concurrent.futures.TimeoutError:
			raise TimeoutError(f"{fn.__name__} timed out after {timeout} seconds")
		except Exception:
			# Re-raise underlying exception for caller to handle
			raise


def generate_story_text(character, world, timeout=60):
	prompt = (
		"Write an engaging ~600-word short story about an adventure of this hero in the world."
		" Use cinematic, slightly whimsical style. Focus on deep philosophical ideas tied to the human condition."
		" Respond in Markdown. Use bold and italics if necessary, but don't overuse subheadings (the story shouldn't have them)."
		f"\n\nCharacter:\n{character}\n\nWorld:\n{world}\n"
	)
	def _call():
		resp = call_gemini_text(prompt)
		return resp.get('raw', '')
	return run_with_timeout(_call, timeout=timeout)


def extract_hero_name(character, timeout=30):
	def _call():
		resp = call_gemini_text(f"Extract just the character's name from this description: {character}. Output only the name, nothing else.")
		return resp.get('raw', '').strip()
	try:
		return run_with_timeout(_call, timeout=timeout)
	except Exception:
		return ''


def generate_visual_prompt_and_image(world_text, prefix, timeout=40):
	"""Return (prompt_text, image_url_or_None)."""
	try:
		prompt_req = (
			f"Generate a detailed visual description prompt for a Studio Ghibli-style fantasy background."
			f" Describe landscape, atmosphere, colors, mood and cinematic quality based on: {world_text}."
			" Output only the visual prompt in one paragraph."
		)
		def _gen_prompt():
			resp = call_gemini_text(prompt_req)
			return resp.get('raw', '').strip()

		visual_prompt = run_with_timeout(_gen_prompt, timeout=timeout)
		if not visual_prompt:
			return None, None

		fname = f"{prefix}_{uuid.uuid4().hex[:8]}.png"
		# generate image (may raise)
		img_path = run_with_timeout(lambda: call_gemini_image(visual_prompt, fname), timeout=60)
		img_url = url_for('static', filename=f'output/{os.path.basename(img_path)}')
		return visual_prompt, img_url
	except Exception as e:
		print(f"[WARNING] Visual generation failed: {e}")
		return None, None


def generate_hero_scene_and_image(character, story_excerpt, timeout=60):
	try:
		prompt_req = (
			f"Generate a detailed visual description prompt for a Studio Ghibli-style cinematic scene illustration."
			f" Depict a dramatic moment of the hero in action, showing unique features and abilities."
			f" Character: {character}. Story excerpt: {story_excerpt}. Output only the visual prompt."
		)
		def _gen():
			resp = call_gemini_text(prompt_req)
			return resp.get('raw', '').strip()

		hero_prompt = run_with_timeout(_gen, timeout=timeout)
		if not hero_prompt:
			return None, None
		fname = f"hero_scene_{uuid.uuid4().hex[:8]}.png"
		img_path = run_with_timeout(lambda: call_gemini_image(hero_prompt, fname), timeout=60)
		img_url = url_for('static', filename=f'output/{os.path.basename(img_path)}')
		return hero_prompt, img_url
	except Exception as e:
		print(f"[WARNING] Hero scene generation failed: {e}")
		return None, None


def generate_bgm_wrapper(world_description, character_description, hero_name, filename, timeout=60):
	try:
		return run_with_timeout(lambda: generate_bgm_instrumental(world_description, character_description, hero_name, filename), timeout=timeout)
	except Exception as e:
		raise


def generate_analogy_text(hero_name, story, timeout=60):
	prompt = (
		"Extract the central theme of this hero story. Then speak directly to the person who imagined this hero (the creator)."
		" Suggest how this story's theme and the hero's journey can inspire them to embark on meaningful 'adventures' in real life."
		" Be specific about life lessons and practical ways to embody the hero's spirit."
		" Respond in Markdown. Use headings and bullet points where helpful."
		f"\n\nHero name: {hero_name}\nStory:\n{story}"
	)
	def _call():
		resp = call_gemini_text(prompt)
		return resp.get('raw', '')
	try:
		return run_with_timeout(_call, timeout=timeout)
	except Exception as e:
		print(f"[WARNING] Analogy generation error: {e}")
		return ''



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
In a {detected_topic} setting, generate 4-5 basic and generic questions to help design a character. The questions should be no longer than a sentence, and the answer is expected to be very brief.
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
Generate exactly 2-3 simple and generic world-building questions. The questions and expected answers should be no longer than a sentence.
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
	character = data.get('character', '')
	world = data.get('world', '')

	result = {
		'story': None,
		'images': [],
		'audio': None,
		'analogy': None,
		'error': None
	}

	# Step 1: Generate Story (must succeed)
	try:
		story_md = generate_story_text(character, world, timeout=60)
		if not story_md:
			raise RuntimeError('Empty story from model')
		result['story'] = story_md
		print("[SUCCESS] Story generated (markdown)")
	except Exception as e:
		print(f"[CRITICAL ERROR] Story generation failed: {e}")
		result['error'] = f"Story generation failed: {str(e)}"
		return jsonify(result), 500

	# Step 2: Extract Hero Name
	hero_name = extract_hero_name(character) or 'the hero'
	if hero_name:
		print(f"[INFO] Hero name extracted: {hero_name}")
	else:
		print("[INFO] Using default hero name")

	# Note: Image and BGM generation moved to dedicated endpoints to reduce memory
	# and allow the frontend to request them separately. They will be performed
	# after returning the core story payload.

	# Step 6: Real-life analogy (optional, produce Markdown)
	try:
		analogy_md = generate_analogy_text(hero_name, result['story'], timeout=30)
		result['analogy'] = analogy_md
		if analogy_md:
			print("[SUCCESS] Analogy generated (markdown)")
		else:
			print("[INFO] Analogy generation returned empty")
	except Exception as e:
		print(f"[WARNING] Analogy generation failed: {e}")
		result['analogy'] = None

	# Add progress tracking info
	# Mark heavy tasks as pending so the frontend can request them individually
	result['steps'] = [
		{'name': 'Story Generation', 'status': 'complete'},
		{'name': 'Hero Name Extraction', 'status': 'complete'},
		{'name': 'Background Image', 'status': 'pending'},
		{'name': 'Hero Scene Image', 'status': 'pending'},
		{'name': 'Background Music', 'status': 'pending'},
		{'name': 'Real-life Inspiration', 'status': 'complete' if result['analogy'] else 'skipped'}
	]
	result['character'] = character
	result['world'] = world
	result['hero_name'] = hero_name

	# Convert Markdown to HTML for client rendering
	try:
		result['story_html'] = md.markdown(result['story'] or '', extensions=['fenced_code', 'tables', 'nl2br'])
	except Exception:
		result['story_html'] = '<pre>' + (result['story'] or '') + '</pre>'

	try:
		result['analogy_html'] = md.markdown(result['analogy'] or '', extensions=['fenced_code', 'tables', 'nl2br'])
	except Exception:
		result['analogy_html'] = '<pre>' + (result['analogy'] or '') + '</pre>'

	return jsonify(result)



@app.route('/generate_image', methods=['POST'])
def generate_image():
	"""Generate either a background or hero scene image.
	Expects JSON: { type: 'background'|'hero', world, character, story_excerpt }
	"""
	data = request.json or {}
	itype = data.get('type')
	world = data.get('world', '')
	character = data.get('character', '')
	story_excerpt = data.get('story_excerpt', '')

	try:
		if itype == 'background':
			prompt, img_url = generate_visual_prompt_and_image(world, 'background')
		elif itype == 'hero':
			prompt, img_url = generate_hero_scene_and_image(character, story_excerpt)
		else:
			return jsonify({'error': 'unknown image type'}), 400

		if img_url:
			return jsonify({'image_url': img_url, 'prompt': prompt})
		else:
			return jsonify({'error': 'generation_failed'}), 500
	except Exception as e:
		return jsonify({'error': str(e)}), 500


@app.route('/generate_bgm', methods=['POST'])
def generate_bgm():
	"""Generate background music independently.
	Expects JSON: { world, character, hero_name }
	"""
	data = request.json or {}
	world = data.get('world', '')
	character = data.get('character', '')
	hero_name = data.get('hero_name', 'the hero')

	try:
		audio_file = f"bgm_{uuid.uuid4().hex[:8]}.mp3"
		audio_path, _ = generate_bgm_wrapper(world[:100], character[:100], hero_name, audio_file, timeout=60)
		audio_url = url_for('static', filename=f'output/{os.path.basename(audio_path)}')
		return jsonify({'audio_url': audio_url})
	except Exception as e:
		return jsonify({'error': str(e)}), 500


@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
	"""Generate a beautifully formatted PDF of the story, character, world, and images."""
	from flask import send_file
	
	data = request.json or {}
	story = data.get('story', '')
	character = data.get('character', '')
	world = data.get('world', '')
	hero_name = data.get('hero_name', 'The Hero')
	analogy = data.get('analogy', '')
	images = data.get('images', [])
	# Use first image (world/background) for page background, not the hero image
	bg_image_path = images[1] if images and len(images) > 1 else None
	
	try:
		# Create PDF in memory
		pdf_buffer = BytesIO()
		doc = SimpleDocTemplate(pdf_buffer, pagesize=letter,
			leftMargin=0.5*inch, rightMargin=0.5*inch,
			topMargin=0.5*inch, bottomMargin=0.5*inch)
		
		# Custom styles with gradients simulated through colors
		styles = getSampleStyleSheet()
		
		# Gradient-like title style
		title_style = ParagraphStyle(
			'CustomTitle',
			parent=styles['Heading1'],
			fontSize=28,
			textColor=colors.HexColor("#f89945"),
			spaceAfter=12,
			alignment=TA_CENTER,
			fontName='Helvetica-Bold'
		)
		
		heading_style = ParagraphStyle(
			'CustomHeading',
			parent=styles['Heading2'],
			fontSize=16,
			textColor=colors.HexColor("#f6c35c"),
			spaceAfter=10,
			spaceBefore=12,
			fontName='Helvetica-Bold'
		)
		
		body_style = ParagraphStyle(
			'CustomBody',
			parent=styles['Normal'],
			fontSize=10,
			alignment=TA_JUSTIFY,
			spaceAfter=12,
			leading=14
		)
		
		# Build PDF content
		story_elements = []
		
		# Title
		story_elements.append(Paragraph(f"{hero_name}'s Adventure", title_style))
		story_elements.append(Spacer(1, 0.2*inch))
		
		# Character section
		story_elements.append(Paragraph("Character Profile", heading_style))
		for para in [p.strip() for p in character.split('\n\n') if p.strip()]:
			story_elements.append(Paragraph(para, body_style))
		story_elements.append(Spacer(1, 0.2*inch))
		
		# World section
		story_elements.append(Paragraph("World Description", heading_style))
		for para in [p.strip() for p in world.split('\n\n') if p.strip()]:
			story_elements.append(Paragraph(para, body_style))
		story_elements.append(Spacer(1, 0.2*inch))
		
		# Story section
		story_elements.append(Paragraph("The Story", heading_style))
		for para in [p.strip() for p in story.split('\n\n') if p.strip()]:
			story_elements.append(Paragraph(para, body_style))
		story_elements.append(Spacer(1, 0.3*inch))
		
		# Prepare optional transparent background image (15% opacity)
		bg_image_reader = None
		if bg_image_path:
			try:
				# Resolve local static paths
				if bg_image_path.startswith('http'):
					img_response = requests.get(bg_image_path, timeout=5)
					img = PILImage.open(BytesIO(img_response.content))
				else:
					if bg_image_path.startswith('/'):
						local_path = os.path.join(app.root_path, bg_image_path.lstrip('/'))
					else:
						local_path = bg_image_path
					img = PILImage.open(local_path)
				
				# Convert to RGBA and apply 15% opacity
				if img.mode != 'RGBA':
					img = img.convert('RGBA')
				
				r, g, b, a = img.split()
				a = a.point(lambda p: int(p * 0.15))
				img.putalpha(a)
				
				img_buffer = BytesIO()
				img.save(img_buffer, format='PNG')
				img_buffer.seek(0)
				bg_image_reader = ImageReader(img_buffer)
			except Exception as e:
				print(f"[WARNING] Could not prepare transparent background image: {e}")
		
		# Hero scene image (if available - use first image if it exists)
		if images and len(images) > 0:
			hero_img_url = images[0]
			try:
				if hero_img_url.startswith('http'):
					img_response = requests.get(hero_img_url, timeout=5)
					img_buffer = BytesIO(img_response.content)
					hero_reader = ImageReader(img_buffer)
					story_elements.append(Paragraph("The Hero's Moment", heading_style))
					story_elements.append(Image(img_buffer, width=5*inch, height=3*inch))
				else:
					if hero_img_url.startswith('/'):
						local_path = os.path.join(app.root_path, hero_img_url.lstrip('/'))
					else:
						local_path = hero_img_url
					img = PILImage.open(local_path)
					img_temp = BytesIO()
					img.save(img_temp, format='PNG')
					img_temp.seek(0)
					hero_reader = ImageReader(img_temp)
					story_elements.append(Paragraph("The Hero's Moment", heading_style))
					story_elements.append(Image(img_temp, width=5*inch, height=3*inch))
				story_elements.append(Spacer(1, 0.3*inch))
			except Exception as e:
				print(f"[WARNING] Could not include hero image: {e}")
		
		# Analogy section (renamed to "In Real Life")
		if analogy:
			story_elements.append(PageBreak())
			story_elements.append(Paragraph("In Real Life", heading_style))
			for para in [p.strip() for p in analogy.split('\n\n') if p.strip()]:
				story_elements.append(Paragraph(para, body_style))
		
		# Draw semi-transparent background on each page
		def _draw_background(canvas_obj, doc_obj):
			if bg_image_reader:
				page_width, page_height = letter
				try:
					canvas_obj.drawImage(bg_image_reader, 0, 0, width=page_width, height=page_height)
				except Exception:
					pass
		
		# Build the PDF with background on every page
		doc.build(story_elements, onFirstPage=_draw_background, onLaterPages=_draw_background)
		pdf_buffer.seek(0)
		
		# Return the PDF file
		return send_file(
			pdf_buffer,
			mimetype='application/pdf',
			as_attachment=True,
			download_name=f"{hero_name.replace(' ', '_')}_Adventure.pdf"
		)
	
	except Exception as e:
		print(f"[ERROR] PDF generation failed: {e}")
		return jsonify({'error': f"PDF generation failed: {str(e)}"}), 500


if __name__ == '__main__':
	app.run(port=8000, debug=True)
