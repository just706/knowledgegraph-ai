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
| 安全 | bcrypt 密码哈希 + python-jose JWT（Bearer） |
| 文档解析 | pypdf（PDF）/ 原生读取（TXT / Markdown） |

> 注：原计划的 `passlib` 因与 bcrypt 4.x 不兼容已移除，改为直接使用 `bcrypt`（依赖更少、更简单，符合 AI 宪法"简单>成熟"）。

## 开发进度（与代码同步）

| Phase | 范围 | 状态 |
|-------|------|------|
| Phase 1 | 项目初始化：前后端工程、环境、Git | ✅ 完成 |
| Phase 2 | 用户系统：注册/登录/JWT/路由守卫 | ✅ 完成 |
| Phase 3 | 知识库：上传/解析/切片/用户隔离 | ✅ 完成 |
| Phase 4 | RAG 系统：向量化 + 检索问答 | ✅ 完成 |
| Phase 5 | 知识图谱：实体/关系抽取与可视化 | ✅ 完成 |
| Phase 6 | 前端展示：图谱/导图可视化 | ✅ 完成 |
| Phase 7 | AI 出题：基于资料生成练习题 | ✅ 完成 |
| Phase 8 | 错题系统：错题收集与针对性练习 | ✅ 完成 |
| 部署 | Docker / Docker Compose 一键部署 + CI 镜像构建 | ✅ 完成 |

## 目录结构

```
.
├── prd.md              # 整合后的项目文档（PRD + 开发计划 + AI 宪法）
├── docs/               # 原始 Word 文档归档
├── .env.example        # 生产环境变量模板（部署用）
├── docker-compose.yml  # 一键编排前后端容器
├── .github/workflows/  # CI：测试 + 镜像构建/推送
├── backend/            # FastAPI 后端
│   ├── app/
│   │   ├── api/        # 路由（health, users, documents, chat, graph, mindmap, quiz, mistakes, stats）
│   │   ├── core/       # 核心逻辑（security：密码哈希 + JWT / crypto：Key 加密）
│   │   ├── models/     # SQLAlchemy ORM 模型（user / document / chunk / chat / quiz / mistake / graph）
│   │   ├── schemas/    # Pydantic 校验/响应模型
│   │   ├── services/   # 业务服务（parser / splitter / embedding / retriever / llm_client / rag ...）
│   │   ├── config.py   # 环境变量配置
│   │   ├── database.py # 引擎与会话
│   │   └── main.py     # 应用入口（Swagger /docs）
│   ├── tests/          # 接口测试（conftest 隔离数据库 + client fixture）
│   ├── Dockerfile      # 后端镜像
│   └── requirements.txt
└── frontend/           # Vue3 前端
    ├── src/
    │   ├── api/        # 接口请求
    │   ├── pages/      # 页面（首页/知识库/问答/图谱/导图/错题本）
    │   ├── router/     # 路由
    │   ├── store/      # Pinia 状态
    │   └── ...
    ├── Dockerfile      # 前端镜像（node 构建 → nginx 运行）
    └── nginx.conf      # Nginx 反代 /api 到后端
```

## 快速开始

### 方式一：Docker 一键部署（推荐）

> 需已安装 Docker 与 Docker Compose。一条命令同时拉起前端（Nginx，:5173）与后端（:8000）。

```bash
# 1. 准备环境变量
cp .env.example .env
# 2. 编辑 .env，至少把 SECRET_KEY 改成随机长字符串

# 3. 构建并启动
docker compose up -d --build

# 访问前端：http://localhost:5173   （API 已由 Nginx 反代到 /api/v1）
# 后端 Swagger：http://localhost:8000/docs
```

数据持久化：SQLite 数据库与上传文件挂载在 `backend-data` 卷中，重建容器不会丢数据。
停止：`docker compose down`；查看日志：`docker compose logs -f`。

### 方式二：本地开发

```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python run.py                 # 启动于 http://localhost:8000，Swagger: /docs
pytest tests/ -q              # 运行接口测试
```

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
| Phase 2 | 用户系统：注册登录、JWT、数据库设计 | ✅ 完成 |
| Phase 3 | 知识库模块：上传、PDF 解析、切片、向量存储 | ⏳ |
| Phase 4 | RAG 系统：Embedding、检索、问答接口 | ⏳ |
| Phase 5 | 知识图谱：实体/关系抽取、Neo4j、展示 | ⏳ |
| Phase 6 | 前端展示：知识库/问答/图谱/导图页 | ⏳ |
| Phase 7 | AI 出题：生成题目、解析 | ⏳ |
| Phase 8 | 错题系统：保存、分析、建议 | ✅ 完成 |
| 部署 | Docker Compose 一键部署、CI 自动构建镜像 | ✅ 完成 |

## AI 宪法核心规则

1. 不破坏已有功能　2. MVP 优先　3. 用户价值优先　4. AI 负责智能，代码负责业务
5. 保持架构简单　6. 每一步都可运行验证　7. 文档与代码同步
