"""
安全工具函数
"""
import re
from pathlib import Path
from typing import Iterable


MAX_FILENAME_LENGTH = 120
DB_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def validate_db_id(db_id: str) -> str:
    """校验数据库 ID，避免路径穿越和非法 Chroma collection 名称。"""
    if not isinstance(db_id, str) or not DB_ID_PATTERN.fullmatch(db_id):
        raise ValueError("数据库 ID 只能包含字母、数字、下划线和短横线，且长度为 1-64")
    return db_id


def ensure_safe_child_path(base_dir: Path, filename: str) -> Path:
    """确保 filename 解析后仍位于 base_dir 目录下。"""
    if not filename or Path(filename).name != filename:
        raise ValueError("文件名不合法")
    base = base_dir.resolve()
    target = (base / filename).resolve()
    if base != target.parent and base not in target.parents:
        raise ValueError("文件路径越界")
    return target


def sanitize_upload_filename(filename: str, allowed_extensions: Iterable[str]) -> str:
    """净化上传文件名并校验扩展名。"""
    raw_name = Path(filename or "").name
    if not raw_name:
        raise ValueError("文件名不能为空")

    ext = Path(raw_name).suffix.lower()
    allowed = {e.lower() for e in allowed_extensions}
    if ext not in allowed:
        raise ValueError(f"不支持的文件格式: {ext or '无扩展名'}")

    stem = Path(raw_name).stem.strip().strip(".")
    safe_stem = "".join(c if c.isalnum() or c in "_-" else "_" for c in stem)
    safe_stem = re.sub(r"_+", "_", safe_stem).strip("_") or "upload"

    max_stem_len = MAX_FILENAME_LENGTH - len(ext)
    safe_stem = safe_stem[:max_stem_len].rstrip("_") or "upload"
    return f"{safe_stem}{ext}"


def unique_child_path(base_dir: Path, filename: str) -> Path:
    """生成不覆盖既有文件的安全子路径。"""
    path = ensure_safe_child_path(base_dir, filename)
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    for idx in range(1, 10_000):
        candidate_name = f"{stem}_{idx}{suffix}"
        candidate = ensure_safe_child_path(base_dir, candidate_name)
        if not candidate.exists():
            return candidate
    raise ValueError("无法生成唯一文件名")
