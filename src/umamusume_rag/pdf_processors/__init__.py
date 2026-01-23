"""
PDF processors for different scenarios.
"""

from __future__ import annotations

from typing import Optional

from ..config import config
from .docling_processor import DoclingProcessor
from .mineru_processor import PDFProcessor, get_pdf_processor as get_mineru_processor
from .markitdown_processor import MarkItDownProcessor
from .qwen_vl_ocr import QwenOCR, QwenVLProcessor

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
    engine = (engine or config.PDF_PROCESSOR_ENGINE).lower()
    if engine == "mineru":
        return get_mineru_processor(**kwargs)
    if engine == "markitdown":
        return MarkItDownProcessor()
    if engine == "docling":
        return DoclingProcessor()
    if engine in ("qwen-vl", "qwen_vl"):
        return QwenVLProcessor()
    raise ValueError(f"Unsupported PDF processor engine: {engine}")
