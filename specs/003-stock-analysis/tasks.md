# Tasks: 个股多Agent深度分析

**输入**: 设计文档来自 `/specs/003-stock-analysis/`
**前置条件**: plan.md（必需）、spec.md（必需）、research.md、data-model.md、contracts/api-contracts.md

**测试**: 未明确要求测试，不生成测试任务。

**组织方式**: 任务按用户故事分组，确保每个故事可独立实现和测试。

## 格式说明: `[ID] [P?] [Story] 描述`

- **[P]**: 可并行执行（不同文件，无依赖）
- **[Story]**: 任务归属的用户故事（如 US1、US2、US3）
- 描述中包含精确文件路径

---

## 阶段 1: 项目初始化（共享基础设施）

**目的**: 数据库迁移和配置扩展

- [x] T001 创建 Alembic 数据库迁移脚本 `backend/app/infrastructure/db/migrations/` — 为 `t_analysis_article` 表新增 `article_type` VARCHAR(20) 默认值'event'和 `analysis_data` JSON 字段；为 `t_chat_session` 表新增 `session_type` VARCHAR(20) 默认值'event_analysis'和 `config` JSON 字段；为 `t_chat_message` 表新增 `agent_data` JSON 字段；创建索引 `idx_article_type`、`idx_session_type`
- [x] T002 [P] 扩展分析配置参数 `backend/app/core/config.py` — 新增配置字段：`analysis_timeout`（默认300秒）、`debate_rounds`（默认2轮）、`risk_debate_rounds`（默认2轮）、`max_tool_calls`（默认3次）、`stock_cache_ttl`（默认300秒）、`llm_deep_model`（默认取 LLM_MODEL 值）

---

## 阶段 2: 基础层（阻塞性前置条件）

**目的**: 所有用户故事共享的基础设施（领域模型、状态定义、AIService 扩展、数据工具）

**⚠️ 关键**: 本阶段必须全部完成后，才能开始任何用户故事的工作

- [x] T003 [P] 创建 AgentType 值对象 `backend/app/domain/value_objects/agent_type.py` — 定义 AgentType 枚举含12个值（market_analyst、fundamentals_analyst、news_analyst、sentiment_analyst、bull_researcher、bear_researcher、research_manager、trader、risky_debator、safe_debator、neutral_debator、risk_judge），映射 display_name 中文显示名和 phase 归属阶段（analysts/debate/trader/risk）
- [x] T004 [P] 扩展 ChatSession 领域实体 `backend/app/domain/entities/chat_session.py` — 新增 `session_type` 字段（默认'event_analysis'），新增 `config` JSON 字段（存储 stock_code、stock_name、analysis_mode、debate_rounds、risk_debate_rounds）
- [x] T005 [P] 扩展 ChatMessage 领域实体 `backend/app/domain/entities/chat_message.py` — 新增 `agent_data` JSON 字段（存储 current_agent、current_phase、agent_statuses 等多Agent中间数据）
- [x] T006 [P] 扩展 SQLAlchemy ORM 模型 `backend/app/infrastructure/db/models.py` — AnalysisArticle 新增列：`article_type`（String(20)，默认'event'）、`analysis_data`（JSON，可空）；ChatSession 新增列：`session_type`（String(20)，默认'event_analysis'）、`config`（JSON，可空）；ChatMessage 新增列：`agent_data`（JSON，可空）
- [x] T007 [P] 扩展 MySQL 对话仓储 `backend/app/infrastructure/repositories/mysql_chat_repo.py` — 更新 create/get 方法以持久化和加载 `session_type`、`config`、`agent_data` 新增字段
- [x] T008 [P] 创建个股分析 DTO `backend/app/application/dtos/stock_analysis_dto.py` — 定义 StockAnalysisConfigDTO（stock_code、stock_name、analysis_mode、debate_rounds、risk_debate_rounds）、StockValidationDTO（valid、stock_code、stock_name、market、message）、RecentAnalysisDTO（has_recent、article_id、title、created_at）、AgentStatusDTO（agent、phase、status）、DebateDTO（speaker、round、content）、DecisionDTO（action、target_price、confidence、risk_score、reasoning）
- [x] T009 创建 StockAnalysisState 状态定义 `backend/app/infrastructure/workflow/state/stock_analysis_state.py` — 实现三层 TypedDict：StockAnalysisInput（stock_code、stock_name、analysis_mode）、StockAnalysisWorking（market_report、fundamentals_report、news_report、sentiment_report、各分析师 tool_call_count、investment_debate_state、investment_plan、trader_investment_plan、risk_debate_state、current_agent、current_phase）、StockAnalysisOutput（title、summary、industries、final_decision、action、target_price、confidence、risk_score、reasoning、error）
- [x] T010 扩展 AIService `backend/app/infrastructure/ai/ai_service.py` — 为 `stream_chat()` 和 `tool_call()` 方法新增 `model`、`temperature`、`max_tokens` 可选参数；新增 `stream_chat_with_tools()` 方法支持 function calling + 流式输出；为 StreamChunk 数据类新增 `agent_id` 可选字段
- [x] T011 创建金融数据工具集 `backend/app/infrastructure/workflow/tools/stock_data_toolkit.py` — 实现4个 @tool 装饰器函数：get_stock_market_data(stock_code, trade_date) → K线/均线/MACD/KDJ、get_stock_fundamentals(stock_code) → PE/PB/营收/净利润/ROE、get_stock_news(stock_code) → 新闻资讯、get_stock_sentiment(stock_code) → 融资融券/北向资金/龙虎榜；实现故障转移链：AKShare → BaoStock → 错误提示；集成 Redis 缓存（5分钟TTL，对应 STOCK_CACHE_TTL 配置）

