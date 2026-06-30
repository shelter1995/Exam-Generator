from models import QuestionTypeConfig
from exam import (
    build_knowledge_context,
    extract_answers,
    format_exam_content,
    generate_exam,
    normalize_essay_answer_numbering,
    validate_exam_content,
)


class FakeLLM:
    def chat(self, prompt, temperature=0.7, max_tokens=8192):
        return """1. [基础] 示例题？
   A. 甲
   B. 乙
   C. 丙
   D. 丁
   **答案：B**
   **解析：**来自资料。

2. [基础] 示例判断。
   **答案：正确**
   **解析：**来自资料。"""


class PromptCaptureLLM:
    def __init__(self, response):
        self.response = response
        self.prompts = []

    def chat(self, prompt, temperature=0.7, max_tokens=8192):
        self.prompts.append(prompt)
        return self.response


def test_extract_answers_reads_choice_and_judge_answers():
    content = """1. [基础] 题目
   **答案：AB**
   **解析：**解析

2. [基础] 判断
   **答案：错误**
   **解析：**解析"""

    assert extract_answers(content, 2) == {1: "AB", 2: "错误"}


def test_validate_exam_content_reports_missing_numbers_and_answers():
    content = """1. [基础] 题目
   **答案：A**
   **解析：**解析

3. [基础] 题目
   **解析：**解析"""

    report = validate_exam_content(content, expected_count=3)

    assert report["valid"] is False
    assert 2 in report["missing_numbers"]
    assert 3 in report["missing_answers"]


def test_generate_exam_includes_provider_and_fills_missing_questions():
    exam = generate_exam(
        title="测试考卷",
        knowledge_results=[{"text": "知识点", "metadata": {"source": "a.md"}, "db_name": "默认库"}],
        question_types=[QuestionTypeConfig(type="single_choice", count=3, score_per_question=2)],
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        llm_client=FakeLLM(),
    )

    assert "使用模型: openai/gpt-4o-mini" in exam
    assert "3. [补充]" in exam
    assert "| 1 | B " in exam


def test_build_knowledge_context_scales_with_question_count_and_keeps_sources():
    results = [
        {"text": f"片段{i}" * 400, "metadata": {"source": f"file{i}.md", "chunk": i}, "db_name": "库"}
        for i in range(1, 8)
    ]

    small = build_knowledge_context(results, total_questions=2)
    large = build_knowledge_context(results, total_questions=30)

    assert "【资料1】原始文件: file1.md" in small
    assert "文档片段" not in small
    assert len(large) > len(small)


def test_generate_exam_uses_configured_difficulty_distribution_and_original_file_sources():
    llm = PromptCaptureLLM("""1. [应用] 示例题？
   A. 甲
   B. 乙
   C. 丙
   D. 丁
   **答案：B**
   **解析：**依据 a.md。""")

    generate_exam(
        title="测试考卷",
        knowledge_results=[{"text": "知识点", "metadata": {"source": "a.md", "chunk": 3}, "db_name": "默认库"}],
        question_types=[QuestionTypeConfig(type="single_choice", count=1, score_per_question=2)],
        difficulty_distribution={"basic": 20, "understanding": 30, "application": 50},
        llm_client=llm,
    )

    assert "难度分布：基础题 20%、理解题 30%、应用题 50%" in llm.prompts[0]
    assert "解析中引用原始文件名" in llm.prompts[0]
    assert "不要写“文档片段" in llm.prompts[0]
    assert "原始文件: a.md" in llm.prompts[0]


def test_normalize_essay_answer_numbering_indents_numbered_answer_lines():
    raw = """31. [理解] 题目内容
   **答案：**
32. 适合交给AI处理。
33. 具体对应动作类型。
   **解析：**依据 a.md。"""

    normalized = normalize_essay_answer_numbering(format_exam_content(raw))

    assert "\n32. 适合交给AI处理。" not in normalized
    assert "\n   32. 适合交给AI处理。" in normalized
    assert "\n   33. 具体对应动作类型。" in normalized
