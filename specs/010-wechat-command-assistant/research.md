# Research: 微信指令助手技术决策记录

**Phase 0 输出** · 2026-08-21 · 基于 `plan.md` Technical Context 与代码实地调研（非猜测，关键假设均已在代码中验证）

## 调研基础：已验证的代码事实

| # | 事实 | 位置 |
|---|---|---|
| F1 | iLink 长轮询已在生产运行，`_handle_message` 中留有明确 TODO 指令扩展点；入站消息为 dict：`message_type`(1=用户)、`from_user_id`、`context_token`、`client_id`(uuid)、`item_list[{type:1, text_item:{text}}]` | `app/application/wechat/ilink_polling_service.py:83-103`、`ilink_client.py:115-123`（出站构造可证入站同构） |
| F2 | `AIService.tool_call(messages, tools, tool_choice)` **已完整支持 function calling**，含 DeepSeek DSML 兜底解析 | `app/infrastructure/ai/ai_service.py:356-412` |
| F3 | 缠论计算签名原生支持手动触发：`ChanlunMonitorUseCase.scan(period, user_id, trigger_type, stock_codes)`；定时任务模式 = 先拉数（`sync_stock_30m` / `_pull_daily_quotes`）再 scan | `app/infrastructure/scheduler/chanlun_scheduler.py:159-197` |
| F4 | 后台任务范式现成：`launch_batch_sync`（`asyncio.create_task` + 防 GC 集合 + 独立 session + 状态回调）；单飞锁范式：`_get_lock(key)` 进程内 `asyncio.Lock` 字典 | `app/application/sync/watchlist_batch_sync.py`、`routers/watchlist.py:155-217` |
| F5 | 主动推送应使用 `send_text_with_fallback`（ret=-2 时降级 tokenless 重试）；「回复」场景 token 新鲜可直接 `send_message`。单条消息上限 ~4000 字符 | `app/infrastructure/wechat/ilink_client.py:131-147` |
| F6 | `RedisCache` 自动降级：连接失败后 get 恒返 None、set 恒为 no-op，不抛异常 | `app/infrastructure/cache/redis_cache.py:14-60` |
| F7 | alembic 迁移链当前 head 为 `k5l6m7n8o9p0`；曾有双分支 merge 教训（stamp 须覆盖所有分支末端） | `migrations/versions/`、记忆[alembic-db-version-drift] |
| F8 | 配置组 `wechat_ilink_*` 已存在（bot_token/user_id/开关等），服务由 `main.py` lifespan 按 `wechat_push_enabled` 装配启动 | `app/core/config.py:78-86`、`app/main.py:165-186` |

---

## D1 消息入口：扩展 ilink_polling_service，不建独立服务

- **Decision**: 在 `_handle_message` 的 TODO 处调用新增 `command_gateway.handle(msg)`；轮询循环、游标、退避、token 刷新逻辑一字不动。
- **Rationale**: 轮询服务已在生产验证（指数退避、游标防重放、CancelledError 语义）；指令处理异常需在网关内部消化，不得影响轮询存活（F1）。
- **Alternatives**: ① 独立常驻服务进程——重复实现轮询/退避/token 管理，违反 KISS，弃；② 定时批量拉取消息——延迟不可接受，弃。

## D2 意图路由：规则白名单 + 单级 LLM Function Calling + 降级链

- **Decision**: 三层顺序：`规则精确匹配`（"跑缠论"/"缠论状态"/"执行记录" + "缠论 <code>" 简单参数）→ 未命中走 `AIService.tool_call`（工具 schema 从注册表自动导出，`tool_choice="auto"`，另设 `chat` 兜底意图）→ LLM 异常/超时（上限 10s）降级回规则层，规则也不命中则回帮助文案。P1 工具 3~4 个，单级路由足够；注册表 schema 携带 `domain` 字段，工具 >12 个时再启用两级（先领域分类再选工具），届时只改路由器内部，工具零改动。
- **Rationale**: F2 证实 function calling 现成可用（含 DSML 兜底）；spec FR-005/008 要求查询与精确指令不依赖 LLM——规则层置前即天然满足。
- **Alternatives**: ① 纯 LLM 路由——违反 FR-008（LLM 挂时链路断），弃；② 上 LangGraph 编排——单次意图解析用不动状态机，违反 KISS，弃；③ 纯规则——无法满足 US3 自然语言诉求，弃。

