#!/usr/bin/env python3
"""
RAG工具脚本 - 用于管理RAG数据库和PDF转换
"""

import argparse
import json
import sys
import time
import os
from pathlib import Path
import logging
from datetime import datetime, timezone

# 添加项目路径到sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from umamusume_rag.rag import RAGManager
from umamusume_rag.config import config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def format_time(seconds: float) -> str:
    """格式化时间显示"""
    if seconds < 60:
        return f"{seconds:.2f}秒"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}分{secs:.2f}秒"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}小时{minutes}分{secs:.2f}秒"


def scan_command(directory: str = None):
    """扫描目录，显示文档文件和PDF转换状态"""
    rag_dir = directory or config.RAG_DIRECTORY
    print(f"📁 扫描目录: {rag_dir}\n")
    
    rag = RAGManager(rag_directory=rag_dir)
    scan_result = rag.scan_directory()
    
    md_files = scan_result["md_files"]
    csv_files = scan_result.get("csv_files", [])
    txt_files = scan_result.get("txt_files", [])
    pdf_files = scan_result["pdf_files"]
    pdf_conversion_status = scan_result["pdf_conversion_status"]
    pdf_md_status = scan_result.get("pdf_md_status", {})
    md_empty_files = scan_result.get("md_empty_files", [])
    
    print("=" * 70)
    print("目录扫描结果")
    print("=" * 70)
    
    print(f"\n📄 Markdown文件 ({len(md_files)} 个):")
    if md_files:
        for md_file in md_files:
            print(f"  ✓ {md_file}")
    else:
        print("  (无)")

    print(f"\n📄 CSV文件 ({len(csv_files)} 个):")
    if csv_files:
        for csv_file in csv_files:
            print(f"  ✓ {csv_file}")
    else:
        print("  (无)")

    print(f"\n📄 TXT文件 ({len(txt_files)} 个):")
    if txt_files:
        for txt_file in txt_files:
            print(f"  ✓ {txt_file}")
    else:
        print("  (无)")

    print(f"\n⚠️ 空内容 Markdown ({len(md_empty_files)} 个):")
    if md_empty_files:
        for md_file in md_empty_files:
            print(f"  ⚠️ {md_file}")
    else:
        print("  (无)")
    
    print(f"\n📕 PDF文件 ({len(pdf_files)} 个):")
    if pdf_files:
        for pdf_file in pdf_files:
            status = pdf_md_status.get(pdf_file, {})
            md_exists = status.get("md_exists", False)
            md_empty = status.get("md_empty", False)
            if md_exists and not md_empty:
                label = "✓ 已转换"
            elif md_exists and md_empty:
                label = "⚠️ MD为空"
            else:
                label = "✗ 未转换"
            print(f"  {label} {pdf_file}")
    else:
        print("  (无)")
    
    # 统计转换状态
    converted_count = sum(1 for has_md in pdf_conversion_status.values() if has_md)
    unconverted_count = len(pdf_files) - converted_count
    empty_md_count = sum(
        1 for info in pdf_md_status.values() if info.get("md_exists") and info.get("md_empty")
    )
    
    print(f"\n📊 转换状态统计:")
    print(f"  已转换: {converted_count} 个")
    print(f"  MD为空: {empty_md_count} 个")
    print(f"  未转换: {unconverted_count} 个")
    print("=" * 70 + "\n")


