# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 安装依赖
COPY pyproject.toml ./
RUN uv sync --no-dev

# 复制应用代码
COPY app/ ./app/
COPY data/ ./data/
COPY .env ./

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]
