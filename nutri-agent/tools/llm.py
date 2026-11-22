"""Shared Gemini chat model, so every LLM call in the process shares one rate limit."""

from functools import lru_cache

from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_google_genai import ChatGoogleGenerativeAI

from config import settings


@lru_cache(maxsize=1)
def get_chat_model() -> ChatGoogleGenerativeAI:
    """
    Built once per process so the rate limiter's budget is shared by the agent
    and the replanner (including concurrent API / Streamlit requests).
    """
    rate_limiter = InMemoryRateLimiter(
        requests_per_second=settings.gemini_rpm / 60,
        check_every_n_seconds=0.5,
        max_bucket_size=1,   # no bursts — space calls evenly
    )
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=0.2,
        max_retries=settings.gemini_max_retries,
        rate_limiter=rate_limiter,
    )


def is_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc)
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg
