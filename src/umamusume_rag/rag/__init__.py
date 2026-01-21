"""
RAG模块：提供文档检索和向量数据库功能
"""

from .rag import (
    RAGManager,
    rag_manager,
    initialize_rag,
    search,
    search_with_scores,
)

# 导出PDF处理相关功能
try:
    from ..pdf_processors import PDFProcessor, get_pdf_processor
    from .download_models import download_mineru_models, ensure_models_downloaded
    
    __all__ = [
        "RAGManager",
        "rag_manager",
        "initialize_rag",
        "search",
        "search_with_scores",
        "PDFProcessor",
        "get_pdf_processor",
        "download_mineru_models",
        "ensure_models_downloaded",
    ]
except ImportError:
    __all__ = [
        "RAGManager",
        "rag_manager",
        "initialize_rag",
        "search",
        "search_with_scores",
    ]


