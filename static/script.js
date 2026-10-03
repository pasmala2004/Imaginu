const $ = (id) => document.getElementById(id);

const els = {
  prompt: $("prompt"),
  style: $("style"),
  aspect: $("aspect"),
  seed: $("seed"),
  button: $("generate"),
  loading: $("loading"),
  alerts: $("alerts"),
  results: $("results"),
  meta: $("meta"),
};

// ---------------------------------------------------------------- helpers
function fillSelect(select, values) {
  for (const v of values) {
    const opt = document.createElement("option");
    opt.value = opt.textContent = v;
    select.appendChild(opt);
  }
}

function showAlert(kind, text) {
  const div = document.createElement("div");
  div.className = `alert ${kind}`;
  div.textContent = text; // textContent: never inject server/user text as HTML
  els.alerts.appendChild(div);
}

function renderImage(boxId, dataUri, error, filename) {
  const box = $(boxId);
  box.replaceChildren();

  if (dataUri) {
    const img = document.createElement("img");
    img.src = dataUri;
    img.alt = filename;
    box.appendChild(img);

    const link = document.createElement("a");
    link.className = "download";
    link.href = dataUri;
    link.download = filename;
    link.textContent = "Download PNG";
    box.appendChild(link);
  } else if (error) {
    const div = document.createElement("div");
    div.className = "alert error";
    div.textContent = error;
    box.appendChild(div);
  }
}

function setBusy(busy) {
  els.button.disabled = busy;
  els.loading.hidden = !busy;
}

// ---------------------------------------------------------------- init
async function init() {
  try {
    const res = await fetch("/api/options");
    const opts = await res.json();
    fillSelect(els.style, opts.styles);
    fillSelect(els.aspect, opts.aspect_ratios);
    els.seed.max = opts.max_seed;
  } catch {
    showAlert("error", "Could not load options from the server.");
  }
}

// ---------------------------------------------------------------- generate
async function generate() {
  const prompt = els.prompt.value.trim();
  els.alerts.replaceChildren();
  els.results.hidden = true;
  els.meta.hidden = true;

  if (!prompt) {
    showAlert("error", "Please describe the image first.");
    return;
  }

  setBusy(true);
  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt,
        style: els.style.value,
        aspect_ratio: els.aspect.value,
        seed: Number(els.seed.value) || 0,
      }),
    });

    let data;
    try {
      data = await res.json();
    } catch {
      throw new Error(`Server returned an unexpected response (${res.status}).`);
    }
    if (!res.ok) throw new Error(data.error || `Request failed (${res.status}).`);

    render(data);
  } catch (err) {
    showAlert("error", err.message);
  } finally {
    setBusy(false);
  }
}

function render(d) {
  if (d.verdict === "block") {
    showAlert("error", d.message || "Request blocked.");
    return;
  }
  if (d.verdict === "rewrite") showAlert("warn", `Your prompt was adjusted: ${d.reason}`);
  if (d.translated_from) showAlert("info", `Translated from ${d.translated_from} to English: ${d.english_prompt}`);
  if (d.notice) showAlert("info", d.notice);

  $("original-prompt").textContent = d.original_prompt;
  $("enhanced-prompt").textContent = d.enhanced_prompt;

  const neg = $("negative-prompt");
  neg.hidden = !d.negative_prompt;
  neg.textContent = d.negative_prompt ? `Negative: ${d.negative_prompt}` : "";

  renderImage("original-box", d.original_image, d.original_error, `original_${d.seed}.png`);
  renderImage("enhanced-box", d.enhanced_image, d.enhanced_error, `enhanced_${d.seed}.png`);
  els.results.hidden = false;

  els.meta.textContent =
    `Style: ${d.style} · Aspect: ${d.aspect_ratio} · Seed: ${d.seed} ` +
    "(same seed for both images, so differences come from the prompt)";
  els.meta.hidden = false;
}

els.button.addEventListener("click", generate);
els.prompt.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") generate();
});

init();