def convert_command(directory: str = None, force: bool = False, force_ocr: bool = False):
    """转换目录中的所有PDF文件为Markdown"""
    rag_dir = directory or config.RAG_DIRECTORY
    print(f"📁 使用目录: {rag_dir}\n")
    
    rag = RAGManager(rag_directory=rag_dir)
    
    # 检查PDF处理器是否可用
    engine = (rag.pdf_processor_engine or "").lower()
    engine_label = engine or "unknown"
    if not rag.pdf_processor:
        print(f"❌ PDF处理器不可用！(engine={engine_label})")
        if engine == "mineru":
            print("   请确保已安装: pip install 'mineru[core]'")
            print(f"   模型目录: {config.MINERU_MODEL_DIR}")
        elif engine == "markitdown":
            print("   请确保已安装: pip install markitdown")
        elif engine in ("qwen-vl", "qwen_vl"):
            print("   请确保已安装: pip install pymupdf transformers torch qwen-vl-utils")
            print(f"   模型目录: {config.QWEN_VL_MODEL_DIR}")
        elif engine in ("", "none", "off", "disabled", "false"):
            print("   PDF处理已禁用。请设置 PDF_PROCESSOR_ENGINE=markitdown/mineru/docling/qwen-vl 后重试。")
        else:
            print("   请确认相关依赖已安装并正确配置。")
        return 1
    
    print(f"✓ PDF处理器已就绪 (engine={engine_label})\n")
    
    # 扫描目录
    print("🔍 正在扫描目录...")
    scan_result = rag.scan_directory()
    
    # 确定需要转换的PDF文件
    pdf_files_to_convert = []
    for pdf_file, has_md in scan_result["pdf_conversion_status"].items():
        if force or not has_md:
            pdf_files_to_convert.append(pdf_file)
    
    if not pdf_files_to_convert:
        print("✓ 所有PDF文件已转换，无需处理")
        return 0
    
    print(f"🔄 开始转换 {len(pdf_files_to_convert)} 个PDF文件...")
    print("=" * 70)
    
    convert_start = time.time()
    parse_method = "ocr" if force_ocr else "auto"
    convert_result = rag.batch_convert_pdfs(
        pdf_files=pdf_files_to_convert,
        force_reconvert=force,
        parse_method=parse_method,
    )
    convert_time = time.time() - convert_start
    
    # 显示转换结果
    print("\n" + "=" * 70)
    print("📊 PDF转换结果")
    print("=" * 70)
    print(f"成功转换: {len(convert_result['converted'])} 个")
    print(f"跳过: {len(convert_result['skipped'])} 个")
    print(f"失败: {len(convert_result['failed'])} 个")
    print(f"总耗时: {format_time(convert_time)}")
    print("=" * 70)
    
    if convert_result['converted']:
        print("\n✅ 成功转换的文件:")
        for pdf_file in convert_result['converted']:
            pdf_path = Path(pdf_file)
            md_path = pdf_path.parent / (pdf_path.stem + ".md")
            print(f"  ✓ {pdf_file}")
            print(f"    → {md_path}")
    
    if convert_result['failed']:
        print("\n❌ 转换失败的文件:")
        for pdf_file in convert_result['failed']:
            print(f"  ✗ {pdf_file}")
    
    print("\n" + "=" * 70)
    print("转换完成！")
    print("=" * 70 + "\n")
    
    return 0 if not convert_result['failed'] else 1


def build_command(directory: str = None, force_convert: bool = False, force_rebuild: bool = False):
    """构建RAG向量数据库"""
    rag_dir = directory or config.RAG_DIRECTORY
    print(f"📁 使用目录: {rag_dir}\n")
    
    rag = RAGManager(rag_directory=rag_dir)
    
    # 0. 缓存检查
    if rag.cache_file.exists() and not force_rebuild:
        print(f"✅ 已找到向量数据库缓存: {rag.cache_file}")
        print("   使用 --force-rebuild 可强制重建")
        return 0

    # 1. 扫描目录
    print("🔍 正在扫描目录...")
    scan_result = rag.scan_directory()
    
    # 2. 转换PDF（如果需要）
    pdf_convert_time = 0
    if force_convert or any(not status for status in scan_result["pdf_conversion_status"].values()):
        print("🔄 开始转换PDF文件...")
        convert_start = time.time()
        
        pdf_files_to_convert = []
        for pdf_file, has_md in scan_result["pdf_conversion_status"].items():
            if force_convert or not has_md:
                pdf_files_to_convert.append(pdf_file)
        
        if pdf_files_to_convert:
            convert_result = rag.batch_convert_pdfs(
                pdf_files=pdf_files_to_convert,
                force_reconvert=force_convert,
            )
            pdf_convert_time = convert_result["total_time"]
            
            print(f"\n📊 PDF转换结果:")
            print(f"  成功转换: {len(convert_result['converted'])} 个")
            print(f"  跳过: {len(convert_result['skipped'])} 个")
            print(f"  失败: {len(convert_result['failed'])} 个")
            print(f"  耗时: {format_time(pdf_convert_time)}")
            
            if convert_result['failed']:
                print(f"\n❌ 转换失败的文件:")
                for failed_file in convert_result['failed']:
                    print(f"  - {failed_file}")
        else:
            print("✓ 所有PDF文件已转换，跳过转换步骤")
    else:
        print("✓ 所有PDF文件已转换，跳过转换步骤")
    
    # 3. 构建向量数据库
    print("\n🏗️  开始构建向量数据库...")
    build_start = time.time()
    
    try:
        rag.initialize(force_rebuild=force_rebuild)
        build_time = time.time() - build_start
        
        print(f"✓ 向量数据库构建完成！")
        print(f"  耗时: {format_time(build_time)}")
        
        # 4. 总结
        print("\n" + "=" * 70)
        print("📊 构建总结")
        print("=" * 70)
        print(f"PDF转换耗时: {format_time(pdf_convert_time)}")
        print(f"数据库构建耗时: {format_time(build_time)}")
        print(f"总耗时: {format_time(pdf_convert_time + build_time)}")
        print("=" * 70 + "\n")
        
        return 0
        
    except Exception as e:
        logger.error(f"构建向量数据库时出错: {e}", exc_info=True)
        print(f"\n❌ 构建失败: {e}")
        return 1


