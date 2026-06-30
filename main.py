"""
FastAPI 主入口
"""
import os
import sys

# 确保项目根目录在 sys.path 中（嵌入式 Python 兼容性）
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from llm import get_available_providers
import config
from database import db_manager
from parser import parse
from exam import generate_exam, count_questions
from security import (
    ensure_safe_child_path,
    sanitize_upload_filename,
    unique_child_path,
    validate_db_id,
)
from tasks import TaskManager
from models import (
    CreateDatabaseRequest, UpdateDatabaseRequest, SearchRequest,
    GenerateExamRequest, ExamPreview, DatabaseInfo,
    LLMSettingsRequest, LLMTestRequest
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="智能知识库出题系统", version="2.0.0")
task_manager = TaskManager(max_workers=2)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.API_CORS_ORIGINS or ["*"],
    allow_credentials="*" not in config.API_CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ========== 首页 ==========

@app.get("/")
def root():
    return FileResponse(str(static_dir / "index.html"))


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/api/health")
def health_check():
    """健康检查"""
    from embedding import embedder

    return {
        "status": "ok",
        "version": "2.0.0",
        "databases": len(db_manager.databases),
        "embedding_loaded": embedder.is_loaded,
        "max_upload_size_mb": config.MAX_UPLOAD_SIZE_MB,
    }


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    """查询后台任务状态"""
    try:
        return task_manager.get(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="任务不存在")


# ========== 数据库管理 ==========

@app.get("/api/databases")
def list_databases():
    """列出所有数据库"""
    return {"databases": db_manager.list()}


@app.post("/api/databases")
def create_database(req: CreateDatabaseRequest):
    """创建新数据库"""
    try:
        validate_db_id(req.db_id)
        db = db_manager.create(req.db_id, req.name, req.description)
        return {"status": "success", "db_id": req.db_id, "name": req.name}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/databases/{db_id}")
def delete_database(db_id: str):
    """删除数据库"""
    try:
        validate_db_id(db_id)
        db_manager.delete(db_id)
        return {"status": "success", "message": f"数据库 {db_id} 已删除"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.put("/api/databases/{db_id}")
def update_database(db_id: str, req: UpdateDatabaseRequest):
    """修改数据库信息"""
    try:
        validate_db_id(db_id)
        db = db_manager.update(db_id, req.name, req.description)
        return {"status": "success", "db_id": db_id, "name": db.name, "description": db.description}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/databases/{db_id}/files")
def list_database_files(db_id: str):
    """列出数据库中已有的文件"""
    try:
        validate_db_id(db_id)
        db = db_manager.get(db_id)
        files = db.list_files()
        return {"db_id": db_id, "files": files}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ========== 文件上传 ==========

def _save_upload(file: UploadFile) -> Path:
    safe_name = sanitize_upload_filename(file.filename or "", config.ALL_SUPPORTED)
    file_path = unique_child_path(config.FILES_DIR, safe_name)
    written = 0
    with open(file_path, "wb") as buffer:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            written += len(chunk)
            if written > config.MAX_UPLOAD_SIZE_BYTES:
                file_path.unlink(missing_ok=True)
                raise ValueError(f"文件超过大小限制：{config.MAX_UPLOAD_SIZE_MB} MB")
            buffer.write(chunk)
    return file_path


def _ingest_saved_file(file_path: Path, db_id: str) -> dict:
    validate_db_id(db_id)
    db = db_manager.get(db_id)
    result = parse(str(file_path), db_id=db_id)
    if result["texts"]:
        db.add(result["texts"], result["metadatas"], result["ids"])
    return {
        "status": "success",
        "filename": file_path.name,
        "db_id": db_id,
        "chunks": len(result["texts"])
    }


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), db_id: str = Form("default")):
    """上传文件到指定数据库"""
    try:
        validate_db_id(db_id)
        file_path = _save_upload(file)
        return _ingest_saved_file(file_path, db_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"上传失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload/task")
