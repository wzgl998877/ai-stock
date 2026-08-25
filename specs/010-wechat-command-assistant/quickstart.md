# Quickstart: 微信指令助手（P1）

**Phase 1 输出** · 2026-08-21 · 本地验证 → 真机联调 → 验收对照

## 0. 前置

- 后端依赖已安装（`pip install -r backend/requirements.txt`）
- `.env` 已含既有 `WECHAT_ILINK_BOT_TOKEN` / `WECHAT_ILINK_USER_ID`（推送配置沿用）
- DB 已执行迁移：`alembic upgrade head`（新增 `t_wechat_command`；**生产部署后须手动跑，upload.py 不含迁移**——运维记忆既定流程）

## 1. 开启功能

`backend/.env` 追加：

```ini
WECHAT_CMD_ENABLED=true
# 授权白名单，留空则默认 = WECHAT_ILINK_USER_ID（本人）
WECHAT_CMD_AUTHORIZED_USERS=
WECHAT_CMD_LLM_TIMEOUT=10
```

## 2. 单元测试（无外部依赖，Fake 全覆盖）

```bash
cd backend
pytest tests/unit/application/wechat/ -v
pytest tests/unit/infrastructure/test_wechat_command_repo.py -v   # Repository 用 SQLite 内存库
```

覆盖面对照（research D12）：网关鉴权/去重、路由规则命中/LLM 解析/降级链、调度快慢分流/单飞/ack 时序/终态推送、工具三路（成功/失败/参数非法）。

## 3. 本地起服务（指令入口随 lifespan 启动）

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 18000
```

启动日志确认三行：`iLink 长轮询任务启动`、`微信指令助手启用（授权 N 人）`、`孤儿指令清理: X 条`。

## 4. 真机联调（唯一可信验收方式）

用自己的微信向 bot 发消息，按下表逐条验证：

| # | 发送 | 预期（对照 contracts/wechat-message-protocol.md） |
|---|---|---|
| 1 | `帮助` | HELP：指令列表 |
| 2 | `跑缠论` | ACK ≤60s → 数分钟内 RESULT（成功 N/失败 M + 信号清单；无信号明说） |
| 3 | ACK 后立刻 `缠论状态` | PROGRESS（进度 n/m） |
| 4 | 任务执行中再发 `跑缠论` | BUSY（不重复启动） |
| 5 | 任务完成后 `执行记录` | 最近 10 条，含本次 status=completed、push_status |
| 6 | `缠论 002940`（在池）/ `缠论 999999`（不在池） | 前者正常执行；后者 CLARIFY 引导 |
| 7 | 换一个未授权微信号发 `跑缠论` | DENY，且 `执行记录` 中该消息仅留痕无任务 |
| 8 | 任意闲聊"今天天气如何" | HELP 引导（不误触发） |

## 5. 验收对照（spec Success Criteria）

- SC-001/002/003：步骤 2/4/5 时序达标
- SC-005：把 `WECHAT_CMD_LLM_TIMEOUT` 调成 0.001 或断开 LLM 网络重跑步骤 2（精确指令）与 5（查询）——仍 100% 成功
- SC-006：iLink 异常重放同 `client_id`（观察日志 `重复消息跳过`）无二次执行
- SC-007：步骤 7
- 数据核对：`SELECT status, COUNT(*) FROM t_wechat_command GROUP BY status` 与实际行为一致；缠论结果与页面信号页一致（`trigger_type='manual'` 溯源）

## 6. 常见排查

- 指令完全无响应：查 `systemctl status ai-stock` / 本地控制台 `iLink 长轮询协议错误(code=-14)`（bot_token 失效需人工更换，程序不自愈）
- LLM 识别差：查日志 `AI tool_call` 与 DSML 解析记录；调优工具 `description`（契约：描述即说明书）
- 疑似卡死：`SELECT * FROM t_wechat_command WHERE status IN ('pending','running') ORDER BY id DESC LIMIT 5`——孤儿会在重启后自动标 failed（D9）
