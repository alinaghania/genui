# GenUI — BNP Paribas Personal Finance

**GenUI** est une demo interactive qui reproduit le site [BNP Paribas Personal Finance](https://personal-finance.bnpparibas/) avec un chatbot Cetelem capable de **muter le contenu de la page en temps reel** via l'IA generative.

L'utilisateur pose une question dans le chatbot (ex: "credit auto", "pret immobilier"), et la page se transforme dynamiquement : le hero, les articles, les chiffres cles, les temoignages... tout le contenu est regenere par **Claude Opus** et les images par **FLUX**.

## Architecture

```
┌─────────────────────────────────────────────┐
│  Frontend (HTML/CSS/JS)                     │
│  - Replique exacte du vrai site BNP PF      │
│  - Chatbot Cetelem en bas a droite           │
│  - Injection progressive des sections HTML   │
│  - Generation d'images via FLUX              │
└──────────────┬──────────────────────────────┘
               │ SSE streaming
┌──────────────▼──────────────────────────────┐
│  Backend Flask (app.py)                      │
│  - Claude Opus 4 (AnthropicFoundry)          │
│  - FLUX.1-Kontext-pro (Azure OpenAI)         │
│  - Streaming SSE vers le frontend            │
│  - Retry logic pour generation d'images      │
└─────────────────────────────────────────────┘
```

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| LLM | Claude Opus via Azure (AnthropicFoundry SDK) |
| Image Gen | FLUX.1-Kontext-pro via Azure OpenAI |
| Backend | Python / Flask |
| Frontend | HTML5, CSS3 (CSS reel du site BNP PF), JavaScript vanilla |
| Streaming | Server-Sent Events (SSE) |

## Fonctionnalites

- **Chatbot Cetelem** : widget en bas a droite, style professionnel bancaire
- **GenUI progressif** : les sections HTML sont injectees une par une pendant le streaming (pas d'attente de la reponse complete)
- **Generation d'images** : chaque section peut contenir des images generees par FLUX avec retry automatique
- **CSS reel** : utilise le vrai CSS du site BNP Paribas Personal Finance (490 KB)
- **Assets reels** : logos, icones, fonts BNPP, images d'articles du vrai site

## Installation

```bash
# Cloner le repo
git clone https://github.com/alinaghania/genui.git
cd genui

# Creer un environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer les dependances
pip install -r requirements.txt
```

## Configuration

Creer un fichier `.env` a la racine du projet avec les variables suivantes :

```env
# Azure OpenAI — FLUX image generation
AZURE_OPENAI_ENDPOINT=https://your-endpoint.cognitiveservices.azure.com/
DEPLOYMENT_NAME=FLUX.1-Kontext-pro
OPENAI_API_VERSION=2025-04-01-preview
api_key=your_flux_api_key

# Azure Anthropic — Claude Opus
ENDPOINT_ANTHROPIC=https://your-endpoint.services.ai.azure.com/anthropic/
DEPLOYMENT_NAME_ANTHROPIC=claude-opus-4-6
API_KEY_ANTHROPIC=your_claude_api_key
```

> **Ne jamais committer le fichier `.env`** — il est dans le `.gitignore`.

## Lancement

```bash
source venv/bin/activate
python app.py
```

Le serveur demarre sur [http://localhost:5000](http://localhost:5000).

## Utilisation

1. Ouvrir http://localhost:5000
2. Cliquer sur le widget Cetelem en bas a droite
3. Taper une requete (ex: "credit auto", "pret immobilier", "rachat de credits")
4. Observer la page se transformer en temps reel

## Structure du projet

```
├── app.py                          # Backend Flask (Claude + FLUX)
├── requirements.txt                # Dependances Python
├── .env                            # Variables d'environnement (non committe)
├── .gitignore
├── README.md
└── static/
    ├── index.html                  # Page principale (replique BNP PF)
    ├── style.css                   # CSS chatbot + GenUI overrides
    ├── app.js                      # GenUI Engine v5 (streaming progressif)
    ├── css/
    │   ├── bnppf-real.css          # CSS reel du site BNP PF (490 KB)
    │   ├── hero.css                # CSS plugin hero
    │   └── highlight-box.css       # CSS plugin highlight-box
    ├── img/                        # Logos, icones, images d'articles
    └── themes/                     # Fonts BNPP, background images CSS
```
