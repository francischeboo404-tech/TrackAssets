"""
Redis-backed caching utility with automatic in-memory fallback.

Set REDIS_URL or REDISCLOUD_URL env var to enable Redis persistence.
Without it, a process-local TTL dict is used (works perfectly for dev
and single-worker deployments; no cross-worker sharing).

Quick usage:
    from app.cache import cache, cached

    # Manual:
    cache.set("key", data, ttl=60)
    value = cache.get("key")      # None on miss/expiry
    cache.delete("key")
    cache.delete_pattern("dashboard:*")

    # Decorator:
    @cached(ttl=120, key_template="summary:{0}:{1}")
    def get_summary(org_id, warehouse_id):
        ...
"""
import json
import logging
import os
import time
from functools import wraps

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# In-memory backend
# ---------------------------------------------------------------------------
class _MemoryCache:
    def __init__(self):
        self._store = {}  # key -> (value, expires_at)

    def get(self, key):
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key, value, ttl=60):
        self._store[key] = (value, time.time() + ttl)

    def delete(self, key):
        self._store.pop(key, None)

    def delete_pattern(self, pattern):
        prefix = pattern.rstrip("*")
        for k in list(self._store.keys()):
            if k.startswith(prefix):
                del self._store[k]

    def flush(self):
        self._store.clear()

    @property
    def backend(self):
        return "memory"


# ---------------------------------------------------------------------------
# Redis backend
# ---------------------------------------------------------------------------
class _RedisCache:
    def __init__(self, client):
        self._r = client

    def get(self, key):
        try:
            raw = self._r.get(key)
            return json.loads(raw) if raw is not None else None
        except Exception as exc:
            logger.warning("Redis GET key=%s error=%s", key, exc)
            return None

    def set(self, key, value, ttl=60):
        try:
            self._r.setex(key, ttl, json.dumps(value, default=str))
        except Exception as exc:
            logger.warning("Redis SET key=%s error=%s", key, exc)

    def delete(self, key):
        try:
            self._r.delete(key)
        except Exception as exc:
            logger.warning("Redis DEL key=%s error=%s", key, exc)

    def delete_pattern(self, pattern):
        try:
            keys = self._r.keys(pattern)
            if keys:
                self._r.delete(*keys)
        except Exception as exc:
            logger.warning("Redis DEL PATTERN pattern=%s error=%s", pattern, exc)

    def flush(self):
        try:
            self._r.flushdb()
        except Exception as exc:
            logger.warning("Redis FLUSH error=%s", exc)

    @property
    def backend(self):
        return "redis"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def _build_cache():
    redis_url = os.environ.get("REDIS_URL") or os.environ.get("REDISCLOUD_URL")
    if not redis_url:
        logger.info("No REDIS_URL set — using in-memory cache (process-local, no persistence)")
        return _MemoryCache()
    try:
        import redis as _redis  # type: ignore[import]
        client = _redis.from_url(
            redis_url,
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=True,
        )
        client.ping()
        safe_url = redis_url.split("@")[-1] if "@" in redis_url else redis_url
        logger.info("Redis cache connected: %s", safe_url)
        return _RedisCache(client)
    except Exception as exc:
        logger.warning("Redis unavailable — falling back to memory cache: %s", exc)
        return _MemoryCache()


# Module-level singleton — created once when app starts
cache = _build_cache()


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------
def cached(ttl=60, key_template=""):
    """
    Cache the return value of the decorated function.

    Args:
        ttl: Time-to-live in seconds.
        key_template: Python format string using positional indices.
                      e.g. "inventory:{0}:{1}" where {0}=org_id, {1}=warehouse_id.
                      If empty, the function's fully-qualified name is used.

    The decorated function gets an `.invalidate(*args)` method that
    deletes the corresponding cache entry.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if key_template:
                try:
                    key = key_template.format(*args)
                except (IndexError, KeyError):
                    key = fn.__module__ + "." + fn.__name__
            else:
                key = fn.__module__ + "." + fn.__name__

            hit = cache.get(key)
            if hit is not None:
                return hit

            result = fn(*args, **kwargs)
            if result is not None:
                cache.set(key, result, ttl=ttl)
            return result

        def _invalidate(*args):
            if key_template:
                try:
                    key = key_template.format(*args)
                except (IndexError, KeyError):
                    key = fn.__module__ + "." + fn.__name__
            else:
                key = fn.__module__ + "." + fn.__name__
            cache.delete(key)

        wrapper.invalidate = _invalidate
        return wrapper
    return decorator
