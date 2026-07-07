"""
AI 智能简历分析系统 - Flask 主应用
部署于阿里云函数计算 FC，handler: index.app

API 接口：
  POST   /api/resume/upload        - 上传 PDF 简历，解析并提取信息
  POST   /api/resume/<id>/match    - 简历与岗位匹配评分
  GET    /api/resume/<id>          - 查询已分析简历结果
  GET    /api/health               - 健康检查
"""
import hashlib
import json
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS

from config import MAX_FILE_SIZE_MB, ALLOWED_EXTENSIONS
from pdf_parser import parse_resume
from ai_extractor import extract_resume_info
from matcher import match_resume
from cache import cache

app = Flask(__name__)
CORS(app)  # 允许前端跨域访问


def _file_hash(data: bytes) -> str:
    """计算文件内容 MD5 作为唯一标识。"""
    return hashlib.md5(data).hexdigest()


def _allowed_file(filename: str) -> bool:
    """检查文件扩展名是否允许。"""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[-1].lower()
    return ext in ALLOWED_EXTENSIONS


# ==================== API 路由 ====================

@app.route('/')
def index():
    """根路径：API 系统信息页"""
    return jsonify({
        "service": "AI 智能简历分析系统",
        "version": "2.0.0",
        "docs": {
            "健康检查": "GET /api/health",
            "上传简历": "POST /api/resume/upload  (multipart/form-data, field: file)",
            "匹配评分": "POST /api/resume/<resume_id>/match  (JSON: {job_description, use_ai})",
            "查询结果": "GET /api/resume/<resume_id>",
            "删除缓存": "DELETE /api/resume/<resume_id>",
        },
        "note": "前端页面请部署至 GitHub Pages"
    })


@app.route('/api/health', methods=['GET'])
def health():
    """健康检查接口。"""
    return jsonify({
        "status": "ok",
        "cache_type": type(cache).__name__,
    })


@app.route('/api/resume/upload', methods=['POST'])
def upload_resume():
    """
    上传 PDF 简历，解析并提取关键信息。
    
    Request: multipart/form-data
      - file: PDF 文件
    
    Response:
      {
        "success": true,
        "data": {
          "resume_id": "md5_hash",
          "parse_result": { "page_count": 2, "char_count": 1500, ... },
          "extracted_info": { "name": "张三", "phone": "...", ... },
          "from_cache": false
        }
      }
    """
    # 1. 验证文件上传
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "请上传 PDF 文件", "code": "NO_FILE"}), 400
    
    file = request.files['file']
    if file.filename == '' or file.filename is None:
        return jsonify({"success": False, "error": "文件名为空", "code": "EMPTY_FILENAME"}), 400
    
    if not _allowed_file(file.filename):
        return jsonify({
            "success": False,
            "error": f"不支持的文件类型，仅允许: {', '.join(ALLOWED_EXTENSIONS)}",
            "code": "INVALID_TYPE"
        }), 400
    
    # 2. 读取文件内容
    file_data = file.read()
    
    if len(file_data) == 0:
        return jsonify({"success": False, "error": "上传的文件为空", "code": "EMPTY_FILE"}), 400
    
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if len(file_data) > max_bytes:
        return jsonify({
            "success": False,
            "error": f"文件大小超过限制 ({MAX_FILE_SIZE_MB}MB)",
            "code": "FILE_TOO_LARGE"
        }), 413
    
    # 3. 计算文件哈希，检查缓存
    resume_id = _file_hash(file_data)
    cached = cache.get(f"resume:{resume_id}")
    if cached:
        cached["from_cache"] = True
        return jsonify({"success": True, "data": cached, "code": "CACHE_HIT"})
    
    # 4. 解析 PDF
    try:
        parse_result = parse_resume(file_data)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"PDF 解析失败: {str(e)}",
            "code": "PARSE_ERROR"
        }), 422
    
    if parse_result.get("error"):
        return jsonify({
            "success": False,
            "data": {"resume_id": resume_id, "parse_result": parse_result},
            "error": parse_result["error"],
            "code": "EXTRACT_FAILED"
        }), 422
    
    # 5. AI 提取关键信息
    try:
        extracted_info = extract_resume_info(parse_result["structured_text"])
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"AI 信息提取失败: {str(e)}",
            "code": "AI_EXTRACT_ERROR"
        }), 500
    
    # 6. 组装结果并缓存
    data = {
        "resume_id": resume_id,
        "parse_result": {
            "page_count": parse_result["page_count"],
            "char_count": parse_result["char_count"],
            "text_preview": parse_result["clean_text"][:500],
        },
        "extracted_info": extracted_info,
        "from_cache": False,
    }
    cache.set(f"resume:{resume_id}", data)
    
    return jsonify({"success": True, "data": data})