**检查点**: 基础层就绪 — 领域实体、状态定义、AIService、数据工具集均已可用，可以开始用户故事实现

---

## 阶段 3: 用户故事 1 — 个股深度分析 (优先级: P1) 🎯 MVP

**目标**: 用户输入A股股票代码/名称，系统通过多Agent协作（4位分析师→辩论→风险辩论→结构化决策）实时流式输出，最终生成报告保存到知识库

**独立测试**: 输入"宁德时代"或"300750"→ 发起完整分析 → 各Agent依次流式输出 → 得到结构化决策（操作方向+目标价+置信度+风险评分）→ 报告保存到知识库

### 用户故事 1 后端实现

- [x] T012 [P] [US1] 创建13个Agent的Prompt模板 `backend/app/infrastructure/workflow/prompts/stock_analysis/` — 每个Agent一个文件：market_analyst.py（技术面分析 system prompt + user template）、fundamentals_analyst.py（基本面分析）、news_analyst.py（新闻分析）、sentiment_analyst.py（情绪分析）、bull_researcher.py（看多论证）、bear_researcher.py（看空论证）、research_manager.py（辩论裁决+投资计划）、trader.py（交易决策）、risky_debator.py（激进风险观点）、safe_debator.py（保守风险观点）、neutral_debator.py（中立风险观点）、risk_judge.py（风险裁决）、signal_extractor.py（结构化决策提取）。每个文件导出 SYSTEM_PROMPT 和 USER_TEMPLATE 字符串。所有 Prompt 必须包含"不构成投资建议"免责声明（FR-010）
- [x] T013 [P] [US1] 创建信号提取领域服务 `backend/app/domain/services/signal_extractor.py` — 实现从 Risk Judge 输出中提取结构化决策：JSON 提取正则、action 容错映射（买入/持有/卖出变体）、14种中文价格模式正则、智能价格推算降级、多层降级链（JSON → 正则 → 智能推算 → 默认持有）。适配自 TradingAgents-CN 的 SignalProcessor（参考 research.md 决策5）
- [x] T014 [P] [US1] 扩展分析解析器 `backend/app/domain/services/analysis_parser.py` — 新增多Agent输出解析方法：从 analysis_data JSON 中提取各Agent摘要，根据Agent报告和辩论结论生成组合标题（≤15字）和摘要（≤80字）
- [x] T015 [US1] 创建4个分析师节点+消息清除节点 `backend/app/infrastructure/workflow/nodes/` — stock_market_analyst.py（技术面分析节点，含 tool_call 循环，最多3次调用 FR-013）、stock_fundamentals_analyst.py（基本面分析）、stock_news_analyst.py（新闻分析）、stock_sentiment_analyst.py（情绪分析）、msg_clear.py（Agent间消息上下文清理）。每个分析师节点流程：加载 Prompt → 调用 AIService.stream_chat_with_tools → 提取报告 → 更新状态（current_agent、current_phase、报告内容）。发射 SSE 事件：agent_status(running) → thinking + content 流 → agent_status(done) → agent_report(summary)
- [x] T016 [US1] 创建辩论节点 `backend/app/infrastructure/workflow/nodes/` — bull_researcher.py（根据所有分析师报告生成看多论据，轮次可通过 state 配置）、bear_researcher.py（生成看空论据，反驳看多观点）、research_manager.py（裁决辩论，使用深度思考模型生成投资计划，参考 research.md 决策9）。发射 SSE：agent_status + 每轮辩论事件
- [x] T017 [US1] 创建交易员节点 `backend/app/infrastructure/workflow/nodes/trader.py` — 根据投资计划使用快速思考模型生成交易建议（买入/持有/卖出 + 目标价）。发射 SSE：agent_status + content 流
- [x] T018 [US1] 创建风险辩论节点 `backend/app/infrastructure/workflow/nodes/` — risky_debator.py（激进风险观点）、safe_debator.py（保守风险观点）、neutral_debator.py（中立风险观点）、risk_judge.py（使用深度思考模型生成最终风险裁决）。风险辩论为三方循环辩论，轮次可配置。发射 SSE：agent_status + 辩论事件
- [x] T019 [US1] 创建信号提取节点+快速决策节点 `backend/app/infrastructure/workflow/nodes/` — signal_extractor_node.py（使用 SignalExtractor 领域服务提取结构化决策：action、target_price、confidence、risk_score，发射 decision SSE 事件）、quick_decision_node.py（快速模式：仅从技术面+基本面报告生成简要决策）
- [x] T020 [US1] 构建个股分析工作流图 `backend/app/infrastructure/workflow/graph/stock_analysis_graph.py` — 使用 LangGraph StateGraph 组装所有节点：START → 技术面分析师 → [工具循环] → 消息清除 → 基本面分析师 → [工具循环] → 消息清除 → 新闻分析师 → [工具循环] → 消息清除 → 情绪分析师 → [工具循环] → 消息清除 → 条件边（quick模式 → 快速决策 → END，full模式 → 看多研究员 ⇄ 看空研究员辩论循环 → 研究管理器 → 交易员 → 激进 ⇄ 保守 ⇄ 中立风险辩论循环 → 风险裁决 → 信号提取 → END）。接受 analysis_mode 参数进行条件路由（参考 research.md 决策10）。构建函数接受 ai_service + session_factory 作为依赖
- [x] T021 [US1] 创建个股分析用例 `backend/app/application/use_cases/stock_analysis_use_case.py` — 编排 StockAnalysisGraph 的 SSE 流：初始化图 → 流式处理状态更新 → yield SSE 事件（agent_status、content、reasoning、debate、agent_report、decision、title、summary、industries、done）。处理超时（可配置，默认300秒 FR-017）、失败时保留部分结果、分析去重（5分钟窗口）。通过 SaveArticleUseCase 将完成的分析保存到知识库（article_type='stock_analysis'，analysis_data=完整结构化JSON）
- [x] T022 [US1] 扩展对话用例 `backend/app/application/use_cases/chat_use_case.py` — 在 stream_message 方法中检测 event_type='stock_analysis' → 委托给 StockAnalysisUseCase 而非 AnalyzeEventUseCase。将请求中的 config 传递给用例
- [x] T023 [US1] 扩展路由层 `backend/app/routers/chat.py` 和 `backend/app/routers/analysis.py` — chat 路由：流式端点前校验 stock_analysis 配置（stock_code 必填，analysis_mode 在 ['quick','full'] 中）；create_session 支持 event_type='stock_analysis' 和 config；stream 端点将 config 传递给用例。analysis 路由新增端点：GET /api/analysis/validate-stock?keyword={}（通过 AKShare 验证股票代码/名称）、GET /api/analysis/stock-recent?stock_code={}&minutes=5（检查近期分析用于去重，对应边界场景）。包含正确的错误响应（400/409/503）

