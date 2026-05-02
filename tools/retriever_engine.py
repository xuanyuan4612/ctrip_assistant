"""
retriever_engine.py — 生产级 RAG 检索引擎

替代原有的 naive numpy 实现。提供：
  1. 中文优化的双层分块管线 (MarkdownHeader + RecursiveCharacter)
  2. 可切换的嵌入模型（OpenAI / BGE 自托管）
  3. Qdrant 持久化向量存储
  4. LangChain Indexing API 增量文档更新
  5. 可选二阶段重排序（Cohere / BGE Cross-Encoder）
  6. 与现有 lookup_policy 工具的完全向后兼容

用法：
    from tools.retriever_engine import get_retriever_tool
    lookup_policy = get_retriever_tool()  # 返回 @tool 装饰的函数

依赖安装：
    pip install langchain-qdrant qdrant-client
    pip install sentence-transformers  # 仅自托管 BGE 时需要
    pip install langchain-cohere       # 仅 Cohere 重排序时需要
"""

from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
from pathlib import Path
from typing import List, Optional

from langchain.indexes import SQLRecordManager, index
from langchain.text_splitter import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from langchain_core.documents import Document
from langchain_core.tools import tool
from langchain_core.vectorstores import VectorStore

# ── 配置 ────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 尝试加载 Dynaconf 配置；若失败则使用硬编码默认值
try:
    from config import settings
    CFG = settings.RAG
except Exception:
    logger.warning("Dynaconf config not available, using hardcoded defaults")
    CFG = None


def _cfg(key: str, default=None):
    """从 Dynaconf 读取配置，带兜底默认值"""
    if CFG is not None:
        try:
            parts = key.split(".")
            val = CFG
            for p in parts:
                val = val[p]
            return val
        except (KeyError, AttributeError):
            pass
    return default


# ── 分块管线 ────────────────────────────────────────────────────


