import importlib
import sys
import types


def test_embedding_model_is_not_loaded_during_module_import(monkeypatch):
    calls = {"created": 0}

    class FakeSentenceTransformer:
        def __init__(self, model_name):
            calls["created"] += 1
            self.model_name = model_name

        def encode(self, texts, show_progress_bar=False, convert_to_numpy=True):
            return [[0.1, 0.2] for _ in texts]

    fake_module = types.SimpleNamespace(SentenceTransformer=FakeSentenceTransformer)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    sys.modules.pop("embedding", None)

    module = importlib.import_module("embedding")

    assert calls["created"] == 0
    assert module.embedder.is_loaded is False
    assert module.embedder.embed(["测试"]) == [[0.1, 0.2]]
    assert calls["created"] == 1
