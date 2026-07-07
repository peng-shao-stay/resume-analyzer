"""
简历与岗位匹配评分模块。
支持：关键词匹配 + AI 语义匹配。
"""
import re
from typing import List, Dict

import json

from ai_extractor import call_deepseek_api


def extract_keywords(job_description: str) -> List[str]:
    """从岗位描述中提取关键词：技能、技术栈、经验要求等。

    先用正则快速提取常见技术关键词，再结合简单的分词策略。
    """
    text = job_description.lower()
    
    # 常见技术关键词库
    tech_keywords = [
        # 编程语言
        "python", "java", "javascript", "typescript", "go", "golang", "rust",
        "c++", "c#", "php", "ruby", "swift", "kotlin", "scala", "dart",
        # 前端
        "react", "vue", "angular", "html5", "css3", "webpack", "node.js",
        "next.js", "nuxt", "小程序",
        # 后端
        "django", "flask", "spring", "springboot", "gin", "express",
        "fastapi", "nginx", "graphql", "restful", "微服务",
        # 数据库
        "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
        "oracle", "sqlserver", "sqlite", "tidb", "hbase",
        # 大数据/AI
        "hadoop", "spark", "flink", "kafka", "tensorflow", "pytorch",
        "机器学习", "深度学习", "自然语言处理", "nlp", "计算机视觉", "cv",
        "大模型", "llm", "langchain", "rag",
        # DevOps
        "docker", "kubernetes", "k8s", "jenkins", "gitlab", "devops",
        "terraform", "ansible", "cicd",
        # 云服务
        "aws", "阿里云", "腾讯云", "azure", "gcp", "云计算", "serverless",
        # 其他
        "linux", "shell", "git", "agile", "scrum", "数据分析", "项目管理",
        "产品经理", "ui设计", "ux", "测试", "自动化测试",
    ]
    
    found = []
    for kw in tech_keywords:
        if kw in text:
            found.append(kw)
    
    # 提取工作经验年限要求
    year_match = re.findall(r'(\d+)[\s-]*年(以上|以下)?.*?(经验|工作)', job_description)
    for m in year_match:
        found.append(f"{m[0]}年经验")
    
    # 提取学历关键词
    edu_keywords = ["本科", "硕士", "博士", "大专", "985", "211"]
    for ek in edu_keywords:
        if ek in text:
            found.append(ek)
    
    return list(set(found))  # 去重


def calculate_keyword_match_score(resume_info: dict, job_keywords: List[str]) -> dict:
    """基于关键词的匹配评分。

    Returns:
        {
            "skill_match_rate": float,     # 技能匹配率 (0-100)
            "matched_keywords": list,      # 匹配上的关键词
            "missing_keywords": list,      # 缺失的关键词
            "score": float,                # 基础分 (0-100)
        }
    """
    if not job_keywords:
        return {
            "skill_match_rate": 0,
            "matched_keywords": [],
            "missing_keywords": [],
            "score": 0,
        }
    
    # 获取候选人的技能列表
    skills = [s.lower() for s in resume_info.get("skills", [])]

    # 从结构化工作经历和项目经历中提取文本用于模糊匹配
    def _extract_text(value):
        """从字段中提取文本，兼容字符串和结构化列表两种格式。"""
        if isinstance(value, list):
            parts = []
            for item in value:
                if isinstance(item, dict):
                    parts.extend(str(v) for v in item.values() if v)
                else:
                    parts.append(str(item))
            return " ".join(parts)
        return str(value) if value else ""

    experience_text = " ".join([
        _extract_text(resume_info.get("work_experience", "")),
        _extract_text(resume_info.get("project_experience", "")),
        str(resume_info.get("job_intention", "")),
        str(resume_info.get("major", "")),
        str(resume_info.get("resume_summary", "")),
    ]).lower()
    
    matched = []
    missing = []
    for kw in job_keywords:
        kw_lower = kw.lower()
        if kw_lower in skills or kw_lower in experience_text:
            matched.append(kw)
        else:
            missing.append(kw)
    
    rate = round(len(matched) / len(job_keywords) * 100, 1) if job_keywords else 0
    return {
        "skill_match_rate": rate,
        "matched_keywords": matched,
        "missing_keywords": missing,
        "score": rate,  # 基础分即关键词匹配率
    }


def calculate_experience_match(resume_info: dict, job_description: str) -> dict:
    """计算工作经验相关性评分。"""
    result = {
        "work_years_score": 0,
        "education_score": 0,
        "analysis": "",
    }
    
    # 提取岗位要求年限
    required_years = None
    year_matches = re.findall(r'(\d+)\s*年', job_description)
    if year_matches:
        required_years = float(min(int(y) for y in year_matches))
    
    candidate_years = resume_info.get("work_years")
    if candidate_years and required_years:
        if isinstance(candidate_years, str):
            try:
                candidate_years = float(candidate_years)
            except ValueError:
                candidate_years = None
    
    if candidate_years and required_years:
        ratio = min(candidate_years / required_years, 1.5)
        result["work_years_score"] = round(min(ratio * 100, 100), 1)
    elif candidate_years and not required_years:
        result["work_years_score"] = 80  # 有经验但未要求年限
    elif not candidate_years and required_years:
        result["work_years_score"] = 30  # 无经验但有要求
    else:
        result["work_years_score"] = 60  # 无法判断
    
    # 学历匹配
    edu = resume_info.get("education", "")
    edu_lower = edu.lower()
    jd_lower = job_description.lower()
    
    edu_hierarchy = {
        "博士": 5, "phd": 5,
        "硕士": 4, "master": 4, "研究生": 4,
        "本科": 3, "bachelor": 3, "学士": 3,
        "大专": 2, "专科": 2,
    }
    
    candidate_edu_level = 0
    for key, level in edu_hierarchy.items():
        if key in edu_lower:
            candidate_edu_level = max(candidate_edu_level, level)
    
    required_edu_level = 0
    for key, level in edu_hierarchy.items():
        if key in jd_lower:
            required_edu_level = max(required_edu_level, level)
    
    if required_edu_level:
        if candidate_edu_level >= required_edu_level:
            result["education_score"] = 100
        else:
            result["education_score"] = round(candidate_edu_level / required_edu_level * 70, 1)
    else:
        result["education_score"] = 80  # 无学历要求
    
    result["analysis"] = f"工作年限匹配: {result['work_years_score']}%, 学历匹配: {result['education_score']}%"
    return result