def make_chinese_text_splitter() -> RecursiveCharacterTextSplitter:
    """创建中文优化的递归字符分块器。

    分隔符优先级（中文特有）：
        段落 > 换行 > 句号/问号/感叹号 > 分号 > 逗号/顿号 > 空格

    Returns:
        RecursiveCharacterTextSplitter 实例
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=_cfg("CHUNKING.CHUNK_SIZE", 512),
        chunk_overlap=_cfg("CHUNKING.CHUNK_OVERLAP", 100),
        separators=_cfg("CHUNKING.SEPARATORS", [
            "\n\n", "\n",
            "。", "！", "？",
            "；",
            "，", "、",
            " ",
            "",
        ]),
        is_separator_regex=False,
    )


def make_markdown_splitter() -> MarkdownHeaderTextSplitter:
    """创建 Markdown 标题感知的粗粒度分块器。

    保留 ## 章节标题作为 metadata["section"]，用于溯源。
    """
    return MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("##", "section"),
        ],
    )


def chunk_faq_document(faq_path: str | Path) -> List[Document]:
    """双层分块管线：Markdown 标题 → 中文递归字符切分

    Args:
        faq_path: FAQ Markdown 文件的路径

    Returns:
        分块后的 Document 列表，每块携带 metadata["section"] 和 metadata["source"]
    """
    faq_path = Path(faq_path)

    with open(faq_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 第一层：按 Markdown ## 标题分组
    section_docs = make_markdown_splitter().split_text(content)

    # 第二层：对每个 section 内的长文本递归切分
    fine_splitter = make_chinese_text_splitter()
    all_chunks = fine_splitter.split_documents(section_docs)

    # 为每个分块补充源追踪信息
    # 用文件内容哈希作为源标识（文件变更时哈希变化 → 自动重新索引）
    file_hash = hashlib.md5(content.encode("utf-8")).hexdigest()[:12]
    source_id = f"{faq_path.name}:{file_hash}"

    for chunk in all_chunks:
        chunk.metadata["source"] = source_id

    logger.info(
        "Chunked %s → %d chunks (file_hash=%s)",
        faq_path.name, len(all_chunks), file_hash,
    )
    return all_chunks


# ── 嵌入模型工厂 ────────────────────────────────────────────────


def create_embeddings():
    """创建嵌入模型实例，支持 OpenAI / BGE 切换。

    配置项 RAG.EMBEDDING.PROVIDER: openai | bge
    """
    provider = _cfg("EMBEDDING.PROVIDER", "openai")

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=_cfg("EMBEDDING.OPENAI.MODEL", "text-embedding-3-small"),
            dimensions=_cfg("EMBEDDING.OPENAI.DIMENSIONS", 768),
            api_key=_cfg("EMBEDDING.OPENAI.API_KEY", None)
                      or os.environ.get("OPENAI_API_KEY"),
            base_url=_cfg("EMBEDDING.OPENAI.API_BASE", None),
        )

    elif provider == "bge":
        from langchain_community.embeddings import HuggingFaceEmbeddings

        model_name = _cfg("EMBEDDING.BGE.MODEL", "BAAI/bge-large-zh-v1.5")
        return HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": _cfg("EMBEDDING.BGE.DEVICE", "cpu")},
            encode_kwargs={
                "normalize_embeddings": _cfg("EMBEDDING.BGE.NORMALIZE", True),
            },
        )

    elif provider == "dmeta":
        from langchain_community.embeddings import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(
            model_name="DMetaSoul/Dmeta-embedding-zh",
            model_kwargs={"device": _cfg("EMBEDDING.BGE.DEVICE", "cpu")},
        )

    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")


# ── 向量存储工厂 ────────────────────────────────────────────────


def create_vector_store(embeddings) -> VectorStore:
    """创建持久化向量存储。

    支持 provider:
        qdrant  — 推荐生产方案：Docker Compose 部署，Rust 高性能
        memory  — 开发测试：InMemoryVectorStore，无需外部服务
    """
    provider = _cfg("VECTOR_STORE.PROVIDER", "qdrant")

    if provider == "qdrant":
        from langchain_qdrant import QdrantVectorStore
        from qdrant_client import QdrantClient
        from qdrant_client.http import models as qmodels

        host = _cfg("VECTOR_STORE.QDRANT.HOST", "localhost")
        port = _cfg("VECTOR_STORE.QDRANT.PORT", 6333)
        collection = _cfg("VECTOR_STORE.QDRANT.COLLECTION", "travel_faq")
        prefer_grpc = _cfg("VECTOR_STORE.QDRANT.PREFER_GRPC", False)
        timeout = _cfg("VECTOR_STORE.QDRANT.TIMEOUT", 30)

        # gRPC 端口仅在使用 gRPC 时连接
        grpc_port = _cfg("VECTOR_STORE.QDRANT.GRPC_PORT", 6334)

        client = QdrantClient(
            host=host,
            port=grpc_port if prefer_grpc else port,
            prefer_grpc=prefer_grpc,
            timeout=timeout,
        )

        # 确保集合存在，自动创建
        embedding_dim = _cfg("EMBEDDING.OPENAI.DIMENSIONS", 768)
        # 对于 BGE 模型，维度固定
        if _cfg("EMBEDDING.PROVIDER", "openai") == "bge":
            embedding_dim = 1024  # bge-large-zh-v1.5 维度

        try:
            client.get_collection(collection)
            logger.info("Qdrant collection '%s' already exists", collection)
        except Exception:
            client.create_collection(
                collection_name=collection,
                vectors_config=qmodels.VectorParams(
                    size=embedding_dim,
                    distance=qmodels.Distance.COSINE,
                ),
                # 启用 BM25 稀疏向量用于混合搜索
                sparse_vectors_config={
                    "sparse": qmodels.SparseVectorParams(
                        index=qmodels.SparseIndexConfig(
                            full_scan_threshold=10000,
                        )
                    )
                } if True else None,
            )
            logger.info("Created Qdrant collection '%s' (dim=%d)", collection, embedding_dim)

        return QdrantVectorStore(
            client=client,
            collection_name=collection,
            embedding=embeddings,
        )

    elif provider == "memory":
        from langchain_core.vectorstores import InMemoryVectorStore
        logger.warning("Using in-memory vector store — data will NOT persist!")
        return InMemoryVectorStore(embedding=embeddings)

    else:
        raise ValueError(f"Unsupported vector store provider: {provider}")


# ── 记录管理器工厂 ──────────────────────────────────────────────


def create_record_manager() -> SQLRecordManager:
    """创建 SQLRecordManager，用于追踪已索引文档的变更。

    使用 SQLite 作为后端（与项目现有 SQLite 一致）。
    生产环境可切换至 Postgres：postgresql://user:pass@host/db
    """
    db_url = _cfg("SOURCES.RECORD_DB", "sqlite:///data/rag_index.db")
    # 确保 data 目录存在
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    namespace = _cfg("VECTOR_STORE.QDRANT.COLLECTION", "travel_faq")
    record_manager = SQLRecordManager(
        namespace=f"qdrant/{namespace}",
        db_url=db_url,
    )
    record_manager.create_schema()
    return record_manager


# ── 索引同步 ─────────────────────────────────────────────────────


def sync_faq_to_vector_store(
    faq_path: str | Path | None = None,
    vector_store: VectorStore | None = None,
    embeddings=None,
    force_reindex: bool = False,
) -> dict:
    """执行增量索引同步：检测 FAQ 文件的变更，仅重新索引变化的分块。

    使用 LangChain Indexing API + SQLRecordManager 实现：
        - 新增内容 → 添加
        - 修改内容 → 更新（删除旧版 + 添加新版）
        - 删除内容 → 自动清除（cleanup="incremental" 模式）
        - 未变更 → 跳过（零开销）

    Args:
        faq_path: FAQ 文件路径（默认从配置读取）
        vector_store: 向量存储实例（默认自动创建）
        embeddings: 嵌入模型实例（默认自动创建）
        force_reindex: 强制全量重新索引

    Returns:
        {"num_added": int, "num_updated": int, "num_deleted": int, "num_skipped": int}
    """
    if faq_path is None:
        faq_path = PROJECT_ROOT / _cfg("SOURCES.FAQ_PATH", "order_faq.md")
    faq_path = Path(faq_path)

    if embeddings is None:
        embeddings = create_embeddings()
    if vector_store is None:
        vector_store = create_vector_store(embeddings)

    record_manager = create_record_manager()

    # 分块
    docs = chunk_faq_document(faq_path)

    # 关键 Bug 警告：
    # LangChain Indexing API 的 batch_size 参数有一个已知问题
    # （issue #19335, #22135）：当同一个 source_id 的文档跨越多个批次时，
    # 后续批次由于前一批的"时间戳窗口"问题会被误判为需要删除并重新添加。
    # 解决方案：设置 batch_size >= len(docs) 或将同源文档放在同一批次。
    batch_size = _cfg("SOURCES.INDEX_BATCH_SIZE", 50)
    if batch_size < len(docs):
        logger.warning(
            "batch_size (%d) < docs count (%d): "
            "Indexing API may delete and re-add unchanged docs across batches. "
            "Consider setting INDEX_BATCH_SIZE >= %d",
            batch_size, len(docs), len(docs),
        )

    # 执行增量索引
    result = index(
        docs,
        record_manager,
        vector_store,
        cleanup="incremental" if not force_reindex else "full",
        source_id_key="source",
        batch_size=batch_size if not force_reindex else len(docs) + 1,
    )

    logger.info("Index sync complete: %s", result)
    return result


# ── RAG 检索工具（LangGraph Agent 集成）────────────────────────–


def build_retriever(
    vector_store: VectorStore | None = None,
    embeddings=None,
):
    """构建检索器，可选包装重排序。

    这是 LangGraph Agent 集成的核心入口。

    Args:
        vector_store: 向量存储实例
        embeddings: 嵌入模型实例

    Returns:
        一个可直接作为 agent tool 使用的检索器
    """
    if embeddings is None:
        embeddings = create_embeddings()
    if vector_store is None:
        vector_store = create_vector_store(embeddings)

    # 基础检索器
    top_k = _cfg("RETRIEVAL.TOP_K", 5)
    use_mmr = _cfg("RETRIEVAL.USE_MMR", False)

    if use_mmr:
        base_retriever = vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": top_k,
                "lambda_mult": _cfg("RETRIEVAL.MMR_LAMBDA", 0.5),
            },
        )
    else:
        base_retriever = vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "k": top_k,
                "score_threshold": _cfg("RETRIEVAL.SCORE_THRESHOLD", 0.0),
            },
        )

    # 判断是否需要重排序
    rerank_enabled = _cfg("RERANK.ENABLED", False)
    if rerank_enabled:
        provider = _cfg("RERANK.PROVIDER", "cohere")
        top_n = _cfg("RERANK.TOP_N", 5)

        if provider == "cohere":
            from langchain_cohere import CohereRerank
            compressor = CohereRerank(
                model=_cfg("RERANK.COHERE.MODEL", "rerank-multilingual-v3.0"),
                top_n=top_n,
            )
        elif provider == "bge_cross_encoder":
            from langchain.retrievers.document_compressors import CrossEncoderReranker
            from langchain_community.cross_encoders import HuggingFaceCrossEncoder

            compressor = CrossEncoderReranker(
                model=HuggingFaceCrossEncoder(
                    model_name=_cfg("RERANK.BGE.MODEL", "BAAI/bge-reranker-v2-m3"),
                ),
                top_n=top_n,
            )
        else:
            raise ValueError(f"Unsupported rerank provider: {provider}")

        from langchain.retrievers import ContextualCompressionRetriever
        retriever = ContextualCompressionRetriever(
            base_compressor=compressor,
            base_retriever=base_retriever,
        )
        logger.info("Reranker enabled: %s (top_k=%d → top_n=%d)", provider, top_k, top_n)
    else:
        retriever = base_retriever

    return retriever


def get_retriever_tool(
    faq_path: str | Path | None = None,
    auto_sync: bool = True,
):
    """获取与现有 lookup_policy 兼容的 @tool 函数。

    这是替换旧 retriever_vector.py 中 lookup_policy 的直接入口。
    用法：
        from tools.retriever_engine import get_retriever_tool
        lookup_policy = get_retriever_tool()

    Args:
        faq_path: FAQ 文件路径
        auto_sync: 是否在首次加载时自动同步索引

    Returns:
        @tool 装饰的 lookup_policy 函数
    """
    embeddings = create_embeddings()
    vector_store = create_vector_store(embeddings)

    # 首次启动时自动同步索引
    if auto_sync:
        try:
            sync_faq_to_vector_store(
                faq_path=faq_path,
                vector_store=vector_store,
                embeddings=embeddings,
            )
        except Exception as e:
            logger.warning("Auto-sync failed (first run?): %s", e)
            logger.warning("Attempting forced re-index...")
            sync_faq_to_vector_store(
                faq_path=faq_path,
                vector_store=vector_store,
                embeddings=embeddings,
                force_reindex=True,
            )

    retriever = build_retriever(vector_store=vector_store, embeddings=embeddings)

    @tool
    def lookup_policy(query: str) -> str:
        """查询航空公司和旅行相关政策。
        在回答用户关于预订、取消、改签、支付、发票、行李等问题之前，使用此函数检索相关上下文。
        """
        docs = retriever.invoke(query)
        if not docs:
            return "未找到相关政策信息。"

        # 带章节来源的格式化输出
        results = []
        for i, doc in enumerate(docs, 1):
            section = doc.metadata.get("section", "通用")
            content = doc.page_content.strip()
            score = getattr(doc, "score", None)
            score_str = f" [相关度: {score:.3f}]" if score is not None else ""
            results.append(f"[来源: {section}]{score_str}\n{content}")

        return "\n\n---\n\n".join(results)

    return lookup_policy


# ── 命令行入口 ───────────────────────────────────────────────────


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "sync":
        # 手动触发索引同步
        print("正在同步 FAQ 到向量存储...")
        result = sync_faq_to_vector_store(force_reindex="--force" in sys.argv)
        print(f"同步完成: {result}")

    elif len(sys.argv) > 1 and sys.argv[1] == "query":
        # 测试查询
        query = sys.argv[2] if len(sys.argv) > 2 else "怎么退票？"
        tool_fn = get_retriever_tool(auto_sync=False)
        print(f"查询: {query}")
        print(tool_fn(query))

    else:
        # 默认行为：测试启动
        print("初始化 RAG 引擎...")
        tool_fn = get_retriever_tool()
        print("\n引擎就绪。测试查询 '怎么退票？':")
        print(tool_fn("怎么退票？"))
