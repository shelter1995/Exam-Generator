"""
OpenAI LLM 客户端（支持 GPT-4、GPT-4o 等）
"""
import logging
from typing import Optional

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from .base import BaseLLM

logger = logging.getLogger(__name__)


class OpenAIClient(BaseLLM):
    """OpenAI GPT 客户端"""

    DEFAULT_MODEL = "gpt-4o"

    def __init__(
        self,
        api_key: str,
        model: str = None,
        base_url: str = None,
        **kwargs
    ):
        super().__init__(api_key, model or self.DEFAULT_MODEL)
        self.base_url = base_url or "https://api.openai.com/v1"

        if OPENAI_AVAILABLE:
            self.client = openai.OpenAI(
                api_key=api_key,
                base_url=self.base_url
            )
        else:
            self.client = None
            logger.warning("OpenAI SDK 未安装，将使用 HTTP 请求")

    def chat(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 8192,
        **kwargs
    ) -> str:
        if not self.api_key:
            raise ValueError("OpenAI API key 未配置")

        if OPENAI_AVAILABLE and self.client:
            return self._chat_with_sdk(prompt, temperature, max_tokens)
        else:
            return self._chat_with_http(prompt, temperature, max_tokens)

    def _chat_with_sdk(self, prompt: str, temperature: float, max_tokens: int) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI SDK 调用失败: {e}")
            raise RuntimeError(f"OpenAI API 调用失败: {e}")

    def _chat_with_http(self, prompt: str, temperature: float, max_tokens: int) -> str:
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
        except Exception as e:
            logger.error(f"OpenAI HTTP 调用失败: {e}")
            raise RuntimeError(f"OpenAI API 调用失败: {e}")

    def get_model_name(self) -> str:
        return self.model

    def validate_config(self) -> Optional[str]:
        if not self.api_key:
            return "OpenAI API key 未配置，请在 .env 中设置 OPENAI_API_KEY"
        return None

    @classmethod
    def get_available_models(cls) -> list:
        """获取支持的模型列表"""
        return [
            {"id": "gpt-4o", "name": "GPT-4o", "description": "最新最强模型，速度快"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "description": "轻量版，性价比高"},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "description": "高速版 GPT-4"},
            {"id": "gpt-4", "name": "GPT-4", "description": "标准 GPT-4 模型"},
        ]
