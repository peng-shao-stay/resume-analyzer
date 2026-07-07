# AI 智能简历分析系统

AI 驱动的简历解析与岗位匹配评估系统。上传 PDF 简历，输入岗位需求，系统自动提取候选人信息并生成详细的中文匹配分析报告。

## 在线演示

> 前端页面: `https://peng-shao-stay.github.io/resume-analyzer/`  
> 后端需部署至阿里云函数计算 FC，见下方[部署说明](#部署)。

## 功能特性

- **多页 PDF 解析** — 自动抽取简历文本，清洗并结构化处理
- **AI 关键信息提取** — 提取姓名、联系方式、教育背景、工作经历、项目经历、技能标签等 26 个结构化字段
- **岗位匹配评估** — 关键词匹配 + AI 语义分析双重评分机制
- **详细中文报告** — 技能/经验/教育三维度评分分析、优劣势评估、面试建议

## 项目架构

```
用户浏览器                   Flask 后端 (Python)
┌──────────────┐           ┌─────────────────────────┐
│              │  HTTP请求  │                         │
│ frontend/    │ ────────→ │ jianliagent/code/       │
│ index.html   │           │                         │
│              │ ←──────── │ index.py   路由层        │
│ 纯静态HTML   │  JSON响应  │ config.py  配置层        │
│              │           │ pdf_parser.py  PDF解析   │
└──────────────┘           │ ai_extractor.py AI提取   │
                           │ matcher.py   匹配评分    │
                           │ cache.py    缓存层       │
                           └─────────────────────────┘
```

### 模块说明

| 模块 | 文件 | 职责 |
|------|------|------|
| 路由层 | `index.py` | Flask 应用入口，定义 5 个 RESTful API 接口 |
| 配置层 | `config.py` | 所有配置通过环境变量注入（12-Factor App） |
| PDF 解析 | `pdf_parser.py` | PDF 文本提取、清洗、按标题结构化分段 |
| AI 提取 | `ai_extractor.py` | 调用 DeepSeek API 从简历文本中提取 26 个结构化字段 |
| 匹配评分 | `matcher.py` | 关键词匹配 + AI 语义匹配双轨评分 |
| 缓存层 | `cache.py` | 统一缓存接口，支持内存缓存和 Redis |

### API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 系统信息 |
| `GET` | `/api/health` | 健康检查 |
| `POST` | `/api/resume/upload` | 上传 PDF 简历（multipart/form-data） |
| `POST` | `/api/resume/<id>/match` | 岗位匹配评分（JSON body） |
| `GET` | `/api/resume/<id>` | 查询已分析简历结果 |
| `DELETE` | `/api/resume/<id>` | 删除缓存结果 |

## 技术选型

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端框架 | Flask 3.x | 轻量级 Python Web 框架 |
| AI 服务 | DeepSeek API | OpenAI 兼容接口，用于信息提取和语义匹配 |
| PDF 解析 | pdfplumber | 多页 PDF 文本提取 |
| 缓存 | Redis / Memory | 支持内存缓存（开发）和 Redis（生产） |
| 部署 | 阿里云函数计算 FC | Serverless 部署，按量付费 |
| 前端 | 原生 HTML/CSS/JS | 零依赖，部署于 GitHub Pages |

## 本地开发

```bash
# 1. 克隆仓库
git clone https://github.com/peng-shao-stay/resume-analyzer.git
cd resume-analyzer

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 安装依赖
pip install -r jianliagent/code/requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 DEEPSEEK_API_KEY

# 5. 启动后端
cd jianliagent/code
python index.py
# 服务运行在 http://localhost:9000

# 6. 打开前端
# 用浏览器打开 frontend/index.html
# 确保 API 地址设置为 http://localhost:9000
```

## 部署

### 后端 — 阿里云函数计算 FC

```bash
# 使用 Serverless Devs 工具
cd jianliagent
s deploy

# 部署完成后获取公网 URL，例如:
# https://xxx.cn-hangzhou.fc.aliyuncs.com
```

部署前确保在 FC 控制台设置环境变量 `DEEPSEEK_API_KEY`。

### 前端 — GitHub Pages

1. Push 代码到 GitHub 仓库的 `main` 分支
2. 在仓库 Settings → Pages 中启用 GitHub Pages
3. Source 选择 "Deploy from a branch"，分支选 `main`，目录选 `/ (root)`
4. 前端页面将部署到 `https://peng-shao-stay.github.io/resume-analyzer/`
5. 打开页面后在 API 地址栏填入部署后的后端 URL

## 环境变量

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `DEEPSEEK_API_KEY` | **是** | - | DeepSeek API 密钥 |
| `DEEPSEEK_BASE_URL` | 否 | `https://api.deepseek.com` | API 地址 |
| `DEEPSEEK_MODEL` | 否 | `deepseek-chat` | 模型名称 |
| `CACHE_TYPE` | 否 | `memory` | 缓存类型（memory/redis） |
| `REDIS_HOST` | 否 | `localhost` | Redis 地址 |
| `MAX_FILE_SIZE_MB` | 否 | `10` | 上传文件大小限制 |

## 数据流

```
PDF 上传 → 文本提取(pdf_parser) → AI 结构化提取(ai_extractor)
    ↓
缓存存储(cache)
    ↓
岗位匹配(matcher):
  ├─ 关键词提取 + 匹配率计算
  ├─ 经验/学历匹配评分
  └─ AI 语义分析(DeepSeek) → 详细中文报告
    ↓
JSON 响应 → 前端可视化展示
```

## License

MIT
