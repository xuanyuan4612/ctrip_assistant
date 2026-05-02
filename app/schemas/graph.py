"""Graph Schema"""
import uuid
from typing import Optional

from pydantic import BaseModel, Field


class GraphChatRequest(BaseModel):
    user_input: str = Field(..., description="用户输入")
    thread_id: Optional[str] = Field(None, description="会话ID (None 则创建新会话)")
    stream: bool = Field(False, description="是否使用 SSE 流式输出")


class GraphChatResponse(BaseModel):
    assistant: str = Field(..., description="AI 助手响应")
    thread_id: str = Field(..., description="会话ID")
