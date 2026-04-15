# 遗留系统迁移上下文报告 (Migration Context Report)

## 1. 系统元信息 (System Meta)
| 属性 | 旧系统 (Legacy) | 目标系统 (Target) |
| :--- | :--- | :--- |
| **JDK 版本** | (e.g. Java 8) | (e.g. Java 17) |
| **框架版本** | (e.g. Spring Boot 2.x) | (e.g. Spring Boot 3.x) |
| **架构模式** | (e.g. MVC 单体) | COLA 分层架构 |
| **数据库** | (e.g. MySQL 5.7) | (e.g. PostgreSQL 14) |
| **ORM 框架** | (e.g. MyBatis / Hibernate) | (e.g. MyBatis-Plus / JPA) |

## 2. 重构范围定义 (Scope Definition)

### 2.1 业务功能范围 (Business Scope)
*   **目标模块**: (e.g. 订单管理模块, 支付核心)
*   **包含的包/类**:
    *   `com.legacy.order.*`
    *   `...`
*   **排除的功能**: (本次不迁移的功能)

### 2.2 组件变更 (Component Changes)
*   [ ] 数据库变更: `Old DB` -> `New DB`
*   [ ] 缓存组件: `Old Cache` -> `New Cache`
*   [ ] 消息队列: `Old MQ` -> `New MQ`
*   [ ] 配置中心: `Old Config` -> `New Config`

### 2.3 架构重构策略 (Architecture Strategy)
*   **分层映射**:
    *   Legacy `Controller` -> Target `Adapter/Controller`
    *   Legacy `Service` -> Target `App/Service` & `Domain/Service`
    *   Legacy `DAO` -> Target `Infra/Repository`
*   **关键设计变更**: (e.g. 引入领域事件, 读写分离)

## 3. 依赖与调用链分析 (Dependencies & Call Graph)

### 3.1 外部依赖 (External Dependencies)
*   (列出所有外部 API 调用、中间件依赖)

### 3.2 关键调用链 (Critical Paths)
*   `入口 A` -> `Service B` -> `DAO C` ...

## 4. 技术债与风险 (Technical Debt & Risks)
| ID | 描述 | 风险等级 | 处理策略 (重构/保留/重写) |
| :--- | :--- | :--- | :--- |
| TD-01 | (e.g. SQL 中使用了 MySQL 特有函数) | High | 在 DB 迁移阶段修正 |
| TD-02 | (e.g. 某个类 3000 行，逻辑极度复杂) | Medium | 拆分为多个领域对象 |

## 5. 数据库 Schema 差异 (Schema Diff)
| 表名 | 旧字段类型 | 新字段类型 | 备注 |
| :--- | :--- | :--- | :--- |
| `t_order` | `is_deleted` (tinyint) | `is_deleted` (boolean) | 类型转换 |
| `...` | ... | ... | ... |
