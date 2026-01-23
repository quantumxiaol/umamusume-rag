"""
Docling processor for PDF-to-Markdown conversion.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def _maybe_set_attr(obj: object, name: str, value: object) -> None:
    if hasattr(obj, name):
        try:
            setattr(obj, name, value)
        except Exception:
            pass


def _enable_docling_ocr(pipeline_options: object) -> None:
    for attr_name in ("do_ocr", "use_ocr", "ocr", "enable_ocr", "ocr_enabled"):
        _maybe_set_attr(pipeline_options, attr_name, True)

    ocr_options = getattr(pipeline_options, "ocr_options", None)
    if ocr_options is None:
        try:
            from docling.datamodel.pipeline_options import OcrOptions

            ocr_options = OcrOptions()
            _maybe_set_attr(pipeline_options, "ocr_options", ocr_options)
        except Exception:
            ocr_options = None

    if ocr_options is not None:
        for attr_name in ("enabled", "use_ocr", "do_ocr"):
            _maybe_set_attr(ocr_options, attr_name, True)


def _build_pdf_pipeline_options(
    pdf_options_cls: type,
    *,
    artifacts_path: str | None,
    use_ocr: bool,
) -> object:
    kwargs: dict[str, object] = {}
    if artifacts_path:
        kwargs["artifacts_path"] = artifacts_path
    if use_ocr:
        kwargs["do_ocr"] = True

    try:
        pipeline_options = pdf_options_cls(**kwargs)
    except TypeError:
        pipeline_options = pdf_options_cls()
        if artifacts_path:
            _maybe_set_attr(pipeline_options, "artifacts_path", artifacts_path)
        if use_ocr:
            _enable_docling_ocr(pipeline_options)
    else:
        if use_ocr:
            _enable_docling_ocr(pipeline_options)

    return pipeline_options


class DoclingProcessor:
    def __init__(
        self, artifacts_path: Optional[str] = None, use_ocr: bool = False
    ) -> None:
        self.artifacts_path = (
            artifacts_path
            if artifacts_path is not None
            else os.getenv("DOCLING_ARTIFACTS_PATH", "")
        )
        self.use_ocr = use_ocr

    def process_pdf_to_markdown(
        self,
        pdf_path: str,
        output_dir: Optional[str] = None,
        output_filename: Optional[str] = None,
        *,
        use_ocr: Optional[bool] = None,
        artifacts_path: Optional[str] = None,
        **kwargs,
    ) -> Optional[str]:
        try:
            from docling.document_converter import DocumentConverter
        except ImportError as exc:
            raise ImportError(
                "docling is not installed. Try: pip install docling"
            ) from exc

        pdf_path_obj = Path(pdf_path)
        if not pdf_path_obj.exists():
            return None

        if output_dir is None:
            final_output_dir = pdf_path_obj.parent
        else:
            final_output_dir = Path(output_dir)
            final_output_dir.mkdir(parents=True, exist_ok=True)

        if output_filename is None:
            output_filename = pdf_path_obj.stem + ".md"

        final_md_path = final_output_dir / output_filename

        use_ocr = self.use_ocr if use_ocr is None else use_ocr
        artifacts_path = (
            self.artifacts_path if artifacts_path is None else artifacts_path
        )

        converter = None
        if pdf_path_obj.suffix.lower() == ".pdf" and (artifacts_path or use_ocr):
            if artifacts_path:
                artifacts_root = Path(artifacts_path)
                if not artifacts_root.exists():
                    raise FileNotFoundError(
                        "Docling artifacts path does not exist. Set "
                        f"DOCLING_ARTIFACTS_PATH to a valid directory "
                        f"(current: {artifacts_root})."
                    )
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import PdfFormatOption

            pipeline_options = _build_pdf_pipeline_options(
                PdfPipelineOptions,
                artifacts_path=artifacts_path or None,
                use_ocr=use_ocr,
            )
            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options
                    )
                }
            )

        if converter is None:
            converter = DocumentConverter()

        result = converter.convert(str(pdf_path_obj))
        try:
            content = result.document.export_to_markdown()
        except Exception:
            content = str(result)

        final_md_path.write_text(content, encoding="utf-8")
        return str(final_md_path)
