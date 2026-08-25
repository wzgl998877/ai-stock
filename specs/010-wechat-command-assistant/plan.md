# Implementation Plan: 微信指令助手（WeChat Command Assistant）

**Branch**: `010-wechat-command-assistant` | **Date**: 2026-08-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/010-wechat-command-assistant/spec.md`

## Summary

通过微信消息驱动系统既有功能（跑缠论、数据同步、AI 分析、行情查询），以「消息网关 → 意图路由（规则 + LLM Function Calling）→ 指令调度（快/慢分流 + 两段式应答）→ 工具注册表执行 → 结果回推」五层架构实现。全部复用现有基础设施：iLink 长轮询入口（代码已预留 TODO 扩展点）、`AIService.tool_call`（已支持 function calling + DSML 兼容）、`ChanlunMonitorUseCase.scan`（签名原生支持手动触发）、`launch_batch_sync` 后台任务范式、iLink 推送通道（含 tokenless 降级）。首期交付 P1：框架 + 缠论三件套（跑缠论 / 缠论状态 / 执行记录）。

## Technical Context

**Language/Version**: Python 3.12（后端，无前端改动）
**Primary Dependencies**: FastAPI、httpx、SQLAlchemy(asyncio) + aiomysql、redis.asyncio、APScheduler（均现有）
**Storage**: MySQL 新表 `t_wechat_command`（指令全生命周期）；Redis（会话上下文，复用 `RedisCache` 自动降级封装）
**Testing**: pytest + pytest-asyncio（对标 `tests/unit/application/test_ilink_polling.py` 的 FakeClient 可编程序列范式）
**Target Platform**: Linux 服务器（systemd 单 worker uvicorn，与现网部署一致）
**Project Type**: web-service 后端扩展（消息驱动的指令入口层）
**Performance Goals**: 受理确认 ≤60s（受长轮询周期约束）；快指令答复 ≤30s；单人低频指令（无需高并发设计）
**Constraints**: LLM 意图解析延迟数秒级（可接受）；iLink 单条消息 ~4000 字符上限（摘要须裁剪）；iLink 推送不保证送达（结果落库 + 查询指令兜底）
**Scale/Scope**: 授权用户 1 人（系统所有者）；P1 工具 3 个，注册表架构支撑后续扩至 20+

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 宪章条款 | 评估 | 结论 |
|---|---|---|
| I. 三模块协同 | 助手是跨模块统一消息入口：跑缠论→模块三、数据同步/行情→模块二、AI 分析→模块一；指令执行复用各模块既有 UseCase 与数据，与页面端天然联动（同一批落库数据） | ✅ 通过 |
| II. 个人投研工具边界 | 无交易类指令（spec FR-019 明确禁止）；信号摘要文案须保留"不构成投资建议"语义（实现时写入摘要模板） | ✅ 通过 |
| III. KISS & YAGNI | 零新框架（不引 Celery/消息队列）、零前端改动、路由层不上 LangGraph（单次 `tool_call` 即可）；全部复用既有抽象 | ✅ 通过 |
| 架构红线：跨层调用 | 消息网关/路由/调度均在 Application 层（`application/wechat/`）；LLM 仅经 `AIService` 统一抽象；DB 仅经 Repository；Domain 不新增依赖 | ✅ 通过 |
| 架构红线：密钥 | bot_token 等已走 `.env`（`wechat_ilink_*` 系列配置），新增配置同模式 | ✅ 通过 |
| 数据约束 | 新表无金额字段（股票代码为字符串，参数存 JSON 扩展字段，核心状态字段可查询可迁移）；alembic 迁移落表 | ✅ 通过 |
| 流式成对实现 | 本特性为消息驱动，无 SSE 场景，不适用 | ✅ N/A |

**门禁结论**：无违宪项，无需 Complexity Tracking。进入 Phase 0。

**Phase 1 设计后复检**（2026-08-21，research/data-model/contracts/quickstart 定稿后）：

- LLM 调用仅经 `AIService.tool_call`（research D2/D8），无散落 SDK 直连 ✅
- 持久化仅经新增 `MySQLWechatCommandRepository`，无越层 SQL；新表无金额字段，核心状态列可查询可迁移 ✅
- tools/ 全部位于 Application 层编排，执行体复用各模块既有 UseCase，Domain 零改动 ✅
- 摘要模板含「不构成投资建议」尾注（contracts/wechat-message-protocol.md §2，对应宪法 II）✅
- 复用优先：12 项决策零新框架、零新外部依赖、零前端改动（KISS/YAGNI）✅

**复检结论**：通过，可进入 `/speckit.tasks`。

## Project Structure

### Documentation (this feature)

```text
specs/010-wechat-command-assistant/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── wechat-message-protocol.md   # 微信消息协议（对外：用户可感知的指令集与回复）
│   └── tool-registry.md             # 工具注册接口（对内：新增指令的扩展契约）
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/app/
├── application/wechat/
│   ├── ilink_polling_service.py        # [改] _handle_message 挂接指令网关（原 TODO 扩展点）
│   ├── command_gateway.py              # [新] 消息网关：鉴权 → msg_id 去重 → 会话装配
│   ├── intent_router.py                # [新] 意图路由：规则白名单 → AIService.tool_call → 降级链
│   ├── command_dispatcher.py           # [新] 指令调度：快/慢分流、单飞锁、ack、两段式应答、结果回推
│   └── tools/                          # [新] 指令工具（注册表模式）
│       ├── __init__.py                 #    registry：注册/发现/导出 LLM tools schema
│       ├── base.py                     #    WeChatTool 基类 + ToolContext/ToolResult
│       ├── chanlun_tools.py            #    P1：run_chanlun（慢）、chanlun_status（快）
│       └── system_tools.py             #    P1：cmd_history（快，纯规则保底）
├── domain/models/wechat_command.py     # [新] WeChatCommand dataclass + 状态枚举
├── infrastructure/repositories/
│   └── mysql_wechat_command_repo.py    # [新] 指令记录 Repository（msg_id 唯一约束兜底去重）
├── infrastructure/db/migrations/versions/
│   └── <rev>_add_wechat_command_table.py  # [新] alembic 迁移（基于当前 head k5l6m7n8o9p0）
└── core/config.py                      # [改] 新增 wechat_cmd_* 配置组

backend/tests/unit/application/wechat/
├── test_ilink_polling.py               # [改] 扩展：指令消息进入网关的用例
├── test_command_gateway.py             # [新] 鉴权/去重/会话
├── test_intent_router.py               # [新] 规则命中/LLM 解析/降级链
├── test_command_dispatcher.py          # [新] 快慢分流/单飞/ack 时序/终态推送
└── test_wechat_tools.py                # [新] 缠论三件套（Fake 推送 + Fake 仓库）
```

**Structure Decision**: 完全遵循既有后端四层架构。指令编排属 Application 层流程（与 `ilink_polling_service` 同级同目录）；工具执行调各模块既有 UseCase，不下沉 Domain；持久化走新增 Repository + alembic。无前端改动，无新增顶层目录。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

无违宪项，不适用。
