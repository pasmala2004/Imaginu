"""
Flask API + static frontend: original prompt vs enhanced prompt, side by side.
run: python app.py   ->  http://127.0.0.1:5000
"""
import base64
import os
import random
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from jinja2 import TemplateNotFound
from werkzeug.exceptions import HTTPException

load_dotenv()

from pipeline import ASPECT_RATIOS, MAX_SEED, STYLES, agent  # noqa: E402

MAX_PROMPT_CHARS = 1000

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
REQUIRED_FILES = ["pipeline.py", "templates/index.html", "static/style.css", "static/script.js"]


def missing_files() -> list[str]:
    return [f for f in REQUIRED_FILES if not (BASE_DIR / f).exists()]


def missing_keys() -> list[str]:
    return [k for k in ("STABILITY_API_KEY", "GROQ_API_KEY") if not os.getenv(k)]


def to_data_uri(img: bytes | None) -> str | None:
    return f"data:image/png;base64,{base64.b64encode(img).decode()}" if img else None


@app.get("/")
def index():
    try:
        return render_template("index.html")
    except TemplateNotFound:
        return (
            "templates/index.html was not found. Keep the folder layout: "
            "app.py, pipeline.py, templates/index.html, static/style.css, static/script.js",
            500,
        )


@app.errorhandler(Exception)
def handle_unexpected(e):
    if isinstance(e, HTTPException):  # 404, 405, ... keep Flask's normal response
        return e
    app.logger.exception("Unhandled error")
    if request.path.startswith("/api/"):
        return jsonify(error=f"Unexpected server error: {type(e).__name__}. Check the server terminal."), 500
    return "Unexpected server error. Check the terminal where the server is running.", 500


@app.get("/api/options")
def options():
    return jsonify({"styles": list(STYLES.keys()), "aspect_ratios": ASPECT_RATIOS, "max_seed": MAX_SEED})


@app.post("/api/generate")
def generate():
    if missing := missing_keys():
        return jsonify(error=f"Server is missing environment variable(s): {', '.join(missing)}"), 500

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify(error="Request body must be a JSON object."), 400
    prompt = str(body.get("prompt", "")).strip()
    style = body.get("style", "No specific style")
    aspect = body.get("aspect_ratio", "1:1")

    try:
        seed = int(body.get("seed") or 0)
    except (TypeError, ValueError):
        return jsonify(error="Seed must be a number."), 400

    # ---- validation
    if not prompt:
        return jsonify(error="Prompt is required."), 400
    if len(prompt) > MAX_PROMPT_CHARS:
        return jsonify(error=f"Prompt is too long (max {MAX_PROMPT_CHARS} characters)."), 400
    if style not in STYLES:
        return jsonify(error="Unknown style."), 400
    if aspect not in ASPECT_RATIOS:
        return jsonify(error="Unknown aspect ratio."), 400
    if not 0 <= seed <= MAX_SEED:
        return jsonify(error=f"Seed must be between 0 and {MAX_SEED}."), 400

    seed = seed or random.randint(1, MAX_SEED)  # 0 = random; same seed used for both images

    try:
        out = agent.invoke({"user_prompt": prompt, "style": style, "aspect_ratio": aspect, "seed": seed})
    except Exception as e:  # LLM / network failure
        app.logger.exception("Agent failed")
        return jsonify(error=f"Something went wrong while processing your prompt: {type(e).__name__}"), 502

    lang = out.get("source_language", "")
    return jsonify(
        verdict=out.get("verdict"),
        reason=out.get("reason", ""),
        message=out.get("message", ""),
        notice=out.get("notice", ""),
        translated_from=lang if lang and lang.strip().lower() != "english" else "",
        english_prompt=out.get("prompt", ""),
        original_prompt=out.get("original_prompt", ""),
        enhanced_prompt=out.get("enhanced", ""),
        negative_prompt=out.get("negative_prompt", ""),
        original_image=to_data_uri(out.get("original_image")),
        enhanced_image=to_data_uri(out.get("enhanced_image")),
        original_error=out.get("original_error", ""),
        enhanced_error=out.get("enhanced_error", ""),
        style=style,
        aspect_ratio=aspect,
        seed=seed,
    )


if __name__ == "__main__":
    if missing := missing_files():
        raise SystemExit(f"Missing file(s) next to app.py: {', '.join(missing)}. Keep the project folder structure.")
    if missing := missing_keys():
        print(f"WARNING: missing environment variable(s): {', '.join(missing)} (set them in .env)")
    app.run(host="127.0.0.1", port=5000, debug=False)