### 用户故事 1 前端实现

- [x] T024 [P] [US1] 扩展前端领域类型 `frontend/src/domain/types.ts` — 新增 AgentType 枚举（12个Agent标识）、AnalysisPhase 枚举（analysts/debate/trader/risk/done）、AnalysisMode 枚举（quick/full）、StockAnalysisConfig 接口（stock_code、stock_name、analysis_mode、debate_rounds、risk_debate_rounds）、AgentStatusEvent 接口（agent、phase、status）、DebateEvent 接口（speaker、round、content）、AgentReportEvent 接口（agent、summary）、DecisionEvent 接口（action、target_price、confidence、risk_score、reasoning）、StockValidationResult 接口（valid、stock_code、stock_name、market、message）
- [x] T025 [P] [US1] 扩展前端领域常量 `frontend/src/domain/constants.ts` — 新增 AGENT_DISPLAY_NAMES 映射（market_analyst→'技术面分析'、fundamentals_analyst→'基本面分析' 等）、AGENT_PHASE_MAPPING、ANALYSIS_MODE_OPTIONS（quick/full）、DEFAULT_DEBATE_ROUNDS、DEFAULT_RISK_DEBATE_ROUNDS
- [x] T026 [P] [US1] 创建个股分析服务 `frontend/src/services/stockAnalysisService.ts` — 实现 API 调用：validateStock(keyword) → GET /api/analysis/validate-stock、checkRecentAnalysis(stockCode, minutes) → GET /api/analysis/stock-recent、streamStockAnalysis(sessionId, request) → POST SSE /api/chat/sessions/{id}/stream 并指定 stock_analysis 事件类型，复用现有 chatService 的 SSE 模式
- [x] T027 [US1] 创建个股分析状态管理 `frontend/src/store/stockAnalysisStore.ts` — Zustand store，状态包含：stockCode、stockName、analysisMode、analysisState（idle/running/done/error）、currentPhase、agentStatuses（Record<AgentType, string>）、agentReports（Record<AgentType, string>）、debates（DebateEvent[]）、decision（DecisionEvent|null）、title、summary、industries、content。动作：setStock、setMode、startAnalysis、updateAgentStatus、addAgentReport、addDebate、setDecision、appendContent、reset。处理 SSE 事件分发到对应的状态更新
- [x] T028 [P] [US1] 创建股票搜索输入组件 `frontend/src/components/stock-analysis/StockSearchInput.tsx` — Ant Design AutoComplete 组件，带防抖的股票验证（调用 stockAnalysisService.validateStock()），选项显示股票代码+名称，未找到时显示"未找到该股票"错误状态，选择后自动填入
- [x] T029 [P] [US1] 创建分析模式选择器组件 `frontend/src/components/stock-analysis/AnalysisModeSelector.tsx` — Ant Design Radio.Group，两个选项：快速分析（quick，"仅技术面+基本面，约1分钟"）和深度分析（full，"4位分析师+辩论+风险辩论，约3-5分钟"），切换时更新 store 中的 analysisMode
- [x] T030 [US1] 创建个股分析主页面 `frontend/src/pages/StockAnalysisPage.tsx` — 三种状态页面：(1) 空闲态：居中布局含 StockSearchInput + AnalysisModeSelector + "开始分析"按钮（未选择有效股票时禁用）；(2) 分析中：顶部显示股票名称+当前阶段，流式内容区展示 Agent 输出，进度指示器；(3) 完成态：完整分析报告含决策摘要 + "保存到知识库"操作。处理 SSE 流生命周期：开始时连接 → 解析事件（agent_status、content、reasoning、debate、agent_report、decision、title、summary、industries、done）→ 更新 store → 完成/出错时断开。显著位置展示"不构成投资建议"免责声明
- [x] T031 [US1] 添加路由和侧边栏入口 — 扩展 `frontend/src/App.tsx` 添加路由 `/stock-analysis` → StockAnalysisPage；扩展 `frontend/src/components/layout/AppLayout.tsx` 侧边栏菜单：新增"个股分析"菜单项（StockOutlined 图标），支持导航到 /stock-analysis，位于"AI事件分析"之后

