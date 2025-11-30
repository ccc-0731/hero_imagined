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

'''
client = genai.Client(api_key=GOOGLE_API_KEY)

prompt = (
    "Create a picture of a ghibli-style profile photo for my DnD character, who is 9yr old very happy and very intelligent gender neutral elf paladin who looks asian and is around 130cm tall. I will do the oath of the ancients so put me in a nature background. I'm holding a short sword, have a short bow slung on back and carry cartographer tools in the backpack. Wearing simple elven clothing, a poor background. Hair is a bit messy but looks cool and cute, with a small strand of orange-yellow near the front. The sword is strapped to the waist and sheathed. Kind and joyful round open eyes."
)

response = client.models.generate_content(
    model="gemini-2.5-flash-image",
    contents=[prompt],
)

for part in response.parts:
    if part.text is not None:
        print(part.text)
    elif part.inline_data is not None:
        image = part.as_image()
        image.save("generated_image.png")'''

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

if __name__ == '__main__':
    call_gemini_image("panda astronaut in space with earth and moon in background, holding a blue lightsaber", "test_image.png")