## D3 去重幂等：DB 唯一索引为准，Redis 仅做快路径

- **Decision**: `t_wechat_command.msg_id` 建唯一索引（取 iLink `client_id`）；网关处理前先 insert，撞唯一索引即判定重复、静默跳过。Redis 只缓存近期已处理 msg_id 作快路径（可选优化）。
- **Rationale**: F6 证实 RedisCache 会静默降级——去重若只依赖 Redis，Redis 故障窗口内重放消息会被重复执行；DB 唯一索引是无条件兜底。游标（F1）已防大部分重放，双保险成本仅一列索引。
- **Alternatives**: ① 纯 Redis 去重——降级时失效，弃；② 纯 DB 查询判重——并发竞态下仍可能双插，唯一索引才是硬约束，查询仅作友好路径。

## D4 会话上下文：RedisCache + JSON list，TTL 30 分钟，降级容忍

- **Decision**: key `wechat:cmd:dialog:{user_id}`，存最近 5 轮 `{role, text, tool_call}`；随 LLM 路由请求送入做指代消解。Redis 不可用时上下文为空——仅退化为单轮对话，链路不死。
- **Rationale**: F6 降级语义与"指代消解失败只是体验降级"的容错要求吻合。
- **Alternatives**: DB 存会话——单人低频场景无查询需求，为存而存，弃。

## D5 慢指令执行：进程内 asyncio 后台任务 + 单飞锁，不引队列

- **Decision**: 对标 F4 双范式：`command_dispatcher` 用 `asyncio.create_task`（防 GC 集合）跑慢工具，按工具声明的 `lock_key` 取 `_get_lock` 同款进程内锁；同类在跑时直接回复当前进度（从 `t_wechat_command` 查 running 记录），不排队不重复启动。
- **Rationale**: 单 worker uvicorn（现网部署形态）+ 单人低频指令，进程内模型完全够；spec 假设已声明无需高并发设计。
- **Alternatives**: ① Celery/RQ——引入 broker 依赖与部署复杂度，YAGNI，弃；② APScheduler 一次性 job——语义绕远，弃。**预留**：dispatcher 对工具暴露统一 `execute(ctx)` 接口，未来换队列只动 dispatcher。

## D6 两段式应答的推送通道选择

- **Decision**: 受理 ack 用 `send_message`（用户消息刚到、context_token 必然新鲜，F1/F5）；任务完成/失败推送用 `send_text_with_fallback`（距用户消息可能超过 token 有效期，tokenless 降级保送达尝试）；推送结果（message_id 有无 + 是否降级）写回 `push_status`。
- **Rationale**: F5 明示两方法的适用场景；iLink ret=0 不保证送达（记忆[ilink-push-delivery-unreliable]），故 push_status 落库 + "执行记录"查询兜底。
- **Alternatives**: 全部走 fallback——ack 场景持有新鲜 token 却不用，白白放弃更可靠的路径，弃。

## D7 缠论触发：直接复用 ChanlunMonitorUseCase.scan + 现成拉数函数

- **Decision**: `run_chanlun` 工具执行体 = `sync_stock_30m`（30m 补数，每股独立 session + Semaphore 限并发，照抄 scan_m30 内层）→ `ChanlunMonitorUseCase.scan("m30", user_id=指令发起人, trigger_type="manual", stock_codes=目标)`。`period=daily` 同理复用 `_pull_daily_quotes` + `scan("daily")`。P1 仅做 30m（用户主诉场景），daily 列为 P2 增强。
- **Rationale**: F3 证实 scan 签名原生支持 `trigger_type` 与 `stock_codes` 白名单，零改动复用；`trigger_type="manual"` 让微信触发与定时扫描在信号数据上可区分溯源。
- **Alternatives**: ① 另起计算管线——重复实现，违宪 KISS，弃；② 只 scan 不补数——数据 stale 时信号无意义（历史教训见 chanlun_scheduler 注释），弃。

