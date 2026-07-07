"""
AI 关键信息提取模块。
调用 DeepSeek API（OpenAI 兼容接口）从简历文本中提取结构化信息。
"""
import json
import requests
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

EXTRACTION_PROMPT = """你是一个专业的简历解析专家。请从以下简历文本中提取关键信息，严格以 JSON 格式返回。
只提取文本中明确存在的信息，不确定的字段填 null 或空字符串。

### 要求提取的字段：

**基本信息（必选）：**
- name: 姓名
- phone: 电话号码
- email: 邮箱地址
- address: 居住地址/城市
- gender: 性别（"男"/"女"，无法判断填 null）
- age: 年龄（数字，无法判断填 null）

**求职信息：**
- job_intention: 求职意向/期望职位
- expected_salary: 期望薪资
- job_type: 工作类型（"全职"/"实习"/"兼职"，无法判断填 null）
- expected_city: 期望工作城市

**教育背景：**
- education: 最高学历（如 "本科"、"硕士"、"博士"、"大专"）
- school: 毕业院校
- major: 专业
- graduation_year: 毕业年份（数字，无法判断填 null）

**工作与经验：**
- work_years: 工作年限（数字，如 3、5.5，应届生填 0）
- work_experience: 工作经历列表，每项包含 company(公司)、position(职位)、duration(时间段)、description(工作内容简述)
- project_experience: 项目经历列表，每项包含 name(项目名)、role(担任角色)、description(项目描述与技术栈)
- skills: 技能标签列表（数组，如 ["Python", "Java", "机器学习"]）
- skill_levels: 技能与熟练度映射（如 {"Python": "精通", "Java": "熟练"}，无法判断填 {}）
- languages: 语言能力（如 {"英语": "CET-6", "普通话": "母语"}，无法判断填 {}）
- certificates: 证书/资格列表（如 ["PMP", "AWS认证"]，无法判断填 []）

**自我评价（可选）：**
- self_evaluation: 自我评价/个人简介
- strengths: 核心优势列表（数组，如 ["沟通能力强", "有团队管理经验"]）

**简历概要：**
- resume_summary: 简历概要（50-100字的综合概述，概括候选人的核心背景、技能方向和经验亮点）

### 输出格式（严格 JSON，不要任何额外文字）：
{
  "name": "",
  "phone": "",
  "email": "",
  "address": "",
  "gender": null,
  "age": null,
  "job_intention": "",
  "expected_salary": "",
  "job_type": null,
  "expected_city": "",
  "education": "",
  "school": "",
  "major": "",
  "graduation_year": null,
  "work_years": null,
  "work_experience": [],
  "project_experience": [],
  "skills": [],
  "skill_levels": {},
  "languages": {},
  "certificates": [],
  "self_evaluation": "",
  "strengths": [],
  "resume_summary": ""
}

### 简历文本：
{resume_text}

请输出 JSON："""


def call_deepseek_api(prompt: str, temperature: float = 0.1, max_tokens: int = 4000) -> str:
    """调用 DeepSeek Chat API，返回响应文本。"""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY 未配置，请在环境变量中设置")

    url = f"{DEEPSEEK_BASE_URL}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": "你是一个精确的简历信息提取助手。只返回 JSON，不输出任何其他内容。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _parse_llm_json(raw: str) -> dict:
    """从 LLM 返回文本中提取 JSON（处理 markdown 代码块包裹等情况）。"""
    raw = raw.strip()
    # 去掉可能的 ```json ... ``` 包裹
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw[:-3]
    return json.loads(raw)


def extract_resume_info(structured_text: str) -> dict:
    """从清洗后的简历文本中提取结构化关键信息。

    Args:
        structured_text: 经过清洗和结构化的简历文本

    Returns:
        dict: 提取的结构化信息，保证字段完整
    """
    default_result = {
        "name": "",
        "phone": "",
        "email": "",
        "address": "",
        "gender": None,
        "age": None,
        "job_intention": "",
        "expected_salary": "",
        "job_type": None,
        "expected_city": "",
        "education": "",
        "school": "",
        "major": "",
        "graduation_year": None,
        "work_years": None,
        "work_experience": [],
        "project_experience": [],
        "skills": [],
        "skill_levels": {},
        "languages": {},
        "certificates": [],
        "self_evaluation": "",
        "strengths": [],
        "resume_summary": "",
    }

    try:
        prompt = EXTRACTION_PROMPT.replace("{resume_text}", structured_text[:6000])
        response = call_deepseek_api(prompt)
        extracted = _parse_llm_json(response)
        # 合并默认值，确保所有字段存在
        result = {**default_result, **extracted}
        return result
    except json.JSONDecodeError:
        return {**default_result, "_error": "AI 返回格式解析失败"}
    except requests.RequestException as e:
        return {**default_result, "_error": f"AI API 调用失败: {str(e)}"}
    except Exception as e:
        return {**default_result, "_error": f"提取过程异常: {str(e)}"}