**检查点**: 完整分析链路可用 — 输入股票代码 → 多Agent协作分析 → 流式输出 → 结构化决策 → 保存知识库

---

## 阶段 4: 用户故事 2 — 分析过程可视化 (优先级: P2)

**目标**: 用户发起分析后，实时看到每个Agent的工作进度和中间结果，而非只等最终结果

**独立测试**: 发起分析后30秒内看到第一个Agent输出，后续Agent依次输出，辩论过程实时展示，无需等待全部分析完成

### 用户故事 2 前端实现

- [x] T032 [US2] 创建Agent进度面板组件 `frontend/src/components/stock-analysis/AgentProgressPanel.tsx` — 垂直时间线展示所有Agent，按阶段分组（分析师→辩论→交易→风险）。每个Agent显示：图标+中文名称+状态指示器（pending=灰色、running=蓝色旋转、done=绿色勾、failed=红色叉）。自动高亮当前运行中的Agent并滚动到可视区域。使用 Ant Design Steps/Timeline 组件，遵循 DESIGN.md 卡片化布局
- [x] T033 [P] [US2] 创建Agent报告卡片组件 `frontend/src/components/stock-analysis/AgentReportCard.tsx` — Ant Design Card 展示单个Agent分析结果：Agent图标+名称、摘要文本（≤100字）、可展开的完整报告区域、数据源标签、时间戳。支持流式状态：Agent运行中显示骨架屏，完成时过渡为完整内容。按Agent类型分色（技术面=蓝色、基本面=绿色、新闻=橙色、情绪=紫色）
- [x] T034 [P] [US2] 创建辩论时间线组件 `frontend/src/components/stock-analysis/DebateTimeline.tsx` — Ant Design Timeline 展示看多/看空辩论轮次和风险辩论轮次。每条记录：发言者头像（看多=绿色↑、看空=红色↓、激进=火焰、保守=盾牌、中立=天平）、轮次编号、论据内容。支持流式：新论据出现时带动画。辩论轮次结束后展示"投资裁决"卡片含研究管理器结论
- [x] T035 [P] [US2] 创建决策卡片组件 `frontend/src/components/stock-analysis/DecisionCard.tsx` — 醒目卡片展示最终结构化决策：操作方向徽章（买入=绿色、持有=蓝色、卖出=红色）、目标价、置信度进度条（0-100%）、风险评分进度条（0-100%，颜色渐变绿色→红色）、决策理由文本、"不构成投资建议"免责声明。使用 Ant Design Progress + Statistic 组件
- [x] T036 [US2] 扩展个股分析状态管理 `frontend/src/store/stockAnalysisStore.ts` — 新增细粒度流式状态：contentBlocks（{agent, type, text} 数组用于流式文本组装）、phaseProgress（各阶段完成百分比）。新增动作：updateStreamingContent(agent, text) 用于增量文本渲染
- [x] T037 [US2] 集成可视化组件到个股分析页面 `frontend/src/pages/StockAnalysisPage.tsx` — 替换基础流式展示为：左侧面板（AgentProgressPanel，固定位置）、右侧面板（可滚动区域含各已完成Agent的 AgentReportCard、辩论阶段的 DebateTimeline、分析完成后的 DecisionCard）。布局：Ant Design Row/Col 分栏，左侧面板280px固定，右侧面板弹性宽度。在活跃Agent的报告卡片中实时显示流式文本，带打字光标动画

