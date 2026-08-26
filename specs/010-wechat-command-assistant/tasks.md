---
description: "微信指令助手实施任务清单"
---

# Tasks: 微信指令助手（WeChat Command Assistant）

**Input**: Design documents from `/specs/010-wechat-command-assistant/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: 项目宪法（CLAUDE.md 质量门禁 + rules/testing.md）强制单元测试——每个实现任务配对测试任务，测试先行（先写失败测试再实现）。

**Organization**: 按用户故事分组。框架层（消息链路 + 注册表 + 持久化）全部在 Foundational，用户故事阶段只写"工具"与"体验增强"，兑现 FR-020/021（新增指令不改框架）。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件、无未完成依赖）
- **[Story]**: 归属用户故事（US1-US6）
- 所有路径相对仓库根目录

---

## Phase 1: Setup

**Purpose**: 配置就绪

- [x] T001 在 `backend/app/core/config.py` 新增 `wechat_cmd_enabled` / `wechat_cmd_authorized_users` / `wechat_cmd_llm_timeout` 三项配置（默认值与回落逻辑见 data-model.md §4，research D10），并在本地 `backend/.env` 与生产 `.env.prod` 模板中补注释项

---

## Phase 2: Foundational（阻塞所有用户故事）

**Purpose**: 指令主链路骨架——域模型、持久化、注册表、网关、路由、调度、装配。完成后任意工具可即插即用。

**⚠️ CRITICAL**: US1-US6 全部依赖本阶段

### Tests（先行，实现前须 FAIL）

- [x] T002 [P] 编写 `backend/tests/unit/infrastructure/test_wechat_command_repo.py`：SQLite 内存库覆盖 msg_id 唯一冲突返回重复、状态机非法迁移拒绝、fail_orphans 孤儿清理三组用例（Fake 范式对标 research D12）
- [x] T003 [P] 编写 `backend/tests/unit/application/wechat/test_command_gateway.py`：授权放行/未授权 DENY、重复 msg_id 跳过、非文本消息忽略、DialogContext 装配四组用例
- [x] T004 [P] 编写 `backend/tests/unit/application/wechat/test_intent_router.py`：规则命中（含带参数 patterns）、LLM tool_call 解析、chat 兜底、LLM 超时降级回规则、全不中回 HELP 五组用例（FakeAIService 预设 tool_calls）
- [x] T005 [P] 编写 `backend/tests/unit/application/wechat/test_command_dispatcher.py`：快指令同步直达 completed、慢指令 ack+后台+终态推送时序、同类单飞 BUSY、执行异常推 FAIL、push_status 回写五组用例（FakeILinkClient 记录 send 序列）

### Implementation

- [x] T006 [P] 创建 `backend/app/domain/models/wechat_command.py`：`WeChatCommand` dataclass + `CommandStatus`/`PushStatus` 枚举 + 合法状态迁移表（对标 `t_sync_task` 风格，data-model.md §1）
- [x] T007 [P] 创建 alembic 迁移 `backend/app/infrastructure/db/migrations/versions/<rev>_add_wechat_command_table.py`：`t_wechat_command` 建表（down_revision=k5l6m7n8o9p0，DDL 按 data-model.md §1，唯一索引 uk_msg_id）
- [x] T008 创建 `backend/app/infrastructure/repositories/mysql_wechat_command_repo.py`：create（撞 uk_msg_id 抛重复信号）/ update_status（状态机守护）/ mark_pushed / fail_orphans / recent_for_user / find_running（使 T002 通过）
- [x] T009 [P] 创建 `backend/app/application/wechat/tools/base.py`：`WeChatTool` 抽象基类 + `ToolContext`/`ToolResult` + `ToolRegistry`（register 重名快速失败、match_pattern 规则匹配、export_llm_tools 导出 OpenAI tools schema 含 chat 兜底），契约严格按 contracts/tool-registry.md §1-§3
- [x] T010 创建 `backend/app/application/wechat/command_gateway.py`：鉴权（T001 白名单）→ 提取 `client_id`/文本（`item_list[0].text_item.text`，F1）→ insert 去重 → 装配 DialogContext（RedisCache，key/轮数/TTL 按 data-model.md §3）→ 调用 intent_router（使 T003 通过）
- [x] T011 创建 `backend/app/application/wechat/intent_router.py`：规则层（registry.match_pattern）→ `AIService.tool_call`（export_llm_tools + 会话历史注入，超时 `wechat_cmd_llm_timeout`）→ 降级链（LLM 异常回规则层 → 仍不中回 HELP 文案），返回 `{tool_name, params} | chat`（使 T004 通过；research D2）
- [x] T012 创建 `backend/app/application/wechat/command_dispatcher.py`：参数校验（schema + 股票池白名单，非法产 CLARIFY）→ 快/慢分流 → 慢指令单飞锁（`_get_lock(lock_key)` 同款）+ ack（`send_message`）+ `asyncio.create_task` 后台执行（防 GC 集合，对标 launch_batch_sync）→ 终态推送（`send_text_with_fallback`，research D6）+ push_status 回写；工具执行异常兜底记 failed 推 FAIL（使 T005 通过）
- [x] T013 修改 `backend/app/application/wechat/ilink_polling_service.py`：`_handle_message` 原 TODO 处挂接 `command_gateway.handle(msg)`（wechat_cmd_enabled 开关包裹；保留 token 刷新；占位 ACK 文案由指令链路的 HELP/回执取代，协议见 contracts/wechat-message-protocol.md §5）；扩展 `backend/tests/unit/application/wechat/test_ilink_polling.py` 验证挂接与开关关闭时行为不变
- [x] T014 修改 `backend/app/main.py` lifespan：启动时执行 `fail_orphans()` 孤儿清理（research D9）+ 日志"微信指令助手启用（授权 N 人）"；关闭时随 stop_polling 一并收尾

**Checkpoint**: 骨架单测全绿；发任意消息可收到 HELP 回复（无工具注册时）。用户故事可并行开工。

---

## Phase 3: User Story 1 - 微信发指令跑缠论 (Priority: P1) 🎯 MVP

**Goal**: 发"跑缠论"/"缠论 002940"→ 秒级 ACK → 后台补数+计算 → 终态推送信号摘要（含失败原因）

**Independent Test**: quickstart.md §4 步骤 2/4/6——真机发指令收 ACK→RESULT；执行中重发收 BUSY；终态后 `t_wechat_command` 状态与页面信号（`trigger_type='manual'`）一致

### Tests（先行）

- [x] T015 [P] 编写 `backend/tests/unit/application/wechat/test_wechat_tools.py` 缠论部分：RunChanlunTool 成功（Fake 仓库+Fake monitor 断言 scan 参数 `trigger_type="manual"` 与 codes）、单股失败不阻断（failed_items 进 FAIL 文案）、参数非法三路用例；摘要含「不构成投资建议」尾注断言

### Implementation

- [x] T016 [P] [US1] 创建 `backend/app/application/wechat/tools/chanlun_tools.py`：`RunChanlunTool`（slow, lock_key="chanlun", patterns 见 data-model.md §2）——执行体 = 逐股 `sync_stock_30m`（独立 session + Semaphore，照抄 chanlun_scheduler.scan_m30 内层）→ `ChanlunMonitorUseCase.scan("m30", user_id=发起人, trigger_type="manual", stock_codes=目标)`；progress 回调写 "n/m"；摘要模板（成功数/失败明细/出信号股票与类型/无信号明说 + 免责尾注，research D7/D11）
- [x] T016a [US1] `RunChanlunTool` 支持日线周期（research D7 预留的 P2 增强，2026-08-26）：pattern 合并支持 `缠论 日线 [代码]`；LLM 层 `period` enum 参数；daily 补数复用 `_pull_daily_quotes`（签名改为返回失败 code 列表，scheduler 调用点零破坏）；`scan(period, ...)` 参数化；非法周期回引导文案。**默认语义修正（同日二审）**：不带周期时 30m+日线双跑（用户主诉"怕漏"，默认只跑 30m 使日线漏算无手动兜底），逐周期独立补数/scan/摘要行、失败集合各轮独立。测试：`test_intent_router.py` 3 个 pattern 用例 + `test_wechat_tools.py` 周期用例（含双跑/单跑/失败隔离）
- [x] T017 [US1] 在 `backend/app/application/wechat/tools/__init__.py` 注册 `RunChanlunTool`，真机联调 quickstart §4 步骤 2/4/6 并把观察结果记入本任务描述（ACK 时延、执行时长、摘要样例）【代码+单测完成 2026-08-21；真机联调待部署后执行】

**Checkpoint**: US1 独立可用——微信可跑缠论并收到结果，MVP 价值达成

---

## Phase 4: User Story 2 - 执行进度与记录随时可查 (Priority: P1)

**Goal**: "缠论状态"/"执行记录"两条纯规则快指令，不依赖 LLM，随时可查进度与历史

**Independent Test**: quickstart §4 步骤 3/5；断开 LLM（超时=0.001s）后两指令仍 100% 可用（SC-005）

### Tests（先行）

- [x] T018 [P] 扩展 `backend/tests/unit/application/wechat/test_wechat_tools.py` 查询部分：ChanlunStatusTool（有 running 任务返回 PROGRESS 文案/无任务明说）、CmdHistoryTool（最近 N 条格式化含 status+push_status）两组用例（Fake repo 预置记录）

### Implementation

- [x] T019 [P] [US2] 创建 `backend/app/application/wechat/tools/chanlun_tools.py` 内 `ChanlunStatusTool`（fast, patterns=["^缠论状态$"]）：读 `find_running` + progress 渲染；无任务时返回最近一条缠论指令结果摘要
- [x] T020 [P] [US2] 创建 `backend/app/application/wechat/tools/system_tools.py`：`CmdHistoryTool`（fast, patterns=["^(执行记录|指令记录)$"]）——`recent_for_user(10)` 格式化为时间/原文/状态/推送状态四列表文
- [x] T021 [US2] 注册两工具（`tools/__init__.py`）+ 真机验证 quickstart §4 步骤 3/5 与 SC-005 降级场景【代码+单测完成 2026-08-21；真机验证待部署后执行】

**Checkpoint**: P1 双故事（US1+US2）闭环——可跑、可查、断 AI 可用

---

## Phase 5: User Story 3 - 自然语言与多轮对话 (Priority: P2)

**Goal**: 口语化表述 + 5 轮指代消解（"它"）；识别失败友好引导；LLM 不可用自动降级告知

**Independent Test**: quickstart §4 步骤 8；同一意图 5 种表述 ≥4 种正确执行（SC-004）

### Tests（先行）

- [ ] T022 [P] 扩展 `backend/tests/unit/application/wechat/test_intent_router.py`：会话历史注入断言（messages 含最近 5 轮）、"把它的缠论也跑了"指代消解（Fake AIService 断言上下文携带上轮 tool_call）、闲聊走 chat 兜底、降级文案含"仅支持精确指令"四组用例

### Implementation

- [ ] T023 [US3] 增强 `backend/app/application/wechat/intent_router.py`：路由成功/失败后回写 DialogContext（user text + tool_call）；LLM 请求注入会话历史做指代消解；降级与 chat 兜底文案按 contracts §2 HELP/CLARIFY 规范（使 T022 通过）
- [ ] T024 [US3] 真机验证：quickstart §4 步骤 8 + 自拟 5 种口语表述跑缠论，记录识别率（目标 ≥4/5）

**Checkpoint**: 体验从"命令行"升级为"对话助手"

---

## Phase 6: User Story 4 - 数据同步与行情查询指令 (Priority: P2)

**Goal**: "同步自选股 30 分钟数据"两段式同步；"自选股行情"/"002940 现在多少钱"秒回

**Independent Test**: quickstart 联调扩展——同步完成后页面端 K 线更新；行情回复 ≤30s（SC-002）

### Tests（先行）

- [ ] T025 [P] 扩展 `backend/tests/unit/application/wechat/test_wechat_tools.py`：SyncDataTool（复用断言+同步范围枚举校验）、SyncStatusTool、StockQuoteTool（行情格式化+代码校验）三组用例

### Implementation

- [ ] T026 [P] [US4] 创建 `backend/app/application/wechat/tools/sync_tools.py`：`SyncDataTool`（slow, lock_key="sync"，复用 `launch_batch_sync` 编排：日K 365 天 + 30m，progress 走 t_sync_task 联动）与 `SyncStatusTool`（fast，读最近同步任务）
- [ ] T027 [P] [US4] 创建 `backend/app/application/wechat/tools/market_tools.py`：`StockQuoteTool`（fast，复用行情批量查询 UseCase，输出 价格/涨跌幅 列表，≤3800 字符裁剪）
- [ ] T028 [US4] 注册 + 真机验证同步两段式与行情秒回

**Checkpoint**: 高频数据操作全部上微信

---

## Phase 7: User Story 5 - AI 分析指令（深度/轻度） (Priority: P3)

**Goal**: "深度分析 002940"/"简单看下 002940"→ 后台分析 → 要点式摘要 + 网页端指引

**Independent Test**: 真机发起深度分析，收到受理与结论摘要；网页端报告页可见完整报告

### Tests（先行）

- [ ] T029 [P] 扩展 `backend/tests/unit/application/wechat/test_wechat_tools.py`：DeepAnalysisTool/LightAnalysisTool（分析级别参数映射、摘要 ≤500 字断言、分析失败推 FAIL）用例

### Implementation

- [ ] T030 [P] [US5] 创建 `backend/app/application/wechat/tools/analysis_tools.py`：`DeepAnalysisTool` / `LightAnalysisTool`（slow, lock_key="analysis"，复用既有分析 UseCase 发起 + records 进度轮询至终态，摘要取报告结论要点裁剪 + "完整报告见网页端"指引）
- [ ] T031 [US5] 注册 + 真机验证深度/轻度两路（对照 spec US5 三场景）

**Checkpoint**: 三模块能力（缠论/数据/分析）全部可微信触达

---

## Phase 8: User Story 6 - 访问控制与写操作安全确认 (Priority: P3)

**Goal**: 写操作二次确认（复述→回复 y→执行）；确认超时/答非所问不执行

**Independent Test**: 未授权账号 DENY（quickstart §4 步骤 7）；写指令走确认流（spec US6 三场景）

### Tests（先行）

- [ ] T032 [P] 扩展 `backend/tests/unit/application/wechat/test_command_dispatcher.py`：risk=write 触发 CONFIRM_ASK、确认后执行回执 CONFIRM_DONE、答非所问/超时不执行三组用例；`test_command_gateway.py` 补未授权不产生任务断言

### Implementation

- [ ] T033 [US6] 增强 `backend/app/application/wechat/command_dispatcher.py` + `command_gateway.py`：`risk="write"` 工具挂二次确认——DialogContext 写 `pending_confirmation`（120s 超时，data-model.md §3），用户下一条消息优先匹配确认流（y/是→执行；其他→失效提示）（使 T032 通过）
- [ ] T034 [P] [US6] 创建 `backend/app/application/wechat/tools/watchlist_tools.py`：`RemoveFromWatchlistTool`（slow, write, 仅 LLM 可达 patterns=[]）作为首个写工具验证确认流；注册后真机走 spec US6 三场景

**Checkpoint**: 安全底线就位，后续写类指令有统一护栏

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T035 [P] 全量摘要模板审查：所有工具 ToolResult.summary 统一含「不构成投资建议」尾注与 ≤3800 字符裁剪（宪法 II / FR-014），在 `backend/tests/unit/application/wechat/test_wechat_tools.py` 加参数化断言
- [ ] T036 [P] 更新 `README.md` 用户使用说明：新增"微信指令助手"章节（指令表 + 示例 + 免责声明），与 contracts/wechat-message-protocol.md §1 保持同源
- [ ] T037 运行 quickstart.md 全量验证（§4 八步 + §5 SC 对照），把结果记录回 quickstart.md 末尾"验证记录"小节
- [ ] T038 全量回归：`pytest tests/unit/application/wechat/ tests/unit/infrastructure/test_wechat_command_repo.py -v` 全绿；跑既有 `tests/unit/application/test_ilink_polling.py` 确认无回归；对比预存失败基线（41 failed/363 passed，记忆既定——新增失败必须归零解释）
- [ ] T039 部署备忘：生产上线须 `upload.py` 后手动 `alembic upgrade head`（记忆：upload 不含迁移；stamp 注意多分支末端覆盖）

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1（Setup）**: 无依赖，立即开始
- **Phase 2（Foundational）**: 依赖 Phase 1；**阻塞 US1-US6 全部**
- **Phase 3-8（用户故事）**: 各依赖 Phase 2 完成；故事间相互独立，可并行或按优先级串行（US1/US2 → US3/US4 → US5/US6）
- **Phase 9（Polish）**: 依赖全部预期交付的故事完成

### User Story Dependencies

- **US1 (P1)**: 仅依赖 Foundational —— MVP 主件
- **US2 (P1)**: 仅依赖 Foundational（查询读 `t_wechat_command`，与 US1 无代码耦合）—— MVP 副件
- **US3 (P2)**: 依赖 Foundational（intent_router/dialog 增强；与 US1/US2 并行无冲突）
- **US4 (P2)**: 仅依赖 Foundational（新工具文件）
- **US5 (P3)**: 仅依赖 Foundational；真机验证建议在 US1 后（分析依赖已同步数据，非代码依赖）
- **US6 (P3)**: 仅依赖 Foundational（dispatcher/gateway 增强 + 新工具）

### Within Each User Story

- 测试任务先行（FAIL → 实现 → PASS）
- base.py 契约内：先工具实现后注册（注册即全链路生效）
- 真机联调是故事完成的必要条件（quickstart 对应步骤）

### Parallel Opportunities

- Phase 2：T002-T005 四个测试文件可并行；T006/T007/T009 可与测试并行（不同文件）
- Phase 3/4 可并行（T016 与 T019/T020 不同文件，注册行无冲突时合流）
- Phase 5/6 可并行；Phase 7/8 可并行
- Phase 9：T035/T036 可并行

---

## Parallel Example: Phase 2 Foundational

```bash
# 四个测试文件并行（互不依赖）：
Task T002: test_wechat_command_repo.py
Task T003: test_command_gateway.py
Task T004: test_intent_router.py
Task T005: test_command_dispatcher.py

