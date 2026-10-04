# Imaginu — Original vs Enhanced Prompt

A small web app that shows how **prompt enhancement** changes an AI-generated image. You type a short idea, pick a style, and get two images: one from your original prompt, one from an LLM-enhanced version. Both use the **same seed**, so any difference comes from the prompt alone.

**Stack:** Flask API · plain HTML/CSS/JS · LangGraph agent · Stable Diffusion 3 (Stability AI) · LLM via Groq

---

## How it works

```
user prompt
    │
    ▼
moderate_input ── block ──────────────► refuse ──► END
    │ safe / rewrite
    ▼
translate  (any language → English; Stable Diffusion only understands English)
    │
    ▼
enhance  (adds style, lighting, composition + a negative prompt)
    │
    ▼
moderate_output  (re-checks the enhanced prompt; falls back to the original if flagged)
    │
    ▼
generate_original ──► generate_enhanced ──► END
```

| Step | What it does |
|---|---|
| **moderate_input** | LLM classifies the prompt as `safe`, `rewrite` (problem removed, intent kept) or `block`. Fails closed: an unclear verdict is treated as `block`. |
| **translate** | Translates the prompt to English (Arabic and other languages) and records the source language. English input is returned unchanged. |
| **enhance** | Rewrites the idea as a rich 40–90 word prompt built around the chosen style, plus a negative prompt. |
| **moderate_output** | The enhancer can introduce violations too, so its output is checked again. |
| **generate_original** | Stability image from your prompt + the style keywords (no negative prompt). |
| **generate_enhanced** | Stability image from the enhanced prompt + negative prompt. |

If one image fails, the other still displays.

---

## Project structure

```
Imaginu/
├── app.py               Flask routes + input validation
├── pipeline.py          LangGraph agent, styles, Stability API call
├── templates/
│   └── index.html       The page
├── static/
│   ├── style.css        Layout, light/dark theme
│   └── script.js        Fetches the API and renders results
├── requirements.txt
├── .env.example         Config template
└── .gitignore
```

---

## Setup

**Requirements:** Python 3.10+, a [Stability AI](https://platform.stability.ai/) API key, and a [Groq](https://console.groq.com/) API key.

```bash
cd Imaginu
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # Windows: copy .env.example .env
# edit .env and add your keys

python app.py
```

Open **http://127.0.0.1:5000**.

### Configuration (`.env`)

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `STABILITY_API_KEY` | yes | — | Stability AI image generation |
| `GROQ_API_KEY` | yes | — | LLM for moderation, translation and enhancement |
| `MODEL_NAME` | no | `qwen/qwen3.8-27b` | Any Groq model id |
| `SD_MODEL` | no | `sd3.5-large` | Stability model sent to the `sd3` endpoint |

---

## Using the app

1. Describe the image in any language, including Arabic (up to 1000 characters). It is translated to English before generation.
2. Choose a **style**. A random seed is picked per request and shared by both images; the aspect ratio defaults to `1:1`.
3. Click **Generate** (or press Ctrl/Cmd + Enter). It takes roughly 30–60 seconds.
4. Compare the two images and download either as PNG.

**Styles:** No specific style, Photorealistic, Cinematic, Anime, Digital art, Oil painting, Watercolor, 3D render, Pixel art, Pencil sketch, Fantasy illustration, Cyberpunk, Minimalist.

The style is applied as prompt keywords to **both** sides (the `sd3` endpoint has no style preset parameter), so the comparison isolates the effect of enhancement. To add or edit styles, change the `STYLES` dict in `pipeline.py`.

---

## API

| Endpoint | Body | Returns |
|---|---|---|
| `GET /api/options` | — | `styles`, `aspect_ratios`, `max_seed` |
| `POST /api/generate` | `{prompt, style}` (optional: `aspect_ratio`, default `1:1`; `seed`, `0`/omitted = random) | `verdict`, `reason`, `notice`, `translated_from`, `english_prompt`, `original_prompt`, `enhanced_prompt`, `negative_prompt`, `original_image`, `enhanced_image` (base64 PNG data URIs), per-image `*_error`, `style`, `aspect_ratio`, `seed` |

The UI only sends `prompt` and `style`; `aspect_ratio` and `seed` remain optional API parameters.

## Notes

Moderation is LLM-based, so it is a safeguard, not a guarantee.