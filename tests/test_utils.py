import pytest

def test_send_chunks_short_message():
    """Messages under 4096 chars yield exactly one chunk."""
    from bot_utils import split_chunks
    chunks = split_chunks("hello world")
    assert chunks == ["hello world"]

def test_send_chunks_long_message():
    """Messages over 4096 chars are split into multiple chunks."""
    from bot_utils import split_chunks
    long_msg = "A" * 5000
    chunks = split_chunks(long_msg)
    assert len(chunks) == 2
    assert all(len(c) <= 4096 for c in chunks)
    assert "".join(chunks) == long_msg

def test_send_chunks_empty():
    """Empty string returns one empty chunk."""
    from bot_utils import split_chunks
    chunks = split_chunks("")
    assert chunks == [""]

def test_is_authorized_matching_id():
    """Returns True when user_id matches ALLOWED_USER_ID."""
    from bot_utils import is_authorized
    assert is_authorized(123456, allowed_id=123456) is True

def test_is_authorized_wrong_id():
    """Returns False when user_id does not match."""
    from bot_utils import is_authorized
    assert is_authorized(999999, allowed_id=123456) is False

def test_retry_success_on_first_try():
    """retry_call returns the value when func succeeds immediately."""
    from bot_utils import retry_call
    result = retry_call(lambda: 42)
    assert result == 42

def test_retry_success_after_failures():
    """retry_call retries and returns on eventual success."""
    from bot_utils import retry_call
    attempts = {"n": 0}
    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise ConnectionError("fail")
        return "ok"
    result = retry_call(flaky, max_retries=3, base_delay=0)
    assert result == "ok"
    assert attempts["n"] == 3

def test_retry_raises_after_max():
    """retry_call raises the last exception after max_retries exhausted."""
    from bot_utils import retry_call
    def always_fail():
        raise ConnectionError("always")
    with pytest.raises(ConnectionError):
        retry_call(always_fail, max_retries=3, base_delay=0)
