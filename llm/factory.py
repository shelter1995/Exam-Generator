"""
LLM 客户端工厂
支持多模型切换：硅基流动、MiniMax、Kimi、火山方舟、GLM、OpenAI、Anthropic、Qwen、DeepSeek、自定义
"""
import logging
from typing import Dict, Optional, List

import config
from .base import BaseLLM
from .minimax import MiniMaxClient
from .openai import OpenAIClient
from .anthropic import AnthropicClient
from .qwen import QwenClient
from .deepseek import DeepSeekClient

logger = logging.getLogger(__name__)

LLM_PROVIDERS: Dict[str, type] = {
    "siliconflow": OpenAIClient,
    "minimax": MiniMaxClient,
    "kimi": OpenAIClient,
    "volcengine": OpenAIClient,
    "glm": OpenAIClient,
    "openai": OpenAIClient,
    "anthropic": AnthropicClient,
    "qwen": QwenClient,
    "deepseek": DeepSeekClient,
    "custom": OpenAIClient,
}


def get_llm_config(provider: str) -> Dict[str, str]:
    provider_config = config.get_provider_config(provider)
    if provider_config:
        result = {
            "api_key": provider_config.get("api_key", ""),
            "base_url": provider_config.get("base_url", ""),
            "model": provider_config.get("model", ""),
            "api_type": provider_config.get("api_type", "openai_compatible"),
        }
        if not result["model"]:
            defaults = config.LLM_PROVIDER_DEFAULTS.get(provider, {})
            result["model"] = defaults.get("model", "")
            result["base_url"] = result["base_url"] or defaults.get("base_url", "")
        return result
    return {}


def create_llm_client(
    provider: str = None,
    model: str = None,
    api_key: str = None,
    base_url: str = None,
    **kwargs
) -> BaseLLM:
    if provider is None:
        provider = config.get_active_provider_id()

    provider = provider.lower()

    if provider not in LLM_PROVIDERS:
        raise ValueError(
            f"不支持的 LLM 提供商: {provider}。"
            f"支持的提供商: {', '.join(LLM_PROVIDERS.keys())}"
        )

    llm_config = get_llm_config(provider)
    final_api_key = api_key or llm_config.get("api_key", "")
    final_base_url = base_url or llm_config.get("base_url", "")
    final_model = model or llm_config.get("model")

    client_class = LLM_PROVIDERS[provider]

    init_kwargs = {"api_key": final_api_key, "model": final_model}
    if final_base_url and provider != "anthropic":
        init_kwargs["base_url"] = final_base_url
    for k, v in llm_config.items():
        if k not in ("api_key", "model") and k not in init_kwargs:
            init_kwargs[k] = v

    client = client_class(**init_kwargs)

    error = client.validate_config()
    if error:
        logger.warning(f"LLM 配置警告: {error}")

    logger.info(f"创建 LLM 客户端: {provider}/{final_model}")
    return client


def get_available_providers() -> List[Dict]:
    result = []
    for pid, defaults in config.LLM_PROVIDER_DEFAULTS.items():
        provider_config = config.get_provider_config(pid)
        is_configured = bool(provider_config.get("api_key"))
        current_model = provider_config.get("model", "") or defaults.get("model", "")

        models = []
        client_class = LLM_PROVIDERS.get(pid)
        if client_class and hasattr(client_class, 'get_available_models'):
            try:
                models = client_class.get_available_models()
            except Exception:
                pass

        result.append({
            "id": pid,
            "name": defaults.get("name", pid),
            "description": defaults.get("description", ""),
            "base_url": provider_config.get("base_url", "") or defaults.get("base_url", ""),
            "api_type": defaults.get("api_type", "openai_compatible"),
            "models": models,
            "is_configured": is_configured,
            "current_model": current_model
        })

    return result

llm = None
