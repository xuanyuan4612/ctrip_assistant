"""决策溯源 - 记录每个 Agent 节点的决策链"""
import json
from datetime import datetime, timezone


class DecisionNode:
    def __init__(
        self,
        node_id: str,
        decision_type: str,
        candidates: list = None,
        selected: str = None,
        confidence: float = 0.0,
    ):
        self.node_id = node_id
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.decision_type = decision_type
        self.candidates = candidates or []
        self.selected = selected
        self.confidence = confidence

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "timestamp": self.timestamp,
            "decision_type": self.decision_type,
            "candidates": self.candidates,
            "selected": self.selected,
            "confidence": self.confidence,
        }


def record_decision(
    state: dict,
    node_id: str,
    decision_type: str,
    candidates: list = None,
    selected: str = None,
    confidence: float = 0.0,
) -> None:
    node = DecisionNode(node_id, decision_type, candidates, selected, confidence)
    path = state.get("decision_path", [])
    path.append(node.to_dict())
    state["decision_path"] = path