**检查点**: 分析过程可视化完整 — Agent进度实时展示，中间结果立即可见，辩论过程动态呈现

---

## 阶段 5: 用户故事 3 — 分析历史与对比 (优先级: P3)

**目标**: 用户查看某只股票的历史深度分析记录，对比不同时间点的分析结论

**独立测试**: 对同一只股票进行两次分析后，能在页面查看历史列表并对比两次分析结果

### 用户故事 3 后端实现

- [x] T038 [US3] 扩展知识库文章列表端点 `backend/app/routers/knowledge.py` 和 `backend/app/application/use_cases/manage_article.py` — 支持查询参数：`article_type=stock_analysis`、`stock_code={code}` 筛选。列表响应中返回 `analysis_data.decision`（action、target_price、confidence、risk_score）用于对比展示，无需返回完整内容。有当前价格时添加 current_price 字段（用于目标价偏离度展示）

### 用户故事 3 前端实现

- [x] T039 [US3] 创建分析历史列表组件 `frontend/src/components/stock-analysis/AnalysisHistoryList.tsx` — Ant Design List 展示选定股票的历史分析记录：每项显示日期、操作方向徽章、目标价、置信度、风险评分。按时间倒序排列。支持点击查看完整报告。空状态显示"暂无分析记录"（遵循 DESIGN.md）。通过 knowledgeService 加载（article_type=stock_analysis&stock_code={code}）
- [x] T040 [US3] 创建分析对比组件 `frontend/src/components/stock-analysis/AnalysisComparison.tsx` — Ant Design Modal/Drawer 并排对比两次分析：对比表格含日期、操作方向、目标价、置信度、风险评分、决策理由摘要行。高亮差异（如操作方向从买入→持有）。有当前价格时展示与目标价的实际偏离度（对应 spec 验收场景3）
- [x] T041 [US3] 集成历史功能到个股分析页面 `frontend/src/pages/StockAnalysisPage.tsx` — 在分析区域下方新增"历史分析"标签/区域展示 AnalysisHistoryList（当前股票）。有≥2条分析时显示"对比分析"按钮打开 AnalysisComparison。新分析完成后自动刷新列表。点击历史记录项跳转到知识库文章详情

