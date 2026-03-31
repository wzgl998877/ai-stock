# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码仓库中工作时提供指导。

## 项目概述

AI Stock 是一款面向个人投资者的 AI 驱动 A 股研究平台，融合三大核心能力：
1. **AI 事件分析 & 行业日志**：使用大模型分析宏观事件对 A 股的影响
2. **行情数据展示**：实时行情、财务数据和 K 线图表
3. **缠论策略监控**：自动化的缠论模式识别及买卖信号

## 技术栈

| 层级 | 技术选型 |
|------|----------|
| 前端 | React 18 + TypeScript + Ant Design 5 + ECharts 5 |
| 后端 | Python FastAPI |
| 股票数据 | AKShare（免费开源 A 股数据） |
| 大模型集成 | 统一抽象层，支持 OpenAI/DeepSeek API |
| 数据库 | PostgreSQL（结构化数据） |
| 缓存 | Redis（行情数据、计算结果） |
| 定时任务 | APScheduler |
| 部署 | Docker Compose |

## 项目架构

```
前端 (React + Ant Design)
    ↓ HTTP API
后端 (Python FastAPI)
    ├── AI 分析服务 → OpenAI / DeepSeek API
    ├── 行情数据服务 → AKShare
    ├── 缠论计算引擎 → 纯 Python 实现
    └── 定时任务调度 → APScheduler
    ↓
数据库层
    ├── PostgreSQL（分析文章、日志、自选股）
    └── Redis（行情数据缓存、计算结果）
```

## 规划目录结构

```
ai-stock/
├── backend/                    # Python 后端
│   ├── api/                    # 路由处理
│   │   ├── analysis.py         # 模块一：AI 分析接口
│   │   ├── market.py           # 模块二：行情数据接口
│   │   └── strategy.py         # 模块三：策略监控接口
│   ├── services/               # 业务逻辑层
│   │   ├── llm_service.py      # 大模型集成封装
│   │   ├── stock_service.py    # AKShare 数据获取
│   │   └── chan_service.py     # 缠论计算引擎
│   ├── models/                 # 数据库模型
│   ├── scheduler/              # 定时任务
│   ├── config.py               # 配置文件（API Key 等）
│   └── main.py                 # 程序入口
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Analysis/       # 模块一页面
│   │   │   ├── Market/         # 模块二页面
│   │   │   └── Strategy/       # 模块三页面
│   │   └── components/         # 公共组件
│   └── package.json
├── docker-compose.yml          # 一键部署配置
├── .env.example                # 环境变量示例
└── README.md
```

## SpecKit 开发流程

本项目使用 SpecKit 进行功能规格说明和实施规划。主要命令：

- `/speckit.specify` - 从自然语言描述创建或更新功能规格
- `/speckit.plan` - 执行实施规划工作流程，生成设计文档
- `/speckit.tasks` - 生成可执行的、依赖关系有序的任务列表
- `/speckit.implement` - 执行实施计划，处理任务
- `/speckit.clarify` - 识别规格说明中不够明确的区域，提出针对性问题
- `/speckit.checklist` - 基于需求生成自定义检查清单
- `/speckit.analyze` - 跨文档一致性和质量分析

功能规格和规划存储在 `.specify/templates/`，并在 `specs/` 目录中记录。

## 环境变量

必需的 `.env` 配置：

```env
# 大模型配置（选其一或多个）
OPENAI_API_KEY=your_openai_key
OPENAI_BASE_URL=https://api.openai.com/v1
DEEPSEEK_API_KEY=your_deepseek_key

# 数据库
DATABASE_URL=postgresql://user:password@localhost:5432/ai_stock

# Redis
REDIS_URL=redis://localhost:6379

# 可选：邮件通知
SMTP_HOST=smtp.qq.com
SMTP_USER=your_email@qq.com
SMTP_PASS=your_smtp_password
```

## 三大核心模块

### 模块一：AI 事件分析 & 行业日志
- 用户输入宏观事件（如："美国打伊朗对 A 股有什么影响？"）
- 大模型生成结构化分析：事件背景 → 影响逻辑 → 受益行业 → 相关股票
- 文章自动标记行业和股票标签，保存到行业日志形成时间线
- 大事提醒功能，到期可一键触发 AI 分析

### 模块二：行情数据展示
- 行业列表和行业详情页
- 个股详情页（类似同花顺/东方财富风格）：
  - 日 K 线图（缩放、均线叠加）
  - 分时图（实时价格走势）
  - 基本信息（股票代码、名称、所属行业、市值）
  - 财务数据（营收、净利润、PE、PB、ROE）
  - 关联大事件（来自模块一标记了该股票的分析文章）

### 模块三：缠论策略监控
- 自选股管理
- 缠论核心要素自动计算：
  - 笔：识别价格的顶底结构
  - 线段：多笔组合形成的趋势段
  - 中枢：三段重叠区域，判断盘整区间
- 买卖点自动标注：
  - 一买、二买、三买及对应的一卖、二卖、三卖
- 报警通知（页面弹窗 + 可选邮件通知）

## 已知限制

1. **AKShare 数据限制**：免费数据有频率限制，实时行情存在几分钟延迟，不适合高频交易
2. **缠论主观性**：缠论本身存在主观判断空间，程序实现为简化版本，仅供参考
3. **投资风险提示**：本工具仅为辅助研究，不构成投资建议

## 开发路线图

1. **第一阶段（基础框架）**：前后端基础框架搭建、数据库/Redis 配置、AKShare 接入
2. **第二阶段（模块一）**：接入大模型 API、自动标签提取、分析日志存储/时间线、大事提醒
3. **第三阶段（模块二）**：行业列表/详情页、K 线/分时图、财务数据展示
4. **第四阶段（模块三）**：缠论计算、买卖点标注、自选股监控/报警
5. **第五阶段（完善与部署）**：Docker 容器化、云服务器部署、性能优化
