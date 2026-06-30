"""
多向量数据库管理
支持动态创建/删除数据库，多库联合搜索
"""
import json
import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings

import config
from security import validate_db_id
from embedding import embedder

logger = logging.getLogger(__name__)


class VectorDatabase:
    """单个向量数据库"""

    def __init__(self, db_id: str, name: str, description: str = ""):
        db_id = validate_db_id(db_id)
        self.db_id = db_id
        self.name = name
        self.description = description
        self.persist_dir = config.VECTORS_DIR / db_id
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
        self.collection = self.client.get_or_create_collection(
            name=f"{db_id}_collection",
            metadata={"db_id": db_id, "name": name, "description": description}
        )

    def add(self, texts: List[str], metadatas: List[Dict] = None, ids: List[str] = None) -> List[str]:
        if ids is None:
            ids = [f"{self.db_id}_{uuid.uuid4().hex[:8]}" for _ in texts]
        if metadatas is None:
            metadatas = [{} for _ in texts]
        for m in metadatas:
            m["db_id"] = self.db_id

        embeddings = embedder.embed(texts)
        self.collection.add(documents=texts, embeddings=embeddings, metadatas=metadatas, ids=ids)
        return ids

    def search(self, query: str, n_results: int = 10) -> List[Dict]:
        embedding = embedder.embed([query])[0]
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=n_results
        )
        formatted = []
        if results["documents"] and len(results["documents"]) > 0:
            for i, doc in enumerate(results["documents"][0]):
                formatted.append({
                    "text": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "score": 1 - results["distances"][0][i] if results["distances"] else 0.0,
                    "db_id": self.db_id,
                    "db_name": self.name
                })
        return formatted

    def count(self) -> int:
        return self.collection.count()

    def clear(self):
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.create_collection(
            name=f"{self.db_id}_collection",
            metadata={"db_id": self.db_id, "name": self.name, "description": self.description}
        )

    def update(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.collection.modify(
            metadata={"db_id": self.db_id, "name": name, "description": description}
        )

    def list_files(self) -> List[Dict]:
        if self.count() == 0:
            return []
        results = self.collection.get(include=["metadatas"])
        files_map = {}
        for meta in results["metadatas"]:
            source = meta.get("source", "未知文件")
            ftype = meta.get("type", "unknown")
            if source not in files_map:
                files_map[source] = {"filename": source, "type": ftype, "chunks": 0}
            files_map[source]["chunks"] += 1
        return sorted(list(files_map.values()), key=lambda x: x["filename"])

    def get_by_source(self, source: str) -> List[Dict]:
        if self.count() == 0:
            return []
        results = self.collection.get(
            where={"source": source},
            include=["documents", "metadatas"]
        )
        items = []
        for i, doc in enumerate(results["documents"]):
            meta = results["metadatas"][i]
            items.append({
                "text": doc,
                "metadata": meta,
                "score": 1.0,
                "db_name": self.name
            })
        return items

    def delete(self):
        shutil.rmtree(self.persist_dir, ignore_errors=True)


class DatabaseManager:
    """多数据库管理器"""

    def __init__(self):
        self.databases: Dict[str, VectorDatabase] = {}
        self._registry = self._load_registry()
        self._init_databases()

    def _load_registry(self) -> Dict[str, Dict]:
        if config.DB_REGISTRY_FILE.exists():
            with open(config.DB_REGISTRY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_registry(self):
        with open(config.DB_REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(self._registry, f, ensure_ascii=False, indent=2)

    def _init_databases(self):
        for db_id, info in self._registry.items():
            try:
                self.databases[db_id] = VectorDatabase(
                    db_id=db_id,
                    name=info.get("name", db_id),
                    description=info.get("description", "")
                )
                logger.info(f"加载数据库: {db_id}")
            except Exception as e:
                logger.error(f"加载数据库 {db_id} 失败: {e}")

    def create(self, db_id: str, name: str, description: str = "") -> VectorDatabase:
        db_id = validate_db_id(db_id)
        if db_id in self.databases:
            raise ValueError(f"数据库 '{db_id}' 已存在")
        db = VectorDatabase(db_id, name, description)
        self.databases[db_id] = db
        self._registry[db_id] = {
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat()
        }
        self._save_registry()
        logger.info(f"创建数据库: {db_id}")
        return db

    def delete(self, db_id: str):
        db_id = validate_db_id(db_id)
        if db_id not in self.databases:
            raise ValueError(f"数据库 '{db_id}' 不存在")
        self.databases[db_id].delete()
        del self.databases[db_id]
        del self._registry[db_id]
        self._save_registry()
        logger.info(f"删除数据库: {db_id}")

    def get(self, db_id: str) -> VectorDatabase:
        db_id = validate_db_id(db_id)
        if db_id not in self.databases:
            raise ValueError(f"数据库 '{db_id}' 不存在")
        return self.databases[db_id]

    def update(self, db_id: str, name: str, description: str = "") -> VectorDatabase:
        db_id = validate_db_id(db_id)
        if db_id not in self.databases:
            raise ValueError(f"数据库 '{db_id}' 不存在")
        db = self.databases[db_id]
        db.update(name, description)
        self._registry[db_id]["name"] = name
        self._registry[db_id]["description"] = description
        self._save_registry()
        logger.info(f"更新数据库: {db_id}")
        return db

    def list(self) -> List[Dict]:
        result = []
        for db_id, db in self.databases.items():
            info = self._registry.get(db_id, {})
            result.append({
                "db_id": db_id,
                "name": db.name,
                "description": db.description,
                "document_count": db.count(),
                "created_at": info.get("created_at", "")
            })
        return result

    def search(self, query: str, db_ids: Optional[List[str]] = None, n_results: int = 10) -> Dict[str, List[Dict]]:
        target_ids = [validate_db_id(db_id) for db_id in db_ids] if db_ids else list(self.databases.keys())
        results = {}
        for db_id in target_ids:
            if db_id in self.databases:
                try:
                    results[db_id] = self.databases[db_id].search(query, n_results)
                except Exception as e:
                    logger.error(f"搜索数据库 {db_id} 失败: {e}")
                    results[db_id] = []
        return results

    def search_all(self, query: str, n_results: int = 10) -> List[Dict]:
        all_results = []
        for db_id, db in self.databases.items():
            try:
                results = db.search(query, n_results)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"搜索数据库 {db_id} 失败: {e}")
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return all_results


db_manager = DatabaseManager()
