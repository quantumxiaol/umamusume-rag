#!/usr/bin/env python3
"""
模型下载工具。
"""

from __future__ import annotations

import argparse
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
        "--skip-embedding",
        action="store_true",
        help="跳过 Embedding 模型下载",
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
    args = parser.parse_args()

    only_specified = args.mineru or args.qwen_vl or args.embedding or args.all
    run_mineru = (args.mineru or not only_specified) and not args.skip_mineru
    run_qwen_vl = (args.qwen_vl or not only_specified) and not args.skip_qwen_vl
    run_embedding = (args.embedding or not only_specified) and not args.skip_embedding

    if args.all:
        run_mineru = not args.skip_mineru
        run_qwen_vl = not args.skip_qwen_vl
        run_embedding = not args.skip_embedding

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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
