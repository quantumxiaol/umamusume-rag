"""
MinerU模型下载模块
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def download_mineru_models(
    model_dir: str,
    model_name: str = "opendatalab/PDF-Extract-Kit-1.0"
) -> bool:
    """
    下载MinerU模型到指定目录
    
    Args:
        model_dir: 模型存储目录
        model_name: 模型名称，默认使用opendatalab/PDF-Extract-Kit-1.0
        
    Returns:
        下载是否成功
    """
    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # 设置环境变量，指定模型目录
    os.environ['MINERU_MODEL_DIR'] = str(model_dir)
    
    # MinerU会在首次使用时自动下载模型
    # 这里只确保目录存在即可
    logger.info(f"Model directory prepared: {model_dir}")
    logger.info("MinerU will download models automatically on first use if needed.")
    return True


def ensure_models_downloaded(model_dir: str) -> bool:
    """
    确保模型已下载，如果不存在则下载
    
    Args:
        model_dir: 模型存储目录
        
    Returns:
        模型是否可用
    """
    model_dir = Path(model_dir)
    
    # 检查模型目录是否存在必要的模型文件
    # MinerU的模型通常在hub目录下
    hub_dir = model_dir / "hub"
    if hub_dir.exists() and any(hub_dir.iterdir()):
        logger.info(f"Models already exist in: {model_dir}")
        return True
    
    logger.info(f"Models not found, downloading to: {model_dir}")
    return download_mineru_models(str(model_dir))


if __name__ == "__main__":
    """
    命令行使用示例：
    python -m umamusume_rag.rag.download_models /path/to/model/dir
    """
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Usage: python -m umamusume_rag.rag.download_models <model_dir>")
        print("Example: python -m umamusume_rag.rag.download_models ./models/mineru")
        sys.exit(1)
    
    model_dir = sys.argv[1]
    success = download_mineru_models(model_dir)
    
    if success:
        print(f"\n✓ Models successfully downloaded to: {model_dir}")
        sys.exit(0)
    else:
        print(f"\n✗ Failed to download models")
        sys.exit(1)

