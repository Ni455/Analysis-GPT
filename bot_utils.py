# bot_utils.py — Shared utilities for the Telegram bot
import time

TELEGRAM_MAX_CHARS = 4096


def split_chunks(text: str, max_len: int = TELEGRAM_MAX_CHARS) -> list[str]:
    """Split text into chunks of at most max_len characters."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        chunks.append(text[:max_len])
        text = text[max_len:]
    return chunks


def is_authorized(user_id: int, allowed_id: int) -> bool:
    """Return True if user_id matches the allowed user."""
    return user_id == allowed_id


def retry_call(func, max_retries: int = 3, base_delay: float = 1.0):
    """
    Call func(), retrying up to max_retries times on any exception.
    Delay doubles each retry: base_delay -> 2*base_delay -> 4*base_delay.
    Raises the last exception if all retries are exhausted.
    """
    last_exc = None
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exc = e
            if attempt < max_retries - 1:
                time.sleep(base_delay * (2 ** attempt))
    raise last_exc
