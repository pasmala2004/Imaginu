# Original vs Enhanced Prompt — Image Compare

A small web app that shows how **prompt enhancement** changes an AI-generated image. You type a short idea, pick a style, and get two images side by side: one from your original prompt, one from an LLM-enhanced version. Both use the **same seed**, so any difference comes from the prompt alone.

**Stack:** Flask API · plain HTML/CSS/JS · LangGraph agent · Stable Diffusion 3 (Stability AI) · LLM via OpenRouter

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
image_compare/
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

**Requirements:** Python 3.10+, a [Stability AI](https://platform.stability.ai/) API key, and an [OpenRouter](https://openrouter.ai/) API key.

```bash
cd image_compare
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
| `OPENROUTER_API_KEY` | yes | — | LLM for moderation and enhancement |
| `MODEL_NAME` | no | `cohere/north-mini-code:free` | Any OpenRouter model id |
| `SD_MODEL` | no | `sd3.5-large` | Stability model sent to the `sd3` endpoint |

---

## Using the app

1. Describe the image in any language, including Arabic (up to 1000 characters). It is translated to English before generation.
2. Choose a **style**, **aspect ratio**, and optionally a **seed** (`0` = random).
3. Click **Generate** (or press Ctrl/Cmd + Enter). It takes roughly 30–60 seconds.
4. Compare the two images and download either as PNG.

**Styles:** No specific style, Photorealistic, Cinematic, Anime, Digital art, Oil painting, Watercolor, 3D render, Pixel art, Pencil sketch, Fantasy illustration, Cyberpunk, Minimalist.

The style is applied as prompt keywords to **both** sides (the `sd3` endpoint has no style preset parameter), so the comparison isolates the effect of enhancement. To add or edit styles, change the `STYLES` dict in `pipeline.py`.

---

## API

### `GET /api/options`
Returns the dropdown values.
```json
{ "styles": ["No specific style", "Photorealistic", "..."], "aspect_ratios": ["1:1", "16:9", "..."], "max_seed": 4294967294 }
```

### `POST /api/generate`
Request:
```json
{ "prompt": "two people walking on a beach", "style": "Cinematic", "aspect_ratio": "16:9", "seed": 0 }
```

Response (abridged):
```json
{
  "verdict": "safe",
  "reason": "",
  "notice": "",
  "original_prompt": "two people walking on a beach, cinematic film still, ...",
  "enhanced_prompt": "Two people strolling along a shoreline at golden hour, ...",
  "negative_prompt": "blurry, low quality, ...",
  "original_image": "data:image/png;base64,...",
  "enhanced_image": "data:image/png;base64,...",
  "original_error": "",
  "enhanced_error": "",
  "style": "Cinematic",
  "aspect_ratio": "16:9",
  "seed": 1834920311
}
```

| Status | Meaning |
|---|---|
| `200` | Processed. Check `verdict`: `block` means no images (see `message`), `rewrite` means the prompt was adjusted (see `reason`). |
| `400` | Invalid input (empty or too long prompt, unknown style or aspect ratio, bad seed) |
| `500` | Server is missing an API key |
| `502` | The LLM or network call failed |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| "Server is missing environment variable(s)" | Check that `.env` sits next to `app.py`, has no quotes or spaces around `=`, and the file isn't named `.env.txt`. Restart the server. |
| `502` / "Something went wrong…" | Free OpenRouter models are rate-limited and sometimes return malformed JSON. Retry, or set `MODEL_NAME` to another model. |
| "Stability's content filter rejected this prompt" | Stability has its own moderation (HTTP 403). Rephrase the prompt. |
| Generic "Internal Server Error" page | Read the traceback in the terminal running `python app.py`. Most common cause: files saved flat, so `templates/index.html` or `static/` is missing. Keep the folder structure shown above. |
| Port 5000 already in use | Change `port=5000` at the bottom of `app.py`. |
| Request takes very long | Two sequential image generations plus three LLM calls; slow free-tier models add to this. |

---

## Security notes

- **Never commit `.env` or hardcode keys.** If a key was ever pasted into a notebook or shared, rotate it.
- Server-side validation limits prompt length, style, aspect ratio and seed.
- The frontend inserts all server and LLM text with `textContent`, never as HTML.
- `app.py` runs with `debug=False` on `127.0.0.1` only. For deployment, use a production server (for example `gunicorn`) behind a reverse proxy, and add authentication and rate limiting, since every request spends API credits.

---

## Limitations

- Moderation relies on an LLM classifier and is not a guarantee. Stability's own filter is a second layer, but neither is perfect.
- Translation adds one extra LLM call per request, and quality depends on the model you choose in `MODEL_NAME`.
- Generation is synchronous: the page waits for the whole pipeline instead of streaming step-by-step progress.
- Images are held in memory and returned as base64; nothing is saved to disk or a database.