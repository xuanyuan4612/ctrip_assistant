"""多智能体对话端点 (SSE 流式)"""
import json
import logging
import uuid

from fastapi import APIRouter, Request
from starlette.responses import StreamingResponse

from app.schemas.graph import GraphChatRequest
from app.services.graph_service import GraphService

router = APIRouter()
log = logging.getLogger("app.api.graph")


async def _stream_graph(user_input: str, user_id: int, username: str, passenger_id: str, thread_id: str):
    yield f"event: thinking\ndata: {json.dumps({'agent': 'classifier', 'status': 'analyzing'})}\n\n"

    result = await GraphService.execute(
        user_input=user_input, user_id=user_id, username=username,
        passenger_id=passenger_id, thread_id=thread_id,
    )

    yield f"event: message\ndata: {json.dumps({'content': result['message']})}\n\n"
    yield f"event: done\ndata: {json.dumps({'thread_id': result['thread_id']})}\n\n"


@router.post("/graph/chat")
async def chat(request: Request, obj_in: GraphChatRequest):
    user_id, username, passenger_id = GraphService.resolve_identity(request)
    thread_id = obj_in.thread_id or f"user_{user_id}:{uuid.uuid4()}"

    if obj_in.stream:
        return StreamingResponse(
            _stream_graph(obj_in.user_input, user_id, username, passenger_id, thread_id),
            media_type="text/event-stream",
            headers={"X-Thread-ID": thread_id},
        )

    result = await GraphService.execute(
        user_input=obj_in.user_input, user_id=user_id, username=username,
        passenger_id=passenger_id, thread_id=thread_id,
    )
    return {"assistant": result["message"], "thread_id": result["thread_id"]}
