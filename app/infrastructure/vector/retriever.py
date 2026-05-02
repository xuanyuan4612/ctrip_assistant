"""RAG 检索器 (Phase 4 shim) — 委托给现有实现"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from tools.retriever_vector import lookup_policy

__all__ = ["lookup_policy"]
