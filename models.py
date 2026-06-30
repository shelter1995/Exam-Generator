"""
Pydantic 数据模型
"""
from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Dict, Any


class DatabaseInfo(BaseModel):
    db_id: str
    name: str
    description: str = ""
    document_count: int = 0
    created_at: str = ""


class CreateDatabaseRequest(BaseModel):
    db_id: str = Field(..., pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""


class UpdateDatabaseRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    db_ids: Optional[List[str]] = None
    n_results: int = Field(10, ge=1, le=100)


class QuestionTypeConfig(BaseModel):
    type: str = Field(..., pattern="^(single_choice|multi_choice|judge|essay)$")
    count: int = Field(..., ge=1, le=100)
    score_per_question: int = Field(..., ge=1, le=100)


class SourceFileConfig(BaseModel):
    db_id: str = Field(..., pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    filename: str = Field(..., min_length=1, max_length=200)


class GenerateExamRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    db_ids: List[str] = Field(..., min_length=1)
    queries: List[str] = Field(default_factory=list)
    source_files: Optional[List[SourceFileConfig]] = None
    question_types: List[QuestionTypeConfig]
    exam_time: str = "90分钟"
    passing_score: int = Field(60, ge=0, le=1000)
    n_results_per_query: int = Field(15, ge=1, le=100)
    merge_db_results: bool = True
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    difficulty_basic: int = Field(50, ge=0, le=100)
    difficulty_understanding: int = Field(35, ge=0, le=100)
    difficulty_application: int = Field(15, ge=0, le=100)

    @model_validator(mode="after")
    def validate_difficulty_total(self):
        total = self.difficulty_basic + self.difficulty_understanding + self.difficulty_application
        if total != 100:
            raise ValueError("难度比例合计必须为 100")
        return self


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
    providers: List[LLMProviderSetting] = Field(default_factory=list)


class LLMTestRequest(BaseModel):
    provider_id: str
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    api_type: str = "openai_compatible"
