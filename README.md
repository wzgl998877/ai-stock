# AI Stock — AI 驱动的 A 股研究平台

> 一款面向个人投资者的 AI 辅助股票研究工具，融合大模型分析、实时行情数据与缠论策略监控三大核心能力。
>
> **本工具仅供投研参考，不构成任何投资建议。**

---

## 本地启动指南

### 环境要求

| 工具 | 版本要求 | 说明 |
|------|---------|------|
| Python | >= 3.10 | 后端运行环境 |
| Node.js | >= 18 | 前端运行环境 |
| MySQL | >= 8.0 | 数据库（Phase 4+ 需要，核心分析流程可暂不依赖） |
| Redis | >= 7.0 | 缓存（Phase 5+ 需要，核心分析流程可暂不依赖） |

### 第一步：配置后端环境变量

```bash
cd backend
cp .env.example .env
```

编辑 `backend/.env`，填入你的 AI API Key（必填，其他项有默认值）：

```env
# === 大模型（必填）===
OPENAI_API_KEY=sk-your-key-here          # 填入你的 DeepSeek 或 OpenAI API Key
OPENAI_BASE_URL=https://api.deepseek.com/v1  # 默认 DeepSeek，也可换成 OpenAI
LLM_MODEL=deepseek-chat                  # 模型名称

# === 数据库（Phase 4+ 需要）===
DATABASE_URL=mysql+aiomysql://root:password@localhost:3306/ai_stock

# === Redis（Phase 5+ 需要）===
REDIS_URL=redis://localhost:6379/0

# === 应用 ===
LOG_LEVEL=info
CORS_ORIGINS=["http://localhost:5173"]
ANALYSIS_TIMEOUT=120
```

> 支持 OpenAI 兼容的任何接口。如果你用 OpenAI 官方，改为：
> `OPENAI_BASE_URL=https://api.openai.com/v1` + `LLM_MODEL=gpt-4o`

### 第二步：安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 第三步：安装前端依赖
改到国内镜像
```bash
npm config set registry https://registry.npmmirror.com
npm config get registry
```

```bash
cd frontend
npm install
```

### 第四步：启动服务

打开两个终端窗口分别启动后端和前端：

**终端 1 — 后端：**

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**终端 2 — 前端：**

```bash
cd frontend
npm run dev
```

### 第五步：开始使用

浏览器打开 http://localhost:5173 ，你将看到 AI 事件分析页面：

1. 选择事件类型（地缘政治 / 政策法规 / 财报季报 / 产业链分析 / 其他）
2. 在输入框描述你想分析的事件（至少 10 个字）
3. 点击「分析」按钮，AI 将流式生成结构化分析报告

### 验证服务是否正常

```bash
# 后端健康检查
curl http://localhost:8000/health
# 应返回: {"status":"ok"}
```

---

## 当前实现进度

| 模块 | 阶段 | 状态 |
|------|------|------|
| 模块一 · AI 事件分析 | 核心分析流程（Phase 1-3） | 已完成，可运行 |
| 模块一 · 保存到知识库 | Phase 4 | 待实现 |
| 模块一 · 知识库浏览搜索 | Phase 5 | 待实现 |
| 模块一 · 相似问题检测 | Phase 6 | 待实现 |
| 模块一 · 大事提醒 | Phase 7 | 待实现 |
| 模块一 · 新用户引导 | Phase 8 | 待实现 |
| 模块二 · 行情数据 | — | 规划中 |
| 模块三 · 缠论策略 | — | 规划中 |

---

## 三大核心模块

### 模块一：AI 事件分析 & 行业日志

- 输入任意宏观事件（例：美国打伊朗对A股有什么影响？）
- AI 调用大模型自动生成分析文章
- 文章涵盖：事件背景 → 影响逻辑 → 受益行业 → 值得关注的相关股票
- 用户可选择是否保存该分析
- 保存后自动归类到对应行业日志，形成时间线记录
- 大事提醒：手动添加即将发生的重要事件，到期前自动提醒

