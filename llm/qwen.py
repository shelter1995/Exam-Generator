"""
通义千问（Qwen）LLM 客户端
"""
import logging
from typing import Optional

from .base import BaseLLM

logger = logging.getLogger(__name__)


class QwenClient(BaseLLM):
    """通义千问（Qwen）客户端"""

    DEFAULT_MODEL = "qwen-plus"
    DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

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
            raise ValueError("DashScope API key 未配置")

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
            logger.error(f"Qwen API 请求失败: {e}")
            raise RuntimeError(f"Qwen API 请求失败: {e}")
        except Exception as e:
            logger.error(f"Qwen 调用失败: {e}")
            raise

    def get_model_name(self) -> str:
        return self.model

    def validate_config(self) -> Optional[str]:
        if not self.api_key:
            return "DashScope API key 未配置，请在 .env 中设置 DASHSCOPE_API_KEY"
        return None

    @classmethod
    def get_available_models(cls) -> list:
        """获取支持的模型列表"""
        return [
            {"id": "qwen-plus", "name": "Qwen Plus", "description": "通义千问Plus，能力强"},
            {"id": "qwen-turbo", "name": "Qwen Turbo", "description": "速度快，适合简单任务"},
            {"id": "qwen-max", "name": "Qwen Max", "description": "最强推理能力"},
            {"id": "qwen-coder-plus", "name": "Qwen Coder Plus", "description": "代码能力增强"},
        ]