async def upload_file_task(file: UploadFile = File(...), db_id: str = Form("default")):
    """上传文件并创建后台入库任务"""
    try:
        validate_db_id(db_id)
        file_path = _save_upload(file)
        task_id = task_manager.submit(f"上传入库: {file_path.name}", _ingest_saved_file, file_path, db_id)
        return {"status": "accepted", "task_id": task_id, "filename": file_path.name, "db_id": db_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建上传任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload/batch")
async def upload_batch(
    files: List[UploadFile] = File(...),
    db_id: str = Form("default")
):
    """批量上传文件"""
    results = []
    for file in files:
        try:
            result = await upload_file(file, db_id)
            results.append(result)
        except Exception as e:
            results.append({"filename": file.filename, "status": "failed", "error": str(e)})
    return {"results": results}


# ========== 搜索 ==========

@app.post("/api/search")
def search(req: SearchRequest):
    """知识库搜索"""
    try:
        if req.db_ids:
            for db_id in req.db_ids:
                validate_db_id(db_id)
        if req.db_ids and len(req.db_ids) > 0:
            results = db_manager.search(req.query, req.db_ids, req.n_results)
        else:
            results = {"_all": db_manager.search_all(req.query, req.n_results)}
        return {"query": req.query, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 出题 ==========

def _generate_exam_response(req: GenerateExamRequest) -> dict:
    for db_id in req.db_ids:
        validate_db_id(db_id)

    # 1. 从多个数据库检索知识
    all_results = []

    if req.source_files and len(req.source_files) > 0:
        # 按文件出题模式
        for sf in req.source_files:
            try:
                validate_db_id(sf.db_id)
                db = db_manager.get(sf.db_id)
                results = db.get_by_source(sf.filename)
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"获取文件 {sf.filename} 失败: {e}")
    else:
        # 1. 从多个数据库检索知识
        for query in req.queries:
            if req.merge_db_results:
                # 合并所有指定数据库的结果
                for db_id in req.db_ids:
                    try:
                        db = db_manager.get(db_id)
                        results = db.search(query, req.n_results_per_query)
                        all_results.extend(results)
                    except Exception as e:
                        logger.warning(f"搜索数据库 {db_id} 失败: {e}")
            else:
                # 分别搜索每个数据库（取Top K）
                db_results = db_manager.search(query, req.db_ids, req.n_results_per_query)
                for db_id, results in db_results.items():
                    all_results.extend(results)

    # 去重并按相关度排序
    seen = set()
    unique_results = []
    for r in sorted(all_results, key=lambda x: x.get("score", 0), reverse=True):
        key = r["text"][:100]
        if key not in seen:
            seen.add(key)
            unique_results.append(r)

    if not unique_results:
        raise HTTPException(status_code=400, detail="未检索到任何知识内容，请先上传文件")

    # 2. 生成考卷
    exam_md = generate_exam(
        title=req.title,
        knowledge_results=unique_results,
        question_types=req.question_types,
        exam_time=req.exam_time,
        passing_score=req.passing_score,
        llm_provider=req.llm_provider,
        llm_model=req.llm_model,
        difficulty_distribution={
            "basic": req.difficulty_basic,
            "understanding": req.difficulty_understanding,
            "application": req.difficulty_application,
        }
    )

    # 3. 统计
    stats = count_questions(exam_md)
    total_questions = sum(q.count for q in req.question_types)

    # 4. 保存文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c if c.isalnum() or c in "_-" else "_" for c in req.title).strip("_") or "exam"
    filename = f"{safe_title}_{timestamp}.md"
    filepath = ensure_safe_child_path(config.EXAMS_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(exam_md)
        f.write(f"\n\n---\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**数据来源**: {', '.join(req.db_ids)}\n")
        f.write(f"**搜索关键词**: {', '.join(req.queries)}\n")
        f.write(f"**题目统计**: 单选 {stats['single']} | 多选 {stats['multi']} | 判断 {stats['judge']} | 简答 {stats['essay']}\n")

    return {
        "status": "success",
        "filename": filename,
        "filepath": str(filepath),
        "preview": exam_md[:2000],
        "stats": {
            "expected": total_questions,
            "single": stats["single"],
            "multi": stats["multi"],
            "judge": stats["judge"],
            "essay": stats["essay"]
        }
    }


@app.post("/api/exam/generate")
def generate_exam_endpoint(req: GenerateExamRequest):
    """生成考题（支持关键词搜索或按文件出题）"""
    try:
        return _generate_exam_response(req)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"出题失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/exam/generate/task")
def generate_exam_task(req: GenerateExamRequest):
    """创建后台出题任务"""
    try:
        task_id = task_manager.submit(f"生成考卷: {req.title}", _generate_exam_response, req)
        return {"status": "accepted", "task_id": task_id}
    except Exception as e:
        logger.error(f"创建出题任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/exam/download/{filename}")
def download_exam(filename: str):
    """下载考卷"""
    try:
        filepath = ensure_safe_child_path(config.EXAMS_DIR, filename)
        if filepath.suffix.lower() != ".md":
            raise ValueError("只能下载 Markdown 考卷")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(str(filepath), filename=filename, media_type="text/markdown")


@app.delete("/api/exam/{filename}")
def delete_exam(filename: str):
    """删除已生成的考卷"""
    try:
        filepath = ensure_safe_child_path(config.EXAMS_DIR, filename)
        if filepath.suffix.lower() != ".md":
            raise ValueError("只能删除 Markdown 考卷")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    filepath.unlink()
    return {"status": "success", "message": f"考卷 {filename} 已删除"}


@app.get("/api/exam/list")
def list_exams():
    """列出已生成的考卷"""
    exam_dir = config.EXAMS_DIR
    exam_dir.mkdir(exist_ok=True)
    files = sorted(exam_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return {
        "exams": [
            {
                "filename": f.name,
                "size": f.stat().st_size,
                "created": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            }
            for f in files[:50]
        ]
    }


# ========== LLM 模型管理 ==========

@app.get("/api/llm/providers")
def list_llm_providers():
    """获取所有可用的 LLM 提供商"""
    try:
        providers = get_available_providers()
        return {"providers": providers}
    except Exception as e:
        logger.error(f"获取 LLM 提供商失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/llm/config")
def get_llm_config():
    """获取当前 LLM 配置"""
    try:
        runtime_config = config.load_llm_config()
        result = {
            "default_provider": config.get_active_provider_id(),
        }
        for pid, defaults in config.LLM_PROVIDER_DEFAULTS.items():
            provider_config = config.get_provider_config(pid)
            result[pid] = {
                "name": defaults.get("name", pid),
                "model": provider_config.get("model", "") or defaults.get("model", ""),
                "base_url": provider_config.get("base_url", "") or defaults.get("base_url", ""),
                "configured": bool(provider_config.get("api_key")),
                "api_type": defaults.get("api_type", "openai_compatible"),
            }
        return result
    except Exception as e:
        logger.error(f"获取 LLM 配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/llm/settings")
def get_llm_settings():
    """获取 LLM 设置（含所有提供商配置）"""
    try:
        runtime_config = config.load_llm_config()
        providers = {}
        for pid, defaults in config.LLM_PROVIDER_DEFAULTS.items():
            provider_config = config.get_provider_config(pid)
            providers[pid] = {
                "name": defaults.get("name", pid),
                "description": defaults.get("description", ""),
                "base_url": provider_config.get("base_url", "") or defaults.get("base_url", ""),
                "api_key": provider_config.get("api_key", ""),
                "model": provider_config.get("model", "") or defaults.get("model", ""),
                "api_type": defaults.get("api_type", "openai_compatible"),
                "is_configured": bool(provider_config.get("api_key")),
            }
        return {
            "active_provider": config.get_active_provider_id(),
            "providers": providers,
        }
    except Exception as e:
        logger.error(f"获取 LLM 设置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/llm/settings")
def save_llm_settings(req: LLMSettingsRequest):
    """保存 LLM 设置"""
    try:
        runtime_config = config.load_llm_config()
        if "providers" not in runtime_config:
            runtime_config["providers"] = {}

        for p in req.providers:
            pid = p.provider_id
            provider_data = {
                "base_url": p.base_url,
                "api_key": p.api_key,
                "model": p.model,
                "api_type": p.api_type,
            }
            if pid in runtime_config["providers"] and not p.api_key:
                old_key = runtime_config["providers"][pid].get("api_key", "")
                if old_key:
                    provider_data["api_key"] = old_key
            runtime_config["providers"][pid] = provider_data

        if req.active_provider:
            runtime_config["active_provider"] = req.active_provider

        config.save_llm_config(runtime_config)
        return {"status": "success", "message": "LLM 设置已保存"}
    except Exception as e:
        logger.error(f"保存 LLM 设置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/llm/test")
def test_llm_connection(req: LLMTestRequest):
    """测试 LLM 连接"""
    try:
        if not req.api_key:
            return {"success": False, "message": "API Key 不能为空"}

        base_url = req.base_url
        model = req.model
        api_type = req.api_type

        if not base_url:
            defaults = config.LLM_PROVIDER_DEFAULTS.get(req.provider_id, {})
            base_url = defaults.get("base_url", "")
        if not model:
            defaults = config.LLM_PROVIDER_DEFAULTS.get(req.provider_id, {})
            model = defaults.get("model", "")

        if not base_url and req.provider_id != "anthropic":
            return {"success": False, "message": "Base URL 不能为空"}

        if not model:
            return {"success": False, "message": "模型名称不能为空"}

        if api_type == "minimax":
            from llm.factory import create_llm_client
            client = create_llm_client(
                provider="minimax",
                model=model,
                api_key=req.api_key,
                base_url=base_url
            )
            response = client.chat("请回复：连接测试成功", temperature=0.1, max_tokens=50)
        elif api_type == "anthropic":
            from llm.factory import create_llm_client
            client = create_llm_client(
                provider="anthropic",
                model=model,
                api_key=req.api_key,
            )
            response = client.chat("Please reply: Connection test successful", temperature=0.1, max_tokens=50)
        else:
            from llm.factory import create_llm_client
            client = create_llm_client(
                provider="openai",
                model=model,
                api_key=req.api_key,
                base_url=base_url
            )
            response = client.chat("请回复：连接测试成功", temperature=0.1, max_tokens=50)

        return {"success": True, "message": f"连接成功！模型回复: {response[:200]}"}
    except ValueError as e:
        return {"success": False, "message": str(e)}
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg or "authentication" in error_msg.lower():
            return {"success": False, "message": f"认证失败：API Key 无效或已过期"}
        elif "404" in error_msg or "Not Found" in error_msg:
            return {"success": False, "message": f"接口地址错误或模型不存在：{error_msg[:200]}"}
        elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            return {"success": False, "message": f"连接超时，请检查网络或 Base URL"}
        else:
            return {"success": False, "message": f"连接失败: {error_msg[:300]}"}


# ========== 启动 ==========

def configure_stdio():
    """Windows 终端输出使用 UTF-8，避免作为模块导入时破坏测试捕获。"""
    import io
    if hasattr(sys.stdout, "detach"):
        sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
    if hasattr(sys.stderr, "detach"):
        sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')


def open_browser(host: str, port: int, delay: float = 2.0):
    import threading
    import webbrowser
    def _open():
        import time
        time.sleep(delay)
        webbrowser.open(f"http://127.0.0.1:{port}")
    threading.Thread(target=_open, daemon=True).start()

if __name__ == "__main__":
    configure_stdio()
    print(f"[*] 启动智能知识库出题系统")
    print(f"[*] API: http://127.0.0.1:{config.API_PORT}")
    print(f"[*] 文档: http://127.0.0.1:{config.API_PORT}/docs")
    open_browser(config.API_HOST, config.API_PORT)
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)