### 模块二：行情数据展示

- 行业列表和行业详情页
- 个股详情页（K 线图、分时图、财务数据）
- 数据来源：AKShare

### 模块三：缠论策略监控

- 自选股管理
- 缠论笔/线段/中枢自动计算
- 买卖点自动标注与报警通知

---

## 项目目录结构

```
ai-stock/
├── backend/                          # Python 后端
│   ├── app/
│   │   ├── main.py                   # FastAPI 应用入口
│   │   ├── core/                     # 基础设施：配置、数据库、异常
│   │   │   ├── config.py             # Pydantic Settings（从 .env 读取）
│   │   │   ├── database.py           # SQLAlchemy 异步引擎
│   │   │   └── exceptions.py         # 统一异常定义
│   │   ├── domain/                   # 领域层（纯业务，无框架依赖）
│   │   │   ├── entities/             # 实体：Article、Reminder、User 等
│   │   │   ├── value_objects/        # 值对象：EventType、IndustryTag
│   │   │   ├── repositories/         # Repository 接口（ABC）
│   │   │   └── services/             # 领域服务：AnalysisParser、SimilarityCalculator
│   │   ├── application/              # 应用层（流程编排）
│   │   │   ├── use_cases/            # 用例：AnalyzeEventUseCase
│   │   │   └── dtos/                 # DTO：请求/响应数据结构
│   │   ├── infrastructure/           # 基础设施层（技术实现）
│   │   │   ├── ai/                   # AI 服务抽象 + Prompt 模板
│   │   │   ├── db/                   # ORM 模型 + Alembic 迁移
│   │   │   └── repositories/         # Repository 实现（MySQL）
│   │   └── routers/                  # 路由：analysis.py、knowledge.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/                         # React 前端
│   ├── src/
│   │   ├── main.tsx                  # React 入口
│   │   ├── App.tsx                   # 路由配置
│   │   ├── pages/                    # 页面：AnalysisPage
│   │   ├── components/               # 组件：EventTypeSelector、AnalysisInput 等
│   │   ├── application/              # 前端编排：useAnalysis
│   │   ├── services/                 # API 服务：analysisService
│   │   ├── store/                    # Zustand 状态：analysisStore
│   │   ├── hooks/                    # Hooks：useSSE、useDraft
│   │   └── domain/                   # 类型定义 + 常量
│   ├── package.json
│   └── .env.example
├── docs/                             # 产品文档、PRD
├── specs/                            # 功能规格、实现计划、任务清单
├── constitution.md                   # 项目宪章（核心原则）
├── rules/                            # 编码规则（后端分层、前端分层）
└── CLAUDE.md                         # AI 助手工作手册
```

---

## 技术架构

```
前端 (React 18 + Ant Design 5 + Zustand)
    ↓ HTTP / SSE
后端 (Python FastAPI)
    ├── Router → Application → Domain → Infrastructure（严格分层）
    ├── AI 分析服务 → httpx 流式调用 OpenAI 兼容 API
    ├── 行情数据服务 → AKShare
    ├── 缠论计算引擎 → 纯 Python 实现
    └── 定时任务调度 → APScheduler
    ↓
数据库层
    ├── MySQL（结构化数据：分析文章、行业、股票）
    └── Redis（缓存：行情数据、计算结果）
```

### 技术选型一览

| 层次 | 技术 | 选择理由 |
|------|------|----------|
| 前端框架 | React 18 + TypeScript | 生态成熟，组件丰富 |
| UI 组件库 | Ant Design 5 | 国内常用，金融类界面适配好 |
| 状态管理 | Zustand | 轻量，API 简洁 |
| 图表库 | ECharts 5 | 支持 K 线图，文档完善 |
| 后端框架 | Python FastAPI | 轻量快速，原生 async，AI 生态最佳 |
| 大模型接口 | 统一封装（支持 OpenAI / DeepSeek） | 灵活切换，httpx 流式调用 |
| 数据库 | MySQL 8.0 | FULLTEXT ngram 中文搜索 |
| 缓存 | Redis | 行情数据高频读取加速 |
| 部署 | Docker Compose | 一键启动，方便迁移 |

