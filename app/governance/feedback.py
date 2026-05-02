"""用户反馈闭环"""
import logging

log = logging.getLogger("app.governance.feedback")


class FeedbackCollector:
    @staticmethod
    def record(user_id: int, thread_id: str, rating: str, reason: str = ""):
        log.info("FEEDBACK | user=%s thread=%s rating=%s reason=%s", user_id, thread_id, rating, reason)

    @staticmethod
    def should_escalate(rating: str) -> bool:
        return rating in ("negative", "unhelpful")
