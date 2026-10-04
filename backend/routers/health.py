from fastapi import APIRouter

from ..config import get_settings
from ..models import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Liveness probe used by Render and the frontend status indicator.
    Checks whether the Gemini API is reachable with the configured key.
    """
    settings = get_settings()

    # Lazy import to avoid forcing GemmaClient init on every health check
    # when the API key might not be set yet during cold start
    reachable = False
    try:
        from ..gemma_client import get_client
        client = get_client()
        reachable = await client.is_reachable()
    except RuntimeError:
        # API key not configured
        reachable = False

    return HealthResponse(
        status="ok" if reachable else "degraded",
        api_reachable=reachable,
        model=settings.gemini_model,
    )