---

## API 端点一览

| 方法 | 路径 | 说明 | 状态 |
|------|------|------|------|
| GET | `/health` | 健康检查 | 已实现 |
| POST | `/api/analysis/stream` | AI 流式分析（SSE） | 已实现 |
| POST | `/api/analysis/articles` | 保存分析到知识库 | 占位 |
| POST | `/api/analysis/similarity` | 相似问题检测 | 占位 |

---

## 服务器部署

### 前置条件

- 本地安装 Python 3 + `paramiko`（`pip install paramiko`）
- 本地安装 Node.js >= 18（用于构建前端）
- 服务器已安装 Python 3、pip3
- 服务器防火墙/安全组已放行对应端口（默认 8000）

### 配置文件准备

部署前需要准备以下配置文件：

| 文件 | 说明 |
|------|------|
| `deploy.conf` | SSH 连接与部署目录配置，从 `deploy.conf.example` 复制 |
| `backend/.env.prod` | 后端生产环境变量（API Key、数据库、端口等） |
| `frontend/.env.production` | 前端生产环境变量（Vite 构建时自动加载） |

```bash
# 1. 部署配置
cp deploy.conf.example deploy.conf
# 编辑 deploy.conf，设置 REMOTE（服务器地址）、DEPLOY_DIR（部署目录）、SSH_PASSWORD（密码，留空则用密钥）

# 2. 后端生产环境变量
# 参考 backend/.env.example，创建 backend/.env.prod
# 必须包含：OPENAI_API_KEY、OPENAI_BASE_URL、LLM_MODEL、PORT 等
# 其中 PORT 决定服务监听端口（默认 8000）

# 3. 前端生产环境变量
# 创建 frontend/.env.production
# 设置 VITE_API_BASE_URL 等前端构建变量
```

### 一键部署

```bash
python upload.py
```

脚本会自动完成以下步骤：

1. **前端构建**：以 `--mode prod` 执行 `vite build`（读取 `frontend/.env.production`）
2. **打包**：将后端代码、`requirements.txt`、`backend/.env.prod`、前端 `dist` 打包为 tar.gz
3. **上传**：通过 SFTP 上传到服务器 `/tmp`
4. **远程部署**：解压 → 安装依赖 → 配置 systemd 服务 → 启动

部署完成后访问 `http://<服务器IP>:<端口>`，前后端同端口，无需 Nginx。

### 常用运维命令

```bash
# 查看服务状态
systemctl status ai-stock

# 查看实时日志
journalctl -u ai-stock -f

# 重启服务
systemctl restart ai-stock

# 停止服务
systemctl stop ai-stock
```

### 更新部署

修改代码后再次执行 `python upload.py` 即可，会自动覆盖并重启服务。

---

## 已知限制与注意事项

1. **AI API Key 必填**：核心分析功能依赖大模型 API，无 Key 无法使用
2. **AKShare 数据限制**：免费数据有频率限制，实时行情存在几分钟延迟
3. **缠论主观性**：缠论本身存在主观判断空间，程序实现为简化版本，仅供参考
4. **投资风险提示**：本工具仅为辅助研究，不构成投资建议，投资有风险

---

## 给 AI 助手（Claude）的说明

- **`constitution.md`**（宪章）：核心原则、技术约束、架构红线
- **`CLAUDE.md`**（工作手册）：编码规则、文档索引、构建命令
- **`rules/backend.md`** + **`rules/frontend.md`**：前后端分层规则

---

*最后更新：2026-05-24*
