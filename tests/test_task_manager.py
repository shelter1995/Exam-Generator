from tasks import TaskManager


def test_task_manager_tracks_successful_task():
    manager = TaskManager(max_workers=1)
    task_id = manager.submit("测试任务", lambda: {"ok": True})
    task = manager.wait(task_id, timeout=5)

    assert task["status"] == "success"
    assert task["result"] == {"ok": True}
    assert task["error"] == ""


def test_task_manager_tracks_failed_task():
    manager = TaskManager(max_workers=1)

    def fail():
        raise RuntimeError("失败")

    task_id = manager.submit("失败任务", fail)
    task = manager.wait(task_id, timeout=5)

    assert task["status"] == "failed"
    assert "失败" in task["error"]
