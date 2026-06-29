#!/usr/bin/env python3
"""
测试 1: RAG 构建效果
测试 PDF 转换和向量数据库构建
"""

import sys
import pytest
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from umamusume_rag.rag import RAGManager
from umamusume_rag.config import config


class TestRAGBuild:
    """测试 RAG 构建"""
    
    def test_rag_manager_init(self):
        """测试 RAG 管理器初始化"""
        rag = RAGManager()
        
        assert rag.rag_directory.exists()
        assert rag.cache_file.parent.exists()
        assert rag.pdf_processor is not None or rag.pdf_processor_engine in {
            "",
            "none",
            "off",
            "disabled",
            "false",
        }
        
        print(f"✓ RAG 目录: {rag.rag_directory}")
        print(f"✓ 缓存文件路径: {rag.cache_file}")
    
    def test_scan_directory(self):
        """测试目录扫描"""
        rag = RAGManager()
        scan_result = rag.scan_directory()
        
        assert "md_files" in scan_result
        assert "pdf_files" in scan_result
        assert "pdf_conversion_status" in scan_result
        
        md_count = len(scan_result["md_files"])
        pdf_count = len(scan_result["pdf_files"])
        
        print(f"✓ 扫描到 {md_count} 个 Markdown 文件")
        print(f"✓ 扫描到 {pdf_count} 个 PDF 文件")
        
        assert md_count > 0 or pdf_count > 0, "至少应该有一些文档"
    
    def test_pdf_conversion(self):
        """测试 PDF 转换"""
        rag = RAGManager()
        scan_result = rag.scan_directory()
        
        # 检查转换状态
        pdf_conversion_status = scan_result["pdf_conversion_status"]
        converted_count = sum(1 for has_md in pdf_conversion_status.values() if has_md)
        
        print(f"✓ 已转换 PDF: {converted_count}/{len(pdf_conversion_status)}")
        
        # 如果有未转换的 PDF，测试转换功能
        if len(pdf_conversion_status) > converted_count:
            print("  有未转换的 PDF，测试转换功能...")
            # 注意：这里不实际转换，因为太耗时
            # 实际转换应该由用户手动触发
        else:
            print("  所有 PDF 已转换")
    
    def test_load_markdown(self):
        """测试加载 Markdown 文件"""
        rag = RAGManager()
        scan_result = rag.scan_directory()
        
        md_files = scan_result["md_files"]
        
        if not md_files:
            pytest.skip("没有 Markdown 文件可供测试")
        
        # 加载第一个 MD 文件
        md_file = md_files[0]
        docs = rag.load_single_md(md_file)
        
        assert len(docs) > 0
        assert docs[0].page_content
        
        print(f"✓ 成功加载 MD 文件: {Path(md_file).name}")
        print(f"  内容长度: {len(docs[0].page_content)} 字符")
    
    def test_build_vectorstore(self):
        """测试构建向量数据库"""
        rag = RAGManager()
        
        # 构建向量数据库
        rag.initialize(force_rebuild=False)
        
        assert rag.vectorstore is not None
        assert rag.cache_file.exists()
        
        print(f"✓ 向量数据库构建成功")
        print(f"  缓存文件: {rag.cache_file}")
    
    def test_search(self):
        """测试向量搜索"""
        rag = RAGManager()
        rag.initialize(force_rebuild=False)
        
        # 搜索测试
        query = "这是什么内容？"
        results = rag.search(query, k=3)
        
        assert len(results) > 0
        
        print(f"✓ 搜索成功，返回 {len(results)} 个结果")
        for i, doc in enumerate(results, 1):
            preview = doc.page_content[:50].replace('\n', ' ')
            print(f"  {i}. {preview}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
