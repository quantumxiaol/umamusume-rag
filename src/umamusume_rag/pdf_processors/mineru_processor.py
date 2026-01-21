"""
PDF处理模块：使用MinerU将PDF转换为Markdown
"""

import os
import logging
import time
from pathlib import Path
from typing import Optional, List

from mineru.cli.common import do_parse, read_fn
from mineru.utils.config_reader import get_device
from mineru.utils.model_utils import get_vram

from ..config import config

logger = logging.getLogger(__name__)


class MinerUPythonAPI:
    """MinerU Python API 封装类"""
    
    def __init__(
        self,
        weights_dir: Optional[str] = None,
        device_mode: Optional[str] = None,
        model_source: str = 'huggingface',
        lang: str = 'ch'
    ):
        """
        初始化 MinerU Python API
        
        Args:
            weights_dir: 模型权重目录，默认从 HF_HOME 环境变量读取
            device_mode: 设备模式 ('cpu', 'cuda', 'cuda:0', 'mps' 等)，默认自动检测
            model_source: 模型源 ('huggingface', 'modelscope', 'local')
            lang: 默认语言 ('ch', 'en', 'korean', 'japan' 等)
        """
        self.lang = lang
        self.weights_dir = self._setup_env(weights_dir, device_mode, model_source)
        logger.info("✅ MinerU Python API 初始化完成")
    
    def _setup_env(
        self,
        weights_dir: Optional[str],
        device_mode: Optional[str],
        model_source: str
    ) -> Path:
        """设置 MinerU 所需的环境变量"""
        # 设置权重目录
        if weights_dir is None:
            weights_dir = Path(os.getenv('HF_HOME', './weights')).absolute()
        else:
            weights_dir = Path(weights_dir).absolute()
        
        weights_dir.mkdir(parents=True, exist_ok=True)
        
        # 确保环境变量被设置
        if 'HF_HOME' not in os.environ:
            os.environ['HF_HOME'] = str(weights_dir)
        if 'HUGGINGFACE_HUB_CACHE' not in os.environ:
            os.environ['HUGGINGFACE_HUB_CACHE'] = str(weights_dir / 'hub')
        
        # 设置设备模式
        if device_mode is None:
            if os.getenv('MINERU_DEVICE_MODE', None) is None:
                device_mode = get_device()
                os.environ['MINERU_DEVICE_MODE'] = device_mode
                logger.info(f"设备模式: {device_mode}")
                
                # 设置虚拟显存（如果是 GPU）
                if device_mode.startswith("cuda") or device_mode.startswith("npu"):
                    vram_size = round(get_vram(device_mode))
                    os.environ['MINERU_VIRTUAL_VRAM_SIZE'] = str(vram_size)
                    logger.info(f"虚拟显存: {vram_size} GB")
        else:
            os.environ['MINERU_DEVICE_MODE'] = device_mode
        
        # 设置模型源
        if os.getenv('MINERU_MODEL_SOURCE', None) is None:
            os.environ['MINERU_MODEL_SOURCE'] = model_source
        
        return weights_dir
    
    def process_file(
        self,
        input_path: str,
        output_dir: str,
        lang: Optional[str] = None,
        backend: str = 'pipeline',
        parse_method: str = 'auto',
        formula_enable: bool = True,
        table_enable: bool = True,
        start_page_id: int = 0,
        end_page_id: Optional[int] = None,
        return_markdown: bool = True,
        **kwargs
    ) -> Optional[str]:
        """
        处理文件（PDF 或图片）并返回 Markdown
        
        Args:
            input_path: 输入文件路径（支持 PDF、PNG、JPG 等）
            output_dir: 输出目录
            lang: 语言代码，默认使用初始化时的 lang
            backend: 后端类型 ('pipeline', 'vlm-transformers', 'vlm-vllm-engine', 'vlm-http-client')
            parse_method: 解析方法 ('auto', 'txt', 'ocr')
            formula_enable: 是否启用公式识别
            table_enable: 是否启用表格识别
            start_page_id: 起始页码（从 0 开始）
            end_page_id: 结束页码（从 0 开始），None 表示处理到最后
            return_markdown: 是否返回 Markdown 内容
            **kwargs: 其他参数传递给 do_parse
        
        Returns:
            str: Markdown 内容（如果 return_markdown=True），否则返回 None
        """
        input_path = Path(input_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if not input_path.exists():
            raise FileNotFoundError(f"输入文件不存在: {input_path}")
        
        logger.info(f"📄 处理文件: {input_path}")
        logger.info(f"📁 输出目录: {output_dir}")
        
        # 读取文件（read_fn 会自动处理 PDF 和图片）
        try:
            pdf_bytes = read_fn(input_path)
            file_name = input_path.stem
        except Exception as e:
            logger.error(f"❌ 读取文件失败: {e}")
            raise
        
        # 使用 do_parse 处理（与命令行工具使用相同的函数）
        try:
            do_parse(
                output_dir=str(output_dir),
                pdf_file_names=[file_name],
                pdf_bytes_list=[pdf_bytes],
                p_lang_list=[lang or self.lang],
                backend=backend,
                parse_method=parse_method,
                formula_enable=formula_enable,
                table_enable=table_enable,
                f_draw_layout_bbox=False,
                f_draw_span_bbox=False,
                f_dump_md=True,
                f_dump_middle_json=False,
                f_dump_model_output=False,
                f_dump_orig_pdf=False,
                f_dump_content_list=False,
                start_page_id=start_page_id,
                end_page_id=end_page_id,
                **kwargs
            )
            
            logger.info("✅ 处理完成")
            
            # 返回 Markdown 内容
            if return_markdown:
                markdown_files = list(output_dir.rglob("*.md"))
                if not markdown_files:
                    logger.warning("⚠️  未找到生成的 Markdown 文件")
                    return None
                
                # 读取第一个 Markdown 文件
                markdown_file = markdown_files[0]
                logger.info(f"📖 读取 Markdown: {markdown_file}")
                
                with open(markdown_file, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
                
                logger.info(f"✅ Markdown 读取完成，长度: {len(markdown_content)} 字符")
                return markdown_content
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 处理失败: {e}", exc_info=True)
            raise


class PDFProcessor:
    """
    PDF处理器：使用MinerU将PDF转换为Markdown
    """
    
    def __init__(self, model_dir: Optional[str] = None):
        """
        初始化PDF处理器
        
        Args:
            model_dir: MinerU模型目录，如果不指定则从配置读取
        """
        # 从配置读取模型目录
        self.model_dir = model_dir or getattr(config, 'MINERU_MODEL_DIR', None)
        if self.model_dir:
            os.environ['MINERU_MODEL_DIR'] = str(self.model_dir)
            logger.info(f"MinerU model directory: {self.model_dir}")
        
        # 初始化 MinerU Python API
        self.mineru_api = MinerUPythonAPI(
            weights_dir=self.model_dir,
            lang='ch'
        )
        logger.info("MinerU PDF processor initialized successfully")
        
    def process_pdf_to_markdown(
        self, 
        pdf_path: str, 
        output_dir: Optional[str] = None,
        output_filename: Optional[str] = None,
        parse_method: str = "auto",
    ) -> Optional[str]:
        """
        将PDF文件转换为Markdown并保存到指定目录
        
        Args:
            pdf_path: PDF文件路径
            output_dir: 输出目录，如果为None则与PDF同目录
            output_filename: 输出文件名，如果为None则使用PDF文件名
            parse_method: MinerU解析策略（auto/txt/ocr）
            
        Returns:
            生成的Markdown文件路径，失败返回None
        """
        import shutil
        import tempfile
        import re
        
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            return None
        
        # 确定最终输出目录和文件名（与PDF同目录）
        if output_dir is None:
            final_output_dir = pdf_path.parent
        else:
            final_output_dir = Path(output_dir)
            final_output_dir.mkdir(parents=True, exist_ok=True)
        
        if output_filename is None:
            output_filename = pdf_path.stem + ".md"
        
        final_md_path = final_output_dir / output_filename
        
        # 如果Markdown文件已存在，跳过处理
        if final_md_path.exists():
            logger.info(f"Markdown file already exists: {final_md_path}, skipping...")
            return str(final_md_path)
        
        # 使用临时目录进行处理（MinerU会在output_dir下创建子目录）
        temp_dir = None
        process_start_time = time.time()  # 记录处理开始时间，用于清理旧文件
        try:
            logger.info(f"Processing PDF: {pdf_path} -> {final_md_path}")
            
            # 创建临时目录用于处理
            temp_dir = Path(tempfile.mkdtemp(prefix="mineru_"))
            logger.debug(f"Using temporary directory: {temp_dir}")
            
            # 使用 MinerU API 处理 PDF（输出到临时目录）
            markdown_content = self.mineru_api.process_file(
                input_path=str(pdf_path),
                output_dir=str(temp_dir),
                return_markdown=True,
                parse_method=parse_method,
            )
            
            if not markdown_content:
                logger.warning(f"No markdown content returned for {pdf_path}")
                return None
            
            # 查找生成的 Markdown 文件
            markdown_files = list(temp_dir.rglob("*.md"))
            if not markdown_files:
                logger.warning(f"No markdown file found in {temp_dir}")
                return None
            
            # 使用最新的Markdown文件
            source_md_file = max(markdown_files, key=lambda p: p.stat().st_mtime)
            logger.info(f"Found generated markdown: {source_md_file}")
            
            # 读取Markdown内容
            with open(source_md_file, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            # 处理图片路径：查找并移动图片，更新MD中的路径
            # MinerU生成的图片通常在 output_dir/auto/images/ 或 output_dir/images/ 下
            image_dirs = [
                temp_dir / "images",
                temp_dir / "auto" / "images",
                source_md_file.parent / "images",
            ]
            
            # 查找所有图片文件
            image_files = []
            for img_dir in image_dirs:
                if img_dir.exists():
                    for img_file in img_dir.rglob("*"):
                        if img_file.is_file() and img_file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                            image_files.append(img_file)
            
            # 如果有图片，创建图片目录并移动图片
            image_path_map = {}  # 旧路径 -> 新路径的映射
            if image_files:
                # 在最终输出目录创建images子目录
                final_images_dir = final_output_dir / "images"
                final_images_dir.mkdir(exist_ok=True)
                
                # 移动图片并构建路径映射
                for img_file in image_files:
                    # 目标路径：使用文件名（避免路径冲突）
                    target_img_name = img_file.name
                    target_img_path = final_images_dir / target_img_name
                    
                    # 如果目标文件已存在，添加前缀避免冲突
                    counter = 1
                    while target_img_path.exists():
                        stem = img_file.stem
                        suffix = img_file.suffix
                        target_img_name = f"{stem}_{counter}{suffix}"
                        target_img_path = final_images_dir / target_img_name
                        counter += 1
                    
                    # 获取在MD中可能使用的各种相对路径形式（旧路径）
                    old_paths = [
                        str(img_file.relative_to(temp_dir)),  # 相对于temp_dir的路径
                        str(img_file.relative_to(source_md_file.parent)),  # 相对于MD文件目录的路径
                        f"images/{img_file.name}",  # 简单的images/文件名
                        f"auto/images/{img_file.name}",  # auto/images/文件名
                        img_file.name,  # 仅文件名
                    ]
                    
                    # 新路径：相对于MD文件的路径
                    new_path = f"images/{target_img_name}"
                    
                    # 构建映射
                    for old_path in old_paths:
                        if old_path not in image_path_map:
                            image_path_map[old_path] = new_path
                    
                    # 移动图片
                    shutil.move(str(img_file), str(target_img_path))
                    logger.debug(f"Moved image: {img_file} -> {target_img_path}")
            
            # 更新MD中的图片路径（如果有图片）
            if image_path_map:
                # 替换MD中的图片路径
                # Markdown图片语法: ![alt](path)
                def replace_md_image(match):
                    alt_text = match.group(1)
                    old_path = match.group(2)
                    # 检查是否需要替换（精确匹配或文件名匹配）
                    for old, new in image_path_map.items():
                        if old_path == old or old_path.endswith('/' + old.split('/')[-1]) or old_path == old.split('/')[-1]:
                            return f'![{alt_text}]({new})'
                    return match.group(0)
                
                md_content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace_md_image, md_content)
                
                # HTML img标签: <img src="path">
                def replace_html_image(match):
                    prefix = match.group(1)
                    old_path = match.group(2)
                    for old, new in image_path_map.items():
                        if old_path == old or old_path.endswith('/' + old.split('/')[-1]) or old_path == old.split('/')[-1]:
                            return f'<img{prefix}src="{new}"'
                    return match.group(0)
                
                md_content = re.sub(r'<img([^>]+)src=["\']([^"\']+)["\']', replace_html_image, md_content)
            
            # 写入最终的Markdown文件
            with open(final_md_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            logger.info(f"Successfully converted PDF to Markdown: {final_md_path}")
            return str(final_md_path)
            
        except Exception as e:
            logger.error(f"Failed to process PDF {pdf_path}: {e}", exc_info=True)
            return None
        finally:
            # 清理临时目录
            if temp_dir and temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                    logger.debug(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary directory {temp_dir}: {e}")
            
            # 清理可能遗留的中间目录和文件（在PDF目录下）
            pdf_parent = pdf_path.parent
            final_images_dir = final_output_dir / "images"
            parent_images_dir = pdf_parent / "images"
            
            # 需要清理的目录列表
            cleanup_dirs = []
            
            # 1. PDF名称目录下的auto目录（MinerU生成的临时目录）
            pdf_name_auto_dir = pdf_parent / pdf_path.stem / "auto"
            if pdf_name_auto_dir.exists() and pdf_name_auto_dir.is_dir():
                cleanup_dirs.append(pdf_name_auto_dir)
            
            # 2. PDF名称目录（如果只包含auto子目录或其他临时文件）
            pdf_name_dir = pdf_parent / pdf_path.stem
            if pdf_name_dir.exists() and pdf_name_dir.is_dir():
                # 检查目录内容
                contents = list(pdf_name_dir.iterdir())
                # 如果只包含auto目录，或者只包含auto和images目录，可以清理
                if len(contents) <= 2:
                    has_only_temp = all(
                        item.name in ["auto", "images"] or 
                        (item.is_file() and item.suffix in ['.json', '.txt', '.log'])
                        for item in contents
                    )
                    if has_only_temp:
                        cleanup_dirs.append(pdf_name_dir)
            
            # 3. 处理PDF父目录下的images目录
            # 如果parent_images_dir就是final_images_dir，说明图片应该保留在这里
            # 但如果MinerU在处理时直接在这里创建了图片，而我们的代码又从临时目录移动了图片
            # 可能会有重复。我们需要清理那些在临时目录处理之前就存在的旧图片
            if parent_images_dir.exists() and parent_images_dir.is_dir():
                if parent_images_dir == final_images_dir:
                    # 这是最终目录，需要清理处理开始前就存在的旧文件
                    # 这些文件可能是MinerU在处理过程中直接创建的临时文件
                    try:
                        old_files = []
                        for img_file in parent_images_dir.iterdir():
                            if img_file.is_file():
                                # 检查文件修改时间是否早于处理开始时间
                                file_mtime = img_file.stat().st_mtime
                                if file_mtime < process_start_time:
                                    old_files.append(img_file)
                        
                        # 删除旧文件
                        for old_file in old_files:
                            try:
                                old_file.unlink()
                                logger.debug(f"已删除旧图片文件: {old_file}")
                            except Exception as e:
                                logger.warning(f"删除旧文件失败 {old_file}: {e}")
                        
                        if old_files:
                            logger.info(f"✅ 已清理 {len(old_files)} 个旧图片文件")
                    except Exception as e:
                        logger.warning(f"检查旧文件失败: {e}")
                else:
                    # 这不是最终目录，可能是MinerU在处理时创建的临时目录
                    cleanup_dirs.append(parent_images_dir)
            
            # 执行清理
            for cleanup_dir in cleanup_dirs:
                if cleanup_dir.exists() and cleanup_dir.is_dir():
                    try:
                        # 递归删除整个目录
                        shutil.rmtree(cleanup_dir)
                        logger.info(f"✅ 已清理中间目录: {cleanup_dir}")
                    except Exception as e:
                        logger.warning(f"⚠️  清理目录失败 {cleanup_dir}: {e}")
            
            # 特殊处理：如果MinerU在处理时直接在PDF父目录下创建了images目录
            # 而我们的代码将图片移动到了final_images_dir，需要清理旧的images目录
            # 但要注意：如果parent_images_dir == final_images_dir，说明是同一个目录，不应该清理
            if parent_images_dir.exists() and parent_images_dir.is_dir():
                if parent_images_dir != final_images_dir:
                    # 不是最终目录，应该已经被上面的逻辑清理了
                    # 但为了确保，再次检查
                    if parent_images_dir.exists():
                        try:
                            shutil.rmtree(parent_images_dir)
                            logger.info(f"✅ 已清理PDF父目录下的旧images目录: {parent_images_dir}")
                        except Exception as e:
                            logger.warning(f"⚠️  清理旧images目录失败 {parent_images_dir}: {e}")
                else:
                    # 是最终目录，但需要检查是否有MinerU直接创建的旧文件
                    # 这些文件的时间戳应该早于我们移动的文件
                    # 为了安全，我们保留所有文件（因为可能都是需要的）
                    # 如果确实有重复，用户可以通过force_reconvert重新处理
                    pass
    
    def process_directory(
        self, 
        directory: str,
        recursive: bool = True,
        output_dir: Optional[str] = None
    ) -> List[str]:
        """
        批量处理目录中的所有PDF文件
        
        Args:
            directory: PDF文件所在目录
            recursive: 是否递归处理子目录
            output_dir: 输出目录，如果为None则每个PDF与对应的MD文件同目录
            
        Returns:
            成功处理的Markdown文件路径列表
        """
        directory = Path(directory)
        if not directory.exists():
            logger.error(f"Directory not found: {directory}")
            return []
        
        pdf_files = list(directory.rglob("*.pdf")) if recursive else list(directory.glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files in {directory}")
        
        results = []
        for pdf_path in pdf_files:
            md_path = self.process_pdf_to_markdown(
                str(pdf_path),
                output_dir=output_dir
            )
            if md_path:
                results.append(md_path)
        
        logger.info(f"Successfully processed {len(results)}/{len(pdf_files)} PDF files")
        return results
    
    def ensure_pdf_converted(self, pdf_path: str) -> Optional[str]:
        """
        确保PDF已转换为Markdown，如果不存在则转换
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            Markdown文件路径，失败返回None
        """
        pdf_path = Path(pdf_path)
        md_path = pdf_path.parent / (pdf_path.stem + ".md")
        
        if md_path.exists():
            try:
                content = md_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                content = ""
            if content.strip():
                logger.debug(f"Markdown file already exists: {md_path}")
                return str(md_path)
        
        return self.process_pdf_to_markdown(str(pdf_path), output_dir=None, output_filename=None)


# 全局实例
_pdf_processor: Optional[PDFProcessor] = None


def get_pdf_processor(model_dir: Optional[str] = None) -> PDFProcessor:
    """
    获取PDF处理器实例（单例模式）
    
    Args:
        model_dir: MinerU模型目录
        
    Returns:
        PDFProcessor实例
    """
    global _pdf_processor
    if _pdf_processor is None:
        _pdf_processor = PDFProcessor(model_dir=model_dir)
    return _pdf_processor
