# 携程 AI 助手 (Ctrip AI Assistant)

> 生产级多智能体旅行服务系统 — 基于 LangGraph 的 Supervisor 多 Agent 架构

## 架构概览

```
┌─────────────────────────────────────────────────────┐
│                    Nginx (:80)                       │
│         / → Vue 前端    /api → FastAPI              │
├─────────────────────────────────────────────────────┤
│  FastAPI (app/)                                      │
│  ┌─────────┐ ┌──────────┐ ┌────────────────────┐   │
│  │ 表现层   │ │ Agent 层  │ │ 治理层 (评估/护栏)  │   │
│  │ REST+SSE│ │ 1+4 Agent │ │ 成本/决策/反馈      │   │
│  └─────────┘ └──────────┘ └────────────────────┘   │
├─────────────────────────────────────────────────────┤
│  MySQL (业务数据)  PostgreSQL (Agent 记忆)  Redis    │
└─────────────────────────────────────────────────────┘
```

## 项目结构

```
ctrip_assistant/
├── app/                    # 后端 (FastAPI + LangGraph)
│   ├── core/               # 配置/安全/异常/日志
│   ├── middleware/          # 认证/CORS/请求ID
│   ├── api/v1/             # REST API + SSE 流式
│   ├── services/           # 业务服务层
│   ├── graph/               # 多智能体编排
│   │   ├── agents/          # 5 个 Agent (主+航班+酒店+租车+旅行)
│   │   ├── tools/           # 工具层 (业务+RAG+系统)
│   │   ├── graph.py         # StateGraph 构建
│   │   └── routing.py       # 路由逻辑
│   ├── db/                  # 数据访问层 (Repository 模式)
│   └── governance/          # 治理层
├── frontend/               # 前端 (Vue 3 + TypeScript)
│   └── src/
│       ├── pages/           # ChatPage / LoginPage / AdminPage
│       ├── components/      # 聊天组件 / 管理组件
│       ├── stores/          # Pinia 状态管理
│       ├── api/             # API 客户端 (SSE 支持)
│       └── router/          # 路由守卫
├── migrations/             # Alembic 数据库迁移
├── tests/                  # 单元测试 + 集成测试
├── docker/                 # Docker 部署配置
├── data/                   # 静态数据 (FAQ, SQLite)
└── .sisyphus/              # 架构设计文档
```

## 快速开始

### 前置条件

| 软件 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 后端运行时 |
| Node.js | 20+ | 前端构建 |
| Poetry | 最新 | Python 依赖管理 |
| Docker + Compose | 最新 | 生产部署 |
| MySQL | 8.0 | 业务数据存储 |

### 1. 克隆并配置

```bash
git clone <repo-url> ctrip_assistant
cd ctrip_assistant

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入:
#   - LLM_API_KEY (OpenAI / DeepSeek)
#   - JWT_SECRET_KEY (python -c "import secrets; print(secrets.token_hex(32))")
#   - DATABASE_URL (MySQL 连接字符串)
```

### 2. 安装依赖

```bash
# 后端
poetry install

# 前端
cd frontend && npm install && cd ..
```

### 3. 数据库初始化

```bash
# 确保 MySQL 运行中，然后执行迁移
alembic upgrade head
```

### 4. 启动开发服务器

```bash
# 终端 1: 后端 (http://localhost:8000)
make dev

# 终端 2: 前端 (http://localhost:5173)
make fe-dev
```

### 5. 验证

```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# API 文档
open http://localhost:8000/docs

# 前端页面
open http://localhost:5173
```

## API 端点

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/v1/auth/register` | 无 | 用户注册 |
| POST | `/api/v1/auth/login` | 无 | 用户登录 (JSON) |
| POST | `/api/v1/auth/token` | 无 | OAuth2 表单 (Swagger) |
| POST | `/api/v1/auth/logout` | JWT | 登出 |
| GET | `/api/v1/users` | JWT | 用户列表 (分页) |
| GET | `/api/v1/users/{id}` | JWT | 用户详情 |
| PATCH | `/api/v1/users/{id}` | JWT | 更新用户 |
| DELETE | `/api/v1/users` | JWT | 批量删除 |
| POST | `/api/v1/graph/chat` | JWT | 多智能体对话 (SSE 流式) |
| GET | `/api/v1/health` | 无 | 健康检查 |

### 对话请求示例

```bash
# 非流式
curl -X POST http://localhost:8000/api/v1/graph/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"user_input": "帮我查下周三北京到苏黎世的航班"}'