def _vectorstore_documents(vectorstore) -> list:
    docstore = getattr(vectorstore, "docstore", None)
    docstore_dict = getattr(docstore, "_dict", None)
    if isinstance(docstore_dict, dict):
        return list(docstore_dict.values())
    return []


def export_faiss_command(
    directory: str = None,
    output: str = "resources/faiss",
    force_rebuild: bool = False,
):
    """导出可移植的 LangChain FAISS 索引目录。"""
    rag_dir = directory or config.RAG_DIRECTORY
    out_dir = Path(output)
    if not out_dir.is_absolute():
        out_dir = project_root / out_dir
    index_dir = out_dir / "faiss_index"

    print(f"📁 使用目录: {rag_dir}")
    print(f"📦 导出目录: {out_dir}\n")

    rag = RAGManager(rag_directory=rag_dir)
    export_start = time.time()

    try:
        if force_rebuild:
            rag.initialize(force_rebuild=True)
        elif not rag.load_cache():
            print(f"❌ 导出失败: 无法加载向量数据库缓存: {rag.cache_file}")
            print("   请先运行: python rag_tools.py build --force-rebuild")
            print("   或显式允许导出前重建: python rag_tools.py export-faiss --force-rebuild")
            return 1

        if rag.vectorstore is None:
            print("❌ 导出失败: 向量数据库未初始化")
            return 1

        index_dir.mkdir(parents=True, exist_ok=True)
        rag.vectorstore.save_local(str(index_dir))

        documents = _vectorstore_documents(rag.vectorstore)
        sources = sorted(
            {
                str(doc.metadata.get("source"))
                for doc in documents
                if getattr(doc, "metadata", None) and doc.metadata.get("source")
            }
        )
        manifest = {
            "index_format": "langchain-faiss-save-local",
            "embedding_model": rag.config["hf_embedding_model"],
            "embedding_device_at_export": rag.config["device"],
            "embedding_normalize": True,
            "chunk_size": rag.config["chunk_size"],
            "chunk_overlap": rag.config["chunk_overlap"],
            "rag_directory": str(rag.rag_directory),
            "cache_file": str(rag.cache_file),
            "chunk_count": len(documents),
            "source_count": len(sources),
            "sources": sources,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "files": {
                "faiss_index": "faiss_index/index.faiss",
                "docstore": "faiss_index/index.pkl",
                "manifest": "manifest.json",
            },
        }
        manifest_path = out_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        elapsed = time.time() - export_start
        print("✅ FAISS 索引导出完成")
        print(f"  index.faiss: {index_dir / 'index.faiss'}")
        print(f"  index.pkl:   {index_dir / 'index.pkl'}")
        print(f"  manifest:    {manifest_path}")
        print(f"  chunks:      {len(documents)}")
        print(f"  sources:     {len(sources)}")
        print(f"  耗时:        {format_time(elapsed)}")
        print("\n上传 HF Dataset 时上传导出目录内的 faiss_index/ 和 manifest.json。")
        return 0
    except Exception as e:
        logger.error(f"导出FAISS索引失败: {e}", exc_info=True)
        print(f"\n❌ 导出失败: {e}")
        return 1


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="RAG工具 - 管理RAG数据库和PDF转换",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 扫描目录
  python rag_tools.py scan

  # 转换所有未转换的PDF
  python rag_tools.py convert

  # 强制重新转换所有PDF
  python rag_tools.py convert --force

  # 构建RAG数据库
  python rag_tools.py build

  # 强制重新转换PDF并重建数据库
  python rag_tools.py build --force-convert --force-rebuild

  # 导出可上传到 Hugging Face Dataset 的 FAISS 索引
  python rag_tools.py export-faiss --output resources/faiss
  python rag_tools.py --export-faiss --output resources/faiss

  # 转换指定PDF（保持同目录同名）
  python rag_tools.py convert-file --file /path/to/file.pdf
  python rag_tools.py convert-file --file /path/to/file.pdf --force-ocr
        """
    )
    parser.add_argument(
        '--export-faiss',
        action='store_true',
        help='导出可上传到 Hugging Face Dataset 的 FAISS 索引'
    )
    parser.add_argument(
        '--output',
        type=str,
        default="resources/faiss",
        help='--export-faiss 的输出目录（默认：resources/faiss）'
    )
    parser.add_argument(
        '--force-rebuild',
        action='store_true',
        help='配合 --export-faiss 使用，导出前强制重建向量数据库'
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # scan命令
    scan_parser = subparsers.add_parser('scan', help='扫描目录，显示PDF和MD文件')
    scan_parser.add_argument(
        '--directory', '-d',
        type=str,
        default=None,
        help=f'要扫描的目录（默认：{config.RAG_DIRECTORY}）'
    )
    
    # convert命令
    convert_parser = subparsers.add_parser('convert', help='转换PDF文件为Markdown')
    convert_parser.add_argument(
        '--directory', '-d',
        type=str,
        default=None,
        help=f'要处理的目录（默认：{config.RAG_DIRECTORY}）'
    )
    convert_parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='强制重新转换所有PDF文件'
    )
    convert_parser.add_argument(
        '--force-ocr',
        action='store_true',
        help='强制使用OCR解析PDF'
    )

    # convert-file命令
    convert_file_parser = subparsers.add_parser('convert-file', help='转换指定PDF为Markdown')
    convert_file_parser.add_argument(
        '--file', '-f',
        type=str,
        required=True,
        help='PDF文件路径'
    )
    convert_file_parser.add_argument(
        '--force',
        action='store_true',
        help='强制重新转换（覆盖已有MD）'
    )
    convert_file_parser.add_argument(
        '--force-ocr',
        action='store_true',
        help='强制使用OCR解析PDF'
    )
    
    # build命令
    build_parser = subparsers.add_parser('build', help='构建RAG向量数据库')
    build_parser.add_argument(
        '--directory', '-d',
        type=str,
        default=None,
        help=f'文档目录（默认：{config.RAG_DIRECTORY}）'
    )
    build_parser.add_argument(
        '--force-convert',
        action='store_true',
        help='强制重新转换所有PDF文件'
    )
    build_parser.add_argument(
        '--force-rebuild',
        action='store_true',
        help='强制重新构建向量数据库（不使用缓存）'
    )

    # export-faiss命令
    export_parser = subparsers.add_parser(
        'export-faiss',
        help='导出可上传到 Hugging Face Dataset 的 FAISS 索引'
    )
    export_parser.add_argument(
        '--directory', '-d',
        type=str,
        default=None,
        help=f'文档目录（默认：{config.RAG_DIRECTORY}）'
    )
    export_parser.add_argument(
        '--output', '-o',
        type=str,
        default="resources/faiss",
        help='输出目录（默认：resources/faiss）'
    )
    export_parser.add_argument(
        '--force-rebuild',
        action='store_true',
        help='导出前强制重新构建向量数据库'
    )

    args = parser.parse_args()

    if args.export_faiss:
        return export_faiss_command(output=args.output, force_rebuild=args.force_rebuild)

    if not args.command:
        parser.print_help()
        return 1
    
    try:
        if args.command == 'scan':
            return scan_command(args.directory)
        elif args.command == 'convert':
            return convert_command(args.directory, args.force, args.force_ocr)
        elif args.command == 'convert-file':
            rag = RAGManager(rag_directory=config.RAG_DIRECTORY)
            parse_method = "ocr" if args.force_ocr else "auto"
            convert_start = time.time()
            result = rag.convert_pdf_to_md(
                args.file, force_reconvert=args.force, parse_method=parse_method
            )
            elapsed = time.time() - convert_start
            if result:
                print(f"✅ 转换完成: {result}")
                print(f"⏱️  耗时: {format_time(elapsed)}")
                return 0
            print("❌ 转换失败")
            print(f"⏱️  耗时: {format_time(elapsed)}")
            return 1
        elif args.command == 'build':
            return build_command(args.directory, args.force_convert, args.force_rebuild)
        elif args.command == 'export-faiss':
            return export_faiss_command(args.directory, args.output, args.force_rebuild)
        else:
            parser.print_help()
            return 1
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
        return 1
    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=True)
        print(f"\n❌ 执行失败: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
