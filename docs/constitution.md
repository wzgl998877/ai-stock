# merch_settle 项目宪章 (Constitution)

本宪章定义了项目的核心原则、技术约束和治理规则，回答"**能不能做**"的问题。

---

## 核心原则

### I. 清算流水线优先 (Pipeline-First)

所有业务变更必须理解并遵循三步清算流水线：**生成清算记录 → 审核/审批 → 生成清算文件**。

- 新增清算相关功能必须明确归属于流水线的哪个阶段
- 清算记录的核心主键为 `settleDate + batchNo + busiType`，所有操作围绕此主键展开
- 清算文件生成后，必须通过 `UpdateStatusRepository.updateStatusTransactional()` 在同一事务中完成所有状态更新

### II. 双访问模式一致性 (Dual-Access Consistency)

每个业务操作必须同时实现 HTTP REST 和 Thrift RPC，且逻辑一致。

- `controller/` 和 `rpc/` 必须调用同一个 Service，禁止各自实现不同逻辑
- 新增接口时，必须同时实现 Controller 和 RPC Handler
- Request DTO 必须定义 `SERVER_BEAN_NAME` 常量用于 RPC 注册

### III. 简洁实用 (KISS & YAGNI)

- 代码修改遵循最小变更原则，不引入不必要的重构
- 不为假设的未来需求提前设计，按当前业务需求实现
- 三行相似代码优于一个过早的抽象
- 复用现有常量和工具类，避免重复造轮子

---

## 技术约束

### 技术栈

- **Java 8** + **Spring Boot 2.0.4**：禁止升级版本
- **Oracle 数据库**：必须使用 Oracle 方言（`SYSDATE`、`NVL`、`TO_DATE`）
- **Spring Data JPA**：Repository 继承 `JpaRepository`，复杂查询使用 `@Query(nativeQuery=true)`

### 架构红线

- **禁止跨层调用**：Controller 禁止直接调用 Repository，Service 禁止调用 RPC
- **禁止循环依赖**：各层之间单向依赖，禁止互相依赖
- **禁止在事务内调用 RPC**：`@Transactional` 方法内部严禁发起远程调用
- **禁止循环内查询**：禁止在循环中执行数据库查询，必须批量操作

### 数据约束

- 清算金额必须使用 `BigDecimal`/`BigInteger`，禁止 `float`/`double`
- SQL 涉及借贷记时，`debit_credit_flag = 'D'` 的金额必须取反，禁止遗漏
- 所有表必须包含 `create_time` 和 `update_time` 字段
- 配置项通过 `application-{profile}.properties` 管理，不同环境独立配置

---

## 治理

### 变更流程

1. **理解上下文**：修改前必须阅读相关 Service、Repository 和 Entity
2. **保持一致**：Controller 和 RPC 必须同步修改
3. **本地验证**：使用 `mvn clean package` 确保编译通过

### Code Review 清单

- [ ] Controller 和 RPC 的逻辑是否一致？
- [ ] 是否违反架构红线（跨层调用、事务内RPC）？
- [ ] SQL 是否处理借贷记取反？
- [ ] 异常是否正确处理，有无空 catch？
- [ ] 新增配置项是否在各环境 properties 中同步？

### 优先级

- 本宪章优先级高于个人编码习惯，所有代码变更必须符合宪章规定
- 宪章修改需团队评审通过，记录修改原因和影响范围
- **详细执行规则见**：[rules/](./rules/) 目录

---

**版本**: 1.0.0 | **批准日期**: 2026-04-03 | **最后修订**: 2026-04-10
