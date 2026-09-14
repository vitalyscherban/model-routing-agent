"""Token counting.

Uses tiktoken's cl100k_base when available so every number this project
reports is an exact count of the strings actually sent and returned, never an
estimate. If tiktoken is unavailable, a length/3.4 approximation is used and
`is_exact` is flipped false so a degraded run can never be mistaken for a
precise one.
"""
from __future__ import annotations

is_exact = True
_enc = None

try:
    import tiktoken

    _enc = tiktoken.get_encoding("cl100k_base")
except Exception:  # pragma: no cover - exercised only without tiktoken installed
    is_exact = False


def count(text: str) -> int:
    if not text:
        return 0
    if _enc is not None:
        return len(_enc.encode(text))
    return max(1, int(len(text) / 3.4))
