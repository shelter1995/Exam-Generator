"""
轻量级后台任务管理
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Lock
from typing import Any, Callable, Dict
import uuid


class TaskManager:
    """进程内任务管理器，适合本地单机长任务。"""

    def __init__(self, max_workers: int = 2):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self._futures = {}
        self._lock = Lock()

    def submit(self, name: str, func: Callable[..., Any], *args, **kwargs) -> str:
        task_id = uuid.uuid4().hex
        now = datetime.now().isoformat()
        with self._lock:
            self.tasks[task_id] = {
                "task_id": task_id,
                "name": name,
                "status": "pending",
                "created_at": now,
                "started_at": "",
                "finished_at": "",
                "result": None,
                "error": "",
            }

        future = self.executor.submit(self._run, task_id, func, *args, **kwargs)
        with self._lock:
            self._futures[task_id] = future
        return task_id

    def _run(self, task_id: str, func: Callable[..., Any], *args, **kwargs):
        with self._lock:
            self.tasks[task_id]["status"] = "running"
            self.tasks[task_id]["started_at"] = datetime.now().isoformat()
        try:
            result = func(*args, **kwargs)
            with self._lock:
                self.tasks[task_id]["status"] = "success"
                self.tasks[task_id]["result"] = result
                self.tasks[task_id]["finished_at"] = datetime.now().isoformat()
            return result
        except Exception as exc:
            with self._lock:
                self.tasks[task_id]["status"] = "failed"
                self.tasks[task_id]["error"] = str(exc)
                self.tasks[task_id]["finished_at"] = datetime.now().isoformat()
            raise

    def get(self, task_id: str) -> Dict[str, Any]:
        with self._lock:
            if task_id not in self.tasks:
                raise KeyError(task_id)
            return dict(self.tasks[task_id])

    def wait(self, task_id: str, timeout: float | None = None) -> Dict[str, Any]:
        future = self._futures[task_id]
        try:
            future.result(timeout=timeout)
        except Exception:
            pass
        return self.get(task_id)
