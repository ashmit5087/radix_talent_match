import logging
from typing import Optional
from supabase import Client, create_client
from .config import settings

logger = logging.getLogger(__name__)

_supabase_client: Optional[Client] = None
_client_initialized: bool = False


def get_supabase_client() -> Optional[Client]:
    """
    Returns the initialized Supabase client if valid credentials are provided,
    otherwise returns None to trigger local fallback repository mode.
    """
    global _supabase_client, _client_initialized

    if _client_initialized:
        return _supabase_client

    url = (settings.SUPABASE_URL or "").strip()
    key = (settings.SUPABASE_KEY or "").strip()

    is_placeholder = (
        not url
        or not key
        or "your-project" in url
        or "placeholder" in url
        or "your-supabase" in key
    )

    if is_placeholder:
        logger.info(
            "Supabase credentials not configured or using placeholders. "
            "Backend will operate in robust in-memory persistence mode."
        )
        _supabase_client = None
    else:
        try:
            _supabase_client = create_client(url, key)
            logger.info(f"Supabase client successfully initialized for URL: {url[:25]}...")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}. Falling back to in-memory mode.")
            _supabase_client = None

    _client_initialized = True
    return _supabase_client


def reset_supabase_client_for_testing():
    """Helper used during test fixtures to reset client state."""
    global _supabase_client, _client_initialized
    _supabase_client = None
    _client_initialized = False
