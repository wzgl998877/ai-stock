# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 语言要求

**始终使用中文回答所有问题和进行所有交流。**

## 📖 编码前必读（重要！）

执行任何 Java 代码修改前，必须按顺序阅读以下文档：

1. **[Constitution（系统宪法）](./constitution.md)** — 理解"**能不能做**"
   （核心原则、技术约束、架构红线）

2. **[Rules（执行规则）](./rules/)** — 理解"**怎么做才对**"
   - [分层与架构](./rules/layer-conventions.md)
   - [数据库操作](./rules/database-rules.md)
   - [命名与注释](./rules/naming-and-comments.md)
   - [异常与日志](./rules/exception-logging.md)

## ⚖️ 规则冲突优先级

当规则冲突时，按以下顺序执行：

1. `constitution.md`
2. `rules/*`
3. `CLAUDE.md`

## 🛠 技术栈

- **Java 8** + **Spring Boot 2.0.4**
- **Spring Data JPA** + Hibernate（Oracle 数据库）
- **Thrift RPC** — 通过内部 `commons-rpc` 库（ZooKeeper 服务发现）
- **Apache POI**（Excel）、**JSch**（SFTP）、**Lombok**

## 🏗 架构要点

基础包路径：`com.jlpay.taifung.merch_settle`

- **双访问模式**：每个业务操作同时暴露 HTTP REST（`controller/`）和 Thrift RPC（`rpc/`）
- **三步清算流水线**：生成清算记录 → 审核/审批 → 生成清算文件并上传SFTP
- **核心主键**：`settleDate + batchNo + busiType`
- **原生 SQL 聚合**：Repository 大量使用 `@Query(nativeQuery=true)` 的 INSERT...SELECT 聚合查询
- **借贷记处理**：SQL 中对 `debit_credit_flag = 'D'` 的记录金额取反

## 📦 构建与运行

```bash
# 构建
mvn clean package

# 本地运行（dev环境，端口8000）
mvn spring-boot:run

# 指定环境运行
mvn spring-boot:run -Dspring-boot.run.profiles=dev
```

## 📚 详细文档索引

- **代码分析报告**：[Code_Analysis_Report.md](./jl-skills/generated/analyze/2026-04-03/Code_Analysis_Report.md)