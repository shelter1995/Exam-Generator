"""
Anthropic Claude LLM 客户端
"""
import logging
from typing import Optional

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from .base import BaseLLM

logger = logging.getLogger(__name__)


class AnthropicClient(BaseLLM):
    """Anthropic Claude 客户端"""

    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def __init__(
        self,
        api_key: str,
        model: str = None,
        **kwargs
    ):
        super().__init__(api_key, model or self.DEFAULT_MODEL)

        if ANTHROPIC_AVAILABLE:
            self.client = anthropic.Anthropic(api_key=api_key)
        else:
            self.client = None
            logger.warning("Anthropic SDK 未安装，将使用 HTTP 请求")

    def chat(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 8192,
        **kwargs
    ) -> str:
        if not self.api_key:
            raise ValueError("Anthropic API key 未配置")

        if ANTHROPIC_AVAILABLE and self.client:
            return self._chat_with_sdk(prompt, temperature, max_tokens)
        else:
            return self._chat_with_http(prompt, temperature, max_tokens)

    def _chat_with_sdk(self, prompt: str, temperature: float, max_tokens: int) -> str:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text if response.content else ""
        except Exception as e:
            logger.error(f"Anthropic SDK 调用失败: {e}")
            raise RuntimeError(f"Claude API 调用失败: {e}")

    def _chat_with_http(self, prompt: str, temperature: float, max_tokens: int) -> str:
        import requests as req

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}]
        }

        try:
            resp = req.post(url, headers=headers, json=data, timeout=(30, 180))
            resp.raise_for_status()
            result = resp.json()
            return result["content"][0]["text"] if result.get("content") else ""
        except Exception as e:
            logger.error(f"Anthropic HTTP 调用失败: {e}")
            raise RuntimeError(f"Claude API 调用失败: {e}")

    def get_model_name(self) -> str:
        return self.model

    def validate_config(self) -> Optional[str]:
        if not self.api_key:
            return "Anthropic API key 未配置，请在 .env 中设置 ANTHROPIC_API_KEY"
        return None

    @classmethod
    def get_available_models(cls) -> list:
        """获取支持的模型列表"""
        return [
            {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "description": "最新高性能模型"},
            {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "description": "强大且快速"},
            {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku", "description": "轻量快速"},
            {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "description": "最强推理能力"},
        ]
