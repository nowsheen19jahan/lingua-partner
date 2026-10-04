# 🌍 Lingua Partner

An AI-powered language learning web app backed by **Google Gemini** (free API — no local model, no GPU, no disk space needed). Practice conversation, get grammar corrections, and build fluency — all in your browser.

---

## Features

| Feature | Detail |
|---|---|
| **Conversation mode** | Immersive back-and-forth practice with inline corrections |
| **Grammar correction mode** | Structured diff of errors + plain-language explanation |
| **14 languages** | Spanish, French, German, Italian, Portuguese, Japanese, Mandarin, Korean, Arabic, Russian, Hindi, Dutch, Polish, Turkish |
| **Session memory** | In-memory conversation history per browser session |
| **Health probe** | `/api/health` endpoint for Render and the status indicator |
| **Responsive UI** | Works on desktop and mobile |

---

## Project structure

```
lingua-partner/
├── backend/
│   ├── __init__.py
│   ├── main.py             # FastAPI app, CORS, static file serving
│   ├── config.py           # Settings (pydantic-settings, reads .env)
│   ├── models.py           # Pydantic request/response schemas
│   ├── gemma_client.py     # Async Google Gemini client
│   ├── session_store.py    # In-memory conversation history
│   ├── prompts.py          # System prompt builders
│   └── routers/
│       ├── chat.py         # POST /api/chat, DELETE /api/chat/{id}
│       ├── grammar.py      # POST /api/grammar
│       └── health.py       # GET /api/health
├── frontend/
│   ├── index.html
│   └── static/
│       ├── css/style.css
│       └── js/app.js
├── render.yaml             # Render deployment spec (single web service)
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Quick start (local)

### Prerequisites
- Python 3.11+
- A free Gemini API key → **https://aistudio.google.com/app/apikey**

### 1. Install dependencies
```powershell
cd lingua-partner
python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure environment
```powershell
copy .env.example .env
```
Open `.env` and replace `your_api_key_here` with your actual Gemini API key:
```
GEMINI_API_KEY=...
```

### 3. Run the server
```powershell
uvicorn backend.main:app --reload
```

Open **http://localhost:8000** in your browser.

---

## API reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/chat` | Send a message; returns AI reply + optional corrections |
| `DELETE` | `/api/chat/{session_id}` | Clear conversation history for a session |
| `POST` | `/api/grammar` | Standalone grammar check |
| `GET` | `/api/health` | Liveness probe — checks Gemini API reachability |

Interactive docs: **http://localhost:8000/docs**

---

## Deploy to Render

1. Push the repo to GitHub
2. In the [Render dashboard](https://dashboard.render.com) click **New → Blueprint** and connect your repo
3. Render reads `render.yaml` and creates the web service
4. Go to the service's **Environment** tab and add `GEMINI_API_KEY` with your key
5. Trigger a deploy — the app will be live in ~1 minute

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(required)* | Google AI Studio API key |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model name |
| `MAX_HISTORY_TURNS` | `20` | Conversation turns kept per session |
| `CORS_ORIGINS` | `*` | Allowed CORS origins (comma-separated) |

### Free tier limits
Gemini's free tier (as of mid-2025) gives you:
- **15 requests / minute**
- **1 million tokens / day**

That's more than enough for personal language practice.

---

## License

MIT
