"""
PDF processors for different scenarios.
"""

from __future__ import annotations

from typing import Optional

from ..config import config

__all__ = [
    "PDFProcessor",
    "DoclingProcessor",
    "MarkItDownProcessor",
    "QwenOCR",
    "QwenVLProcessor",
    "get_pdf_processor",
    "get_mineru_processor",
]


def get_pdf_processor(engine: Optional[str] = None, **kwargs):
    engine = (engine or config.PDF_PROCESSOR_ENGINE).strip().lower()
    if engine in ("", "none", "off", "disabled", "false"):
        return None
    if engine == "mineru":
        from .mineru_processor import get_pdf_processor as get_mineru_processor

        return get_mineru_processor(**kwargs)
    if engine == "markitdown":
        from .markitdown_processor import MarkItDownProcessor

        return MarkItDownProcessor()
    if engine == "docling":
        from .docling_processor import DoclingProcessor

        return DoclingProcessor()
    if engine in ("qwen-vl", "qwen_vl"):
        from .qwen_vl_ocr import QwenVLProcessor

        return QwenVLProcessor()
    raise ValueError(f"Unsupported PDF processor engine: {engine}")


def __getattr__(name: str):
    if name == "PDFProcessor":
        from .mineru_processor import PDFProcessor

        return PDFProcessor
    if name == "get_mineru_processor":
        from .mineru_processor import get_pdf_processor as get_mineru_processor

        return get_mineru_processor
    if name == "MarkItDownProcessor":
        from .markitdown_processor import MarkItDownProcessor

        return MarkItDownProcessor
    if name == "DoclingProcessor":
        from .docling_processor import DoclingProcessor

        return DoclingProcessor
    if name == "QwenOCR":
        from .qwen_vl_ocr import QwenOCR

        return QwenOCR
    if name == "QwenVLProcessor":
        from .qwen_vl_ocr import QwenVLProcessor

        return QwenVLProcessor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
