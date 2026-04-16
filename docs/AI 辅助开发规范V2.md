## 一、这份规范到底在解决什么问题
这份规范面向“存量 Java 项目 + 多人协作”场景，核心目标不是“让 AI 写更多代码”，而是“让团队稳定交付”。

主要解决 4 个痛点：

1. 需求边界不清，开发做到一半频繁返工。  
2. 技术方案不统一，同类问题每个人写法都不同。  
3. 质量门禁不稳定，测试和审查容易流于形式。  
4. 文档沉淀不足，后续接手和复盘成本高。

<font style="color:rgb(15, 17, 21);">可参考</font>[ai-coding](https://xgdmo-ap-southeast-1.devops.alibabacloudcs.com/codeup/xgdmo/taifungbank/ai-coding)<font style="color:rgb(15, 17, 21);">快速开始体验完整流程。</font>

---

## 二、Claude Code 简介与安装（简版）
### 1）Claude Code 是什么
`Claude Code` 是运行在命令行里的 AI 编程助手。  
你给它目标，它会结合当前仓库代码和规范，协助完成分析、改动、测试与文档更新。

在本规范中的分工：

+ `Claude Code`：执行引擎
+ `Spec Kit`：开发主流程（`specify -> plan -> tasks -> implement`）
+ `constitution.md + rules/*`：红线与细则约束

### 2）安装方式（Windows/Mac/Linux 通用）
前置环境：

+ Node.js 18+
+ Windows 建议安装 Git for Windows

安装与校验：

```bash
npm install -g @anthropic-ai/claude-code
claude --version
```

配置（以智谱适配为例）：

+ Windows：`%USERPROFILE%/.claude/settings.json`
+ Mac/Linux：`~/.claude/settings.json`

```json
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "your_zhipu_api_key",
    "ANTHROPIC_BASE_URL": "https://open.bigmodel.cn/api/anthropic",
    "API_TIMEOUT_MS": "3000000",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": 1
  }
}
```

并创建：

+ Windows：`%USERPROFILE%/.claude.json`
+ Mac/Linux：`~/.claude.json`

```json
{
  "hasCompletedOnboarding": true
}
```

启动：

```bash
claude
```

---

## 三、两个关键文档：`CLAUDE.md` 与 `constitution.md`
### 1）为什么最关键
+ `CLAUDE.md`：告诉 AI “怎么做”（流程、上下文、命令、入口）
+ `constitution.md`：告诉 AI “不能做什么”（不可突破的红线）

可以理解为：

+ `CLAUDE.md` 是流程导航
+ `constitution.md` 是安全护栏

### 2）怎么写（最小可用清单）
以下直接以当前仓库的 `CLAUDE.md` 和 `constitution.md` 为模板，团队只需要替换“项目变量”。

#### A. `CLAUDE.md`（按当前文件结构改）
保留不动的部分：

+ 语言要求（始终中文）
+ 编码前必读顺序（`constitution.md -> rules/*`）
+ 规则冲突优先级

需要替换的部分（必须改成你自己项目的真实值）：

1. **技术栈**：JDK/Spring Boot/数据库/RPC 中间件版本  
2. **基础包路径**：如 `com.jlpay.taifung.merch_settle`  
3. **架构要点**：双访问模式、核心主键、关键业务流水线  
4. **构建与运行命令**：`mvn` 或 `gradle` 的实际命令  
5. **文档索引链接**：`Code_Analysis_Report.md` 的实际日期路径

#### B. `constitution.md`（按当前文件结构改）
保留不动的部分：

+ “核心原则 / 技术约束 / 治理 / 优先级”这四段结构
+ “宪章高于个人习惯”的治理原则

需要替换的部分（必须改成你自己项目的真实值）：

1. **核心业务原则**：例如“清算流水线优先”是否改为你项目主流程  
2. **接口模式规则**：是否同时支持 HTTP + RPC，还是单入口  
3. **架构红线**：跨层调用限制、事务边界、循环查库等  
4. **数据约束**：金额类型、数据库方言、借贷记规则  
5. **Review 清单**：改成你们团队实际检查项

#### C. 最终只改哪里（给团队的执行口径）
只改：

+ `CLAUDE.md` 的技术栈、包路径、命令、架构要点
+ `constitution.md` 的业务原则、红线、数据约束、Review 清单
+ `rules/*` 的命名、数据库、异常日志细则

不改：

+ 主流程顺序（`specify -> plan -> tasks -> implement -> review -> docs`）
+ 规则优先级（`constitution.md > rules/* > CLAUDE.md`）

---

## 四、设计原则
**Spec Kit 是唯一开发主线，ai-first 只提供规范库和项目分析能力。**

****

| 工具 | 职责 | 是否参与编码 |
| --- | --- | --- |
| Claude Code | AI 执行引擎 | 是 |
| Spec Kit | 需求全流程开发 | 是（主线） |
| ai-first `/analyze` | 项目初始化分析 | 仅启动时一次 |
| ai-first `jl-skills/specs/` | Java 规范注入 | 规范文件，不执行命令 |
| ai-first `/review` | PR 前代码审查 | 可选 |
| ai-first `/docs` | 开发完成后文档沉淀 | 每次需求完成后 |


---

## 五、目录结构规范
```plain
project-root/
├── CLAUDE.md                        ← 操作手册（提交 Git）
├── CLAUDE.local.md                  ← 本机私有配置（加入 .gitignore）
├── constitution.md                  ← 项目宪法（提交 Git）
│
├── specs/                           ← Spec Kit 需求规范（提交 Git）
│   └── {序号}-{需求简名}/
│       ├── spec.md                  ← 做什么
│       ├── plan.md                  ← 怎么做
│       └── tasks.md                 ← 原子任务清单
│
├── jl-skills/                       ← ai-first 规范库（提交 Git，按团队标准修改）
│   └── specs/
│       ├── （已迁移至 rules/*）       ← 编码规范已迁移，不再维护单文件
│       ├── COMMON_CONVENTIONS.md
│       └── DDD与可视化规范.md
│
├── rules/                           ← 项目执行规则（提交 Git，当前主规范来源）
│   ├── layer-conventions.md
│   ├── database-rules.md
│   ├── naming-and-comments.md
│   └── exception-logging.md
│
├── .claude/
│   └── skills/                      ← ai-first 技能（提交 Git）
│       ├── analyze/SKILL.md
│       ├── review/SKILL.md
│       └── docs/SKILL.md
│
├── docs/                            ← 项目知识库（提交 Git，长期维护）
│   ├── ARCHITECTURE.md              ← 全局架构图（/analyze 生成后维护）
│   ├── INTEGRATION.md               ← 业务接入文档
│   ├── CHANGELOG/                   ← 版本变更日志目录
│   │   ├── v0.0.0-init.md
│   │   └── v1.0.0-*.md
│   └── FEATURES/                    ← 功能归档目录（/docs 主输出）
│       └── {功能模块名}/
│           ├── README.md            ← 功能索引
│           ├── SPEC.md              ← 需求文档
│           ├── DESIGN.md            ← 设计文档（如存在）
│           ├── QA.md                ← 测试用例（如存在）
│           ├── INTERFACE.md         ← 接口说明（如存在）
│           ├── DDL.sql              ← 数据脚本（如存在）
│           ├── ANALYZE.md           ← 架构分析文档（如存在）
│           └── CaseTest*.py         ← Python E2E 脚本（如存在）
│
└── .agent/
    └── temp/                        ← AI 临时工件（加入 .gitignore）
```

---

## 六、项目初始化流程（只做一次）
### Step 1：安装工具
```bash
# 安装 Spec Kit
specify init . --ai claude

# 部署 ai-first 技能（从 ai-first 仓库拷贝）
cp -r ai-first/00-JL-Skills/skills/analyze  .claude/skills/
cp -r ai-first/00-JL-Skills/skills/review   .claude/skills/
cp -r ai-first/00-JL-Skills/skills/docs     .claude/skills/
cp -r ai-first/00-JL-Skills/jl-skills       ./jl-skills
```

### Step 2：生成 CLAUDE.md 初稿
```plain
/init
```

### Step 3：深度分析项目架构
```plain
/analyze
```

走三步（选开发者模式）：

1. 静态结构分析 → 技术栈、模块结构图、ER 图
2. 动态流程分析 → 核心链路时序图、调用链
3. 影响面分析 → 变更波及范围、风险评估

完成后自动生成 `jl-skills/generated/analyze/{日期}/Code_Analysis_Report.md`

### Step 4：补全 CLAUDE.md
在初稿基础上补充以下内容（尖括号内替换为实际值）：

```markdown
## 技术栈
- 框架：Spring Boot <版本> / JDK <版本> / MySQL <版本>
- 构建：mvn clean install -DskipTests
- 测试：mvn test -pl <模块名>
- 架构：COLA 分层

## 模块结构
- adapter/        接收外部请求，禁止包含业务逻辑
- client/         对外接口定义（API + DTO）
- application/    服务编排，实现 client 接口
- domain/         核心业务，禁止依赖 infrastructure
- infrastructure/ 技术实现（DB/缓存/外部调用）
- common/         工具/枚举/常量，禁止依赖业务模块

## 关键入口
- 主类：<主类全路径>
- 路由前缀：<路由前缀>
- 全局异常处理：<GlobalExceptionHandler 路径>

## 构建与测试命令
- 全量构建：mvn clean install
- 单模块测试：mvn test -pl <模块名>

## 硬红线（禁止事项）
- 禁止 domain 层出现 @Table/@Mapper 等基础设施注解
- 禁止修改已对外发布接口的字段结构
- 禁止在事务方法内发起 HTTP/RPC 调用
- 禁止在循环中执行数据库查询
- 禁止未经审批引入新 Maven 依赖

## 参考规范
@constitution.md
@rules/layer-conventions.md
@rules/database-rules.md
@rules/naming-and-comments.md
@rules/exception-logging.md
@jl-skills/generated/analyze/<日期>/Code_Analysis_Report.md
```

### Step 5：写 constitution.md
```markdown
# 项目宪法

## 架构原则
- 分层依赖方向：adapter → application → domain，infrastructure → domain
- domain 层必须纯净，不依赖任何框架技术（无 Spring/MyBatis 注解）
- @Transactional 只允许标注在 application 层
- PO 对象严禁出现在 client 层返回值和 application 层入参

## 对象转换规则
- infrastructure → domain：PO 转 Entity（使用 MapStruct，禁止手写 setter 透传）
- application → infrastructure：Entity 转 PO
- DTO 禁止包含业务逻辑

## 测试原则
- 新增业务逻辑必须有对应单元测试
- 核心链路必须有集成测试覆盖
- 禁止删除或注释已有测试用例
- 单元测试禁止启动 Spring 容器（纯 JUnit 5 + Mockito）
- 测试命名：test_{方法名}_{条件}_{预期结果}

## 依赖原则
- 优先使用已有依赖解决问题
- 引入新依赖必须在 plan.md「依赖变更」章节说明理由，经人工审批
- 禁止引入与现有依赖功能重复的库

## 兼容原则
- 对外接口只允许新增字段，禁止修改/删除已有字段
- 数据库变更必须提供 rollback 脚本
- 存量数据变更必须说明迁移方案
```

### Step 6：校准 Rules 执行规则
打开 `rules/` 下规则文件，确保与团队标准一致：

+ `rules/layer-conventions.md`（分层依赖与架构边界）
+ `rules/database-rules.md`（SQL、事务、回滚）
+ `rules/naming-and-comments.md`（命名与注释）
+ `rules/exception-logging.md`（异常与日志）

### Step 7：初始化文档库
```plain
/docs
```

生成基础文档：`README.md`、`docs/ARCHITECTURE.md`、`docs/INTEGRATION.md`、`docs/CHANGELOG/v0.0.0-init.md`，并初始化 `docs/FEATURES/` 目录

---

## 七、需求开发流程（每次重复）
### Spec Kit 标准开发流程
**第一步：执行 **`/speckit.specify`**（自动创建需求目录与分支）**

**第二步：需求规范化**

```plain
/speckit.specify
```

人工审核 `spec.md` 后进入下一步，审核要点：

```plain
□ 做什么、不做什么边界清晰
□ 异常场景已覆盖（空值、越权、并发等）
□ 验收标准可量化、可验证
□ 明确影响到哪些已有功能
□ 与产品/业务方确认对齐
```

**第三步：技术方案**

```plain
/speckit.plan
```

人工审核 `plan.md` 后进入下一步，审核要点：

```plain
□ 方案贴合 COLA 分层，没有另起炉灶
□ 改的是已有模块，而不是新建一套
□ 新增/变更表结构合理，rollback 脚本已规划
□ 已有对外接口无字段删除/修改
□ 新依赖已在「依赖变更」章节说明理由
□ Constitution Check：逐条对照宪法，无违反
□ 影响面已评估，回归测试范围已确认
```

**第四步：任务分解**

```plain
/speckit.tasks
```

人工审核 `tasks.md` 后进入下一步，审核要点：

```plain
□ 每个任务独立可执行，可单独跑测试
□ 顺序合理（DB 迁移 → 领域层 → 应用层 → 接口层 → 测试）
□ 单个任务不超过半天工作量，否则继续拆
□ 测试任务与实现任务配对（先写测试，再写实现）
```

**第五步：逐任务实现**

```plain
/speckit.implement
```

执行规则：

+ 每完成一个任务，立即执行 `mvn test -pl {相关模块}`
+ 测试失败不允许继续下一个任务，必须先修复
+ `tasks.md` 中的任务逐条勾选，不允许跳过

**第六步：代码审查（PR 前必须）**

```plain
/review
```

审查维度：架构合规性、安全、代码质量、测试覆盖。

**第七步：文档沉淀（合并后执行）**

```plain
/docs
```

将 `plan.md` 中的有价值内容蒸馏进对应模块文档：

+ 更新版本日志 → `docs/CHANGELOG/{version}-{summary}.md`
+ 功能归档 → `docs/FEATURES/{模块名}/`（至少 `README.md` + `SPEC.md`，按实际补 `DESIGN.md`、`QA.md`、`INTERFACE.md`、`DDL.sql`、`ANALYZE.md`、`CaseTest*.py`）
+ 更新项目入口 → `README.md`（功能表与版本索引）

---

## 八、PR 提交门禁清单
每次 PR 提交前，必须确认以下所有项：

```plain
开发完整性
□ tasks.md 所有任务已勾选
□ spec.md 的验收标准逐条可验证

代码质量
□ /review 审查无高风险问题
□ mvn test 全量通过，无跳过的测试
□ 无 TODO 遗留（除非加了 issue 编号）

架构合规
□ domain 层无 @Table/@Mapper 等基础设施注解
□ 无 PO 对象穿透到 client 层
□ 对外接口无字段删除/修改（只允许新增）
□ 无事务方法内的 HTTP/RPC 调用
□ 无循环内数据库查询

变更安全
□ DB 变更：rollback 脚本已提交
□ 存量数据变更：迁移方案已说明
□ 新依赖：已在 plan.md 说明理由

文档同步
□ /docs 已更新对应模块文档
□ README 已同步功能与版本索引
□ 变更日志已落到 `docs/CHANGELOG/`
```

---

## 九、文档生命周期
| 文档 | 存放位置 | 生命周期 | 维护时机 |
| --- | --- | --- | --- |
| 架构全景 | `docs/ARCHITECTURE.md` | 长期 | 架构变更时更新 |
| 功能归档索引 | `docs/FEATURES/{模块}/README.md` | 长期，持续追加 | 每次功能归档后 |
| 功能需求 | `docs/FEATURES/{模块}/SPEC.md` | 长期，持续追加 | 每次需求完成后 |
| 功能设计 | `docs/FEATURES/{模块}/DESIGN.md` | 长期，按需更新 | 有设计输出时 |
| 测试用例 | `docs/FEATURES/{模块}/QA.md` | 长期，按需更新 | 有测试产出时 |
| 变更日志 | `docs/CHANGELOG/{version}-{summary}.md` | 永久，流水账 | 每次发布/集成时追加 |
| 需求规范 | `specs/{序号}-{名称}/` | 一次性 | 上线后归档，不再修改 |


---

## 十、规范注入机制
AI 每次会话加载规范的顺序（优先级从高到低）：

```plain
1. constitution.md         最高优先级，不可逾越的红线
        ↓
2. CLAUDE.md              操作手册，@引用以下文件
        ↓
3. rules/*                          项目执行规则（编码/分层/数据库/日志）
        ↓
4. Code_Analysis_Report.md           项目架构地图
```

**修改规范的入口：**

| 想改什么 | 改哪个文件 |
| --- | --- |
| 架构红线（分层/事务/兼容） | `constitution.md` |
| Java 编码风格（命名/日志/异常） | `rules/naming-and-comments.md` + `rules/exception-logging.md` |
| 分层与数据库规则 | `rules/layer-conventions.md` + `rules/database-rules.md` |
| 构建测试命令 | `CLAUDE.md` |
| 项目模块边界说明 | `CLAUDE.md` |


---

## 十一、流程总览
```plain
项目初始化（只做一次）
    /init → 补全 CLAUDE.md
    /analyze → 生成架构地图 → @引用进 CLAUDE.md
    写 constitution.md
    校准 rules/*（填入团队标准）
    /docs → 初始化文档库
         │
         ▼
每个需求开发
    /speckit.specify（自动创建 specs/{序号}-{名称}/ 与分支）→ spec.md → 人审（边界/异常/验收）
         │
    /speckit.plan → plan.md → 人审（分层/兼容/依赖/宪法）
         │
    /speckit.tasks → tasks.md → 人审（粒度/顺序）
         │
    /speckit.implement → 逐任务 + mvn test（失败不继续）
         │
    /review → PR 前门禁
         │
    合并后 /docs → 归档到 docs/FEATURES/{模块}/ 并更新 docs/CHANGELOG/
```

---

## 十二、使用这套流程会带来什么好处
### 好处一：服务内会形成完整文档资产
执行 `/docs` 后，文档会持续沉淀到 `docs/CHANGELOG/` 和 `docs/FEATURES/{模块}/`，形成“可追溯的项目知识库”。

长期价值：

+ 新成员接手更快
+ 线上问题复盘有依据
+ 需求、方案、实现、测试和发布记录能串起来

### 好处二：代码规范统一，质量持续提升
通过 `constitution.md` + `rules/*` + `/review`，可以把“个人风格”收敛到“团队标准”。

直接效果：

+ 架构违规（如事务内远程调用、循环查库）会被提前拦截
+ 代码风格和异常日志写法趋于一致
+ PR 质量更稳定，线上风险下降

