# -*- coding: utf-8 -*-
"""
JSON 结构化日志配置

提供两种日志格式：
  1. JSON 格式（生产环境）：结构化日志，方便 ELK/Loki 等日志平台收集和分析
  2. 控制台格式（开发环境）：带颜色的可读格式，方便本地调试

设计原则：
  - 每个日志条目包含固定字段（时间戳、级别、记录器、位置、消息）
  - 可选字段（request_id、user_id、exception）根据上下文动态附加
  - 生产环境使用 RotatingFileHandler 自动轮转，避免日志文件无限增长
  - WHY：结构化日志便于自动化分析，颜色输出提升开发体验
"""
import json
import logging
import logging.handlers
from datetime import datetime, timezone

from app.core.config import settings


class JsonFormatter(logging.Formatter):
    """
    JSON 日志格式化器

    将每条日志记录格式化为一行 JSON 字符串，包含以下字段：
      - timestamp：ISO 8601 格式的时间戳（UTC）
      - level：日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
      - logger：记录器名称（如 "app.middleware.auth"）
      - module：源代码模块名
      - function：函数名
      - line：行号
      - message：日志消息
      - request_id：请求追踪 ID（由 RequestIDMiddleware 注入）
      - user_id：用户 ID（由 AuthMiddleware 注入）
      - exception：异常堆栈（仅当记录异常时包含）

    为什么用 JSON：
      - 日志平台（ELK/Loki）原生支持 JSON 解析，可直接建索引
      - 字段结构固定，便于编写告警规则（如 level=ERROR 触发钉钉通知）
      - 兼容 logstash 格式，可无缝对接日志采集管道
    """

    def format(self, record: logging.LogRecord) -> str:
        """将 LogRecord 格式化为 JSON 字符串"""
        # 基础字段：所有日志记录都包含
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        # 可选字段：通过 extra 参数注入（在中间件中设置）
        # 例如：logger.info("msg", extra={"request_id": "xxx"})
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        # 异常信息：logger.exception() 调用时自动填充 exc_info
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)
        # ensure_ascii=False 保证中文正常显示，而不是转义成 \uXXXX
        return json.dumps(log_entry, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """
    控制台日志格式化器（开发环境）

    特点：
      - 带颜色：ERROR 红色、WARNING 黄色、其他灰色
      - 固定宽度级别名方便对齐阅读
      - 包含精确到毫秒的时间戳

    字段说明：
      %(asctime)s     → 2024-01-15 10:30:45
      %(levelname)-8s → INFO     (左对齐，占8字符)
      %(name)s        → app.services.auth
      %(funcName)s    → login
      %(lineno)d      → 42
      %(message)s     → 实际日志消息
    """

    # ANSI 颜色码
    grey = "\x1b[38;20m"    # 灰色：INFO/DEBUG
    yellow = "\x1b[33;20m"  # 黄色：WARNING
    red = "\x1b[31;20m"     # 红色：ERROR/CRITICAL
    reset = "\x1b[0m"       # 重置颜色

    # 日志格式模板
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"

    def format(self, record: logging.LogRecord) -> str:
        """根据日志级别应用不同颜色"""
        # 选择颜色：ERROR 及以上用红色，WARNING 用黄色，其他用灰色
        if record.levelno >= logging.ERROR:
            fmt = self.red + self.fmt + self.reset
        elif record.levelno >= logging.WARNING:
            fmt = self.yellow + self.fmt + self.reset
        else:
            fmt = self.grey + self.fmt + self.reset
        formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def setup_logging() -> None:
    """
    初始化全局日志配置

    在应用启动时调用一次（由 main.py 的 lifespan 钩子触发）。

    配置策略：
      1. 根日志器级别从 settings.LOG_LEVEL 读取
      2. 生产环境（JSON 格式 + 非 DEBUG 模式）：
         - 同时输出到控制台和滚动文件 logs/app.log
         - 文件按 10MB 轮转，保留最近 5 个备份
      3. 开发环境（Console 格式 或 DEBUG 模式）：
         - 仅输出到控制台，带颜色高亮
      4. 降低第三方库的日志级别，减少干扰

    WHY：区分生产和开发格式，让日志既适合人工阅读也适合机器收集
    """
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)

    # 清除已有 handler，防止反复调用 setup_logging 时重复添加
    root.handlers.clear()

    # 生产模式：JSON 格式 + 非 DEBUG
    if settings.LOG_FORMAT == "json" and not settings.DEBUG:
        # 控制台输出（JSON）
        handler: logging.Handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())

        # 文件输出（JSON），自动轮转
        # WHY RotatingFileHandler：防止单个日志文件无限增长占满磁盘
        file_handler = logging.handlers.RotatingFileHandler(
            "logs/app.log",          # 日志文件路径
            maxBytes=10 * 1024 * 1024,  # 单文件最大 10MB
            backupCount=5,           # 保留 5 个备份文件
            encoding="utf-8",        # 支持中文日志
        )
        file_handler.setFormatter(JsonFormatter())
        root.addHandler(file_handler)
    else:
        # 开发模式：带颜色的可读格式
        handler = logging.StreamHandler()
        handler.setFormatter(ConsoleFormatter())

    root.addHandler(handler)

    # 降低第三方库的日志级别，过滤调试信息
    # WHY：uvicorn/sqlalchemy/httpx 的 DEBUG 日志过于冗长，干扰问题排查
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
