"""
多题型考题生成器
支持单选/多选/判断/简答，分批生成，格式后处理
支持多模型切换：MiniMax、OpenAI、Claude、Qwen、DeepSeek
"""
import re
import logging
from typing import List, Dict, Any, Optional

import config
from models import QuestionTypeConfig
from llm import create_llm_client

logger = logging.getLogger(__name__)


QUESTION_TYPE_PROMPTS = {
    "single_choice": {
        "name": "单选题",
        "desc": "每题4个选项（A/B/C/D），只有一个正确答案",
        "answer_example": "**答案：B**",
        "format": """{num}. [难度] 题目内容
   A. 选项1
   B. 选项2
   C. 选项3
   D. 选项4
   **答案：X**
   **解析：**详细解析"""
    },
    "multi_choice": {
        "name": "多选题",
        "desc": "每题4-6个选项，有2个或以上正确答案",
        "answer_example": "**答案：ABD**",
        "format": """{num}. [难度] 题目内容
   A. 选项1
   B. 选项2
   C. 选项3
   D. 选项4
   E. 选项5（可选）
   **答案：XX**
   **解析：**详细解析"""
    },
    "judge": {
        "name": "判断题",
        "desc": "判断陈述的正确性，答案只能是正确或错误",
        "answer_example": "**答案：正确**",
        "format": """{num}. [难度] 题目描述内容。
   **答案：正确/错误**
   **解析：**详细解析"""
    },
    "essay": {
        "name": "简答题",
        "desc": "需要简要回答的开放性问题，提供参考答案要点",
        "answer_example": "**答案：**参考答案要点",
        "format": """{num}. [难度] 题目内容
   **答案：**参考答案要点（分点列出）
   **解析：**详细解析与评分标准"""
    }
}