## D8 LLM 工具 schema：从注册表自动导出

- **Decision**: `WeChatTool` 基类声明 `name/domain/description/parameters/kind/lock_key/risk`；注册表提供 `export_llm_tools()` 把声明转成 OpenAI tools 格式（含一个 `chat` 兜底工具）。新增工具自动进入 LLM 可见集合，无需改路由器。
- **Rationale**: spec FR-020/021（注册式扩展、不改既有逻辑）的落地点；schema 单一事实源避免工具描述两处维护漂移。
- **Alternatives**: 手工维护一份 LLM tools 副本——双份漂移，违宪"Prompt 模板化管理"精神，弃。

## D9 僵尸任务清理：启动时扫尾

- **Decision**: `main.py` lifespan 启动轮询前执行一次 `wechat_command_repo.fail_orphans()`：把遗留 `running/pending` 状态记录批量标 `failed`（error_message="服务重启中断"）。
- **Rationale**: spec Edge Case 明确要求不留"永久执行中"；单 worker 下进程重启必然丢任务，启动扫尾是最简单可靠的补偿。
- **Alternatives**: 心跳超时判定——为单人低频场景引入定时巡检，过度设计，弃。

## D10 授权用户与配置

- **Decision**: `settings` 新增 `wechat_cmd_enabled: bool = False`、`wechat_cmd_authorized_users: str = ""`（逗号分隔；为空时默认取 `wechat_ilink_user_id`——即推送接收人本人）。网关校验 `from_user_id ∈ 白名单`，未授权只回礼貌拒绝且不产生记录以外的任何副作用。
- **Rationale**: F8 配置模式一致；默认值让"现有推送用户=指令用户"零配置可用，符合单人系统实际。
- **Alternatives**: DB 用户表——单用户场景过度设计，弃。

## D11 结果摘要与文案边界

- **Decision**: 摘要目标 ≤500 字（微信一屏可读），硬上限 3800 字符（F5 的 4000 上限留余量）；信号摘要模板固定含「不构成投资建议」尾注（宪法 II）；`run_chanlun` 摘要 = 成功/失败数 + 出信号股票与信号类型列表（无信号则明说"本期无新信号"）。
- **Rationale**: 宪章 Research-Only 条款 + spec FR-014。
- **Alternatives**: 全量信号清单直推——超长且不可读，弃。

## D12 测试策略：FakeClient/FakeRepo 范式

- **Decision**: 全部单测用可编程 Fake（对标 F1 目录下 `test_ilink_polling.py` 的 FakeClient/FakeStore）：FakeILinkClient 记录 send 调用序列、FakeCommandRepo 内存实现、FakeTool 注册表；不 mock 全局 asyncio；LLM 路由测试注入 FakeAIService 返回预设 tool_calls。真实验证走 quickstart.md 的真机流程。
- **Rationale**: 仓库既有测试范式一致；后端存在 41 failed/363 passed 的预存基线（记忆[backend-preexisting-test-failures]），新测试必须独立可跑，不与旧失败纠缠。
- **Alternatives**: 集成测试起真 Redis/MySQL——CI 环境不具备，单测层 Fake 已覆盖分支语义，弃。

---

## 结论

12 项决策全部落在「复用现有件 + 单 worker 进程内模型」框架内，无新框架、无新外部依赖、无前端改动； Constitutional gates 复检见 plan.md（Phase 1 后复检亦通过）。所有 spec FR/SC 均有对应决策支撑，无 NEEDS CLARIFICATION 残留。
