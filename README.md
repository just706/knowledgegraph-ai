# KnowledgeGraph AI 智能学习助手

基于 **LLM + RAG + 知识图谱** 的智能学习助手，帮助用户从"拥有资料"转变为"真正理解和掌握知识"。

> 完整需求、开发计划与 AI 宪法见 [`prd.md`](./prd.md)。

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue3 + TypeScript + Vite + Element Plus + Vue Router + Pinia |
| 后端 | FastAPI + SQLAlchemy + Pydantic |
| 数据库（MVP 占位） | SQLite（后续 PostgreSQL / Neo4j / Chroma） |
| AI（后续 Phase） | LLM API + Embedding + RAG + LangChain/LangGraph |

## 目录结构

```
.
├── prd.md              # 整合后的项目文档（PRD + 开发计划 + AI 宪法）
├── docs/               # 原始 Word 文档归档
├── backend/            # FastAPI 后端
│   ├── app/
│   │   ├── api/        # 路由（health, users 占位）
│   │   ├── models/     # SQLAlchemy ORM 模型
│   │   ├── schemas/    # Pydantic 校验/响应模型
│   │   ├── config.py   # 环境变量配置
│   │   ├── database.py # 引擎与会话
│   │   └── main.py     # 应用入口（Swagger /docs）
│   ├── tests/          # 接口测试
│   └── requirements.txt
└── frontend/           # Vue3 前端
    └── src/
        ├── api/        # 接口请求
        ├── layouts/    # 布局
        ├── pages/      # 页面（首页/知识库/问答/图谱/导图/错题本）
        ├── router/     # 路由
        ├── store/      # Pinia 状态
        ├── styles/     # 全局样式
        └── utils/      # 工具函数
```

## 快速开始

### 后端

```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python run.py                 # 启动于 http://localhost:8000，Swagger: /docs
pytest tests/ -q              # 运行接口测试
```

### 前端

```bash
cd frontend
npm install
cp .env.example .env
npm run dev                   # 启动于 http://localhost:5173
```

## 开发阶段（Phase）

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | 项目初始化：前后端工程、环境、Git | ✅ 完成 |
| Phase 2 | 用户系统：注册登录、JWT、数据库设计 | ⏳ 待开始 |
| Phase 3 | 知识库模块：上传、PDF 解析、切片、向量存储 | ⏳ |
| Phase 4 | RAG 系统：Embedding、检索、问答接口 | ⏳ |
| Phase 5 | 知识图谱：实体/关系抽取、Neo4j、展示 | ⏳ |
| Phase 6 | 前端展示：知识库/问答/图谱/导图页 | ⏳ |
| Phase 7 | AI 出题：生成题目、解析 | ⏳ |
| Phase 8 | 错题系统：保存、分析、建议 | ⏳ |

## AI 宪法核心规则

1. 不破坏已有功能　2. MVP 优先　3. 用户价值优先　4. AI 负责智能，代码负责业务
5. 保持架构简单　6. 每一步都可运行验证　7. 文档与代码同步
