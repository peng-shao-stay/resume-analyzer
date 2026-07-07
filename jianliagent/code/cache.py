"""
缓存模块：支持内存缓存和 Redis 两种后端。
避免重复解析和 AI 调用，节省成本和时间。
"""
import time
import json
import threading
from config import (
    CACHE_TYPE, REDIS_HOST, REDIS_PORT, REDIS_PASSWORD,
    REDIS_DB, REDIS_TTL, MEMORY_CACHE_TTL,
)


class MemoryCache:
    """线程安全的内存缓存，带 TTL 过期机制。"""

    def __init__(self):
        self._store: dict = {}
        self._lock = threading.Lock()

    def get(self, key: str):
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.time() > entry["expires_at"]:
                del self._store[key]
                return None
            return entry["data"]

    def set(self, key: str, data, ttl: int = None):
        ttl = ttl or MEMORY_CACHE_TTL
        with self._lock:
            self._store[key] = {
                "data": data,
                "expires_at": time.time() + ttl,
            }

    def delete(self, key: str):
        with self._lock:
            self._store.pop(key, None)

    def clear(self):
        with self._lock:
            self._store.clear()


class RedisCache:
    """Redis 缓存后端。"""

    def __init__(self):
        import redis
        self.client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD or None,
            db=REDIS_DB,
            decode_responses=True,
        )

    def get(self, key: str):
        data = self.client.get(key)
        if data:
            return json.loads(data)
        return None

    def set(self, key: str, data, ttl: int = None):
        ttl = ttl or REDIS_TTL
        self.client.setex(key, ttl, json.dumps(data, ensure_ascii=False, default=str))

    def delete(self, key: str):
        self.client.delete(key)


def get_cache():
    """工厂方法：根据配置返回缓存实例。"""
    if CACHE_TYPE == "redis":
        try:
            return RedisCache()
        except Exception:
            # Redis 连接失败时降级到内存缓存
            return MemoryCache()
    return MemoryCache()


# 全局缓存实例
cache = get_cache()
