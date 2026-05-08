"""
DeepSeek LLM 客户端
"""
import logging
from typing import Optional

from .base import BaseLLM

logger = logging.getLogger(__name__)


class DeepSeekClient(BaseLLM):
    """DeepSeek 客户端"""

    DEFAULT_MODEL = "deepseek-chat"
    DEFAULT_BASE_URL = "https://api.deepseek.com"

    def __init__(
        self,
        api_key: str,
        model: str = None,
        base_url: str = None,
        **kwargs
    ):
        super().__init__(api_key, model or self.DEFAULT_MODEL)
        self.base_url = base_url or self.DEFAULT_BASE_URL

    def chat(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 8192,
        **kwargs
    ) -> str:
        if not self.api_key:
            raise ValueError("DeepSeek API key 未配置")

        import requests as req

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            resp = req.post(url, headers=headers, json=data, timeout=(30, 180))
            resp.raise_for_status()
            result = resp.json()
            return result["choices"][0]["message"]["content"] or ""
        except requests.exceptions.RequestException as e:
            logger.error(f"DeepSeek API 请求失败: {e}")
            raise RuntimeError(f"DeepSeek API 请求失败: {e}")
        except Exception as e:
            logger.error(f"DeepSeek 调用失败: {e}")
            raise

    def get_model_name(self) -> str:
        return self.model

    def validate_config(self) -> Optional[str]:
        if not self.api_key:
            return "DeepSeek API key 未配置，请在 .env 中设置 DEEPSEEK_API_KEY"
        return None

    @classmethod
    def get_available_models(cls) -> list:
        """获取支持的模型列表"""
        return [
            {"id": "deepseek-chat", "name": "DeepSeek Chat", "description": "通用对话模型"},
            {"id": "deepseek-coder", "name": "DeepSeek Coder", "description": "代码专用模型"},
            {"id": "deepseek-prover", "name": "DeepSeek Prover", "description": "数学推理专用"},
        ]
