# 携程 AI 助手 (Ctrip AI Assistant)

> 生产级多智能体旅行服务系统

## 快速开始

### 环境要求
- Python 3.11+
- Poetry
- Docker

### 安装
```bash
cp .env.example .env
# 编辑 .env 填入真实 API Key 和数据库凭据
poetry install
```

### 运行
```bash
make dev
# http://localhost:8000/docs 查看 API 文档
# http://localhost:8000/api/v1/health 健康检查
```

### Docker 部署
```bash
make build
make up
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/register` | 用户注册 |
| POST | `/api/v1/auth/login` | 用户登录 |
| POST | `/api/v1/auth/token` | OAuth2 Token |
| GET | `/api/v1/users` | 用户列表 |
| GET | `/api/v1/users/{id}` | 用户详情 |
| PATCH | `/api/v1/users/{id}` | 更新用户 |
| DELETE | `/api/v1/users` | 批量删除 |
| POST | `/api/v1/graph/chat` | 多智能体对话 |
| GET | `/api/v1/health` | 健康检查 |

## 架构

六层分层架构: 基础层 → 能力层 → Agent 层 → 编排层 → 表现层 → 治理层

## 测试
```bash
make test
```
