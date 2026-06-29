import os
import pickle
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging

# Load config early so HF cache env vars are set before importing HF-based libs.
from ..config import config

# Langchain imports
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import (
    CSVLoader, 
    TextLoader, 
    DirectoryLoader
)
from langchain_core.documents import Document

from ..pdf_processors import get_pdf_processor
from .download_models import ensure_models_downloaded

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
_DISABLED_PDF_ENGINES = {"", "none", "off", "disabled", "false"}


class RAGManager:
    """
    通用RAG管理器
    支持多种文档格式：PDF、Markdown、CSV、TXT
    支持多种PDF处理引擎：none、MinerU、MarkItDown、Docling、Qwen-VL
    """
    
    def __init__(self, rag_directory: Optional[str] = None, pdf_processor_engine: Optional[str] = None):
        """
        初始化RAG管理器
        
        Args:
            rag_directory: RAG文档目录路径，如果不指定则从配置读取
        """
        # 从环境变量或参数读取配置
        rag_dir = rag_directory or config.RAG_DIRECTORY
        if not os.path.exists(rag_dir):
            logger.warning(f"RAG directory not found: {rag_dir}, creating it...")
            os.makedirs(rag_dir, exist_ok=True)
        
        self.rag_directory = Path(rag_dir)
        # 缓存文件放在 resources/vector/ 目录下
        vector_dir = self.rag_directory.parent / 'vector'
        vector_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = vector_dir / 'vectorstore_cache.pkl'
        self.vectorstore = None
        self.config = self._load_config()
        
        self.pdf_processor_engine = (
            pdf_processor_engine
            if pdf_processor_engine is not None
            else config.PDF_PROCESSOR_ENGINE
        ).strip().lower()
        self.pdf_processor = None
        self._initialize_pdf_processor()

        logger.info(f"RAG Manager initialized with directory: {self.rag_directory}")
        if self.pdf_processor:
            logger.info(
                "PDF processing: using %s for PDF to Markdown conversion",
                self.pdf_processor_engine,
            )
        elif self._pdf_processing_disabled():
            logger.info("PDF processing: disabled")
        else:
            logger.info(
                "PDF processing: unavailable for engine=%s",
                self.pdf_processor_engine,
            )
        
    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        return {
            'chunk_size': int(os.getenv('CHUNK_SIZE', '500')),
            'chunk_overlap': int(os.getenv('CHUNK_OVERLAP', '100')),
            'hf_embedding_model': os.getenv('HF_EMBEDDING_MODEL', 'Qwen/Qwen3-Embedding-0.6B'),
            'device': os.getenv('EMBEDDING_DEVICE', 'cpu')
        }

    def _pdf_processing_disabled(self) -> bool:
        return self.pdf_processor_engine in _DISABLED_PDF_ENGINES

    def _initialize_pdf_processor(self) -> None:
        if self.pdf_processor or self._pdf_processing_disabled():
            return

        try:
            if self.pdf_processor_engine == "mineru":
                ensure_models_downloaded(config.MINERU_MODEL_DIR)
            self.pdf_processor = get_pdf_processor(
                engine=self.pdf_processor_engine,
                model_dir=config.MINERU_MODEL_DIR,
            )
            if self.pdf_processor:
                logger.info(
                    "PDF processor initialized (engine=%s, model_dir=%s)",
                    self.pdf_processor_engine,
                    config.MINERU_MODEL_DIR,
                )
        except Exception as e:
            logger.warning(f"Failed to initialize PDF processor: {e}", exc_info=True)
            self.pdf_processor = None
    
    
    def _load_pdf_with_mineru(self, pdf_path: Path) -> List[Document]:
        """使用配置的PDF处理器将PDF转换为Markdown后加载"""
        if not self.pdf_processor:
            logger.error("PDF processor not available")
            return []
        
        try:
            md_path = self.pdf_processor.process_pdf_to_markdown(str(pdf_path))
            if md_path and Path(md_path).exists():
                # 加载生成的Markdown文件
                logger.info(f"Loading converted Markdown file: {md_path}")
                return self.load_single_md(md_path)
            else:
                logger.warning(f"Failed to convert PDF to Markdown: {pdf_path}")
                return []
        except Exception as e:
            logger.error(f"PDF processor failed to process {pdf_path}: {e}")
            return []
    
    def _has_corresponding_md(self, pdf_path: Path) -> bool:
        """检查是否存在对应的Markdown文件"""
        md_path = pdf_path.parent / (pdf_path.stem + ".md")
        return md_path.exists() and not self._is_markdown_empty(md_path)
    
    def _ensure_pdf_converted_to_md(self, pdf_path: Path) -> Optional[Path]:
        """
        确保PDF已转换为Markdown，如果不存在则转换
        
        Returns:
            生成的Markdown文件路径，失败返回None
        """
        if not self.pdf_processor:
            return None
        
        try:
            md_path = self.pdf_processor.ensure_pdf_converted(str(pdf_path))
            return Path(md_path) if md_path else None
        except Exception as e:
            logger.warning(f"Failed to convert PDF to Markdown: {pdf_path}, error: {e}")
            return None
    
    def load_single_pdf(self, pdf_path: str) -> List[Document]:
        """
        加载单个PDF文件，使用MinerU转换为Markdown后加载
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            logger.warning(f"PDF file not found: {pdf_path}")
            return []
        
        logger.info(f"Loading PDF: {pdf_path}")
        
        # 如果配置为优先使用Markdown文件，且存在对应的MD文件，则直接加载MD
        if config.PREFER_MARKDOWN_FILES and self._has_corresponding_md(pdf_path):
            md_path = pdf_path.parent / (pdf_path.stem + ".md")
            logger.info(f"Found corresponding Markdown file, loading {md_path} instead of PDF")
            return self.load_single_md(str(md_path))
        
        # 如果配置为自动转换PDF到MD，且PDF处理器可用，则转换后加载
        if config.AUTO_CONVERT_PDF_TO_MD and self.pdf_processor:
            md_path = self._ensure_pdf_converted_to_md(pdf_path)
            if md_path:
                logger.info(f"PDF converted to Markdown, loading {md_path}")
                return self.load_single_md(str(md_path))
        
        # 使用配置的PDF处理器转换PDF
        return self._load_pdf_with_mineru(pdf_path)
    
    def load_single_md(self, md_path: str) -> List[Document]:
        """加载单个Markdown文件"""
        md_path = Path(md_path)
        if not md_path.exists():
            logger.warning(f"Markdown file not found: {md_path}")
            return []
        if self._is_markdown_empty(md_path):
            logger.warning(f"Markdown file is empty, skipping: {md_path}")
            return []
        
        try:
            loader = TextLoader(str(md_path), encoding='utf-8')
            return loader.load()
        except Exception as e:
            logger.error(f"Failed to load markdown {md_path}: {e}")
            return []
    
    def load_single_csv(self, csv_path: str) -> List[Document]:
        """加载单个CSV文件"""
        csv_path = Path(csv_path)
        if not csv_path.exists():
            logger.warning(f"CSV file not found: {csv_path}")
            return []
        
        try:
            loader = CSVLoader(str(csv_path), encoding='utf-8')
            return loader.load()
        except Exception as e:
            logger.error(f"Failed to load CSV {csv_path}: {e}")
            return []
    
    def load_directory_documents(self, file_patterns: Optional[List[str]] = None) -> List[Document]:
        """
        加载目录中的所有文档
        
        Args:
            file_patterns: 文件匹配模式列表，如['**/*.md', '**/*.pdf']
                          如果为None，则加载所有支持的文件类型
        """
        if file_patterns is None:
            file_patterns = ['**/*.txt', '**/*.md', '**/*.csv', '**/*.pdf']
        
        documents = []
        
        for pattern in file_patterns:
            logger.info(f"Searching for files matching: {pattern}")
            matching_files = list(self.rag_directory.glob(pattern))
            
            # 如果配置为优先使用Markdown文件，过滤掉已有对应MD文件的PDF
            if config.PREFER_MARKDOWN_FILES and '**/*.pdf' in pattern:
                filtered_files = []
                pdf_files = [f for f in matching_files if f.suffix.lower() == '.pdf']
                other_files = [f for f in matching_files if f.suffix.lower() != '.pdf']
                
                for pdf_file in pdf_files:
                    if not self._has_corresponding_md(pdf_file):
                        filtered_files.append(pdf_file)
                    else:
                        logger.debug(f"Skipping PDF {pdf_file.name} (corresponding MD file exists)")
                
                matching_files = filtered_files + other_files
            
            for file_path in matching_files:
                logger.info(f"Loading file: {file_path}")
                
                if file_path.suffix.lower() == '.pdf':
                    docs = self.load_single_pdf(str(file_path))
                elif file_path.suffix.lower() in ['.md', '.txt']:
                    docs = self.load_single_md(str(file_path))
                elif file_path.suffix.lower() == '.csv':
                    docs = self.load_single_csv(str(file_path))
                else:
                    logger.warning(f"Unsupported file type: {file_path}")
                    continue
                
                documents.extend(docs)
        
        logger.info(f"Total documents loaded: {len(documents)}")
        return documents
    
    def load_documents(self, file_paths: Optional[List[str]] = None) -> List[Document]:
        """
        通用文档加载方法
        
        Args:
            file_paths: 指定要加载的文件路径列表
                       如果为None，则自动加载目录中的所有支持文件
        
        Returns:
            加载的文档列表
        """
        documents = []
        
        if file_paths is None:
            # 自动发现并加载所有文件
            logger.info(f"Auto-discovering documents in: {self.rag_directory}")
            return self.load_directory_documents()
        
        # 加载指定的文件
        for file_path_str in file_paths:
            file_path = Path(file_path_str)
            
            # 如果是相对路径，则相对于rag_directory
            if not file_path.is_absolute():
                file_path = self.rag_directory / file_path
            
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                continue
            
            logger.info(f"Loading file: {file_path}")
            
            # 如果配置为优先使用Markdown文件，且是PDF文件，检查是否有对应的MD
            if file_path.suffix.lower() == '.pdf' and config.PREFER_MARKDOWN_FILES:
                if self._has_corresponding_md(file_path):
                    md_path = file_path.parent / (file_path.stem + ".md")
                    logger.info(f"Found corresponding Markdown file, loading {md_path} instead of PDF")
                    docs = self.load_single_md(str(md_path))
                else:
                    docs = self.load_single_pdf(str(file_path))
            elif file_path.suffix.lower() == '.pdf':
                docs = self.load_single_pdf(str(file_path))
            elif file_path.suffix.lower() in ['.md', '.txt']:
                docs = self.load_single_md(str(file_path))
            elif file_path.suffix.lower() == '.csv':
                docs = self.load_single_csv(str(file_path))
            else:
                logger.warning(f"Unsupported file type: {file_path}")
                continue
            
            documents.extend(docs)
        
        logger.info(f"Total documents loaded: {len(documents)}")
        return documents
    
    def split_documents(self, documents: List) -> List:
        """分割文档"""
        separators = ["\n\n", "\n", "。", "！", "？", "，", " ", ""]
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config['chunk_size'],
            chunk_overlap=self.config['chunk_overlap'],
            length_function=len,
            add_start_index=True,
            separators=separators,
        )
        texts = text_splitter.split_documents(documents)
        return texts
    
    def create_vectorstore(self, texts: List):
        """创建向量数据库"""
        hf_embedding_model = HuggingFaceEmbeddings(
            model_name=self.config['hf_embedding_model'],
            model_kwargs={'device': self.config['device']},
            encode_kwargs={'normalize_embeddings': True}
        )
        self.vectorstore = FAISS.from_documents(texts, hf_embedding_model)
        return self.vectorstore
    
    def save_cache(self):
        """保存向量数据库到本地缓存"""
        if self.vectorstore is None:
            logger.warning("No vectorstore to save")
            return
        
        try:
            self.rag_directory.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.vectorstore, f)
            logger.info(f"向量数据库已缓存到: {self.cache_file}")
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
    
    def load_cache(self) -> bool:
        """从本地缓存加载向量数据库"""
        if not self.cache_file.exists():
            return False
        
        try:
            with open(self.cache_file, 'rb') as f:
                self.vectorstore = pickle.load(f)
            logger.info("已从本地缓存加载向量数据库")
            return True
        except Exception as e:
            logger.error(f"加载缓存失败: {e}")
            return False
    
    def initialize(self, file_paths: Optional[List[str]] = None, force_rebuild: bool = False):
        """
        初始化RAG系统
        
        Args:
            file_paths: 指定要加载的文件路径列表，None表示自动发现所有文件
            force_rebuild: 是否强制重建向量数据库
        """
        # 如果强制重建或缓存不存在，则重新构建
        if force_rebuild or not self.load_cache():
            logger.info(f"正在构建向量数据库...")
            
            documents = self.load_documents(file_paths)
            
            if not documents:
                raise ValueError("未找到任何文档进行加载，请检查RAG目录或文件路径")
            
            logger.info(f"成功加载 {len(documents)} 个文档")
            
            texts = self.split_documents(documents)
            logger.info(f"文档分割完成，共 {len(texts)} 个文本块")
            
            self.create_vectorstore(texts)
            self.save_cache()
        else:
            logger.info("使用缓存的向量数据库")
    
    def search(self, query: str, k: int = 4) -> List:
        """搜索相关文档"""
        if self.vectorstore is None:
            raise ValueError("向量数据库未初始化，请先调用 initialize_rag()")
        
        results = self.vectorstore.similarity_search(query, k=k)
        return results
    
    def search_with_scores(self, query: str, k: int = 4) -> List:
        """搜索相关文档并返回相似度分数"""
        if self.vectorstore is None:
            raise ValueError("向量数据库未初始化，请先调用 initialize_rag()")
        
        results_with_scores = self.vectorstore.similarity_search_with_score(query, k=k)
        return results_with_scores

    def _is_markdown_empty(self, path: Path) -> bool:
        if not path.exists():
            return True
        if path.stat().st_size == 0:
            return True
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return False
        return len(content.strip()) == 0
    
    def scan_directory(self, directory: Optional[str] = None) -> Dict[str, Any]:
        """
        扫描目录，返回文档文件列表与 PDF 转换状态
        
        Args:
            directory: 要扫描的目录，如果为None则使用self.rag_directory
            
        Returns:
            包含以下键的字典：
            - md_files: MD文件路径列表
            - csv_files: CSV文件路径列表
            - txt_files: TXT文件路径列表
            - pdf_files: PDF文件路径列表
            - md_empty_files: 内容为空的 MD 文件路径列表
            - pdf_conversion_status: PDF文件转换状态字典 {pdf_path: has_md}
            - pdf_md_status: PDF对应MD的详细状态
        """
        scan_dir = Path(directory) if directory else self.rag_directory
        if not scan_dir.exists():
            logger.warning(f"Directory not found: {scan_dir}")
            return {
                "md_files": [],
                "csv_files": [],
                "txt_files": [],
                "pdf_files": [],
                "md_empty_files": [],
                "pdf_conversion_status": {},
                "pdf_md_status": {},
            }

        # 扫描文档文件
        md_files = [str(f) for f in scan_dir.rglob("*.md")]
        csv_files = [str(f) for f in scan_dir.rglob("*.csv")]
        txt_files = [str(f) for f in scan_dir.rglob("*.txt")]
        
        # 扫描PDF文件
        pdf_files = list(scan_dir.rglob("*.pdf"))
        pdf_files = [str(f) for f in pdf_files]
        
        # 检查PDF是否已转换为MD
        pdf_conversion_status = {}
        pdf_md_status = {}
        md_empty_files = []

        for md_path in md_files:
            md_path_obj = Path(md_path)
            if self._is_markdown_empty(md_path_obj):
                md_empty_files.append(md_path)

        for pdf_path in pdf_files:
            pdf_path_obj = Path(pdf_path)
            md_path = pdf_path_obj.parent / (pdf_path_obj.stem + ".md")
            md_exists = md_path.exists()
            md_empty = self._is_markdown_empty(md_path) if md_exists else True
            pdf_conversion_status[pdf_path] = md_exists and not md_empty
            pdf_md_status[pdf_path] = {
                "md_path": str(md_path),
                "md_exists": md_exists,
                "md_empty": md_empty if md_exists else False,
            }
        
        return {
            "md_files": md_files,
            "csv_files": csv_files,
            "txt_files": txt_files,
            "pdf_files": pdf_files,
            "md_empty_files": md_empty_files,
            "pdf_conversion_status": pdf_conversion_status,
            "pdf_md_status": pdf_md_status,
        }
    
    def batch_convert_pdfs(
        self, 
        pdf_files: Optional[List[str]] = None,
        force_reconvert: bool = False,
        parse_method: str = "auto",
    ) -> Dict[str, Any]:
        """
        批量将PDF转换为Markdown
        
        Args:
            pdf_files: PDF文件路径列表，如果为None则扫描目录中的所有PDF
            force_reconvert: 是否强制重新转换已存在的MD文件
            
        Returns:
            包含转换结果的字典：
            - converted: 成功转换的文件列表
            - skipped: 跳过的文件列表（已存在且不强制转换）
            - failed: 转换失败的文件列表
            - total_time: 总耗时（秒）
        """
        import time
        start_time = time.time()
        
        if not self.pdf_processor:
            self._initialize_pdf_processor()
        
        if not self.pdf_processor:
            logger.warning("PDF processor not available, cannot convert PDFs")
            return {
                "converted": [],
                "skipped": [],
                "failed": [],
                "total_time": 0
            }
        
        if pdf_files is None:
            scan_result = self.scan_directory()
            pdf_files = scan_result["pdf_files"]
        
        converted = []
        skipped = []
        failed = []
        
        for pdf_path in pdf_files:
            pdf_path_obj = Path(pdf_path)
            md_path = pdf_path_obj.parent / (pdf_path_obj.stem + ".md")
            
            # 如果MD已存在且不强制转换，则跳过
            if md_path.exists() and not force_reconvert:
                if self._is_markdown_empty(md_path):
                    try:
                        md_path.unlink()
                        logger.info(f"检测到空MD文件，准备重新转换: {md_path}")
                    except Exception as e:
                        logger.warning(f"删除空MD文件失败: {e}")
                else:
                    logger.info(f"跳过已存在的MD文件: {md_path}")
                    skipped.append(str(pdf_path))
                    continue
            
            # 如果强制转换，删除已存在的MD文件
            if md_path.exists() and force_reconvert:
                try:
                    md_path.unlink()
                    logger.info(f"删除已存在的MD文件: {md_path}")
                except Exception as e:
                    logger.warning(f"删除MD文件失败: {e}")
            
            # 转换PDF
            try:
                logger.info(f"正在转换PDF: {pdf_path}")
                result_md_path = self.pdf_processor.process_pdf_to_markdown(
                    str(pdf_path),
                    output_dir=None,
                    output_filename=None,
                    parse_method=parse_method,
                )
                if result_md_path:
                    converted.append(str(pdf_path))
                    logger.info(f"成功转换: {pdf_path} -> {result_md_path}")
                else:
                    failed.append(str(pdf_path))
                    logger.error(f"转换失败: {pdf_path}")
            except Exception as e:
                failed.append(str(pdf_path))
                logger.error(f"转换PDF时出错 {pdf_path}: {e}", exc_info=True)
        
        total_time = time.time() - start_time
        
        return {
            "converted": converted,
            "skipped": skipped,
            "failed": failed,
            "total_time": total_time
        }

    def convert_pdf_to_md(
        self,
        pdf_path: str,
        force_reconvert: bool = False,
        parse_method: str = "auto",
    ) -> Optional[str]:
        """
        将单个PDF转换为同名Markdown文件（输出到PDF同目录）。

        Args:
            pdf_path: PDF文件路径
            force_reconvert: 是否强制重新转换（覆盖已有MD）
            parse_method: MinerU 解析策略（auto/txt/ocr）

        Returns:
            Markdown文件路径，失败返回None
        """
        if not self.pdf_processor:
            self._initialize_pdf_processor()

        if not self.pdf_processor:
            logger.warning("PDF processor not available, cannot convert PDF")
            return None

        pdf_path_obj = Path(pdf_path)
        md_path = pdf_path_obj.parent / (pdf_path_obj.stem + ".md")
        if md_path.exists():
            if force_reconvert or self._is_markdown_empty(md_path):
                try:
                    md_path.unlink()
                    logger.info(f"删除已存在的MD文件: {md_path}")
                except Exception as e:
                    logger.warning(f"删除MD文件失败: {e}")
            else:
                logger.info(f"Markdown文件已存在，跳过转换: {md_path}")
                return str(md_path)

        return self.pdf_processor.process_pdf_to_markdown(
            str(pdf_path_obj),
            output_dir=None,
            output_filename=None,
            parse_method=parse_method,
        )
    
    def get_indexed_documents(self) -> List[Dict[str, Any]]:
        """
        获取向量数据库中已索引的文档列表
        
        Returns:
            文档信息列表，每个元素包含：
            - source: 文档源路径
            - metadata: 文档元数据
        """
        if self.vectorstore is None:
            logger.warning("向量数据库未初始化")
            return []
        
        try:
            # 从FAISS向量数据库中获取所有文档
            # FAISS的vectorstore有一个docstore属性，包含所有文档
            
            # 方法1：尝试从docstore获取（最可靠的方法）
            if hasattr(self.vectorstore, 'docstore'):
                documents = []
                seen_sources = set()
                
                # 尝试不同的方式访问docstore
                docstore_dict = None
                if hasattr(self.vectorstore.docstore, '_dict'):
                    docstore_dict = self.vectorstore.docstore._dict
                elif hasattr(self.vectorstore.docstore, 'dict'):
                    docstore_dict = self.vectorstore.docstore.dict
                elif hasattr(self.vectorstore.docstore, '__dict__'):
                    # 尝试直接访问__dict__
                    docstore_dict = getattr(self.vectorstore.docstore, '__dict__', {}).get('_dict')
                
                if docstore_dict:
                    for doc_id, doc in docstore_dict.items():
                        if hasattr(doc, 'metadata') and hasattr(doc, 'page_content'):
                            source = doc.metadata.get("source", "Unknown")
                            if source not in seen_sources:
                                seen_sources.add(source)
                                documents.append({
                                    "source": source,
                                    "metadata": doc.metadata
                                })
                    if documents:
                        return documents
                
                # 如果_dict不可用，尝试遍历docstore
                try:
                    if hasattr(self.vectorstore.docstore, 'search'):
                        # 尝试通过search方法获取
                        for doc_id in range(len(self.vectorstore.docstore)):
                            try:
                                doc = self.vectorstore.docstore.search({doc_id})
                                if doc and hasattr(doc, 'metadata'):
                                    source = doc.metadata.get("source", "Unknown")
                                    if source not in seen_sources:
                                        seen_sources.add(source)
                                        documents.append({
                                            "source": source,
                                            "metadata": doc.metadata
                                        })
                            except:
                                continue
                    if documents:
                        return documents
                except:
                    pass
            
            # 方法2：如果docstore不可用，尝试通过多次搜索获取
            # 使用不同的查询词来尽可能获取所有文档
            try:
                seen_sources = set()
                documents = []
                # 使用多个常见查询词来获取更多文档
                query_words = ["文档", "内容", "信息", "数据", "文本", "资料"]
                for query_word in query_words:
                    try:
                        results = self.vectorstore.similarity_search(query_word, k=1000)
                        for doc in results:
                            source = doc.metadata.get("source", "Unknown")
                            if source not in seen_sources:
                                seen_sources.add(source)
                                documents.append({
                                    "source": source,
                                    "metadata": doc.metadata
                                })
                    except:
                        continue
                
                if documents:
                    return documents
            except Exception as e:
                logger.warning(f"无法通过搜索获取文档列表: {e}")
            
            # 如果所有方法都失败，返回空列表
            logger.warning("无法获取文档列表，所有方法都失败了")
            return []
                
        except Exception as e:
            logger.error(f"获取已索引文档列表时出错: {e}", exc_info=True)
            return []

# 全局实例
rag_manager = RAGManager()

# 便捷函数（向后兼容）
def initialize_rag(mode: str = "auto", force_rebuild: bool = False, file_paths: Optional[List[str]] = None):
    """
    初始化RAG系统（向后兼容）
    
    Args:
        mode: 已弃用，为了向后兼容保留，推荐使用file_paths参数
        force_rebuild: 是否强制重建缓存
        file_paths: 指定要加载的文件路径列表，None表示自动发现所有文件
    """
    if mode != "auto":
        logger.warning(f"mode参数已弃用，将自动发现所有文件。如需指定文件，请使用file_paths参数")
    
    rag_manager.initialize(file_paths=file_paths, force_rebuild=force_rebuild)

def search(query: str, k: int = 4) -> List:
    """搜索相关文档"""
    return rag_manager.search(query, k)

def search_with_scores(query: str, k: int = 4) -> List:
    """搜索文档并返回相似度分数"""
    return rag_manager.search_with_scores(query, k)
