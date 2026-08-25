# Contract: 工具注册接口（对内扩展契约）

**Phase 1 输出** · 2026-08-21 · 新增一条微信指令的唯一入口契约（spec FR-020/021）。**新增工具不得改动 gateway / router / dispatcher 任何一行**，只允许新增文件 + 在 `tools/__init__.py` 注册一行。

## 1. WeChatTool 声明契约

```python
class WeChatTool(ABC):
    name: str          # ^[a-z_]+$，全局唯一，即 LLM function name
    domain: str        # strategy | market | sync | analysis | system
    description: str   # 给 LLM 的中文能力描述，须含 1-2 个触发示例
    parameters: dict   # JSON Schema 风格：{"codes": {"type": "array", ...}, ...}
    kind: str          # "fast"（同步秒回）| "slow"（后台任务 + 两段式应答）
    lock_key: str | None   # 同类互斥锁类别；None = 允许并行
    risk: str          # "read_only" | "write"（write 自动挂二次确认，P3 生效）
    patterns: list[str]    # 精确匹配正则（规则层入口）；空列表 = 仅 LLM 可达
```

约束：
- `description` + `parameters` 会被 `registry.export_llm_tools()` 原样导出为 OpenAI tools schema——**它们就是 LLM 眼中的说明书**，质量直接决定识别率
- `patterns` 只允许无歧义语法（带参数的简单形态，如 `^缠论 (\d{6})$`）；复杂语义一律交给 LLM 层
- 禁止 `risk="write"` 且 `patterns` 非空的组合（写操作必须走 LLM 显式意图 + 二次确认，不进规则快路径）

## 2. 执行契约

```python
async def execute(self, ctx: ToolContext) -> ToolResult: ...
```

### ToolContext（dispatcher 注入）

| 字段 | 类型 | 保证 |
|---|---|---|
| `user_id` | str | 已通过授权校验的发送者 |
| `params` | dict | **已通过参数校验**（dispatcher 按 `parameters` schema + 股票池白名单校验后才调用） |
| `session_factory` | async_sessionmaker | 每次使用自建独立 session（对标 launch_batch_sync） |
| `report_progress` | async (str) -> None | 更新 `t_wechat_command.progress`（如 "3/10"）；快指令为 no-op |

### ToolResult

| 字段 | 类型 | 语义 |
|---|---|---|
| `summary` | str | 推送给用户的终态摘要（≤3800 字符；信号类含「不构成投资建议」） |
| `succeeded` / `failed_items` | int / list | 成功数 / 失败明细（`[{code, reason}]`），驱动 `BUSY`/`FAIL` 文案 |
| `meta` | dict | 附加数据（如 task_id），落 `result_summary` 之外的可查询字段 |

规则：
- `execute` 内部任何异常：dispatcher 兜底捕获 → 记 `failed` → 推 `FAIL`。工具自身**不允许静默吞异常后返回成功**
- `execute` 内不得直接调 `send_message`（回复通道由 dispatcher 独占，保证两段式时序与 push_status 一致）
- 慢工具执行体不得 `await` 无超时的外部 IO（数据拉取须走既有带 Semaphore/超时的封装）

## 3. 注册契约

```python
# tools/__init__.py
registry.register(ChanlunRunTool())     # 启动时 import 即注册；重名将抛异常快速失败
```

注册后自动获得：LLM 路由可见、规则层匹配、两段式应答、进度落库、执行记录可查、单飞互斥。**不注册 = 不存在**，无配置文件、无数据库声明。

## 4. 新增一个工具的步骤（验收口径）

1. 新建 `tools/<domain>_tools.py`，声明 WeChatTool 子类 + `execute`
2. `tools/__init__.py` 加一行 `registry.register(...)`
3. 单测：`test_wechat_tools.py` 增加 Fake 依赖用例（识别/执行/失败三路）
4. 完成——不改 gateway/router/dispatcher（code review 检查项）

## 5. 非目标（防止接口腐化）

- 不支持工具间编排（一次指令=一个工具；组合诉求由 LLM 层拆多次指令或 P4 再议）
- 不支持工具内多轮反问（`CLARIFY` 由 dispatcher 的参数校验统一产生）
- 不向前端暴露 HTTP（本期无页面改动；未来页面接入另立契约）
