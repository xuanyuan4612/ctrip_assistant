"""
retriever_vector.py — 向后兼容的查询工具

【已重构】此文件现在作为 retriever_engine.py 的轻量级 shim。
生产 RAG 逻辑已迁移至 retriever_engine.py，提供：
  - 中文优化分块管线
  - Qdrant 持久化向量存储
  - LangChain Indexing API 增量更新
  - 可选重排序

保持 lookup_policy 工具签名不变，所有已有调用方无需修改。
"""

from tools.retriever_engine import get_retriever_tool

# 向后兼容导出：保持旧的全局 retriever 对象引用
# 但实际使用中应通过 get_retriever_tool() 获取
lookup_policy = get_retriever_tool()

if __name__ == "__main__":
    print(lookup_policy("怎么才能退票呢？"))
