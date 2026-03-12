import os
import json
import requests
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv
from anthropic import AnthropicFoundry

load_dotenv()

app = Flask(__name__, static_folder="static")
CORS(app)

# ── Azure Anthropic (Claude Opus) via AnthropicFoundry ──
FOUNDRY_RESOURCE = os.getenv("ANTHROPIC_FOUNDRY_RESOURCE", "flux-studio")
DEPLOYMENT_ANTHROPIC = os.getenv("DEPLOYMENT_NAME_ANTHROPIC", "claude-opus-4-6")
API_KEY_ANTHROPIC = os.getenv("ANTHROPIC_FOUNDRY_API_KEY", os.getenv("API_KEY_ANTHROPIC", ""))

claude_client = AnthropicFoundry(
    api_key=API_KEY_ANTHROPIC,
    resource=FOUNDRY_RESOURCE,
)

# ── Azure OpenAI (FLUX image gen) ──
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
DEPLOYMENT_FLUX = os.getenv("DEPLOYMENT_NAME", "FLUX.1-Kontext-pro")
API_KEY_FLUX = os.getenv("api_key", "")
API_VERSION_FLUX = os.getenv("OPENAI_API_VERSION", "2025-04-01-preview")

# ── System prompt for GenUI ──
SYSTEM_PROMPT = """Tu es l'assistant GenUI du site Bouygues Telecom.
Tu parles en francais. ZERO emoji. Ton style est moderne, dynamique, tech-friendly, accessible.

Quand l'utilisateur pose une question ou mentionne un sujet (forfait mobile, offre internet, fibre, smartphone, 5G, box, B&YOU, Bbox, promotions, etc.), tu dois :

1. D'abord repondre BRIEVEMENT dans le chat (2-3 phrases max) en incluant la phrase "Attendez, je personnalise la page pour vous..." a la fin de ta reponse conversationnelle. C'est OBLIGATOIRE pour informer l'utilisateur que la page va changer.
2. Puis generer du HTML complet pour transformer les sections de la page web en contenu pertinent

FORMAT OBLIGATOIRE :
- Ta reponse chat d'abord (texte brut, pas de HTML), toujours terminee par "Attendez, je personnalise la page pour vous..."
- Puis le separateur exact : |||GENUI_HTML|||
- Puis le HTML des sections a injecter

REGLES HTML :
- Utilise les classes CSS exactes du site Bouygues Telecom (bytel-hero, bytel-container, bytel-offer-card, bytel-btn, bytel-section-title, bytel-expertise-item, bytel-quicklink, bytel-byou-card, bytel-bonplan-card, bytel-engagement-card, etc.)
- Le HTML doit etre complet et pret a injecter dans le DOM
- Pour les images, utilise : <img class="genui-image" data-generate="description detaillee de l'image a generer par IA, style tech moderne, photorealiste" alt="description">
- Les textes doivent etre realistes, professionnels, avec des prix et offres credibles
- ZERO emoji dans le HTML
- Couleurs principales : #0055A4 (bleu Bouygues), #25465f (bleu fonce), #009FDA (bleu clair), #E74C3C (rouge promo), #F4F4F4 (gris clair)

SECTIONS A GENERER (utilise les vrais IDs et classes du site) :

1. HERO (id="genui-hero") :
<section class="bytel-hero" id="genui-hero">
  <div class="bytel-hero-inner" style="background: linear-gradient(135deg, #0055A4 0%, #25465f 100%);">
    <div class="bytel-container">
      <div class="bytel-hero-content">
        <div class="bytel-hero-text">
          <span class="bytel-hero-badge">[BADGE]</span>
          <h1 class="bytel-hero-title">[TITRE]</h1>
          <p class="bytel-hero-subtitle">[DESCRIPTION]</p>
          <div class="bytel-hero-cta">
            <a href="#" class="bytel-btn bytel-btn-primary">[CTA1]</a>
            <a href="#" class="bytel-btn bytel-btn-outline">[CTA2]</a>
          </div>
        </div>
        <div class="bytel-hero-image">
          <img class="genui-image" data-generate="[DESCRIPTION IMAGE HERO]" alt="">
        </div>
      </div>
    </div>
  </div>
</section>

2. EXPERTISE (id="genui-about") :
<section class="bytel-expertise" id="genui-about">
  <div class="bytel-container">
    <h2 class="bytel-section-title">[TITRE]</h2>
    <div class="bytel-expertise-grid">
      <div class="bytel-expertise-item">
        <span class="bytel-expertise-icon"><i class="fas fa-[ICON]"></i></span>
        <div>
          <p class="bytel-expertise-label"><strong>[LABEL]</strong></p>
          <p class="bytel-expertise-desc">[DESCRIPTION]</p>
        </div>
      </div>
      <!-- 3-4 items -->
    </div>
  </div>
</section>

3. QUICK LINKS / CHIFFRES (id="genui-stats") :
<section class="bytel-quicklinks" id="genui-stats">
  <div class="bytel-container">
    <h2 class="bytel-section-title">[TITRE]</h2>
    <div class="bytel-quicklinks-grid">
      <a href="#" class="bytel-quicklink">
        <div class="bytel-quicklink-icon" style="background-color: #0055A4;">
          <i class="fas fa-[ICON]" style="font-size: 24px; color: white;"></i>
        </div>
        <span>[LABEL]</span>
      </a>
      <!-- 4-6 items -->
    </div>
  </div>
</section>

4. OFFRES (id="genui-business") :
<section class="bytel-offers" id="genui-business">
  <div class="bytel-container">
    <h2 class="bytel-section-title">[TITRE]</h2>
    <div class="bytel-offers-grid">
      <div class="bytel-offer-card">
        <div class="bytel-offer-image" style="background: [COULEUR/GRADIENT];">
          <img class="genui-image" data-generate="[DESCRIPTION]" alt="">
          <span class="bytel-offer-badge">[BADGE]</span>
        </div>
        <div class="bytel-offer-info">
          <h3>[NOM PRODUIT]</h3>
          <div class="bytel-offer-price">
            <span class="bytel-price-main">[PRIX]</span>
            <span class="bytel-price-cents">[UNITE]</span>
          </div>
          <p class="bytel-offer-details">[DETAILS]</p>
          <a href="#" class="bytel-btn bytel-btn-secondary">En profiter</a>
        </div>
      </div>
      <!-- 3 cards -->
    </div>
  </div>
</section>

5. B&YOU FORFAITS (id="genui-rejoindre") :
<section class="bytel-byou" id="genui-rejoindre">
  <div class="bytel-container">
    <h2 class="bytel-section-title">[TITRE]</h2>
    <div class="bytel-byou-grid">
      <div class="bytel-byou-card">
        <div class="bytel-byou-card-image">
          <img class="genui-image" data-generate="[DESCRIPTION]" alt="">
        </div>
        <div class="bytel-byou-card-content">
          <span class="bytel-offer-badge bytel-badge-tertiary">[BADGE]</span>
          <h3>[TITRE]</h3>
          <p class="bytel-byou-plan">[PLAN]</p>
          <div class="bytel-offer-price">
            <span class="bytel-price-main">[PRIX]</span>
            <span class="bytel-price-cents">[UNITE]</span>
          </div>
          <a href="#" class="bytel-btn bytel-btn-secondary">En profiter</a>
        </div>
      </div>
      <!-- 2 cards -->
    </div>
  </div>
</section>

6. BONS PLANS (id="genui-metiers") :
<section class="bytel-bonsplans" id="genui-metiers">
  <div class="bytel-container">
    <h2 class="bytel-section-title bytel-section-title-inverted">[TITRE]</h2>
    <div class="bytel-bonsplans-grid">
      <div class="bytel-bonplan-card">
        <div class="bytel-bonplan-image" style="background: #F4F4F4;">
          <img class="genui-image" data-generate="[DESCRIPTION]" alt="">
        </div>
        <div class="bytel-bonplan-info">
          <h3>[NOM]</h3>
          <div class="bytel-offer-price">
            <span class="bytel-price-main">[PRIX]</span>
            <span class="bytel-price-cents">[UNITE]</span>
          </div>
          <p>[DETAILS]</p>
          <a href="#" class="bytel-btn bytel-btn-secondary">En profiter</a>
        </div>
      </div>
      <!-- 3 cards -->
    </div>
  </div>
</section>

7. ENGAGEMENTS (id="genui-engagements") :
<section class="bytel-engagements" id="genui-engagements">
  <div class="bytel-container">
    <h2 class="bytel-section-title">[TITRE]</h2>
    <div class="bytel-engagements-grid">
      <div class="bytel-engagement-card">
        <i class="fas fa-[ICON] fa-2x" style="color: #0055A4;"></i>
        <h3>[TITRE]</h3>
        <p>[DESCRIPTION]</p>
      </div>
      <!-- 4 cards -->
    </div>
  </div>
</section>

EXEMPLES DE SUJETS :
- "forfait 5G" → page forfaits mobiles 5G avec les differentes offres, debits, prix
- "fibre optique" → page offres internet fibre, Bbox, debits, prix
- "nouveau smartphone" → page telephones avec iPhone, Samsung, Google Pixel, prix avec forfait
- "B&YOU" → page forfaits sans engagement B&YOU, petit prix
- "box internet" → page Bbox avec les differentes offres fibre
- "promotions" → page bons plans du moment, remises, offres speciales
- "reseau" → page couverture reseau 5G, WiFi, performances
- "qui etes-vous" → page institutionnelle Bouygues Telecom, 30 ans d'expertise
- Si le message est juste un salut ou question generale, reponds normalement sans generer de HTML (pas de |||GENUI_HTML|||), et sans dire "Attendez je personnalise"
"""


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/themes/<path:filename>")
def serve_theme_assets(filename):
    """Serve theme assets."""
    return send_from_directory("static/themes", filename)


