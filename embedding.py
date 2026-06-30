"""
文本嵌入模型封装
"""
import logging
from typing import List
import config

logger = logging.getLogger(__name__)


class EmbeddingModel:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.model = None
        self._initialized = True

    @property
    def is_loaded(self) -> bool:
        return self.model is not None

    def _load(self):
        if self.model is not None:
            return
        from sentence_transformers import SentenceTransformer

        logger.info(f"加载Embedding模型: {config.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(config.EMBEDDING_MODEL)
        logger.info("Embedding模型加载完成")

    def embed(self, texts: List[str]) -> List[List[float]]:
        if isinstance(texts, str):
            texts = [texts]
        self._load()
        embeddings = self.model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return embeddings.tolist() if hasattr(embeddings, "tolist") else embeddings


embedder = EmbeddingModel()
