#!/usr/bin/env python3
"""
Docling PDF -> Markdown test script.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from umamusume_rag.pdf_processors import DoclingProcessor


def _pick_default_pdf() -> Path:
    return Path("resources/test_docs/test0.pdf")


def _default_output_path(pdf_path: Path) -> Path:
    return pdf_path.parent / f"{pdf_path.stem}.docling.md"


def _resolve_output(
    output: str | None, pdf_path: Path
) -> tuple[str | None, str | None]:
    if not output:
        return None, None
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return str(output_path.parent), output_path.name


def main() -> int:
    parser = argparse.ArgumentParser(description="Docling PDF -> Markdown")
    parser.add_argument("--pdf", type=str, default=None, help="PDF file path")
    parser.add_argument("--output", type=str, default=None, help="Output MD path")
    parser.add_argument("--use-ocr", action="store_true", help="Enable OCR")
    parser.add_argument(
        "--artifacts-path",
        type=str,
        default=None,
        help="Docling artifacts path",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf) if args.pdf else _pick_default_pdf()
    processor = DoclingProcessor(
        artifacts_path=args.artifacts_path, use_ocr=args.use_ocr
    )
    output_path = Path(args.output) if args.output else _default_output_path(pdf_path)
    output_dir, output_filename = _resolve_output(str(output_path), pdf_path)

    result = processor.process_pdf_to_markdown(
        str(pdf_path),
        output_dir=output_dir,
        output_filename=output_filename,
        use_ocr=args.use_ocr,
        artifacts_path=args.artifacts_path,
    )
    if not result:
        print("Conversion failed.")
        return 1
    print(f"Output: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
