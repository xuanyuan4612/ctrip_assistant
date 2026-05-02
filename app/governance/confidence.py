"""置信度估计 - 路由/检索/事实/回答四层置信度"""


def estimate_routing_confidence(candidates: list, selected_index: int = 0) -> float:
    """从候选方案分数估算路由置信度"""
    if not candidates:
        return 0.0
    return candidates[selected_index].get("score", 0.0) if selected_index < len(candidates) else 0.0


def estimate_retrieval_confidence(similarities: list) -> float:
    """从检索相似度估算检索置信度"""
    if not similarities:
        return 0.0
    return sum(similarities) / len(similarities)


def estimate_answer_confidence(routing_conf: float, retrieval_conf: float, factuality_conf: float) -> float:
    """加权综合回答置信度: 事实×0.5 + 检索×0.3 + 路由×0.2"""
    return factuality_conf * 0.5 + retrieval_conf * 0.3 + routing_conf * 0.2


def confidence_label(score: float) -> str:
    if score >= 0.85:
        return "high"
    elif score >= 0.70:
        return "medium"
    elif score >= 0.50:
        return "low"
    return "unreliable"
