import os
import json
import base64
from pathlib import Path
from uuid import uuid4
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)
app.secret_key = "sneaker-studio-dev-key"

HCAPTCHA_SITE_KEY = os.environ.get("HCAPTCHA_SITE_KEY", "")
HCAPTCHA_SECRET   = os.environ.get("HCAPTCHA_SECRET", "")

OPENAI_API_KEY     = os.environ.get("OPENAI_API_KEY", "")
OPENAI_TEXT_MODEL  = os.environ.get("OPENAI_TEXT_MODEL", "gpt-4o-mini")
OPENAI_IMAGE_MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-2.5-flare")
openai_client      = OpenAI(api_key=OPENAI_API_KEY, timeout=120) if OPENAI_API_KEY else None
GENERATED_DIR     = Path(app.static_folder) / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

DESIGN_PROMPT = """You are an expert sneaker designer. Generate a detailed concept based on:
Style: {style}, Primary Color: {primary_color}, Accent Color: {accent_color},
Material: {material}, Occasion: {occasion}, Inspiration: {inspiration}

Respond with raw JSON only — no markdown, no explanation.
{{"name":"2-4 word creative name","tagline":"punchy tagline max 10 words","description":"2-3 sentence design description","materials":["mat1","mat2","mat3"],"colorways":[{{"name":"colorway name","sole":"#hex","upper":"#hex","accent":"#hex","lace":"#hex","tongue":"#hex"}}],"features":["feat1","feat2","feat3","feat4"],"sole_type":"sole tech description","target_audience":"who this is for","retail_price":"$XXX","style_tags":["tag1","tag2","tag3"]}}
Generate exactly 3 colorways: user colors first, then 2 creative variations. All hex codes must be valid #RRGGBB."""

def get_prefs(data):
    return {
        "style": data.get("style", "Casual"),
        "material": data.get("material", "Leather"),
        "occasion": data.get("occasion", "Everyday"),
        "primary_color": data.get("primary_color", "#7a7af0"),
        "accent_color": data.get("accent_color", "#32c81e"),
        "inspiration": data.get("inspiration", "")
    }

HCAPTCHA_VERIFY_URL = "https://api.hcaptcha.com/siteverify"

def verify_hcaptcha(token):
    try:
        r = requests.post(
            HCAPTCHA_VERIFY_URL,
            data={"secret": HCAPTCHA_SECRET, "response": token},
            timeout=5
        )
        r.raise_for_status()
        result = r.json()
    except ValueError:
        app.logger.exception("hCaptcha verification returned invalid JSON")
        return False
    except requests.RequestException:
        app.logger.exception("hCaptcha verification request failed")
        return False

    if not result.get("success"):
        app.logger.warning(
            "hCaptcha verification rejected token: %s",
            result.get("error-codes", ["unknown error"])
        )
        return False
    return True

def generate_concept(prefs):
    if not openai_client:
        raise RuntimeError("OPENAI_API_KEY is not configured. Add your OpenAI API key to .env and restart the server.")
    chat = openai_client.chat.completions.create(
        model=OPENAI_TEXT_MODEL,
        messages=[
            {"role": "system", "content": "Sneaker design expert. Pure JSON only."},
            {"role": "user",   "content": DESIGN_PROMPT.format(**prefs)},
        ],
        temperature=0.85, max_tokens=1200,
        response_format={"type": "json_object"},
    )
    content = chat.choices[0].message.content
    if not content:
        raise RuntimeError("OpenAI returned an empty sneaker concept.")
    raw = content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"): raw = raw[4:]
    return json.loads(raw.strip().rstrip("```").strip())

def generate_sneaker_image(prefs, concept):
    if not openai_client:
        raise RuntimeError("OPENAI_API_KEY is not configured. Add your OpenAI API key to .env and restart the server.")

    prompt = (
        f"Premium sneaker concept product render named {concept.get('name', 'custom sneaker')}. "
        f"{concept.get('description', '')} "
        f"Style: {prefs['style']}; material: {prefs['material']}; occasion: {prefs['occasion']}. "
        f"Primary color {prefs['primary_color']} with accent color {prefs['accent_color']}. "
        "Three-quarter side view of one shoe, clean dark studio backdrop, dramatic softbox lighting, "
        "high-detail photorealistic footwear design, sharp focus, no people, no text, no logos, no watermark."
    )
    image_response = openai_client.images.generate(
        model=OPENAI_IMAGE_MODEL,
        prompt=prompt,
        size="1024x1024",
    )
    if not image_response.data:
        raise RuntimeError("OpenAI returned no image.")
    image_data = image_response.data[0].b64_json
    if not image_data:
        raise RuntimeError("OpenAI did not return image data.")
    filename = f"sneaker-{uuid4().hex}.png"
    (GENERATED_DIR / filename).write_bytes(base64.b64decode(image_data, validate=True))
    return f"/static/generated/{filename}"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/studio")
def studio():
    return render_template("studio.html", hcaptcha_site_key=HCAPTCHA_SITE_KEY)

@app.route("/history")
def history():
    return render_template("history.html", designs=[])

@app.route("/generate", methods=["POST"])
def generate():
    data  = request.get_json(silent=True) or request.form

    if not HCAPTCHA_SITE_KEY or not HCAPTCHA_SECRET:
        return jsonify({
            "error": "CAPTCHA is not configured. Set HCAPTCHA_SITE_KEY and HCAPTCHA_SECRET in .env."
        }), 500

    # GATE 1: Check for CAPTCHA token
    token = data.get("h-captcha-response", "")
    if not token:
        return jsonify({"error": "Please complete the CAPTCHA."}), 400

    # GATE 2: Verify token with hCaptcha servers
    if not verify_hcaptcha(token):
        return jsonify({"error": "CAPTCHA verification failed."}), 400

    prefs = get_prefs(data)
    try:
        concept = generate_concept(prefs)
        image_url = generate_sneaker_image(prefs, concept)
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Malformed AI response: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"Concept generation failed: {e}"}), 500
    return jsonify({"success": True, "concept": concept, "image_url": image_url, "prefs": prefs})

if __name__ == "__main__":
    app.run(debug=True)