# 流式 (SSE)
curl -X POST http://localhost:8000/api/v1/graph/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"user_input": "帮我规划去苏黎世的行程", "stream": true}'
```

## 前端页面

| 页面 | 路由 | 说明 |
|------|------|------|
| 登录/注册 | `/login` | 用户认证 |
| 智能对话 | `/` | 主聊天界面 (流式对话 + 会话管理) |
| 管理仪表盘 | `/admin` | 统计概览 |
| 用户管理 | `/admin/users` | 用户列表/搜索 |
| 对话监控 | `/admin/conversations` | 对话记录 |
| 文档管理 | `/admin/documents` | RAG 文档上传 |

## 常用命令

```bash
make dev         # 启动后端 (开发模式)
make fe-dev      # 启动前端 (开发模式)
make test        # 运行测试
make build       # 构建 Docker 镜像
make up          # 启动 Docker Compose
make down        # 停止 Docker Compose
make migrate     # 数据库迁移
make fe-build    # 构建前端生产包
```

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `DATABASE_URL` | ✅ | MySQL 连接串 |
| `JWT_SECRET_KEY` | ✅ | JWT 签名密钥 (64 字符 hex) |
| `LLM_API_KEY` | ✅ | DeepSeek API Key |
| `LLM_PROVIDER` | ❌ | `deepseek` (默认) 或 `openai` |
| `LLM_MODEL` | ❌ | `deepseek-chat` (默认) |
| `LLM_API_BASE` | ❌ | 默认 `https://api.deepseek.com/v1` |
| `EMBEDDING_API_KEY` | ❌ | Embedding API Key |
| `REDIS_URL` | ❌ | Redis 连接 (缓存/限流) |
| `PG_DATABASE_URL` | ❌ | PostgreSQL 连接 (Agent 记忆) |
| `CORS_ORIGINS` | ❌ | 允许的前端源 |
| `LOG_LEVEL` | ❌ | `INFO` (默认) 或 `DEBUG` |

## 测试

```bash
# 运行所有测试
make test

# 仅单元测试
pytest tests/unit/ -v

# 仅集成测试
pytest tests/integration/ -v
```

## 部署

