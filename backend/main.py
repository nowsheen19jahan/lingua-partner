import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .routers import chat, grammar, health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.gemini_api_key:
        logger.warning(
            "GEMINI_API_KEY is not set. "
            "Chat endpoints will return 503. "
            "Add your key to .env — get one free at https://aistudio.google.com/app/apikey"
        )
    else:
        logger.info("Gemini API configured (model: %s)", settings.gemini_model)
        # Warm up the client singleton
        try:
            from .gemma_client import get_client
            get_client()
        except RuntimeError as exc:
            logger.error("Failed to initialise Gemini client: %s", exc)
    yield
    logger.info("Shutting down Lingua Partner.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description="AI-powered language learning partner backed by Google Gemini.",
    lifespan=lifespan,
)

# CORS — allow all origins by default (tighten for production as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(grammar.router)

# Serve the frontend as static files
app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR / "static")),
    name="static",
)

# Catch-all: serve index.html for root and any unmatched path
from fastapi.responses import FileResponse  # noqa: E402


@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    target = FRONTEND_DIR / full_path
    if target.exists() and target.is_file():
        return FileResponse(str(target))
    return FileResponse(str(FRONTEND_DIR / "index.html"))