@app.route('/api/resume/<resume_id>/match', methods=['POST'])
def match_resume_api(resume_id: str):
    """
    将简历与岗位需求进行匹配评分。
    
    Request: JSON
      {
        "job_description": "岗位需求描述文本...",
        "use_ai": true          // 可选，是否启用 AI 语义评分
      }
    
    Response:
      {
        "success": true,
        "data": {
          "resume_id": "...",
          "match_result": { ... },
          "from_cache": false
        }
      }
    """
    # 1. 检查简历是否已解析
    cached_resume = cache.get(f"resume:{resume_id}")
    if not cached_resume:
        return jsonify({
            "success": False,
            "error": "简历未找到，请先上传简历",
            "code": "RESUME_NOT_FOUND"
        }), 404
    
    # 2. 解析请求
    body = request.get_json(silent=True)
    if not body or not body.get("job_description", "").strip():
        return jsonify({
            "success": False,
            "error": "请提供岗位需求描述 (job_description)",
            "code": "MISSING_DESCRIPTION"
        }), 400
    
    job_description = body["job_description"].strip()
    use_ai = body.get("use_ai", True)
    
    # 3. 检查匹配结果缓存
    match_cache_key = f"match:{resume_id}:{hashlib.md5(job_description.encode()).hexdigest()}"
    cached_match = cache.get(match_cache_key)
    if cached_match:
        return jsonify({"success": True, "data": cached_match, "code": "CACHE_HIT"})
    
    # 4. 执行匹配
    try:
        extracted_info = cached_resume["extracted_info"]
        match_result = match_resume(extracted_info, job_description, use_ai=use_ai)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"匹配评分失败: {str(e)}",
            "code": "MATCH_ERROR"
        }), 500
    
    # 5. 组装结果并缓存
    data = {
        "resume_id": resume_id,
        "job_description": job_description[:500],
        "match_result": match_result,
        "from_cache": False,
    }
    cache.set(match_cache_key, data)
    
    # 同时更新简历缓存，附加匹配结果
    cached_resume["match_result"] = match_result
    cached_resume["job_description"] = job_description[:500]
    cache.set(f"resume:{resume_id}", cached_resume)
    
    return jsonify({"success": True, "data": data})


@app.route('/api/resume/<resume_id>', methods=['GET'])
def get_resume_result(resume_id: str):
    """
    查询已解析的简历结果（含匹配结果，如有）。
    
    Response:
      {
        "success": true,
        "data": { ... }
      }
    """
    cached = cache.get(f"resume:{resume_id}")
    if not cached:
        return jsonify({
            "success": False,
            "error": "简历未找到，请先上传简历",
            "code": "RESUME_NOT_FOUND"
        }), 404
    
    return jsonify({"success": True, "data": cached})


@app.route('/api/resume/<resume_id>', methods=['DELETE'])
def delete_resume_result(resume_id: str):
    """删除缓存的简历结果。"""
    cache.delete(f"resume:{resume_id}")
    return jsonify({"success": True, "message": "已删除"})


@app.errorhandler(413)
def too_large(e):
    return jsonify({"success": False, "error": "文件大小超过限制", "code": "FILE_TOO_LARGE"}), 413


@app.errorhandler(500)
def server_error(e):
    return jsonify({
        "success": False,
        "error": "服务器内部错误",
        "code": "SERVER_ERROR"
    }), 500


# ---- WSGI 入口（FC 通过 handler: index.app 调用）----
# app 已在顶部定义

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000, debug=True)