详见下方 [部署环境指南](#部署环境指南)。

## 架构文档

完整架构设计见 `.sisyphus/` 目录:
- `DEVELOPMENT_DOC.md` — 完整开发文档 (项目唯一权威架构文档)
- `upgrade-architecture.md` — 全局架构升级方案
- `subsystem-redesign.md` — 核心子系统重设计
- `infrastructure-scalability.md` — 基础设施与扩展性
- `agent-governance-layered.md` — Agent 治理与分层架构
- `agent-decision-knowledge.md` — 决策智能与知识生命周期

## 技术栈

| 层次 | 技术 |
|------|------|
| 后端框架 | FastAPI + Uvicorn |
| Agent 框架 | LangGraph (StateGraph) |
| LLM | OpenAI / DeepSeek |
| 前端 | Vue 3 + TypeScript + Tailwind CSS |
| 业务数据库 | MySQL 8.0 |
| Agent 记忆 | PostgreSQL 16 |
| 缓存 | Redis 7 |
| 向量存储 | Qdrant (预留) |
| 部署 | Docker Compose + Nginx |
| 监控 | Prometheus + Grafana (预留) |

---

## 部署环境指南

### 环境分级

| 环境 | 用途 | 配置来源 | 数据 |
|------|------|---------|------|
| **开发 (dev)** | 本地开发调试 | `.env` (本地) | SQLite / 本地 MySQL |
| **测试 (staging)** | 预发布验证 | `.env.staging` | 测试 MySQL (脱敏数据) |
| **生产 (prod)** | 正式服务 | 环境变量 / Vault | 生产 MySQL + PostgreSQL |

### 环境一: 本地开发

**适用**: 单机开发调试

```bash
# 1. 确保 Python 3.11+ 和 Node.js 20+ 已安装

# 2. 安装依赖
poetry install
cd frontend && npm install && cd ..

# 3. 配置 .env
cp .env.example .env
# 编辑 .env，至少填入 LLM_API_KEY 和 JWT_SECRET_KEY

# 4. 启动 MySQL (Docker)
docker run -d --name mysql-dev \
  -e MYSQL_ROOT_PASSWORD=root123 \
  -e MYSQL_DATABASE=ctrip_assistant \
  -p 3306:3306 mysql:8.0

# 5. 数据库迁移
alembic upgrade head

# 6. 启动服务
make dev     # 后端 :8000
make fe-dev  # 前端 :5173
```

### 环境二: Docker Compose 单机部署

**适用**: 小规模生产 / 内部使用

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入生产凭据

# 2. 构建并启动
make build
make up

# 服务端口:
#   :80    → Nginx → 前端 + API
#   :3306  → MySQL
#   :6379  → Redis
#   :8000  → FastAPI (内部)

# 3. 数据库迁移
docker compose -f docker/docker-compose.yml exec app alembic upgrade head

# 4. 查看日志
docker compose -f docker/docker-compose.yml logs -f app
```

### 环境三: K8s 生产集群

**适用**: 大规模生产 (需已部署 K8s 集群 + Nginx Ingress Controller)

```bash
# 1. 构建镜像
cd k8s
docker build -t ctrip/app:latest -f Dockerfile.app ..
docker build -t ctrip/frontend:latest -f Dockerfile.frontend ../frontend

# 2. 部署 Staging
kubectl apply -k overlays/staging
kubectl -n ctrip-assistant-staging wait --for=condition=available deployment/app --timeout=300s

# 3. 数据库迁移
kubectl -n ctrip-assistant-staging exec deploy/app -- alembic upgrade head

# 4. 验证
curl http://staging.ctrip.example.com/api/v1/health

# 5. 部署 Production
kubectl apply -k overlays/production
bash deploy.sh production
```

**K8s 资源清单**:

| 资源 | 用途 | 副本数 |
|------|------|--------|
| Deployment/app | FastAPI 后端 | 3 (HPA: 3-20) |
| Deployment/redis | 缓存 | 1 |
| StatefulSet/mysql | 业务数据库 | 1 |
| Service/app | 内部服务发现 | — |
| Service/mysql | 数据库连接 | — |
| Service/redis | 缓存连接 | — |
| Ingress | 外部入口 (/ → 前端, /api → 后端) | — |
| HPA | 自动扩缩 | CPU 70% |

**Pod 拓扑 (Production)**:
```
                    ┌──────────────────┐
                    │  Ingress (Nginx) │
                    │  / → frontend     │
                    │  /api → app       │
                    │  SSE: buffering   │
                    │  off, timeout 300s│
                    └────────┬─────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
    ┌───────────┐     ┌───────────┐     ┌───────────┐
    │ app-pod-1 │     │ app-pod-2 │     │ app-pod-3 │
    │ FastAPI   │     │ FastAPI   │     │ FastAPI   │
    │ :8000     │     │ :8000     │     │ :8000     │
    └─────┬─────┘     └─────┬─────┘     └─────┬─────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │  MySQL   │ │  Redis   │ │  Qdrant  │
        │ Stateful │ │  Deploy  │ │ (预留)   │
        │  Set     │ │          │ │          │
        └──────────┘ └──────────┘ └──────────┘
```

**Staging vs Production**:

| 配置 | Staging | Production |
|------|---------|-----------|
| 副本数 | 1 | 3 |
| HPA | 关闭 | 3-20 |
| CPU Request | 250m | 500m |
| Mem Request | 256Mi | 512Mi |
| Ingress Host | staging.ctrip.example.com | assistant.ctrip.com |
| TLS | 关闭 | 开启 |

### 首次部署检查清单

- [ ] `.env` 文件已配置 (至少 LLM_API_KEY + JWT_SECRET_KEY + DATABASE_URL)
- [ ] MySQL 已运行并创建 `ctrip_assistant` 数据库
- [ ] 数据库迁移已执行 (`alembic upgrade head`)
- [ ] 前端已构建 (`make fe-build`) 或使用开发模式
- [ ] 健康检查通过: `curl /api/v1/health`
- [ ] LLM API 连通: 发送一条测试对话
- [ ] CORS_ORIGINS 包含前端域名
- [ ] Nginx 配置了 SSE 支持 (`proxy_buffering off`)
- [ ] 日志目录 `logs/` 有写入权限

### 常见问题

**Q: 前端代理不工作 (Vite 开发模式)**
A: 确保 `frontend/vite.config.ts` 中 proxy 指向 `http://localhost:8000`，后端已启动。

**Q: LLM API 调用失败**
A: 检查 `.env` 中 `LLM_API_KEY` 和 `LLM_API_BASE` 是否正确。测试: `curl -H "Authorization: Bearer $LLM_API_KEY" $LLM_API_BASE/models`

**Q: 数据库连接失败**
A: 检查 MySQL 是否运行 (`docker ps | grep mysql`)，`DATABASE_URL` 格式是否正确。

**Q: SSE 流式不工作**
A: Nginx 需要 `proxy_buffering off` 和 `proxy_read_timeout 300s`。Vite 开发模式下不需要额外配置。
