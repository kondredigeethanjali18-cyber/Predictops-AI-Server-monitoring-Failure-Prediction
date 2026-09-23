import os
import time
import json
import logging
import threading
from functools import wraps
from typing import Any, Optional, Dict, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Environment Configuration
REDIS_URL = os.getenv("REDIS_URL", os.getenv("REDIS_URI", "")).strip()
REDIS_HOST = os.getenv("REDIS_HOST", "localhost").strip()
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
ENABLE_CACHE = os.getenv("ENABLE_CACHE", "true").lower() in ("true", "1", "yes")

# In-Memory Cache Store: key -> (value, expiry_timestamp, created_at)
_MEMORY_CACHE: Dict[str, Tuple[Any, float, float]] = {}
_CACHE_LOCK = threading.RLock()

# Cache Performance Metrics
_STATS = {
    "hits": 0,
    "misses": 0,
    "sets": 0,
    "deletes": 0,
    "invalidations": 0,
    "start_time": time.time()
}

# Optional Redis Client instance
_REDIS_CLIENT = None
_REDIS_INITIALIZED = False


def _get_redis_client():
    """Initializes and returns the Redis client if reachable, otherwise None."""
    global _REDIS_CLIENT, _REDIS_INITIALIZED
    if _REDIS_INITIALIZED:
        return _REDIS_CLIENT

    _REDIS_INITIALIZED = True
    try:
        import redis
        if REDIS_URL:
            client = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
        else:
            client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                socket_connect_timeout=1,
                socket_timeout=1
            )
        client.ping()
        _REDIS_CLIENT = client
        logger.info(f"Connected to distributed Redis cache at {REDIS_URL or f'{REDIS_HOST}:{REDIS_PORT}'}")
        return _REDIS_CLIENT
    except Exception as exc:
        logger.info(f"Redis cache not reachable ({exc}). Running with high-speed In-Memory TTL cache.")
        _REDIS_CLIENT = None
        return None


class CacheService:
    """
    Hybrid Dual-Tier Cache Service:
    - Tier 1: Distributed Redis (if reachable)
    - Tier 2: Thread-Safe In-Memory TTL/LRU Cache (automatic fallback)
    """

    @staticmethod
    def get(key: str) -> Optional[Any]:
        """Retrieves a cached item by key if not expired."""
        if not ENABLE_CACHE:
            return None

        # 1. Try Redis first if available
        redis_client = _get_redis_client()
        if redis_client:
            try:
                raw_data = redis_client.get(f"predictops:{key}")
                if raw_data is not None:
                    _STATS["hits"] += 1
                    return json.loads(raw_data.decode("utf-8"))
            except Exception as e:
                logger.debug(f"Redis get error for {key}: {e}")

        # 2. Fall back to thread-safe in-memory cache
        now = time.time()
        with _CACHE_LOCK:
            entry = _MEMORY_CACHE.get(key)
            if entry:
                value, expiry, _ = entry
                if expiry > now:
                    _STATS["hits"] += 1
                    return value
                else:
                    # Prune expired item
                    del _MEMORY_CACHE[key]

            _STATS["misses"] += 1
            return None

    @staticmethod
    def set(key: str, value: Any, ttl: int = 5) -> bool:
        """Stores an item in the cache with a specified TTL in seconds."""
        if not ENABLE_CACHE:
            return False

        now = time.time()
        expiry = now + ttl

        # 1. Store in Redis if available
        redis_client = _get_redis_client()
        if redis_client:
            try:
                serialized = json.dumps(value, default=str)
                redis_client.setex(f"predictops:{key}", ttl, serialized)
            except Exception as e:
                logger.debug(f"Redis set error for {key}: {e}")

        # 2. Store in In-Memory cache
        with _CACHE_LOCK:
            _MEMORY_CACHE[key] = (value, expiry, now)
            _STATS["sets"] += 1
            # Auto-prune if memory cache exceeds 2000 keys
            if len(_MEMORY_CACHE) > 2000:
                CacheService._prune_expired()

        return True

    @staticmethod
    def delete(key: str) -> bool:
        """Deletes a specific key from all cache tiers."""
        redis_client = _get_redis_client()
        if redis_client:
            try:
                redis_client.delete(f"predictops:{key}")
            except Exception:
                pass

        with _CACHE_LOCK:
            if key in _MEMORY_CACHE:
                del _MEMORY_CACHE[key]
                _STATS["deletes"] += 1
                return True
        return False

    @staticmethod
    def invalidate_prefix(prefix: str) -> int:
        """Invalidates all keys matching a specific prefix (e.g. 'metrics:', 'predictions:')."""
        count = 0
        redis_client = _get_redis_client()
        if redis_client:
            try:
                keys = redis_client.keys(f"predictops:{prefix}*")
                if keys:
                    count += len(keys)
                    redis_client.delete(*keys)
            except Exception:
                pass

        with _CACHE_LOCK:
            matching = [k for k in _MEMORY_CACHE.keys() if k.startswith(prefix)]
            for k in matching:
                del _MEMORY_CACHE[k]
                count += 1
            _STATS["invalidations"] += 1

        return count

    @staticmethod
    def clear():
        """Clears all cached items."""
        redis_client = _get_redis_client()
        if redis_client:
            try:
                keys = redis_client.keys("predictops:*")
                if keys:
                    redis_client.delete(*keys)
            except Exception:
                pass

        with _CACHE_LOCK:
            _MEMORY_CACHE.clear()

    @staticmethod
    def _prune_expired():
        """Internal helper to clean up expired in-memory items."""
        now = time.time()
        expired = [k for k, (_, exp, _) in _MEMORY_CACHE.items() if exp <= now]
        for k in expired:
            del _MEMORY_CACHE[k]

    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """Returns comprehensive cache diagnostics and hit ratios."""
        now = time.time()
        with _CACHE_LOCK:
            active_mem_keys = sum(1 for _, exp, _ in _MEMORY_CACHE.values() if exp > now)
            total_requests = _STATS["hits"] + _STATS["misses"]
            hit_ratio = round((_STATS["hits"] / total_requests * 100), 2) if total_requests > 0 else 0.0

        redis_client = _get_redis_client()
        backend_name = "Redis (Distributed)" if redis_client else "In-Memory TTL/LRU (Thread-Safe)"

        return {
            "status": "active" if ENABLE_CACHE else "disabled",
            "backend": backend_name,
            "hits": _STATS["hits"],
            "misses": _STATS["misses"],
            "total_requests": total_requests,
            "hit_ratio_percent": f"{hit_ratio}%",
            "active_in_memory_keys": active_mem_keys,
            "uptime_seconds": round(now - _STATS["start_time"], 1)
        }


def cached_response(ttl: int = 4, key_prefix: str = ""):
    """
    Decorator for FastAPI endpoint handlers to cache JSON responses.
    Example:
        @router.get("/all-servers")
        @cached_response(ttl=4, key_prefix="metrics:all_servers")
        def all_servers():
            ...
    """
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache_key = key_prefix or f"route:{func.__module__}.{func.__name__}"
            cached_val = CacheService.get(cache_key)
            if cached_val is not None:
                return cached_val

            result = func(*args, **kwargs)
            if result is not None:
                CacheService.set(cache_key, result, ttl=ttl)
            return result

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache_key = key_prefix or f"route:{func.__module__}.{func.__name__}"
            cached_val = CacheService.get(cache_key)
            if cached_val is not None:
                return cached_val

            result = await func(*args, **kwargs)
            if result is not None:
                CacheService.set(cache_key, result, ttl=ttl)
            return result

        import asyncio
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator
