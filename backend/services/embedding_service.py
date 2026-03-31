"""
Embedding service: wraps Ollama's nomic-embed-text model.
Returns int8-quantized bytes for storage in sqlite-vec.
Uses a small LRU cache to avoid re-embedding identical texts.
"""
import os
import struct
import asyncio
from functools import lru_cache
from typing import Optional

import httpx

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = "nomic-embed-text"
EMBEDDING_DIM = 768


async def embed(text: str) -> Optional[bytes]:
    """
    Embed text using nomic-embed-text via Ollama.
    Returns bytes (int8-quantized float32 vector) for sqlite-vec storage, or None on error.
    """
    text = text.strip()
    if not text:
        return None

    # Check LRU cache (synchronous lookup by hash)
    cache_key = _hash_text(text)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{OLLAMA_BASE}/api/embeddings",
                json={"model": EMBED_MODEL, "prompt": text},
            )
            resp.raise_for_status()
            floats = resp.json().get("embedding", [])
            if not floats or len(floats) != EMBEDDING_DIM:
                print(f"WARNING: Unexpected embedding dim: {len(floats)}")
                return None
            quantized = _quantize_int8(floats)
            _set_cached(cache_key, quantized)
            return quantized
    except Exception as e:
        print(f"ERROR: Embedding failed: {e}")
        return None


def _quantize_int8(floats: list[float]) -> bytes:
    """
    Quantize float32 embeddings to int8 for 4x storage savings.
    Maps the range [min, max] → [-127, 127].
    """
    min_val = min(floats)
    max_val = max(floats)
    scale = max(abs(min_val), abs(max_val)) or 1.0
    ints = [max(-127, min(127, int(round(v / scale * 127)))) for v in floats]
    return struct.pack(f"{len(ints)}b", *ints)


def _hash_text(text: str) -> str:
    import hashlib
    return hashlib.md5(text.encode()).hexdigest()


# ── Simple thread-safe LRU cache (128 entries) ────────────────────────────────
_cache: dict[str, bytes] = {}
_cache_order: list[str] = []
_CACHE_MAX = 128


def _get_cached(key: str) -> Optional[bytes]:
    return _cache.get(key)


def _set_cached(key: str, value: bytes):
    if key in _cache:
        _cache_order.remove(key)
    elif len(_cache) >= _CACHE_MAX:
        oldest = _cache_order.pop(0)
        del _cache[oldest]
    _cache[key] = value
    _cache_order.append(key)


async def check_embed_model_available() -> bool:
    """Verify nomic-embed-text is available in Ollama."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_BASE}/api/tags")
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
            available = any(EMBED_MODEL in m for m in models)
            if not available:
                print(f"WARNING: '{EMBED_MODEL}' not found in Ollama. Run: ollama pull {EMBED_MODEL}")
            return available
    except Exception as e:
        print(f"ERROR: Cannot reach Ollama for embedding check: {e}")
        return False
