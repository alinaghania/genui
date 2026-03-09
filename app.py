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
ENDPOINT_ANTHROPIC = os.getenv("ENDPOINT_ANTHROPIC")
DEPLOYMENT_ANTHROPIC = os.getenv("DEPLOYMENT_NAME_ANTHROPIC", "claude-opus-4-6")
API_KEY_ANTHROPIC = os.getenv("API_KEY_ANTHROPIC", "")

claude_client = AnthropicFoundry(
    api_key=API_KEY_ANTHROPIC,
    base_url=ENDPOINT_ANTHROPIC,
)

# ── Azure OpenAI (FLUX image gen) ──
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
DEPLOYMENT_FLUX = os.getenv("DEPLOYMENT_NAME", "FLUX.1-Kontext-pro")
API_KEY_FLUX = os.getenv("api_key", "")
API_VERSION_FLUX = os.getenv("OPENAI_API_VERSION", "2025-04-01-preview")

# ── System prompt for GenUI ──
SYSTEM_PROMPT = """Tu es l'assistant GenUI du site BNP Paribas Personal Finance (Cetelem).
Tu parles en francais. ZERO emoji. Ton style est professionnel, bancaire, sobre.

Quand l'utilisateur pose une question ou mentionne un sujet (credit auto, pret immobilier, credit conso, rachat de credits, assurance, epargne, etc.), tu dois :

1. D'abord repondre BRIEVEMENT dans le chat (2-3 phrases max) en incluant la phrase "Attendez, je personnalise la page pour vous..." a la fin de ta reponse conversationnelle. C'est OBLIGATOIRE pour informer l'utilisateur que la page va changer.
2. Puis generer du HTML complet pour transformer les sections de la page web en contenu pertinent

FORMAT OBLIGATOIRE :
- Ta reponse chat d'abord (texte brut, pas de HTML), toujours terminee par "Attendez, je personnalise la page pour vous..."
- Puis le separateur exact : |||GENUI_HTML|||
- Puis le HTML des sections a injecter

REGLES HTML :
- Utilise les classes CSS exactes du vrai site BNP Paribas Personal Finance (Hero, Hero-card, wp-block-cnx-hero, highlight-box, block-carrousel-articles, key-figures, etc.)
- Le HTML doit etre complet et pret a injecter dans le DOM
- Pour les images, utilise : <img class="genui-image" data-generate="description detaillee de l'image a generer par IA, style bancaire professionnel, photorealiste" alt="description">
- Les textes doivent etre realistes, professionnels, avec des chiffres credibles
- ZERO emoji dans le HTML

SECTIONS A GENERER (utilise les vrais IDs et classes du site) :

1. HERO (id="genui-hero") :
<div class="container" id="genui-hero">
  <div style="--hero-background-color: #337F37;" class="Hero is-home wp-block-cnx-hero">
    <div class="Hero-image-wrapper">
      <img class="Hero-image genui-image" data-generate="[DESCRIPTION IMAGE HERO]" alt="">
    </div>
    <div class="Hero-card-wrapper">
      <div class="Hero-card">
        <h1 class="Hero-title">[TITRE]</h1>
        <p class="Hero-paragraph">[PARAGRAPHE]</p>
        <div class="container">
          <div class="wp-block-button is-style-fill has-open-sans-font-family">
            <a class="wp-block-button__link wp-element-button" href="#">[CTA]</a>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

2. QUI SOMMES-NOUS (id="genui-about") :
<div class="container" id="genui-about">
  <div class="wp-block-group d-flex flex-column d-xl-grid my-5 is-layout-grid wp-container-core-group-is-layout-2">
    <div style="--highlight-box-background-color: #337F37;" class="highlight-box is-horizontal mt-5 mt-lg-0 wp-block-cnx-highlight-box">
      <div class="highlight-box-title-column">
        <div class="highlight-box-top-radius"></div>
        <h2 class="highlight-box-title longer-top"><span class="title1">[TITRE1]</span><br><span class="title2">[TITRE2]</span></h2>
      </div>
    </div>
    <div class="wp-block-group is-layout-constrained">
      <p class="has-open-sans-font-family">[TEXTE]</p>
    </div>
  </div>
</div>

3. CHIFFRES CLES (id="genui-stats") :
<div class="container" id="genui-stats">
  <div class="wp-block-group key-figures-wrapper is-layout-constrained">
    <h2 class="wp-block-heading my-5" style="font-size:32px;">[TITRE]</h2>
    <ul class="wp-block-list key-figures">
      <li><div class="wp-block-media-text is-stacked-on-mobile background-1"><div class="wp-block-media-text__content"><p class="title">[CHIFFRE]</p><p class="text">[LABEL]</p></div></div></li>
      <!-- 4-6 items -->
    </ul>
  </div>
</div>

4. ACTU BUSINESS (id="genui-business") :
<div class="container" id="genui-business">
  <div class="wp-block-group wide-bg-green">
    <div class="block-carrousel-articles business">
      <div class="container">
        <div class="articles-header"><div class="title-wrapper"><h2>[TITRE]</h2></div></div>
        <div class="articles">
          <article class="article-container"><div class="article">
            <div class="image"><img class="genui-image" data-generate="[DESCRIPTION]" alt="" loading="lazy"></div>
            <div class="info">
              <div class="categories"><a class="btn" style="--cat-bg: #4ba5dc;" href="#">[CATEGORIE]</a></div>
              <h3 class="article-title"><a href="#">[TITRE ARTICLE]</a></h3>
            </div>
          </div></article>
          <!-- 3-4 articles -->
        </div>
      </div>
    </div>
  </div>
</div>

EXEMPLES DE SUJETS :
- "pret auto" → page credit automobile avec taux, durees, avantages, image de voiture
- "pret immobilier" → page credit immobilier avec simulation, taux, image maison
- "credit conso" → page credit a la consommation, montants, conditions
- "rachat de credits" → page rachat/regroupement de credits
- "qui etes vous" → page institutionnelle BNP Paribas Personal Finance / Cetelem
- Si le message est juste un salut ou question generale, reponds normalement sans generer de HTML (pas de |||GENUI_HTML|||), et sans dire "Attendez je personnalise"
"""


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/themes/<path:filename>")
def serve_theme_assets(filename):
    """Serve theme assets (fonts, background images) referenced by real BNP PF CSS."""
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
    print("BNP Paribas Personal Finance - GenUI Server")
    print(f"  Claude: {DEPLOYMENT_ANTHROPIC} @ {ENDPOINT_ANTHROPIC}")
    print(f"  FLUX:   {DEPLOYMENT_FLUX} @ {AZURE_OPENAI_ENDPOINT}")
    app.run(debug=True, host="0.0.0.0", port=5000)
