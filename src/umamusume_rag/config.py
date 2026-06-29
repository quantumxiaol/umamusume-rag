from __future__ import annotations

from pathlib import Path
import os

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")


def _resolve_optional_path(value: str) -> str:
    if not value:
        return ""
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str((PROJECT_ROOT / value.lstrip("./")).resolve())


class Config:
    """
    配置类：集中管理所有环境变量
    """

    # ================== LLM Settings ==================
    # Info LLM (用于信息查询)
    INFO_LLM_MODEL_NAME: str = os.getenv("INFO_LLM_MODEL_NAME", "qwen-max-latest")
    INFO_LLM_MODEL_BASE_URL: str = os.getenv("INFO_LLM_MODEL_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    INFO_LLM_MODEL_API_KEY: str = os.getenv("INFO_LLM_MODEL_API_KEY", "")

    # ================== RAG Settings ==================
    HF_EMBEDDING_MODEL: str = os.getenv("HF_EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-0.6B")
    HF_Embedding_Model: str = HF_EMBEDDING_MODEL  # Backward-compatible alias.
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "2000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    
    # Embedding设备：cpu, cuda, mps
    EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "cpu")

    # ================== HuggingFace Cache ==================
    HF_HOME: str = _resolve_optional_path(os.getenv("HF_HOME", ""))
    HUGGINGFACE_HUB_CACHE: str = _resolve_optional_path(
        os.getenv("HUGGINGFACE_HUB_CACHE", "")
    )

    # 注意：RAG_DIRECTORY 是相对路径，需转为绝对路径
    _rag_dir = os.getenv("RAG_DIRECTORY", "./resources/docs")
    RAG_DIRECTORY: str = str((PROJECT_ROOT / _rag_dir.lstrip("./")).resolve())
    
    # ================== MinerU Settings ==================
    # MinerU模型目录
    _mineru_model_dir = os.getenv("MINERU_MODEL_DIR", "./models/hub")
    MINERU_MODEL_DIR: str = str(
        (PROJECT_ROOT / _mineru_model_dir.lstrip("./")).resolve()
    )

    # PDF处理引擎（none/markitdown/mineru/docling/qwen-vl）
    PDF_PROCESSOR_ENGINE: str = os.getenv("PDF_PROCESSOR_ENGINE", "none")
    
    # 是否自动将PDF转换为Markdown
    AUTO_CONVERT_PDF_TO_MD: bool = os.getenv("AUTO_CONVERT_PDF_TO_MD", "false").lower() == "true"
    
    # 是否优先使用Markdown文件（如果存在对应的MD文件，跳过PDF）
    PREFER_MARKDOWN_FILES: bool = os.getenv("PREFER_MARKDOWN_FILES", "true").lower() == "true"

    # ================== Qwen VL OCR Settings ==================
    _qwen_vl_model_dir = os.getenv(
        "QWEN_VL_MODEL_DIR", "./models/Qwen2.5-VL-7B-Instruct"
    )
    QWEN_VL_MODEL_DIR: str = str(
        (PROJECT_ROOT / _qwen_vl_model_dir.lstrip("./")).resolve()
    )
    QWEN_VL_REPO_ID: str = os.getenv(
        "QWEN_VL_REPO_ID", "Qwen/Qwen2.5-VL-7B-Instruct"
    )
    QWEN_VL_DEVICE: str = os.getenv("QWEN_VL_DEVICE", "auto")
    QWEN_VL_DTYPE: str = os.getenv("QWEN_VL_DTYPE", "auto")
    QWEN_VL_MAX_TOKENS: int = int(os.getenv("QWEN_VL_MAX_TOKENS", "2048"))

    @classmethod
    def validate_llm(cls):
        """
        验证LLM问答所需配置是否已设置。
        """
        missing = []
        if not cls.INFO_LLM_MODEL_API_KEY:
            missing.append("INFO_LLM_MODEL_API_KEY")
        if missing:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")

    @classmethod
    def validate(cls):
        """
        Backward-compatible alias for LLM validation.
        """
        cls.validate_llm()

# 创建一个全局实例，方便导入
config = Config()

if config.HF_HOME:
    os.environ["HF_HOME"] = config.HF_HOME
if config.HUGGINGFACE_HUB_CACHE:
    os.environ["HUGGINGFACE_HUB_CACHE"] = config.HUGGINGFACE_HUB_CACHE
