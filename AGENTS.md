# AGENTS.md

## 入口

- **FastAPI REST API**: `make dev` 或 `uv run uvicorn app.main:create_app --reload --host 0.0.0.0 --port 8000 --factory`
- **前端开发**: `make fe-dev` 或 `cd frontend && npm run dev`（Vite 端口 5173，自动代理 `/api` → `:8000`）

## 包管理

- 使用 **uv**（`uv sync` 安装，`uv run ...` 执行），**不是 poetry**——README 说 poetry 是错的
- `pyproject.toml` 中有 `[tool.uv]` 配置段，无 poetry 相关配置

## 双配置系统（重要）

项目有**两套独立配置**，互不干扰：
- **`app/core/config.py`**（pydantic-settings）—— `app/` 目录使用，从 `.env` 读取。导入方式：`from app.core.config import settings`
- **`config/`**（Dynaconf）—— `db/` 和 `tools/` 目录使用，从 `config/development.yml` 读取。导入方式：`from config import settings`。`EMP_ENV` 切换环境

**字段名不同**：Dynaconf 是 `settings.DATABASE.DRIVER`，pydantic-settings 是 `settings.DATABASE_URL`。

## 关键运行时问题

⚠️ **`app/graph/agents/*.py` 文件中 import 了不存在的模块**：
```python
from graph_chat.llm_tavily import tavily_tool, llm  # graph_chat/ 目录不存在
from graph_chat.base_data_model import ...            # 同样不存在
```
受影响的文件：`primary.py`, `flight.py`, `hotel.py`, `car_rental.py`, `excursion.py`。运行任何 agent 相关代码前需先解决。

## 数据库

- **MySQL**：用户认证数据（FastAPI 启动时需要 `DATABASE_URL`）
- **SQLite `travel_new.sqlite`**：业务/旅行数据。`app/db/async_db.py` 和 `tools/` 都使用
- **`travel2.sqlite`**：备份副本，由 `tools/init_db.update_dates()` 用于重置数据
- 测试使用 SQLite 内存库（见 `tests/conftest.py`）
- `make migrate` → `alembic -c migrations/alembic.ini upgrade head`
- `alembic.ini` 在 `migrations/` 目录内，**不在项目根目录**

## 多智能体图

- **单一入口**：`app/graph/graph.py` 中的 `build_graph()` — 之前多份图构建代码（`graph_gradio.py`, `finally_graph.py`, `第三个流程图.py`）已不存在
- 架构：1 个 Primary Agent（Supervisor）+ 4 个 Sub-Agent（flight, hotel, car_rental, excursion）
- Human-in-the-loop：4 个 `*_sensitive_tools` 节点前中断，用户输入 `'y'` 确认
- Checkpointer：`MemorySaver`（内存中，未使用 PostgreSQL）

## LLM 配置

- 默认：DeepSeek（`LLM_API_BASE=https://api.deepseek.com/v1`），备用 OpenAI
- 通过 `.env` 配置（`LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY` 等）
- 意图分类器可独立配置低成本模型（`CLASSIFIER_MODEL`, `CLASSIFIER_TEMPERATURE`）

## 认证

- JWT Bearer Token，中间件层实现（`app/middleware/auth.py`）
- `AUTH_WHITELIST` 使用 `re.fullmatch` 匹配路径——注意 `fullmatch` 严格匹配完整路径
- 测试白名单路径时需要精确匹配（例如 `/docs` 不会匹配 `/docs#/default`）

## 前端

- Vue 3 + TypeScript + Tailwind CSS + Pinia
- Vite 开发服务器端口 5173，`/api` 代理到 `localhost:8000`
- SSE 流式对话使用 `@microsoft/fetch-event-source`

## 测试

```bash
make test                              # 全量 + 覆盖率
pytest tests/ -v --cov=app             # 同上
pytest tests/unit/ -v                  # 仅单元测试
pytest tests/integration/ -v           # 仅集成测试
```

## Docker 部署

```bash
make build    # docker compose -f docker/docker-compose.yml build
make up       # docker compose -f docker/docker-compose.yml up -d
make fe-build # 构建前端生产包 (vue-tsc && vite build)
```
- Nginx 反向代理（`:80` → 前端 + API），SSE 需要 `proxy_buffering off`
- ⚠️ `docker/Dockerfile` 和 `k8s/Dockerfile.app` 中 `COPY data/` 行引用了不存在的 `data/` 目录——构建前需创建或删除该行
- ⚠️ `k8s/Dockerfile.app` 中 `COPY alembic.ini` 从根目录复制，但实际在 `migrations/alembic.ini`

## K8s 部署

- `k8s/` 目录包含完整生产集群部署配置（base + staging/production overlays）
- 使用 Kustomize 管理环境差异
- 两个独立 Dockerfile：`k8s/Dockerfile.app`（FastAPI）和 `k8s/Dockerfile.frontend`（Nginx + Vue）
- K8s Dockerfile.app 注释写 "Poetry" 但实际使用 `uv`（代码正确，注释错误）

## 不再存在的文件/目录

以下在旧版 AGENTS.md 中被引用但已移除：
- `graph_chat/` 整个目录（及 `graph_gradio.py`, `llm_tavily.py`）
- `main.py`（根目录）— 入口已移到 `app/main.py`
- `finally_graph.py`, `第三个流程图.py`
- 硬编码的 `passenger_id = "3442 587242"` — 现从数据库查询

## tools/__init__.py 已知 Bug

**已修复**。第 9、12 行 `local_file` / `backup_file` 现已正确使用 f-string（`f"{basic_dir}/..."`），无需再关注。
