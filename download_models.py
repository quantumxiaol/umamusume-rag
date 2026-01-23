#!/usr/bin/env python3
"""
模型下载工具。
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from umamusume_rag.config import config
from umamusume_rag.rag.download_models import ensure_models_downloaded

# Import after config so HF_HOME/HUGGINGFACE_HUB_CACHE are set first.
from huggingface_hub import snapshot_download


def _default_hf_cache_dir() -> str:
    if config.HUGGINGFACE_HUB_CACHE:
        return config.HUGGINGFACE_HUB_CACHE
    if config.HF_HOME:
        return str(Path(config.HF_HOME) / "hub")
    return ""

PROJECT_ROOT = Path(__file__).resolve().parent


def _resolve_project_path(value: str) -> str:
    if not value:
        return ""
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str((PROJECT_ROOT / value.lstrip("./")).resolve())


def _default_docling_dir() -> str:
    return _resolve_project_path(
        os.getenv("DOCLING_ARTIFACTS_PATH", "./models/DocLing")
    )


def download_mineru(model_dir: str) -> None:
    ensure_models_downloaded(model_dir)


def download_qwen_vl(model_dir: str, repo_id: str) -> None:
    target_dir = Path(model_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=repo_id,
        local_dir=str(target_dir),
        local_dir_use_symlinks=False,
    )

def download_embedding(repo_id: str, local_dir: str | None = None) -> None:
    if Path(repo_id).exists():
        print(f"ℹ️  Embedding 模型路径已存在，跳过下载: {repo_id}")
        return
    kwargs = {}
    if local_dir:
        target_dir = Path(local_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        kwargs["local_dir"] = str(target_dir)
        kwargs["local_dir_use_symlinks"] = False
    else:
        cache_dir = _default_hf_cache_dir()
        if cache_dir:
            kwargs["cache_dir"] = cache_dir
    snapshot_download(repo_id=repo_id, **kwargs)


def download_docling(output_dir: str, force: bool, progress: bool) -> None:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        from docling.utils.model_downloader import download_models
    except ImportError as exc:
        raise SystemExit(
            "docling is not installed. Try: pip install docling"
        ) from exc

    download_models(
        output_dir=target_dir,
        force=force,
        progress=progress,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Download model weights")
    parser.add_argument(
        "--all",
        action="store_true",
        help="下载所有模型",
    )
    parser.add_argument(
        "--mineru",
        action="store_true",
        help="下载 MinerU 相关模型",
    )
    parser.add_argument(
        "--qwen-vl",
        action="store_true",
        help="下载 Qwen2.5-VL 权重",
    )
    parser.add_argument(
        "--skip-mineru",
        action="store_true",
        help="跳过 MinerU 模型下载",
    )
    parser.add_argument(
        "--skip-qwen-vl",
        action="store_true",
        help="跳过 Qwen2.5-VL 模型下载",
    )
    parser.add_argument(
        "--embedding",
        action="store_true",
        help="下载 Embedding 模型",
    )
    parser.add_argument(
        "--docling",
        action="store_true",
        help="下载 Docling 模型",
    )
    parser.add_argument(
        "--skip-embedding",
        action="store_true",
        help="跳过 Embedding 模型下载",
    )
    parser.add_argument(
        "--skip-docling",
        action="store_true",
        help="跳过 Docling 模型下载",
    )
    parser.add_argument(
        "--mineru-dir",
        type=str,
        default=config.MINERU_MODEL_DIR,
        help="MinerU 模型目录",
    )
    parser.add_argument(
        "--qwen-vl-dir",
        type=str,
        default=config.QWEN_VL_MODEL_DIR,
        help="Qwen2.5-VL 模型目录",
    )
    parser.add_argument(
        "--qwen-vl-repo",
        type=str,
        default=config.QWEN_VL_REPO_ID,
        help="Qwen2.5-VL HuggingFace 仓库 ID",
    )
    parser.add_argument(
        "--embedding-repo",
        type=str,
        default=config.HF_Embedding_Model,
        help="Embedding HuggingFace 仓库 ID",
    )
    parser.add_argument(
        "--embedding-dir",
        type=str,
        default="",
        help="Embedding 本地存储目录（为空则使用 HuggingFace 默认缓存）",
    )
    parser.add_argument(
        "--docling-dir",
        type=str,
        default=_default_docling_dir(),
        help="Docling 模型目录",
    )
    parser.add_argument(
        "--docling-force",
        action="store_true",
        help="强制重新下载 Docling 模型",
    )
    parser.add_argument(
        "--docling-progress",
        action="store_true",
        help="显示 Docling 下载进度",
    )
    args = parser.parse_args()

    only_specified = (
        args.mineru or args.qwen_vl or args.embedding or args.docling or args.all
    )
    run_mineru = (args.mineru or not only_specified) and not args.skip_mineru
    run_qwen_vl = (args.qwen_vl or not only_specified) and not args.skip_qwen_vl
    run_embedding = (args.embedding or not only_specified) and not args.skip_embedding
    run_docling = (args.docling or not only_specified) and not args.skip_docling

    if args.all:
        run_mineru = not args.skip_mineru
        run_qwen_vl = not args.skip_qwen_vl
        run_embedding = not args.skip_embedding
        run_docling = not args.skip_docling

    if run_mineru:
        print(f"📦 下载 MinerU 模型到: {args.mineru_dir}")
        download_mineru(args.mineru_dir)

    if run_qwen_vl:
        print(f"📦 下载 Qwen2.5-VL 模型到: {args.qwen_vl_dir}")
        download_qwen_vl(args.qwen_vl_dir, args.qwen_vl_repo)

    if run_embedding:
        if args.embedding_dir:
            print(f"📦 下载 Embedding 模型到: {args.embedding_dir}")
        else:
            cache_dir = _default_hf_cache_dir()
            if cache_dir:
                print(f"📦 下载 Embedding 模型到: {cache_dir}")
            else:
                print("📦 下载 Embedding 模型到: HuggingFace 默认缓存")
        download_embedding(args.embedding_repo, args.embedding_dir or None)

    if run_docling:
        print(f"📦 下载 Docling 模型到: {args.docling_dir}")
        download_docling(
            output_dir=args.docling_dir,
            force=args.docling_force,
            progress=args.docling_progress,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
