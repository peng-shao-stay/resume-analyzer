"""
PDF 简历解析模块：提取文本、清洗、结构化分段。
使用 pypdf（纯 Python，无 C 依赖，跨平台兼容）。
"""
import io
import re
from pypdf import PdfReader


def extract_text_from_pdf(file_data: bytes) -> str:
    """从 PDF 二进制数据中提取纯文本，支持多页。"""
    text_parts = []
    reader = PdfReader(io.BytesIO(file_data))
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text)
    return "\n".join(text_parts)


def clean_text(raw_text: str) -> str:
    """清洗提取的文本：去除乱码字符、合并多余空白、统一换行。"""
    # 保留中英文、数字、常用标点符号和换行
    text = re.sub(
        r'[^一-龥a-zA-Z0-9\s.,;:!?@#()+\-*/=：，。；！？《》【】（）／＋－＊＝％＠＃￥…—\n]',
        '', raw_text
    )
    # 合并连续空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 合并行内多余空格（保留中文间的正常空格）
    text = re.sub(r'[ \t]{2,}', ' ', text)
    # 去除首尾空白
    text = text.strip()
    return text


def structure_resume_text(text: str) -> str:
    """对简历文本做结构化分段识别：按常见标题切分段落块。
    返回带标记的结构化文本，方便后续 AI 提取。"""
    headers = [
        "基本信息", "个人信息", "教育背景", "教育经历", "学历",
        "工作经历", "工作经验", "工作背景",
        "项目经历", "项目经验", "项目",
        "技能", "专业技能", "技术栈", "技能特长",
        "自我评价", "个人评价", "求职意向", "求职期望",
        "联系方式", "社交",
    ]
    pattern = "|".join(re.escape(h) for h in headers)
    # 在每个匹配的标题前插入换行标记
    text = re.sub(f'({pattern})', r'\n[SEP]\n\1', text, flags=re.IGNORECASE)
    return text


def parse_resume(file_data: bytes) -> dict:
    """完整的简历解析流程：PDF → 文本提取 → 清洗 → 结构化。

    Returns:
        dict: {
            "raw_text": str,        # 原始文本
            "clean_text": str,      # 清洗后文本
            "structured_text": str, # 结构化文本
            "page_count": int,      # 页数
            "char_count": int,      # 清洗后字符数
        }
    """
    reader = PdfReader(io.BytesIO(file_data))
    page_count = len(reader.pages)

    raw = extract_text_from_pdf(file_data)
    if not raw.strip():
        return {
            "raw_text": "",
            "clean_text": "",
            "structured_text": "",
            "page_count": page_count,
            "char_count": 0,
            "error": "PDF 无可提取文本，可能是扫描件或图片型 PDF",
        }

    cleaned = clean_text(raw)
    structured = structure_resume_text(cleaned)

    return {
        "raw_text": raw.strip(),
        "clean_text": cleaned,
        "structured_text": structured,
        "page_count": page_count,
        "char_count": len(cleaned),
    }
