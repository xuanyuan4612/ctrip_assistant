# -*- coding: utf-8 -*-
"""
健康检查端点

提供应用健康状态检查，用于：
  1. Kubernetes/ Docker 容器的存活探针（Liveness Probe）和就绪探针（Readiness Probe）
  2. 负载均衡器的健康检测
  3. 监控系统（如 Prometheus）定期轮询

设计约束：
  - 无认证：健康检查需要在认证之前执行，否则负载均衡器无法判断服务状态
  - 轻量级：不应包含数据库查询等耗时操作，避免级联故障
  - 标准响应：返回状态、版本号、时间戳，监控系统可据此判断服务是否正常

返回字段说明：
  - status：固定为 "healthy"，表示应用正在运行
  - version：应用版本号，便于确认部署版本
  - timestamp：ISO 格式时间戳（UTC），方便监控系统计算响应延迟
"""
from datetime import datetime, timezone

from fastapi import APIRouter
from starlette.responses import JSONResponse

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    健康检查端点

    返回应用的基础运行状态。此端点位于认证白名单中，
    无需 JWT 令牌即可访问。

    WHY GET 方法：
      - 健康检查通常使用 GET，语义上符合"查询资源状态"
      - 负载均衡器和 Kubernetes 探针默认使用 GET

    Returns:
        JSONResponse:
        {
            "status": "healthy",           # 服务运行状态
            "version": "1.0.0",            # 当前版本号
            "timestamp": "2024-01-15T..."  # UTC 时间戳
        }
    """
    return JSONResponse(
        content={
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