**检查点**: 历史分析可查看、可对比，辅助用户复盘

---

## 阶段 6: 用户故事 4 — 快速分析模式 (优先级: P4)

**目标**: 用户选择快速模式，仅运行技术面+基本面分析师，1分钟内得出简要分析

**独立测试**: 选择"快速分析"后60秒内得到包含技术面+基本面摘要的简要报告

**备注**: 后端 Graph 已在阶段3 T020 支持条件路由（quick 模式走快速决策节点），本阶段聚焦前端增强和体验优化

### 用户故事 4 前端实现

- [x] T042 [US4] 增强分析模式选择器 `frontend/src/components/stock-analysis/AnalysisModeSelector.tsx` — 更新快速模式描述含时间估算（"约30-60秒"），新增 tooltip 解释快速模式范围（仅技术面+基本面，无辩论环节）。调整按钮文案："快速分析" vs "深度分析"
- [x] T043 [US4] 更新个股分析页面适配快速模式显示 `frontend/src/pages/StockAnalysisPage.tsx` — 当 analysisMode='quick' 时：仅显示2个Agent卡片（技术面+基本面），隐藏 AgentProgressPanel 的辩论/风险阶段，显示简化版决策卡片（无辩论/风险上下文），展示"快速分析报告"徽章。快速分析自动保存到知识库
- [x] T044 [US4] 更新状态管理适配快速模式 `frontend/src/store/stockAnalysisStore.ts` — 新增 quickAnalysisResult 状态存储简化结果（market_summary、fundamentals_summary、brief_advice）。处理快速模式 SSE 事件（更少的 agent_status，无辩论事件，简化决策）

**检查点**: 快速分析模式可用 — 60秒内得到简要报告

---

## 阶段 7: 收尾与横切关注点

**目的**: 边界场景处理、免责声明强化、故障转移、最终验证

- [x] T045 [P] 实现边界场景处理 `backend/app/application/use_cases/stock_analysis_use_case.py` — 处理：无效股票代码（400响应）、停牌股票（继续使用历史数据分析+标注"当前停牌"警告）、单Agent LLM调用失败（保留已完成结果，降级处理）、5分钟内重复分析（409响应+返回最近分析链接）、分析超时>10分钟（终止+保存部分结果）、并发分析防重（409响应）
- [x] T046 [P] 强化"不构成投资建议"免责声明 — 确保后端 Prompt（T012）包含免责声明、前端 DecisionCard（T035）显示持久免责横幅、StockAnalysisPage（T030）显示底部免责声明（FR-010）
- [x] T047 [P] 实现工具调用故障转移 `backend/app/infrastructure/workflow/tools/stock_data_toolkit.py` — 每个工具：尝试 AKShare → 失败时尝试 BaoStock → 失败时返回含可用数据的错误消息（FR-012）。添加3秒超时重试逻辑（SC-005）
- [ ] T048 执行 quickstart.md 端到端验证 — 按照 `specs/003-stock-analysis/quickstart.md` 步骤：启动后端+前端、验证 validate-stock API、验证 SSE 流式输出（curl）、验证前端页面完整流程、验证知识库集成。修复发现的问题

---

## 依赖关系与执行顺序

### 阶段依赖

- **阶段1（初始化）**: 无依赖 — 可立即开始
- **阶段2（基础层）**: 依赖阶段1完成 — 阻塞所有用户故事
- **用户故事1（阶段3）**: 依赖阶段2完成 — 核心分析能力
- **用户故事2（阶段4）**: 依赖阶段3完成 — 可视化基于 US1 的 SSE 事件
- **用户故事3（阶段5）**: 依赖阶段3完成 — 历史读取 US1 保存的分析文章
- **用户故事4（阶段6）**: 依赖阶段3完成 — 快速模式使用 US1 的图条件路由
- **收尾（阶段7）**: 依赖所有期望的用户故事完成

### 用户故事依赖

- **US1 (P1)**: 阶段2完成后即可开始 — 无其他故事依赖
- **US2 (P2)**: 依赖 US1 — 渲染 US1 的 SSE 事件为丰富UI
- **US3 (P3)**: 依赖 US1 — 读取 US1 保存的分析文章
- **US4 (P4)**: 依赖 US1 — 使用 US1 图中的快速模式条件路由

