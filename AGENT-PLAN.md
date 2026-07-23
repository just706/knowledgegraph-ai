# 混合架构设计：Router + Workflow 为主 + Agent 兜底

> 设计稿，纯方案（本文档不含代码）。已按此落地实现，代码位于：backend/app/router.py、backend/app/agent.py、backend/app/services/llm_client.py（tool_call_completion）、backend/app/api/chat.py（dispatch 接线）。
> 目标：在**不重造现有能力**的前提下，给系统加一层"智能调度"——明确意图走确定性的 Workflow（现有 services），只有开放/复合意图才进 ReAct Agent 兜底。
> 设计哲学（沿用工程原则）：**简单优先、最小依赖（仅 requests）、按 user_id 隔离、不编造、LLM 失败一律降级、工具调用带用户自有 Key 计费。**

---

## 0. 为什么是这版（改版说明）

上一版把所有请求都塞进 ReAct Agent（含"生成计划"这种确定性任务也走 Agent 循环），既慢、贵、又难控，且拆分了 tools/、memory/ 子目录并新增 user_memory 表与抽象基类——过度设计。

本版修正为**分层混合**（Anthropic 生产实践结论：确定性 Workflow 为主 + 局部 Agent 为辅）：

- 明确意图（计划 / 出题 / 构建图谱 / 统计）→ **Workflow**：直接调现有 services，一行不改，不进 Agent。
- 复合 / 开放意图（"我学得怎样并安排 + 出题"）→ **Agent**：ReAct 循环组合调用上面的 Workflow 入口。
- **Router** 做系统入口分流，用**规则**（关键词 / 意图模板），**不额外调一次 LLM**，零开销。

---

## 1. 整体架构

系统入口是一个规则路由层，按意图把请求分到两条路径：

- Workflow 路径（确定性）：计划、出题、图谱查询、统计概览，各自直接调用对应 service，不调用 LLM 做下一步决策。
- Agent 路径（开放兜底）：仅当规则无法匹配的复合 / 开放意图才进入，用 ReAct 循环组合调用 Workflow 入口工具，超步数或异常时降级普通 RAG。

两条路径共享同一个 services 底座：plan_service、quiz_generator、graph_builder、stats_service、rag。

核心要点：4 个确定性任务继续用现有 Workflow，一行不改，不进 Agent；Agent 的工具就是这 4 个 Workflow 的入口加上 search_knowledge（RAG）。Router 用规则，不引入 LLM 路由开销。

---

## 2. Router 设计（规则路由，不调 LLM）

Router 是纯函数层，按关键词匹配意图并返回路由结果，无任何网络 / LLM 调用。匹配按优先级从高到低。

预设的路由规则（顺序即优先级，先匹配先命中）：

- 计划类：命中"计划 / 安排 / 复习 / 规划"等关键词 → 走计划 Workflow。
- 出题类：命中"出题 / 练习 / 做题 / 测验 / 题目"等关键词 → 走出题 Workflow。
- 图谱类：命中"图谱 / 构建 / 生成图谱 / 知识网络"等关键词 → 走图谱查询 Workflow。
- 统计类：命中"统计 / 掌握度 / 薄弱 / 错题 / 进度 / 学得怎么样"等关键词 → 走统计 Workflow。
- 兜底：以上都不匹配 → 走 Agent。

可选增强（非必须）：
- 复合意图（同时含统计与计划）→ 显式归到 Agent，让 Agent 组合调用。
- 前端"智能体模式"开关，用 payload 的 mode 字段强制走 Agent。
- 未来如需更灵活，可平滑升级为 LLM Router（先让小模型做一次意图分类），但当前阶段不需要。

---

## 3. Workflow 层（确定性任务，复用现有 services，零改动）

每条路由直接调用已有的 service 函数，不进 Agent、不调 LLM 决策下一步。返回结构保持现有格式，仅追加 mode 标记便于前端区分。

对应关系（全部已存在，零改动）：

- 计划路由 → plan_service.generate_plan：基于用户数据生成学习计划，确定性生成。
- 出题路由 → quiz_generator.generate_quiz：可传 subject / count / sources / q_types，确定性生成。
- 图谱路由 → graph_builder.get_graph：只读查询用户图谱，确定性查询。
- 统计路由 → stats_service.get_overview：返回掌握度、薄弱点、错题分布、近 7 天趋势，确定性查询。

重要约束：图谱的抽取 / 构建写入操作（build_graph / extract_graph）是写入型，保持由现有上传流程触发，不接入 Router、不暴露给 Agent，避免越权改写。

