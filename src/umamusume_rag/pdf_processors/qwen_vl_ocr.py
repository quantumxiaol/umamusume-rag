"""
Qwen2.5-VL OCR tool for image-to-Markdown conversion.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import torch
from PIL import Image
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
from qwen_vl_utils import process_vision_info

from ..config import config

DEFAULT_OCR_PROMPT = (
    "你是一个专业的文档数字化专家。请将这张图片中的内容转录为高质量的 Markdown 文本。\n"
    "\n"
    "### 核心要求\n"
    "1. **阅读顺序 (关键)**：\n"
    "   - 请严格按照人类阅读逻辑处理版面。\n"
    "   - 对于多栏排版（如杂志、论文），请**先读左栏，再读右栏**，将它们合并为连续的段落流。\n"
    "   - **绝对禁止**将多栏正文识别为 Markdown 表格（即不要使用 |---| 语法），除非它真的是一张数据统计表。\n"
    "\n"
    "2. **内容清洗**：\n"
    "   - **忽略页眉页脚**：不要输出页码、页眉装饰线或无关的版面标记。\n"
    "   - **拼接断词**：如果行尾有连字符（Hyphenation）将单词切断（如 'con- nection'），请还原为完整单词（'connection'）。\n"
    "   - **修正OCR错误**：基于上下文自动修正明显的拼写错误（如将 'Umanusume' 修正为 'Umamusume'），但不要篡改人名或专有名词。\n"
    "\n"
    "3. **格式规范**：\n"
    "   - 标题：准确识别标题层级（使用 #, ##, ###）。\n"
    "   - 表格：只有当遇到真正的结构化数据表时，才使用 Markdown 表格语法。\n"
    "   - 图片：如果遇到图片，请用 `![图片描述](image_placeholder)` 占位，不要试图转录图片里的装饰性文字。\n"
    "   - 公式：如果是数学公式，请使用 LaTeX 格式（$ 或 $$ 包裹）。\n"
    "\n"
    "### 输出格式\n"
    "直接输出 Markdown 内容，不需要包含 '好的'、'这是结果' 等任何开场白或结束语。"
)
class QwenOCR:
    DEFAULT_MAX_IMAGE_SIDE = 1280

    def __init__(
        self,
        model_dir: Optional[str] = None,
        device: Optional[str] = None,
        dtype: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        self.model_dir = Path(model_dir or config.QWEN_VL_MODEL_DIR)
        self.device = device or config.QWEN_VL_DEVICE
        self.dtype = dtype or config.QWEN_VL_DTYPE
        self.max_tokens = max_tokens or config.QWEN_VL_MAX_TOKENS
        self._model = None
        self._processor = None

    def _resolve_dtype(self) -> Optional[torch.dtype]:
        if not self.dtype or self.dtype == "auto":
            return None
        mapping = {
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
            "float32": torch.float32,
        }
        return mapping.get(self.dtype, None)

    def _load(self) -> None:
        if self._model is not None and self._processor is not None:
            return

        if not self.model_dir.exists():
            raise FileNotFoundError(
                f"Qwen2.5-VL 模型目录不存在: {self.model_dir}"
            )

        self._processor = AutoProcessor.from_pretrained(
            self.model_dir, trust_remote_code=True
        )
        torch_dtype = self._resolve_dtype()
        # Load on CPU first; avoid device_map="auto" to prevent MPS warmup crashes.
        self._model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            self.model_dir,
            torch_dtype=torch_dtype,
            trust_remote_code=True,
            device_map=None,
            low_cpu_mem_usage=False,
        )

        target_device = self.device
        if target_device in ("auto", "", None):
            if torch.backends.mps.is_available():
                target_device = "mps"
            elif torch.cuda.is_available():
                target_device = "cuda"
            else:
                target_device = "cpu"

        if target_device:
            self._model.to(target_device)

    def image_to_markdown(
        self, image_path: str | Image.Image, prompt: Optional[str] = None
    ) -> str:
        self._load()
        assert self._processor is not None
        assert self._model is not None

        if isinstance(image_path, Image.Image):
            image = image_path.convert("RGB")
        else:
            image = Image.open(image_path).convert("RGB")

        max_side = self.DEFAULT_MAX_IMAGE_SIDE
        if max(image.size) > max_side:
            scale = max_side / max(image.size)
            new_size = (int(image.width * scale), int(image.height * scale))
            image = image.resize(new_size, Image.LANCZOS)
        user_prompt = prompt or DEFAULT_OCR_PROMPT

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": user_prompt},
                ],
            }
        ]

        text = self._processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self._processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        inputs = inputs.to(self._model.device)
        generated = self._model.generate(**inputs, max_new_tokens=self.max_tokens)
        generated_ids = generated[:, inputs["input_ids"].shape[-1] :]
        output = self._processor.batch_decode(
            generated_ids, skip_special_tokens=True
        )
        return output[0].strip() if output else ""


class QwenVLProcessor:
    def __init__(
        self,
        model_dir: Optional[str] = None,
        device: Optional[str] = None,
        dtype: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        self.ocr = QwenOCR(
            model_dir=model_dir,
            device=device,
            dtype=dtype,
            max_tokens=max_tokens,
        )

    def process_pdf_to_markdown(
        self,
        pdf_path: str,
        output_dir: Optional[str] = None,
        output_filename: Optional[str] = None,
        max_pages: Optional[int] = None,
        dpi: int = 200,
        prompt: Optional[str] = None,
        parse_method: str = "auto",
        **kwargs,
    ) -> Optional[str]:
        try:
            import fitz  # PyMuPDF
        except ImportError as exc:
            raise ImportError(
                "pymupdf 未安装，请先安装 pymupdf 依赖。"
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

        doc = fitz.open(str(pdf_path_obj))
        page_count = doc.page_count
        limit = min(page_count, max_pages) if max_pages else page_count

        parts = []
        for page_index in range(limit):
            page = doc.load_page(page_index)
            matrix = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=matrix)
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            text = self.ocr.image_to_markdown(image, prompt=prompt)
            if not text:
                continue
            parts.append(f"## Page {page_index + 1}\n\n{text}")

        doc.close()

        if not parts:
            return None

        final_md_path.write_text("\n\n".join(parts), encoding="utf-8")
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
