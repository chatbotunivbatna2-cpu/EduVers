import os
import json
import logging
import redis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
DEFAULT_TTL = int(os.getenv('CACHE_DEFAULT_TTL', 300))

try:
    _r = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=2)
    _r.ping()
    logger.info('redis connected, cache active')
except Exception:
    _r = None
    logger.warning('redis unavailable, continuing without cache')

def cache_get(key):
    if _r is None:
        return None
    try:
        val = _r.get(key)
        if val:
            return json.loads(val)
    except Exception:
        pass
    return None

def cache_set(key, data, ttl=None):
    if _r is None:
        return
    try:
        _r.setex(key, ttl or DEFAULT_TTL, json.dumps(data, ensure_ascii=False))
    except Exception:
        pass
