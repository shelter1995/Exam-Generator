"""
系统配置管理
"""
import os
import json
from pathlib import Path
from typing import Dict, Optional

# 加载 .env 文件
from dotenv import load_dotenv
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

STORAGE_DIR = BASE_DIR / "storage"
FILES_DIR = STORAGE_DIR / "files"
VECTORS_DIR = STORAGE_DIR / "vectors"

FILES_DIR.mkdir(parents=True, exist_ok=True)
VECTORS_DIR.mkdir(parents=True, exist_ok=True)

# 支持的文件类型
SUPPORTED_DOCUMENTS = [".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".md", ".py", ".js", ".html", ".json"]
SUPPORTED_AUDIO = [".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".wma"]
SUPPORTED_VIDEO = [".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"]
ALL_SUPPORTED = SUPPORTED_DOCUMENTS + SUPPORTED_AUDIO + SUPPORTED_VIDEO

# ========== 模型路径配置 ==========
# 优先复用 rag-core 已有的本地模型，避免重复下载

# --- Embedding 模型 (BGE-M3) ---
# 尝试多个可能的本地路径，按优先级排列
BGE_M3_CANDIDATES = [
    BASE_DIR / "models" / "bge-m3",
]
EMBEDDING_MODEL = "BAAI/bge-m3"  # 默认从 HuggingFace 下载
for candidate in BGE_M3_CANDIDATES:
    if candidate.exists() and (candidate / "config.json").exists():
        EMBEDDING_MODEL = str(candidate)
        print(f"[INFO] 使用本地 BGE-M3 模型: {candidate}")
        break
else:
    print(f"[WARN] 未找到本地 BGE-M3 模型，将尝试从 HuggingFace 下载: BAAI/bge-m3")
    print(f"[WARN] 若无网络，请手动下载模型放到 models/bge-m3/ 目录")

# --- Whisper 模型 (base) ---
WHISPER_CANDIDATES = [
    BASE_DIR / "models" / "whisper" / "base.pt",
]
WHISPER_MODEL_PATH = None
for candidate in WHISPER_CANDIDATES:
    if candidate.exists():
        WHISPER_MODEL_PATH = str(candidate)
        # 设置 whisper 环境变量，让它直接使用本地模型
        os.environ["WHISPER_CACHE_DIR"] = str(candidate.parent)
        print(f"[INFO] 使用本地 Whisper 模型: {candidate}")
        break

# 文本分块
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50

# API 配置
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# MiniMax
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.chat/v1")
MINIMAX_MODEL = os.getenv("MINIMAX_MODEL", "MiniMax-M2.7")

# OpenAI API 配置（可选）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Anthropic Claude API 配置（可选）
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

# 通义千问（DashScope）API 配置（可选）
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-plus")

# DeepSeek API 配置（可选）
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 默认 LLM 提供商（可选：minimax, openai, anthropic, qwen, deepseek）
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "minimax")

# --- FFmpeg 路径 ---
FFMPEG_CANDIDATES = [
    BASE_DIR / "ffmpeg.exe",
    BASE_DIR / "bin" / "ffmpeg.exe",
]
# 尝试查找以 ffmpeg 开头的文件夹中的 ffmpeg.exe
for subdir in BASE_DIR.iterdir():
    if subdir.is_dir() and "ffmpeg" in subdir.name.lower():
        candidate = subdir / "bin" / "ffmpeg.exe"
        if candidate.exists():
            FFMPEG_CANDIDATES.insert(0, candidate)

FFMPEG_PATH = None
for candidate in FFMPEG_CANDIDATES:
    if candidate.exists():
        FFMPEG_PATH = str(candidate)
        print(f"[INFO] 使用本地 FFmpeg: {candidate}")
        break

# 数据库注册表
DB_REGISTRY_FILE = STORAGE_DIR / "db_registry.json"

# ========== LLM 运行时配置 ==========

LLM_CONFIG_FILE = STORAGE_DIR / "llm_config.json"

LLM_PROVIDER_DEFAULTS: Dict[str, Dict] = {
    "siliconflow": {
        "name": "硅基流动",
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "Qwen/Qwen2.5-72B-Instruct",
        "api_type": "openai_compatible",
        "description": "硅基流动 SiliconFlow，支持多种开源模型"
    },
    "minimax": {
        "name": "MiniMax",
        "base_url": "https://api.minimax.chat/v1",
        "model": "MiniMax-M2.7",
        "api_type": "minimax",
        "description": "国内 AI 公司，MiniMax-M2.7 模型"
    },
    "kimi": {
        "name": "Kimi（月之暗面）",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-128k",
        "api_type": "openai_compatible",
        "description": "月之暗面 Kimi，长上下文模型"
    },
    "volcengine": {
        "name": "火山方舟",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "",
        "api_type": "openai_compatible",
        "description": "火山方舟，需填入接入点 ID 作为模型名"
    },
    "glm": {
        "name": "GLM（智谱）",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-plus",
        "api_type": "openai_compatible",
        "description": "智谱 AI GLM-4 系列模型"
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "api_type": "openai_compatible",
        "description": "GPT-4o, GPT-4 等强大模型"
    },
    "anthropic": {
        "name": "Anthropic Claude",
        "base_url": "https://api.anthropic.com",
        "model": "claude-sonnet-4-20250514",
        "api_type": "anthropic",
        "description": "Claude 3.5 Sonnet, Claude 3 Opus 等"
    },
    "qwen": {
        "name": "通义千问",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
        "api_type": "openai_compatible",
        "description": "阿里云 Qwen 系列模型"
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "api_type": "openai_compatible",
        "description": "性价比高的国产模型"
    },
    "custom": {
        "name": "自定义",
        "base_url": "",
        "model": "",
        "api_type": "openai_compatible",
        "description": "自定义 OpenAI 兼容接口"
    }
}


def load_llm_config() -> Dict:
    if LLM_CONFIG_FILE.exists():
        try:
            with open(LLM_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    config = _migrate_env_to_config()
    save_llm_config(config)
    return config


def save_llm_config(config: Dict) -> None:
    LLM_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LLM_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_provider_config(provider_id: str) -> Optional[Dict]:
    runtime_config = load_llm_config()
    providers = runtime_config.get("providers", {})
    if provider_id in providers:
        return providers[provider_id]
    defaults = LLM_PROVIDER_DEFAULTS.get(provider_id, {})
    return {
        "base_url": defaults.get("base_url", ""),
        "api_key": "",
        "model": defaults.get("model", ""),
        "api_type": defaults.get("api_type", "openai_compatible")
    }


def get_active_provider_id() -> str:
    runtime_config = load_llm_config()
    return runtime_config.get("active_provider", "minimax")


def _migrate_env_to_config() -> Dict:
    env_mapping = {
        "minimax": {
            "api_key": os.getenv("MINIMAX_API_KEY", ""),
            "base_url": os.getenv("MINIMAX_BASE_URL", "https://api.minimax.chat/v1"),
            "model": os.getenv("MINIMAX_MODEL", "MiniMax-M2.7"),
        },
        "openai": {
            "api_key": os.getenv("OPENAI_API_KEY", ""),
            "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "model": os.getenv("OPENAI_MODEL", "gpt-4o"),
        },
        "anthropic": {
            "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
            "model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        },
        "qwen": {
            "api_key": os.getenv("DASHSCOPE_API_KEY", ""),
            "base_url": os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            "model": os.getenv("QWEN_MODEL", "qwen-plus"),
        },
        "deepseek": {
            "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
            "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        },
    }

    providers = {}
    for pid, defaults in LLM_PROVIDER_DEFAULTS.items():
        if pid in env_mapping:
            env_vals = env_mapping[pid]
            providers[pid] = {
                "base_url": env_vals.get("base_url", defaults.get("base_url", "")),
                "api_key": env_vals.get("api_key", ""),
                "model": env_vals.get("model", defaults.get("model", "")),
                "api_type": defaults.get("api_type", "openai_compatible"),
            }
        else:
            providers[pid] = {
                "base_url": defaults.get("base_url", ""),
                "api_key": "",
                "model": defaults.get("model", ""),
                "api_type": defaults.get("api_type", "openai_compatible"),
            }

    active_provider = os.getenv("LLM_PROVIDER", "minimax")
    return {"active_provider": active_provider, "providers": providers}
