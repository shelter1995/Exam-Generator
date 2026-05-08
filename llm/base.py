"""
LLM 模型基类定义
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseLLM(ABC):
    """LLM 模型抽象基类"""

    def __init__(self, api_key: str, model: str = None, **kwargs):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    def chat(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 8192,
        **kwargs
    ) -> str:
        """
        发送对话请求并返回响应内容

        Args:
            prompt: 用户输入的提示词
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成 token 数

        Returns:
            模型生成的文本内容
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """获取当前模型名称"""
        pass

    @classmethod
    def get_provider_name(cls) -> str:
        """获取提供商名称"""
        return cls.__name__.replace("Client", "").lower()

    def validate_config(self) -> Optional[str]:
        """
        验证配置是否正确

        Returns:
            错误信息，如果配置正确返回 None
        """
        if not self.api_key:
            return f"{self.get_provider_name()} API key 未配置"
        return None
