"""
MiniMax LLM 客户端
"""
import logging
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .base import BaseLLM

logger = logging.getLogger(__name__)


class MiniMaxClient(BaseLLM):
    """MiniMax LLM 客户端（带连接池和自动重试）"""

    DEFAULT_BASE_URL = "https://api.minimax.chat/v1"
    DEFAULT_MODEL = "MiniMax-M2.7"

    def __init__(
        self,
        api_key: str,
        base_url: str = None,
        model: str = None,
        **kwargs
    ):
        super().__init__(api_key, model or self.DEFAULT_MODEL)
        self.base_url = base_url or self.DEFAULT_BASE_URL

        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[502, 503, 504],
            allowed_methods=["POST", "GET"]
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=5, pool_maxsize=10)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def chat(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 8192,
        **kwargs
    ) -> str:
        if not self.api_key:
            raise ValueError("MiniMax API key 未配置")

        url = f"{self.base_url}/text/chatcompletion_v2"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            resp = self.session.post(url, headers=headers, json=data, timeout=(30, 180))
            resp.raise_for_status()
            result = resp.json()
            if result.get("base_resp", {}).get("status_code", 0) != 0:
                err_msg = result.get("base_resp", {}).get("status_msg", "未知错误")
                logger.error(f"MiniMax API 返回错误: {err_msg}")
                raise RuntimeError(f"MiniMax API 错误: {err_msg}")
            choice = result["choices"][0]
            content = choice.get("message", {}).get("content", "")
            if not content:
                msgs = choice.get("messages", [])
                if msgs:
                    content = msgs[-1].get("text", msgs[-1].get("content", ""))
            return content
        except requests.exceptions.ConnectTimeout as e:
            logger.error(f"MiniMax API 连接超时: {e}")
            raise RuntimeError("MiniMax API 连接超时，请检查网络或稍后重试")
        except requests.exceptions.ReadTimeout as e:
            logger.error(f"MiniMax API 读取超时: {e}")
            raise RuntimeError("MiniMax API 响应超时，请减少题量或稍后重试")
        except requests.exceptions.RequestException as e:
            logger.error(f"MiniMax API 请求失败: {e}")
            raise RuntimeError(f"MiniMax API 请求失败: {e}")
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            raise

    def get_model_name(self) -> str:
        return self.model

    def validate_config(self) -> Optional[str]:
        if not self.api_key:
            return "MiniMax API key 未配置，请在 .env 中设置 MINIMAX_API_KEY"
        return None
