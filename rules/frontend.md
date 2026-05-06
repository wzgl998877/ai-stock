## 一、总体架构（强制）

Page → Application → Domain → Service

---

## 二、目录结构（强制）

src/
 ├── pages/
 ├── components/
 ├── application/
 ├── domain/
 ├── services/
 ├── store/
 ├── hooks/
 ├── utils/

---

## 二.一、核心依赖（强制）

以下包必须在 `package.json` 中声明，禁止省略：

| 依赖 | 用途 |
|------|------|
| react | UI 框架 |
| react-router-dom | 路由 |
| antd | UI 组件库 |
| zustand | 状态管理 |
| echarts | 图表（K线、分时、技术指标） |
| echarts-for-react | ECharts React 封装（可选） |
| axios | HTTP 请求 |

---

## 三、分层职责（强制）

### 3.1 pages（页面层）

- 负责页面结构
- 调用 application
- 禁止业务逻辑
- 禁止直接请求 API

---

### 3.2 components（组件层）

- 纯 UI 展示
- 可复用
- 不包含业务逻辑

---

### 3.3 application（用例层）

- 编排前端业务逻辑
- 调用 services
- 处理数据转换

```js
export const runAnalysis = async (input) => {
  return await api.analyze(input)
}
```

------

### 3.4 domain（可选）

- 表达业务模型
- 简单逻辑处理

```js
class Analysis {
  constructor(data) {
    this.data = data
  }

  summary() {
    return this.data.content.slice(0, 100)
  }
}
```

------

### 3.5 services（数据访问层）

- 所有 API 请求必须在此层
- 统一封装

```js
export const analyze = (data) => {
  return request.post('/api/analysis', data)
}
```

------

## 四、状态管理

- 使用 Zustand
- 状态集中管理
- 避免组件内状态膨胀

------

## 五、AI交互规范（核心）

### 流式输出（必须）

```js
const es = new EventSource('/api/stream')
```

### UI必须支持

- 实时输出
- 自动滚动
- 停止生成
- loading状态

------

## 六、内容渲染

- 使用 Markdown 渲染
- 支持结构化展示

------

## 七、用户体验

必须实现：

- 草稿自动保存（localStorage）
- 错误提示
- 加载状态

------

## 八、搜索体验

- 输入防抖（debounce）
- 关键词高亮

------

## 九、组件规范

- 优先使用 Ant Design
- 禁止重复造组件

------

## 十、接口规范

- 所有 API 必须通过 services 调用
- 禁止在组件中直接使用 fetch

------

## 十一、扩展性

必须支持：

- 后端接口替换
- AI能力增强
- 页面扩展

------

## 十二、核心原则

UI负责展示
Application负责逻辑
Service负责数据