# 与域模型/迁移/基类并行：
Task T006: wechat_command.py（domain model）
Task T007: alembic 迁移
Task T009: tools/base.py（注册表基类）
```

---

## Implementation Strategy

### MVP First（US1 + US2）

1. Phase 1 Setup → Phase 2 Foundational（链路骨架全绿）
2. Phase 3 US1（跑缠论）+ Phase 4 US2（查询保底）
3. **STOP and VALIDATE**: quickstart §4 步骤 1-7 全过 → 可部署真机试用（P1 闭环即治"缠论没跑"痛点）

### Incremental Delivery

1. MVP（US1+US2）→ 部署验证
2. +US3 自然语言 / +US4 数据同步（P2，体验与覆盖面）
3. +US5 AI 分析 / +US6 写操作确认（P3，完整愿景）
4. 每个故事独立可测可回滚；新工具即插即用不动框架（FR-020/021 验收口径）

---

## Notes

- 测试失败基线：仓库存在 41 failed/363 passed 预存基线（mock 漂移），本特性测试须独立全绿，勿与旧失败纠缠（T038）
- alembic：迁移基于 head k5l6m7n8o9p0；生产 stamp 多分支教训见记忆[alembic-db-version-drift]
- 真机联调依赖 iLink bot_token 有效（-14 需人工更换，程序不自愈）
- [P] 标记 = 不同文件且无未完成依赖；同文件任务禁止并行