---

## 4. Agent 兜底层（仅开放 / 复合意图）

轻量单文件实现，不拆子目录、无抽象基类。核心是一个 ReAct 循环，工具直接复用 Workflow 入口函数。

### 4.1 工具调用能力（阶段 0 新增）

在 llm_client 中新增统一的工具调用返回结构（文本 或 工具调用列表二选一）。三厂商适配策略：

- openai_compatible 系（DeepSeek / Qwen / GLM / Kimi / Ollama 等，占绝大多数）：完整多轮工具循环，原生支持。
- anthropic / gemini：因多轮 tool 回灌格式繁琐，先实现单轮（返回工具调用时执行一次并把结果转自然语言再请求一次），否则降级普通 RAG。避免在这里写两套完整适配拖慢进度。

### 4.2 工具集（复用 Workflow 入口）

Agent 暴露给 LLM 的工具全部是现有能力的薄封装：

- get_study_stats：获取当前用户学习概览，无需参数，内部调 stats_service.get_overview。
- generate_quiz：针对学科 / 薄弱点生成练习题，可传 subject / count / sources / q_types，内部调 quiz_generator.generate_quiz。
- search_knowledge：在用户知识库检索资料并生成回答（RAG），可传 query / top_k，内部调 rag.answer。
- make_plan：生成今日个性化学习计划，无需参数，内部调 plan_service.generate_plan。

约束：图谱抽取写入操作不列为工具，避免 Agent 自主改写用户图谱。

### 4.3 ReAct 循环

- 无 LLM 凭证 → 直接降级普通 RAG，保持可用。
- 循环（最多 5 步）：
  - 调用工具调用接口，让 LLM 决策下一步；
  - 若返回最终文本 → 结束，返回答案（标记 mode=agent）；
  - 若返回工具调用 → 执行对应工具（异常捕获，返回错误文本让 LLM 改策略），结果按厂商格式回灌对话；
- 超步数 / 异常 → 降级普通 RAG。

安全护栏（沿用工程哲学）：
- 最大步数 5，防模型死循环烧钱。
- 每个工具调用内部异常捕获，出错返回错误文本，最坏整体降级 RAG。
- 所有工具调用强制 user_id 隔离，LLM 无法越权读他人数据。
- 写入型操作不暴露给 Agent，避免自主改写风险。

---

## 5. Memory（轻量，可选，复用现有）

当前阶段不新增 user_memory 表。短期背景直接复用现有 chat_messages 表：

- 短期记忆：Agent 构造对话时，从 chat_messages 取最近若干条作为历史背景，不新增任何结构。
- 长期记忆：本版暂不实现。若未来需要跨会话画像，再单独立项，且只存 key/value 文本、不回写业务表。这把上一版被否的"重 Memory 模块"彻底拿掉，符合轻量诉求。

---

## 6. 接线到 chat.py（改动极小）

chat 接口把原来对 rag.answer 的调用改为统一走 Router 的 dispatch 入口。payload 需携带 query、history、extra（前端透传参数，如 subject / count）、可选 mode。

前端（PC + 移动端）可在输入框加一个"智能体 / 普通"切换：选普通即强制跳过 Router 直走 RAG；选智能体即走本混合架构。不加也能用（默认 Router）。

---

## 7. 落地顺序（更轻）

- 阶段 0：llm_client 加工具调用能力（OpenAI 系优先，其余单轮降级）。
- 阶段 1：写 router（规则分类 + 4 条 Workflow 路由 + Agent 兜底）。
- 阶段 2：写 agent（工具集 + 分发 + ReAct 循环 + 降级）。
- 阶段 3：chat.py 加 dispatch 分支。
- 阶段 4：前端模式切换（可选）。
- 阶段 5：验证——问"我学得怎样并安排明天 + 出几道题"，应路由到 Agent 并自动 stats → plan → quiz。

---

## 8. 风险与注意

- 多厂商工具回灌格式是最大复杂度点（anthropic / gemini 的回传与 OpenAI 不同）。阶段 0 先只保证 openai_compatible 系完整多轮，其余降级单轮或 RAG，不阻塞主流程。
- Router 规则可能误判复合意图（如"统计 + 计划"被统计先命中）。缓解：规则里把"同时含统计与计划 / 出题"显式归到 Agent，或加 mode 强路由。
- Agent 兜底时仍可能慢 / 贵，故最大步数 5 + 无凭证降级 RAG，保证任何情况下都有可用回答。