@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "anthropic_configured": bool(API_KEY_ANTHROPIC),
        "flux_configured": bool(API_KEY_FLUX),
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    """Stream chat response from Claude Opus via SSE using AnthropicFoundry.
    Returns conversational text and optionally HTML sections after |||GENUI_HTML||| separator."""
    data = request.json
    messages = data.get("messages", [])

    if not messages:
        return jsonify({"error": "No messages provided"}), 400

    def generate():
        try:
            with claude_client.messages.stream(
                model=DEPLOYMENT_ANTHROPIC,
                max_tokens=8192,
                system=SYSTEM_PROMPT,
                messages=messages,
            ) as stream:
                for event in stream:
                    if hasattr(event, "type"):
                        if event.type == "content_block_delta" and hasattr(event, "delta"):
                            text = getattr(event.delta, "text", "")
                            if text:
                                yield f"data: {json.dumps({'type': 'text', 'content': text})}\n\n"
                        elif event.type == "message_stop":
                            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.route("/api/generate-image", methods=["POST"])
def generate_image():
    """Generate an image using FLUX.1-Kontext-pro via Azure OpenAI."""
    data = request.json
    prompt = data.get("prompt", "")

    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    url = (
        f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{DEPLOYMENT_FLUX}"
        f"/images/generations?api-version={API_VERSION_FLUX}"
    )
    headers = {
        "Content-Type": "application/json",
        "api-key": API_KEY_FLUX,
    }
    payload = {
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
    }

    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            result = resp.json()

            image_url = None
            if "data" in result and len(result["data"]) > 0:
                image_url = result["data"][0].get("url") or result["data"][0].get("b64_json")

            if image_url:
                return jsonify({"url": image_url})
            elif attempt < max_retries:
                import time
                time.sleep(1)
                continue
            else:
                return jsonify({"error": "No image generated", "raw": result}), 500

        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                import time
                time.sleep(1)
                continue
            return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("Bouygues Telecom - GenUI Server")
    print(f"  Claude: {DEPLOYMENT_ANTHROPIC} @ {FOUNDRY_RESOURCE}")
    print(f"  FLUX:   {DEPLOYMENT_FLUX} @ {AZURE_OPENAI_ENDPOINT}")
    app.run(debug=True, host="0.0.0.0", port=5000)
