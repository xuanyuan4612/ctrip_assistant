# -*- coding: utf-8 -*-
"""
结构化异常体系

定义应用中可能抛出的所有业务异常。所有异常继承自 AppException，
最终由 main.py 中的全局异常处理器统一捕获并转换成 JSON 响应。

设计原则：
  - 分层清晰：基础类 → 业务类，每个异常对应一种 HTTP 状态码
  - 统一格式：所有异常返回 {"error": {"code": "...", "message": "..."}} 结构
  - 语义明确：异常类名直接说明问题类型，方便调用方理解和处理
  - WHY：统一的异常体系保证 API 错误响应格式一致，前端可以统一解析
"""
from fastapi import HTTPException, status


class AppException(HTTPException):
    """
    应用异常基类

    继承自 FastAPI 的 HTTPException，所有自定义异常都继承此类。
    子类只需指定 status_code 和默认 detail 消息。

    为何不直接使用 HTTPException：
      - 通过类层次结构区分异常类型，catch 时更精确
      - 可在异常类上附加业务相关的元数据
    """

    def __init__(self, detail: str, status_code: int = 500):
        """
        Args:
            detail: 错误详情文本（最终返回给前端）
            status_code: HTTP 状态码，默认为 500 内部错误
        """
        super().__init__(status_code=status_code, detail=detail)


class AuthenticationError(AppException):
    """认证失败异常（401）

    使用场景：
      - 登录时用户名或密码错误
      - 注册时用户名已存在
      - JWT 令牌缺失、无效或过期
    """

    def __init__(self, detail: str = "认证失败"):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)


class PermissionDeniedError(AppException):
    """权限不足异常（403）

    使用场景：
      - 用户尝试访问无权访问的资源
      - 需要管理员权限但当前用户是普通用户
    """

    def __init__(self, detail: str = "权限不足"):
        super().__init__(detail=detail, status_code=status.HTTP_403_FORBIDDEN)


class NotFoundError(AppException):
    """资源不存在异常（404）

    使用场景：
      - 查询的用户/订单/会话不存在
      - 请求的 API 端点不存在（由 FastAPI 默认处理）
    """

    def __init__(self, detail: str = "资源不存在"):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)


class ValidationError(AppException):
    """数据验证失败异常（422）

    使用场景：
      - 请求体字段类型不匹配
      - 必填字段缺失
      - 字段值不符合业务规则（如密码太短）
    """

    def __init__(self, detail: str = "数据验证失败"):
        super().__init__(detail=detail, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class RateLimitError(AppException):
    """请求频率限制异常（429）

    使用场景：
      - 登录接口频繁请求触发防暴力破解
      - 全局 API 调用超过每分钟配额
      - 单用户 Token 预算耗尽
    """

    def __init__(self, detail: str = "请求过于频繁"):
        super().__init__(detail=detail, status_code=status.HTTP_429_TOO_MANY_REQUESTS)


class LLMServiceError(AppException):
    """LLM 服务不可用异常（503）

    使用场景：
      - LLM API 返回 5xx 错误
      - API 调用超时
      - 主备 Provider 均不可用
      - Token 预算耗尽
    """

    def __init__(self, detail: str = "AI 服务暂时不可用"):
        super().__init__(detail=detail, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


class VectorStoreError(AppException):
    """向量检索服务异常（503）

    使用场景：
      - Qdrant 服务连接失败
      - 向量检索超时
      - 索引操作异常
    """

    def __init__(self, detail: str = "向量检索服务异常"):
        super().__init__(detail=detail, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
