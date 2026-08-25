# Data Model: 微信指令助手

**Phase 1 输出** · 2026-08-21 · 持久化风格对标 `t_sync_task`（字符串状态、`create_time` 命名、alembic 迁移）

## 1. 持久化实体：WeChatCommand（表 `t_wechat_command`）

一条微信指令的完整生命周期记录（spec Key Entity「指令记录」）。域模型为 `@dataclass`（`app/domain/models/wechat_command.py`），经 `MySQLWechatCommandRepository` 读写。

### 字段

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGINT | PK, AUTO_INCREMENT | |
| `msg_id` | VARCHAR(128) | **UNIQUE**, NOT NULL | iLink 入站消息 `client_id`（真机实测 92 字符长格式，128 留余量）；幂等去重的硬约束（research D3） |
| `user_id` | VARCHAR(64) | NOT NULL | 发送者 `from_user_id`（`xxx@im.wechat`） |
| `raw_text` | VARCHAR(512) | NOT NULL | 用户原文 |
| `tool_name` | VARCHAR(64) | NULL | 解析出的工具名；NULL = 未识别（闲聊/帮助类，不执行） |
| `params_json` | JSON | NULL | 解析出的参数（如 `{"codes":["002940"],"period":"m30"}`） |
| `status` | VARCHAR(16) | NOT NULL, DEFAULT 'pending' | 见状态机 |
| `progress` | VARCHAR(64) | NULL | 人类可读进度（"3/10"） |
| `result_summary` | TEXT | NULL | 结果摘要（推送原文，≤3800 字符，research D11） |
| `push_status` | VARCHAR(16) | NULL | `pending` / `pushed` / `degraded`（tokenless 降级）/ `failed` |
| `error_message` | VARCHAR(1024) | NULL | 失败原因（终态必填，spec FR-013） |
| `create_time` | DATETIME | NOT NULL | 受理时间 |
| `update_time` | DATETIME | NOT NULL | 最后状态变更时间 |

### 状态机

```
pending ──dispatch──→ running ──┬──→ completed ──push──→ (push_status 置位)
   │                             └──→ failed ────push──→ (push_status 置位)
   └──(未识别/未授权)──→ closed   [tool_name=NULL，仅留痕]
```

- 合法迁移：`pending→running→completed|failed`；`pending→closed`；非法迁移由 Repository 拒绝（防竞态双写）
- 孤儿清理：服务启动时 `running|pending` → `failed`（error_message="服务重启中断"，research D9）
- 快指令可由 dispatcher 一步直达 `completed`（执行+落库原子完成）

### 验证规则（源自 spec）

- `msg_id` 唯一索引：重复消息插入失败 → 静默跳过（FR-004）
- `params` 执行前校验：股票代码须匹配 `^\d{6}$` 且 ∈ 自选池或明确指定（FR-009）
- 终态记录 `error_message` 与 `result_summary` 二选一必填（FR-013/015）

### DDL 草案（alembic 迁移 `<rev>_add_wechat_command_table.py`，基于 head `k5l6m7n8o9p0`）

```sql
CREATE TABLE t_wechat_command (
    id             BIGINT AUTO_INCREMENT PRIMARY KEY,
    msg_id         VARCHAR(128) NOT NULL,
    user_id        VARCHAR(64)  NOT NULL,
    raw_text       VARCHAR(512) NOT NULL,
    tool_name      VARCHAR(64)  NULL,
    params_json    JSON         NULL,
    status         VARCHAR(16)  NOT NULL DEFAULT 'pending',
    progress       VARCHAR(64)  NULL,
    result_summary TEXT         NULL,
    push_status    VARCHAR(16)  NULL,
    error_message  VARCHAR(1024) NULL,
    create_time    DATETIME     NOT NULL,
    update_time    DATETIME     NOT NULL,
    UNIQUE KEY uk_msg_id (msg_id),
    KEY idx_user_time (user_id, create_time),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

> 索引 `idx_status` 服务"执行记录/缠论状态"查询；`idx_user_time` 服务按人倒序翻页。

## 2. 运行时实体：CommandTool（注册表，非持久化）

spec Key Entity「指令能力目录」。定义于 `application/wechat/tools/base.py`：

| 属性 | 类型 | 说明 |
|---|---|---|
| `name` | str | 唯一标识（LLM function name，`^[a-z_]+$`） |
| `domain` | str | 领域分组（strategy/market/sync/analysis/system），两级路由预留（D2） |
| `description` | str | 给 LLM 的能力描述（中文，含触发示例） |
| `parameters` | dict | JSON Schema 风格参数声明 |
| `kind` | `fast` / `slow` | fast=同步秒回；slow=后台任务+两段式应答 |
| `lock_key` | str \| None | 同类互斥锁类别；None=允许并行 |
| `risk` | `read_only` / `write` | write 强制二次确认（spec FR-018，P3 生效） |
| `patterns` | list[str] | 精确匹配正则白名单（规则层入口；空=仅 LLM 可达） |
| `handler` | async callable | `async def execute(ctx: ToolContext) -> ToolResult` |

**P1 注册清单**：

| name | kind | lock_key | patterns（示意） | 对应 spec |
|---|---|---|---|---|
| `run_chanlun` | slow | `chanlun` | `^(跑|执行|算)?缠论(\s+(全部|自选|[0-9]{6}))?$` | US1 |
| `chanlun_status` | fast | — | `^缠论状态$` | US2 |
| `cmd_history` | fast | — | `^(执行记录|指令记录)$` | US2 |
| `chat` | fast | — | （兜底意图，非注册工具，路由器内置） | US3 场景3 |

## 3. 会话上下文：DialogContext（Redis，非持久化实体）

- key：`wechat:cmd:dialog:{user_id}`；value：JSON list，最近 5 轮 `{"role": "user"|"assistant", "text": str, "tool_call": {name, params} | null}`
- TTL 30 分钟（滑动：每轮读写后重置）
- 降级：RedisCache 不可用 → 上下文为空，指代消解退化为单轮（research D4）
- 写操作确认态（P3）：同 key 下 `pending_confirmation` 字段，超时 120 秒自动失效

## 4. 配置实体（`core/config.py` 新增组）

| 配置 | 默认 | 说明 |
|---|---|---|
| `wechat_cmd_enabled` | `False` | 指令功能总开关（与 `wechat_push_enabled` 独立） |
| `wechat_cmd_authorized_users` | `""` | 逗号分隔白名单；空则回落 `wechat_ilink_user_id`（research D10） |
| `wechat_cmd_llm_timeout` | `10` | 意图解析 LLM 超时秒数（超时走降级链） |

## 5. 实体关系

- `WeChatCommand` ← msg_id ─ iLink 入站消息（外部系统，不落库原文 JSON，仅 `raw_text`）
- `CommandTool`（运行时） ─执行→ 各模块既有 UseCase（缠论 `ChanlunMonitorUseCase`、同步 `sync_stock_30m` 等）→ 各模块既有表（`t_strategy_signal`、`t_stock_kline_30m`…，**本特性不改既有表**）
- `DialogContext`（Redis）─ 附带 → 意图路由请求（LLM messages 上下文）
