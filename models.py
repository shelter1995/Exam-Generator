"""
Pydantic 数据模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class DatabaseInfo(BaseModel):
    db_id: str
    name: str
    description: str = ""
    document_count: int = 0
    created_at: str = ""


class CreateDatabaseRequest(BaseModel):
    db_id: str
    name: str
    description: str = ""


class UpdateDatabaseRequest(BaseModel):
    name: str
    description: str = ""


class SearchRequest(BaseModel):
    query: str
    db_ids: Optional[List[str]] = None
    n_results: int = 10


class QuestionTypeConfig(BaseModel):
    type: str = Field(..., pattern="^(single_choice|multi_choice|judge|essay)$")
    count: int = Field(..., ge=1, le=100)
    score_per_question: int = Field(..., ge=1, le=100)


class SourceFileConfig(BaseModel):
    db_id: str
    filename: str


class GenerateExamRequest(BaseModel):
    title: str
    db_ids: List[str]
    queries: List[str] = []
    source_files: Optional[List[SourceFileConfig]] = None
    question_types: List[QuestionTypeConfig]
    exam_time: str = "90分钟"
    passing_score: int = 60
    n_results_per_query: int = 15
    merge_db_results: bool = True
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None


class ExamPreview(BaseModel):
    title: str
    total_questions: int
    total_score: int
    exam_time: str
    passing_score: int
    content: str


class LLMProviderSetting(BaseModel):
    provider_id: str
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    api_type: str = "openai_compatible"


class LLMSettingsRequest(BaseModel):
    active_provider: Optional[str] = None
    providers: List[LLMProviderSetting] = []


class LLMTestRequest(BaseModel):
    provider_id: str
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    api_type: str = "openai_compatible"