def ai_match_scoring(resume_info: dict, job_description: str) -> dict:
    """使用 DeepSeek AI 对匹配度进行语义级精准评分，生成详细中文分析报告。

    Returns:
        {
            "ai_score": float,
            "ai_analysis": dict with detailed breakdown
        }
    """
    prompt = f"""你是一个资深招聘顾问和人才评估专家。请对比候选人简历和岗位需求，进行全面的匹配度评估。

### 候选人简历信息：
{json.dumps(resume_info, ensure_ascii=False, indent=2)}

### 岗位需求：
{job_description}

### 请严格按照以下 JSON 格式返回评估结果（不要任何额外文字）：
{{
  "overall_score": 0-100的整数，综合匹配度评分，
  "skill_score": 0-100的整数，技能匹配度评分,
  "experience_score": 0-100的整数，经验匹配度评分,
  "education_score": 0-100的整数，学历匹配度评分,
  "skill_match_detail": "技能匹配的详细分析说明，指出候选人掌握了哪些岗位所需技能，以及技能水平的匹配程度，100-200字",
  "experience_match_detail": "工作经验匹配的详细分析，评估工作年限、行业背景、岗位相关性的匹配情况，100-200字",
  "education_match_detail": "教育背景匹配的详细分析，评估学历层次、专业对口程度、学校背景等，80-150字",
  "strengths": ["候选人的核心竞争力1", "核心竞争力2", "核心竞争力3"],
  "gaps": ["与岗位要求的主要差距1", "差距2", "差距3"],
  "matched_keywords_ai": ["AI识别出的匹配关键词1", "关键词2"],
  "missing_keywords_ai": ["AI识别出的缺失关键要求1", "缺失2"],
  "recommendation": "综合评价和建议，包含是否建议面试、候选人定位、以及面试中应重点考察的方向，150-250字",
  "candidate_level": "候选人级别评估，如'初级(1-3年)'/'中级(3-5年)'/'高级(5-10年)'/'资深(10年+)'/'专家'",
  "interview_suggestions": ["面试建议问题方向1", "建议问题2", "建议问题3"]
}}

请输出 JSON："""

    try:
        response = call_deepseek_api(prompt, temperature=0.3, max_tokens=4096)
        response = response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[-1]
            if response.endswith("```"):
                response = response[:-3]
        ai_result = json.loads(response)
        return {
            "ai_score": ai_result.get("overall_score", 0),
            "ai_analysis": {
                "skill_score": ai_result.get("skill_score", 0),
                "experience_score": ai_result.get("experience_score", 0),
                "education_score": ai_result.get("education_score", 0),
                "skill_match_detail": ai_result.get("skill_match_detail", ""),
                "experience_match_detail": ai_result.get("experience_match_detail", ""),
                "education_match_detail": ai_result.get("education_match_detail", ""),
                "strengths": ai_result.get("strengths", []),
                "gaps": ai_result.get("gaps", []),
                "matched_keywords_ai": ai_result.get("matched_keywords_ai", []),
                "missing_keywords_ai": ai_result.get("missing_keywords_ai", []),
                "recommendation": ai_result.get("recommendation", ""),
                "candidate_level": ai_result.get("candidate_level", ""),
                "interview_suggestions": ai_result.get("interview_suggestions", []),
            },
        }
    except Exception as e:
        return {
            "ai_score": 0,
            "ai_analysis": {"error": f"AI 评分异常: {str(e)}"},
        }


def match_resume(resume_info: dict, job_description: str, use_ai: bool = True) -> dict:
    """综合匹配评分入口。

    Args:
        resume_info: 从简历提取的结构化信息
        job_description: 岗位需求描述
        use_ai: 是否启用 AI 语义评分

    Returns:
        dict: 完整的匹配评分结果
    """
    # 1. 提取岗位关键词
    job_keywords = extract_keywords(job_description)
    
    # 2. 关键词匹配
    kw_result = calculate_keyword_match_score(resume_info, job_keywords)
    
    # 3. 经验匹配
    exp_result = calculate_experience_match(resume_info, job_description)
    
    # 4. 综合评分
    composite_score = round(
        kw_result["score"] * 0.5 + exp_result["work_years_score"] * 0.3 + exp_result["education_score"] * 0.2,
        1
    )
    
    result = {
        "job_keywords": job_keywords,
        "keyword_match": kw_result,
        "experience_match": exp_result,
        "composite_score": composite_score,
        "ai_match": None,
    }
    
    # 5. AI 语义评分（加分项）
    if use_ai:
        ai_result = ai_match_scoring(resume_info, job_description)
        result["ai_match"] = ai_result
        # 如果有 AI 评分，用 AI 分占 60%，基础分占 40%
        if ai_result.get("ai_score", 0) > 0:
            result["composite_score"] = round(
                composite_score * 0.4 + ai_result["ai_score"] * 0.6, 1
            )
    
    return result