def format_exam_content(raw: str) -> str:
    """统一考题格式"""
    content = raw

    content = re.sub(r'^\s*```markdown\s*\n?', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\n?\s*```\s*$', '', content)

    lines = content.split('\n')
    cleaned = [re.sub(r'^(\s*)>\s?', r'\1', line) for line in lines]
    content = '\n'.join(cleaned)

    content = re.sub(r'\*{3,}', '**', content)

    content = re.sub(
        r'\*\*\s*答案\s*[:：]\s*([^*\n]+?)\s*\*\*',
        lambda m: f"**答案：{m.group(1).strip()}**",
        content
    )
    content = re.sub(
        r'(?<!\*)\b答案\s*[:：]\s*([A-F]+|正确|错误)\b(?!\*)',
        r'**答案：\1**',
        content
    )

    content = re.sub(r'\*\*[ \t]*解析\s*[:：]\s*\*{2,}', '**解析：**', content)
    content = re.sub(r'\*\*[ \t]*解析\s*[:：]\s*([^*\n]+?)\s*\*\*', r'**解析：**\1', content)
    content = re.sub(r'\*\*[ \t]*解析\s*[:：]\s*(?!\*)', '**解析：**', content)
    content = re.sub(r'(?<!\*)\b解析\s*[:：]\s*', '**解析：**', content)

    content = re.sub(r'\n([A-F])\.\s', r'\n   \1. ', content)

    content = re.sub(r'\n{4,}', '\n\n\n', content)

    return content.strip()


def normalize_essay_answer_numbering(content: str) -> str:
    """避免简答题答案内部编号被 Markdown 渲染成新题号。"""
    lines = content.split('\n')
    normalized = []
    in_answer = False
    for line in lines:
        is_question_line = bool(re.match(r'^\d+\.\s*\[', line))
        if is_question_line:
            in_answer = False

        if '**答案：**' in line:
            in_answer = True
        elif '**解析：**' in line:
            in_answer = False

        if in_answer and re.match(r'^\d+\.\s+', line) and not is_question_line:
            line = '   ' + line
        normalized.append(line)
    return '\n'.join(normalized)


def generate_question_batch(
    knowledge: str,
    qtype: str,
    count: int,
    start_num: int,
    score: int,
    llm_client = None,
    difficulty_distribution: Dict[str, int] = None
) -> str:
    """生成某一批次的题目"""
    cfg = QUESTION_TYPE_PROMPTS[qtype]
    end_num = start_num + count - 1
    difficulty_distribution = difficulty_distribution or {
        "basic": 50,
        "understanding": 35,
        "application": 15,
    }
    difficulty_text = (
        f"基础题 {difficulty_distribution['basic']}%、"
        f"理解题 {difficulty_distribution['understanding']}%、"
        f"应用题 {difficulty_distribution['application']}%"
    )
    essay_extra = ""
    if qtype == "essay":
        essay_extra = "\n7. 简答题答案要用短横线分点，不要在答案或解析中使用行首阿拉伯数字编号（如 1.、2.、32.）"

    prompt = f"""你是专业的企业培训考题设计师。请基于以下知识内容，设计 {count} 道{cfg['name']}（第 {start_num}-{end_num} 题，每题{score}分）。

【考题要求】
1. 必须生成完整的 {count} 道{cfg['name']}，编号从 {start_num} 到 {end_num}
2. {cfg['desc']}
3. 所有题目必须严格基于提供的知识内容，不能编造
4. 每道题都要有详细的答案和解析
5. 难度分布：{difficulty_text}
6. 题目要体现实际业务场景
{essay_extra}

【输出格式要求】
必须严格按照以下格式输出，不要添加 ```markdown 代码块标记：

{cfg['format'].replace('{num}', str(start_num))}

（下一题）

【知识内容】
{knowledge}

严格要求：
- 必须生成完整的 {count} 道题目，编号从 {start_num} 到 {end_num}
- 不得省略任何题目
- 答案格式必须是 {cfg['answer_example']}
- 解析格式必须是 **解析：**开头
- 解析中引用原始文件名，例如“依据《文件名.docx》”
- 不要写“文档片段X”“片段X”“第X页”等用户无法定位的来源描述
- 不要输出 ```markdown 标记
- 不要输出答案速查表"""

    if llm_client is None:
        llm_client = create_llm_client()

    content = llm_client.chat(prompt, temperature=0.6, max_tokens=8192)
    content = format_exam_content(content)
    if qtype == "essay":
        content = normalize_essay_answer_numbering(content)
    return content


def generate_placeholder(start: int, end: int, qtype: str, score: int, reason: str = "") -> str:
    """生成占位题"""
    hint = f"（{reason}）" if reason else ""
    parts = []
    for i in range(start, end + 1):
        if qtype == "single_choice":
            parts.append(f"{i}. [补充] 本题因生成异常需手动补充{hint}\n   A. 选项A\n   B. 选项B\n   C. 选项C\n   D. 选项D\n   **答案：A**\n   **解析：**请根据资料补充。")
        elif qtype == "multi_choice":
            parts.append(f"{i}. [补充] 本题因生成异常需手动补充{hint}\n   A. 选项A\n   B. 选项B\n   C. 选项C\n   D. 选项D\n   **答案：AB**\n   **解析：**请根据资料补充。")
        elif qtype == "judge":
            parts.append(f"{i}. [补充] 本题因生成异常需手动补充{hint}。\n   **答案：正确**\n   **解析：**请根据资料补充。")
        elif qtype == "essay":
            parts.append(f"{i}. [补充] 本题因生成异常需手动补充{hint}。\n   **答案：**（参考答案要点）\n   **解析：**请根据资料补充。")
    return "\n\n".join(parts)


def extract_answers(content: str, expected_count: int) -> Dict[int, str]:
    """从考卷内容中提取答案。"""
    answers = {}
    for qnum in range(1, expected_count + 1):
        pattern = rf'(?ms)^{qnum}\.\s*\[.*?\].*?\*\*答案：\s*([A-F]+|正确|错误|[^*\n]+?)\s*\*\*'
        match = re.search(pattern, content)
        if match:
            answers[qnum] = match.group(1).strip()
    return answers


def validate_exam_content(content: str, expected_count: int) -> Dict[str, Any]:
    """校验题号、答案和解析是否完整。"""
    numbers = [int(n) for n in re.findall(r'(?m)^(\d+)\.\s*\[', content)]
    answers = extract_answers(content, expected_count)
    missing_numbers = [n for n in range(1, expected_count + 1) if n not in numbers]
    missing_answers = [n for n in numbers if 1 <= n <= expected_count and n not in answers]
    missing_analysis = [
        n for n in numbers
        if 1 <= n <= expected_count
        and not re.search(rf'(?ms)^{n}\.\s*\[.*?(?=^\d+\.\s*\[|\Z).*?\*\*解析：\*\*', content)
    ]
    return {
        "valid": not missing_numbers and not missing_answers and not missing_analysis,
        "numbers": numbers,
        "missing_numbers": missing_numbers,
        "missing_answers": missing_answers,
        "missing_analysis": missing_analysis,
        "answers": answers,
    }


def build_knowledge_context(
    search_results: List[Dict],
    total_questions: int = 10,
    max_fragments: int = None,
    max_len: int = None
) -> str:
    """构建知识上下文"""
    if max_fragments is None:
        max_fragments = min(40, max(8, total_questions))
    if max_len is None:
        max_len = 900 if total_questions >= 20 else 600

    fragments = []
    for idx, r in enumerate(search_results[:max_fragments]):
        text = r["text"]
        source = r.get("metadata", {}).get("source", "未知")
        db_name = r.get("db_name", "未知")
        truncated = text[:max_len] if len(text) > max_len else text
        fragments.append(f"【资料{idx+1}】原始文件: {source} (知识库: {db_name})\n{truncated}")
    return "\n\n".join(fragments)


def generate_exam(
    title: str,
    knowledge_results: List[Dict],
    question_types: List[QuestionTypeConfig],
    exam_time: str = "90分钟",
    passing_score: int = 60,
    llm_provider: str = None,
    llm_model: str = None,
    llm_client = None,
    difficulty_distribution: Dict[str, int] = None
) -> str:
    """
    生成完整考卷

    Args:
        title: 考卷标题
        knowledge_results: 检索到的知识内容
        question_types: 题型配置列表
        exam_time: 考试时间
        passing_score: 合格分数
        llm_provider: 指定 LLM 提供商（如 "openai", "anthropic" 等）
        llm_model: 指定模型名称（如 "gpt-4o", "claude-3-5-sonnet-20241022" 等）
    """
    total_questions = sum(q.count for q in question_types)
    total_score = sum(q.count * q.score_per_question for q in question_types)
    knowledge = build_knowledge_context(knowledge_results, total_questions=total_questions)

    if llm_client is None and (llm_provider or llm_model):
        llm_client = create_llm_client(provider=llm_provider, model=llm_model)

    all_sections = []
    current_num = 1
    section_idx = 1

    for qt in question_types:
        qtype = qt.type
        count = qt.count
        score = qt.score_per_question
        cfg = QUESTION_TYPE_PROMPTS[qtype]

        print(f"  生成 {cfg['name']}: {count} 道 (第 {current_num}-{current_num + count - 1} 题)")

        batch_size = 25
        section_parts = []
        batch_start = current_num

        while batch_start < current_num + count:
            batch_end = min(batch_start + batch_size - 1, current_num + count - 1)
            batch_count = batch_end - batch_start + 1

            try:
                part = generate_question_batch(
                    knowledge,
                    qtype,
                    batch_count,
                    batch_start,
                    score,
                    llm_client,
                    difficulty_distribution,
                )
                section_parts.append(part)
            except Exception as e:
                err_msg = str(e)[:80]
                logger.error(f"生成 {cfg['name']} 批次失败: {e}")
                section_parts.append(generate_placeholder(batch_start, batch_end, qtype, score, err_msg))

            batch_start = batch_end + 1

        section_md = "\n\n".join(section_parts)
        report = validate_exam_content(section_md, current_num + count - 1)
        missing_in_section = [
            n for n in report["missing_numbers"]
            if current_num <= n <= current_num + count - 1
        ]
        if missing_in_section:
            logger.warning(f"{cfg['name']} 缺少题号: {missing_in_section}")
            for qnum in missing_in_section:
                section_md += "\n\n" + generate_placeholder(qnum, qnum, qtype, score, "题量校验补齐")

        section_title = f"## {['一', '二', '三', '四', '五'][section_idx - 1]}、{cfg['name']}"
        section_title += f"（第{current_num}-{current_num + count - 1}题，每题{score}分，共{count * score}分）\n\n"
        all_sections.append(section_title + section_md)

        current_num += count
        section_idx += 1

    questions_md = "\n\n---\n\n".join(all_sections)

    provider_info = ""
    if llm_provider:
        model_name = llm_model or "默认"
        provider_info = f" | 使用模型: {llm_provider}/{model_name}"

    exam = f"""# {title}

## 考试说明
- 总题量：{total_questions}题
- 总分：{total_score}分
- 考试时间：{exam_time}
- 合格线：{passing_score}分{provider_info}

---

{questions_md}

---

## 答案速查表

| 题号 | 答案 | 题号 | 答案 | 题号 | 答案 | 题号 | 答案 |
|------|------|------|------|------|------|------|------|
"""

    answers = extract_answers(questions_md, total_questions)
    for row_start in range(1, total_questions + 1, 4):
        row = []
        for col in range(4):
            qnum = row_start + col
            if qnum <= total_questions:
                ans = answers.get(qnum, "?")
                row.append(f"| {qnum} | {ans} ")
            else:
                row.append("| | ")
        exam += "".join(row) + "|\n"

    exam += "\n---\n\n**考试结束，祝您取得优异成绩！**\n"
    return exam


def count_questions(exam_md: str) -> Dict[str, int]:
    """统计考卷中各题型数量"""
    blocks = re.findall(r'(?ms)^\d+\.\s*\[.*?(?=^\d+\.\s*\[|\Z)', exam_md)
    single = multi = judge = essay = 0
    for block in blocks:
        match = re.search(r'\*\*答案：\s*([^*\n]+?)\s*\*\*', block)
        if not match:
            continue
        ans = match.group(1).strip()
        if re.fullmatch(r'[A-D]', ans):
            single += 1
        elif re.fullmatch(r'[A-F]{2,}', ans):
            multi += 1
        elif ans in ("正确", "错误"):
            judge += 1
        else:
            essay += 1
    return {"single": single, "multi": multi, "judge": judge, "essay": max(0, essay)}
