from elevenlabs.client import ElevenLabs
from elevenlabs.play import play
import os
import uuid
import requests
from dotenv import load_dotenv
from flask import url_for


# ---------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------
from dotenv import load_dotenv
load_dotenv(dotenv_path="/Users/luchen/Desktop/GitHub/hero_imagined/.env")


ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    raise RuntimeError("Missing ELEVENLABS_API_KEY in environment.")

# If running standalone, simulate Flask's STATIC path
STATIC_OUTPUT = os.path.join(os.getcwd(), "static", "output")
os.makedirs(STATIC_OUTPUT, exist_ok=True)


# ---------------------------------------------------------------------
# Generate BGM with ElevenLabs
# ---------------------------------------------------------------------
def generate_bgm_instrumental(world_description, character_description, hero_name, filename):
    """
    Generate ~30 seconds of instrumental background music using ElevenLabs.
    Music is based on the story's worldbuilding.
    """
    out_path = os.path.join(STATIC_OUTPUT, filename)

    music_prompt = (
        f"Instrumental cinematic fantasy theme for a hero named {hero_name}. "
        f"World: {world_description}. "
        f"Character: {character_description}. "
        f"Tone: emotional, adventurous, atmospheric, warm, slightly whimsical. "
        f"Focus on orchestral textures, light percussion, gentle strings."
    )

    url = "https://api.elevenlabs.io/v1/music"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }

    body = {
        "prompt": music_prompt,
        "music_length_ms": 30000,             # 30s
        "output_format": "mp3_44100_128",
        "force_instrumental": True
    }

    try:
        resp = requests.post(url, headers=headers, json=body, stream=True, timeout=90)

        if resp.status_code != 200:
            raise RuntimeError(f"ElevenLabs error {resp.status_code}: {resp.text}")

        # Stream audio chunks
        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return out_path

    except Exception as e:
        print(f"[ERROR] BGM generation failed: {e}")
        raise


# ---------------------------------------------------------------------
# Manual test payload
# ---------------------------------------------------------------------
if __name__ == "__main__":

    # filename for output
    audio_file = "test_bgm.mp3"

    try:
        audio_path = generate_bgm_instrumental(
            world_description="""A world of massive crystalline AI data centers
            that expand autonomously, where humans cannot go outside after dark,
            and devices randomly fail due to unstable infrastructure. There is fear,
            but also the whisper of lost benevolence deep inside the Core.""",

            character_description="""Ren, a 9-year-old nonbinary prodigy with a single
            golden hair strand. They fly, build machines, and carry a dead AI’s data chip
            from their childhood—haunted by the sibling they lost to AI inaction.""",

            hero_name="Ren",
            filename=audio_file
        )

        print("[SUCCESS] BGM generated at:", audio_path)

    except Exception as e:
        print(f"[WARNING] Could not generate BGM: {e}")
