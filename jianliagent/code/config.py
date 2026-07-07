"""
系统配置：DeepSeek API、Redis 缓存、文件限制等。
所有敏感信息通过环境变量注入，遵循 12-Factor App。
"""
import os

# ---- DeepSeek API 配置 ----
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")  # deepseek-chat 或 deepseek-reasoner

# ---- 缓存配置 ----
CACHE_TYPE = os.getenv("CACHE_TYPE", "memory")  # memory | redis

# Redis 配置（CACHE_TYPE=redis 时生效）
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_TTL = int(os.getenv("REDIS_TTL", "3600"))  # 缓存有效期（秒），默认 1 小时

# 内存缓存 TTL
MEMORY_CACHE_TTL = int(os.getenv("MEMORY_CACHE_TTL", "3600"))

# ---- 文件上传限制 ----
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))  # 最大上传文件大小（MB）
ALLOWED_EXTENSIONS = {"pdf"}

# ---- FC 环境检测 ----
IS_FC = os.getenv("FC_SERVICE_NAME", "") != ""
