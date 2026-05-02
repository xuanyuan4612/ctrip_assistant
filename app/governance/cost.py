"""成本管理 - Token 预算和成本归因"""
import logging

log = logging.getLogger("app.governance.cost")


class TokenBudget:
    def __init__(self, per_user_day: int = 100_000, per_session: int = 50_000):
        self.per_user_day = per_user_day
        self.per_session = per_session

    def check(self, user_id: int, tokens_used_today: int, tokens_this_session: int) -> bool:
        if tokens_used_today >= self.per_user_day:
            log.warning(f"User {user_id} exceeded daily token budget")
            return False
        if tokens_this_session >= self.per_session:
            log.warning(f"User {user_id} exceeded session token budget")
            return False
        return True

    def record(self, user_id: int, session_id: str, model: str, input_tokens: int, output_tokens: int):
        log.info(
            "TOKEN_USAGE | user=%s session=%s model=%s in=%d out=%d",
            user_id, session_id, model, input_tokens, output_tokens,
        )
