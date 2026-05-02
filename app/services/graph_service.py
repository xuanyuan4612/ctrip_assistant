"""Graph 编排服务"""
import logging
import uuid

from fastapi import Request

from app.core.exceptions import AuthenticationError

log = logging.getLogger("app.services.graph")


class GraphService:
    @staticmethod
    def resolve_identity(request: Request) -> tuple:
        """从 JWT 令牌解析用户身份"""
        raw = getattr(request.state, "username", "")
        if ":" not in raw:
            raise AuthenticationError("无效的用户身份")

        user_id_str, username = raw.split(":", 1)
        user_id = int(user_id_str)

        from app.db.repositories.user import UserRepository
        user = UserRepository().get_by_username_raw(user_id)
        passenger_id = user.passenger_id if user and user.passenger_id else ""

        return user_id, username, passenger_id

    @staticmethod
    async def execute(user_input: str, user_id: int, username: str, passenger_id: str, thread_id: str = None) -> dict:
        """执行多智能体对话"""
        if not thread_id:
            thread_id = f"user_{user_id}:{uuid.uuid4()}"

        try:
            from app.graph.graph import build_default_graph
            from app.graph.agents.classifier import UserContext

            graph = build_default_graph()
            context = UserContext(id=user_id, username=username, passenger_id=passenger_id)
            config = {"configurable": {"thread_id": thread_id, "user_context": context}}

            if user_input.strip().lower() == "y":
                events = graph.stream(None, config, stream_mode="values")
            else:
                events = graph.stream({"messages": [("user", user_input)]}, config, stream_mode="values")

            result = ""
            for event in events:
                messages = event.get("messages", [])
                if messages:
                    msg = messages[-1] if isinstance(messages, list) else messages
                    if hasattr(msg, "content") and msg.content:
                        result = msg.content

            if not result:
                current = graph.get_state(config)
                if current.next:
                    result = "AI助手即将执行操作。是否批准？输入'y'继续。"

            return {"message": result or "已处理", "thread_id": thread_id}

        except Exception as e:
            log.exception("Graph execution failed")
            return {"message": f"服务处理中: {str(e)[:100]}", "thread_id": thread_id}