### 阶段3（US1）内部关键路径

```
T012（Prompt模板）──┐
T013（信号提取服务）──┤
T014（分析解析器）──┤
                    ├── T015-T019（节点实现）──→ T020（工作流图）──→ T021（用例）──→ T022（对话用例）──→ T023（路由）
T009（状态定义）────┘
T010（AIService）──┘
T011（数据工具集）──┘

T024-T025（类型/常量）──┐
T026（服务层）──────────┤
T027（状态管理）────────┼── T028-T029（搜索/模式组件）──→ T030（主页面）──→ T031（路由入口）
                         ┘
```

### 并行执行机会

- **阶段1**: T001、T002 可并行
- **阶段2**: T003-T008 均可并行（不同文件，无依赖）；T009-T011 需在 T006 之后顺序执行
- **阶段3后端**: T012、T013、T014 可并行；T015-T018 可并行（不同节点文件）
- **阶段3前端**: T024、T025、T026 可并行；T028、T029 可并行
- **阶段4**: T033、T034、T035 可并行（不同组件文件）
- **阶段5**: T039、T040 可并行（不同组件文件）
- **阶段6**: T042-T044 需顺序执行（每步基于前一步）
- **阶段7**: T045、T046、T047 可并行

---

## 并行示例：阶段3后端节点

```bash
# T012（Prompt）+ T009（状态）+ T010（AIService）+ T011（工具集）完成后：

# 并行启动所有分析师节点：
任务 T015: "创建4个分析师节点+消息清除节点"
任务 T016: "创建辩论节点"
任务 T017: "创建交易员节点"
任务 T018: "创建风险辩论节点"

# 然后顺序执行：
任务 T019: "创建信号提取节点+快速决策节点"
任务 T020: "构建个股分析工作流图"
```

## 并行示例：阶段3前端

```bash
# 并行启动类型、常量和服务：
任务 T024: "扩展前端领域类型 frontend/src/domain/types.ts"
任务 T025: "扩展前端领域常量 frontend/src/domain/constants.ts"
任务 T026: "创建个股分析服务"

# 然后顺序执行：
任务 T027: "创建个股分析状态管理"
任务 T028: "创建股票搜索输入组件"
任务 T029: "创建分析模式选择器组件"
任务 T030: "创建个股分析主页面"
任务 T031: "添加路由和侧边栏入口"
```

---

## 实施策略

### MVP 优先（仅用户故事1）

1. 完成阶段1：初始化（T001-T002）
2. 完成阶段2：基础层（T003-T011）— **关键，阻塞一切**
3. 完成阶段3：用户故事1（T012-T031）— **核心分析能力**
4. **停步验证**: 输入股票代码 → 完整分析流程 → 结构化决策 → 保存知识库
5. 可部署/演示

### 增量交付

1. 完成初始化+基础层 → 基础就绪
2. 增加 US1 → 端到端测试 → **部署/演示（MVP！）**
3. 增加 US2 → 实时可视化测试 → 部署/演示
4. 增加 US3 → 历史对比测试 → 部署/演示
5. 增加 US4 → 快速分析测试 → 部署/演示
6. 收尾 → 边界场景+验证 → 最终发布

### 多人并行策略

1. 团队共同完成初始化+基础层
2. 基础层完成后：
   - 开发者A：US1 后端（T012-T023）
   - 开发者B：US1 前端（T024-T031，类型/服务就绪后）
3. US1 完成后：
   - 开发者A：US3 后端（T038）+ US4 后端（图已完成）
   - 开发者B：US2 前端（T032-T037）
4. 然后 US3 前端（T039-T041）+ US4 前端（T042-T044）并行

---

## 备注

- [P] 标记 = 不同文件，无依赖，可并行
- [Story] 标签将任务映射到具体用户故事，便于追溯
- 每个用户故事应可独立完成和测试
- 每完成一个任务或逻辑组后提交
- 在任何检查点停下独立验证
- 后端遵循 DDD 分层：Router → Application → Domain → Infrastructure
- 前端遵循：Page → Application → Service；所有 API 调用经 services/
- 所有 AI 调用经 AIService，节点不直接使用 langchain SDK
- 所有 Prompt 在 `infrastructure/workflow/prompts/` 目录，节点内不硬编码
- 分析模式（quick/full）通过图条件路由处理，非独立图
