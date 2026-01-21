"""
MarkItDown processor for PDF-to-Markdown conversion.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class MarkItDownProcessor:
    def process_pdf_to_markdown(
        self,
        pdf_path: str,
        output_dir: Optional[str] = None,
        output_filename: Optional[str] = None,
        **kwargs,
    ) -> Optional[str]:
        try:
            from markitdown import MarkItDown
        except ImportError as exc:
            raise ImportError(
                "markitdown 未安装，请先安装 markitdown 依赖。"
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

        converter = MarkItDown()
        result = converter.convert(str(pdf_path_obj))
        content = getattr(result, "text_content", None)
        if content is None:
            content = str(result)

        final_md_path.write_text(content, encoding="utf-8")
        return str(final_md_path)

    def ensure_pdf_converted(self, pdf_path: str) -> Optional[str]:
        pdf_path_obj = Path(pdf_path)
        md_path = pdf_path_obj.parent / (pdf_path_obj.stem + ".md")
        if md_path.exists():
            try:
                content = md_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                content = ""
            if content.strip():
                return str(md_path)
        return self.process_pdf_to_markdown(str(pdf_path_obj))
