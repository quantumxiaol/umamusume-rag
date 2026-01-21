#!/usr/bin/env python3
"""
Qwen2.5-VL PDF -> Markdown 测试脚本
"""

from __future__ import annotations

import argparse
from pathlib import Path

from umamusume_rag.config import config
from umamusume_rag.pdf_processors import QwenVLProcessor


def _pick_default_pdf() -> Path:
    return Path("resources/test_docs/test0.pdf")


def _default_output_path(pdf_path: Path) -> Path:
    return pdf_path.parent / f"{pdf_path.stem}.qwenvl.md"


def _resolve_output(output: str | None, pdf_path: Path) -> tuple[str | None, str | None]:
    if not output:
        return None, None
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return str(output_path.parent), output_path.name


def main() -> int:
    parser = argparse.ArgumentParser(description="Qwen2.5-VL PDF -> Markdown")
    parser.add_argument("--pdf", type=str, default=None, help="PDF文件路径")
    parser.add_argument("--output", type=str, default=None, help="输出Markdown路径")
    parser.add_argument("--max-pages", type=int, default=3, help="最多处理页数")
    parser.add_argument("--dpi", type=int, default=200, help="渲染分辨率")
    parser.add_argument("--prompt", type=str, default=None, help="自定义OCR提示词")
    args = parser.parse_args()

    pdf_path = Path(args.pdf) if args.pdf else _pick_default_pdf()
    processor = QwenVLProcessor(
        model_dir=config.QWEN_VL_MODEL_DIR,
        device=config.QWEN_VL_DEVICE,
        dtype=config.QWEN_VL_DTYPE,
        max_tokens=config.QWEN_VL_MAX_TOKENS,
    )
    output_path = Path(args.output) if args.output else _default_output_path(pdf_path)
    output_dir, output_filename = _resolve_output(str(output_path), pdf_path)

    result = processor.process_pdf_to_markdown(
        str(pdf_path),
        output_dir=output_dir,
        output_filename=output_filename,
        max_pages=args.max_pages,
        dpi=args.dpi,
        prompt=args.prompt,
    )
    if not result:
        print("❌ 转换失败")
        return 1
    print(f"✅ 输出: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
