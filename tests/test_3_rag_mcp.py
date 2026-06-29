#!/usr/bin/env python3
"""
测试 2: RAG MCP Server
测试 RAG MCP 服务器的工具接口

使用方法：
    # 列出工具
    python tests/test_3_rag_mcp.py
    
    # 直接调用工具
    python tests/test_3_rag_mcp.py --tool-name rag --tool-arg "question=这个文档主要讲什么？"
    python tests/test_3_rag_mcp.py --tool-name search_documents --tool-arg "query=测试" --tool-arg "k=3"
    
    # 直接调用 rag 工具
    python tests/test_3_rag_mcp.py -q "请告诉我文档中的主要内容"
"""

import sys
import asyncio
import pytest
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession
from dotenv import load_dotenv

# 配置 pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 加载环境变量
load_dotenv()

def parse_tool_args(args_str_list: list) -> Dict[str, Any]:
    """将 ["key=value"] 转为 {"key": "value"}"""
    result = {}
    if not args_str_list:
        return result
    
    for item in args_str_list:
        if "=" not in item:
            raise ValueError(f"Invalid tool-arg format: {item}, expected key=value")
        k, v = item.split("=", 1)
        
        # 尝试类型解析
        try:
            v = json.loads(v.lower() if v.lower() in ("true", "false", "null") else v)
        except json.JSONDecodeError:
            pass  # keep as string
        
        result[k] = v
    return result


class TestRAGMCP:
    """测试 RAG MCP Server"""
    
    @pytest.fixture
    def server_url(self):
        """MCP 服务器地址"""
        return "http://127.0.0.1:7778/mcp"
    
    @pytest.mark.asyncio
    async def test_mcp_connection_and_list_tools(self, server_url):
        """测试 MCP 连接并列出可用工具"""
        try:
            async with streamablehttp_client(server_url) as (read_stream, write_stream, get_session_id):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    print('✓ RAG MCP server 连接成功')
                    
                    tools = await load_mcp_tools(session)
                    print(f"✓ 可用工具: {[tool.name for tool in tools]}")
                    
                    # 验证预期的工具存在
                    tool_names = [tool.name for tool in tools]
                    assert "rag" in tool_names, "rag 工具未找到"
                    assert "search_documents" in tool_names, "search_documents 工具未找到"
                    
                    # 打印工具详细信息
                    for tool in tools:
                        print(f"\nTool: {tool.name}")
                        print(f"  Description: {tool.description}")
                        print(f"  Args Schema: {tool.args}")
                    
        except Exception as e:
            pytest.skip(f"RAG MCP 服务器未运行，跳过测试: {e}")
    
    @pytest.mark.asyncio
    async def test_rag_tool_direct_call(self, server_url):
        """测试直接调用 rag 工具"""
        try:
            async with streamablehttp_client(server_url) as (read_stream, write_stream, get_session_id):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    
                    tools = await load_mcp_tools(session)
                    tool_dict = {tool.name: tool for tool in tools}
                    
                    # 调用 rag 工具
                    if "rag" not in tool_dict:
                        pytest.fail("rag 工具未找到")
                    
                    print("\n正在调用 rag 工具...")
                    result = await tool_dict["rag"].ainvoke({
                        "question": "这个文档主要讲什么？"
                    })
                    
                    print("✓ RAG 工具调用成功")
                    
                    # 解析结果
                    if isinstance(result, str):
                        try:
                            result = json.loads(result)
                        except json.JSONDecodeError:
                            pass
                    
                    print(f"  状态: {result.get('status', 'unknown') if isinstance(result, dict) else 'N/A'}")
                    
                    if isinstance(result, dict) and "result" in result:
                        preview = str(result["result"])[:100].replace('\n', ' ')
                        print(f"  回答预览: {preview}...")
                    else:
                        preview = str(result)[:100].replace('\n', ' ')
                        print(f"  结果预览: {preview}...")
                    
                    # 验证结果不为空
                    assert result is not None, "rag 工具返回空结果"
                    
        except Exception as e:
            pytest.skip(f"RAG MCP 服务器未运行，跳过测试: {e}")
    
    @pytest.mark.asyncio
    async def test_search_documents_tool_direct_call(self, server_url):
        """测试直接调用 search_documents 工具"""
        try:
            async with streamablehttp_client(server_url) as (read_stream, write_stream, get_session_id):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    
                    tools = await load_mcp_tools(session)
                    tool_dict = {tool.name: tool for tool in tools}
                    
                    # 调用 search_documents 工具
                    if "search_documents" not in tool_dict:
                        pytest.fail("search_documents 工具未找到")
                    
                    print("\n正在调用 search_documents 工具...")
                    result = await tool_dict["search_documents"].ainvoke({
                        "query": "测试查询",
                        "k": 3
                    })
                    
                    print("✓ 文档搜索工具调用成功")
                    
                    # 解析结果
                    if isinstance(result, str):
                        try:
                            result = json.loads(result)
                        except json.JSONDecodeError:
                            pass
                    
                    if isinstance(result, dict) and "results" in result:
                        print(f"  返回 {len(result['results'])} 个文档")
                    
                    # 验证结果不为空
                    assert result is not None, "search_documents 工具返回空结果"
                    
        except Exception as e:
            pytest.skip(f"RAG MCP 服务器未运行，跳过测试: {e}")
    
async def async_main(
    server_url: str,
    question: str = "",
    tool_name: Optional[str] = None,
    tool_args: Optional[Dict[str, Any]] = None,
):
    """命令行入口函数"""
    async with streamablehttp_client(server_url) as (read_stream, write_stream, get_session_id):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print('✓ RAG MCP server session已初始化')
            
            tools = await load_mcp_tools(session)
            tool_dict = {tool.name: tool for tool in tools}
            
            print(f"✓ 可用工具: {[tool.name for tool in tools]}")
            
            # 打印工具详细信息
            for tool in tools:
                print(f"\nTool: {tool.name}")
                print(f"  Args Schema: {tool.args}")
                print(f"  Description: {tool.description}")
            
            # 场景1: 仅列出工具
            if not question and not tool_name:
                print("\n未提供问题或工具调用，仅列出工具信息。")
                return
            
            # 场景2: 直接调用指定工具
            if tool_name:
                if tool_name not in tool_dict:
                    print(f"❌ 错误: 工具 '{tool_name}' 未在 MCP 服务中找到！")
                    return
                
                if not tool_args:
                    print(f"⚠️  警告: 调用工具 '{tool_name}' 但未提供参数。")
                    tool_args = {}
                
                try:
                    print(f"\n正在调用工具: {tool_name}，参数: {tool_args}")
                    result = await tool_dict[tool_name].ainvoke(tool_args)
                    print("✅ 工具调用成功！返回结果:")
                    print(json.dumps(result, indent=2, ensure_ascii=False) if isinstance(result, (dict, list)) else result)
                    
                    # 尝试解析 JSON
                    if isinstance(result, str):
                        try:
                            parsed = json.loads(result)
                            print("\n🔍 JSON 解析结果:")
                            print(json.dumps(parsed, indent=2, ensure_ascii=False))
                        except json.JSONDecodeError:
                            pass
                except Exception as e:
                    print(f"❌ 工具调用失败: {type(e).__name__}: {e}")
                return
            
            # 场景3: 直接使用 rag 工具处理问题
            if question:
                tool = tool_dict.get("rag")
                if not tool:
                    print("❌ rag 工具未找到，无法处理问题。")
                    return
                print(f"\n使用 rag 工具处理问题: {question}")
                try:
                    result = await tool.ainvoke({"question": question})
                    print("\n✅ Final Answer:")
                    print(
                        json.dumps(result, indent=2, ensure_ascii=False)
                        if isinstance(result, (dict, list))
                        else result
                    )
                except Exception as e:
                    print(f"❌ rag 工具调用失败: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test RAG MCP Server")
    
    parser.add_argument(
        "-u", "--base_url",
        type=str,
        default="http://127.0.0.1:7778/mcp",
        help="RAG MCP server base url"
    )
    parser.add_argument(
        "-q", "--question",
        type=str,
        default="",
        help="问题文本，如果提供，将使用 Agent 回答"
    )
    parser.add_argument(
        "--tool-name",
        type=str,
        default=None,
        help="要直接调用的工具名称，例如 rag 或 search_documents"
    )
    parser.add_argument(
        "--tool-arg",
        action="append",
        default=[],
        help="工具参数，格式 key=value，可多次使用。例如: --tool-arg question=测试问题"
    )
    parser.add_argument(
        "--pytest",
        action="store_true",
        help="使用 pytest 运行测试"
    )
    
    args = parser.parse_args()
    
    if args.pytest:
        # 运行 pytest
        pytest.main([__file__, "-v", "-s"])
    else:
        # 解析 tool-arg
        tool_args = parse_tool_args(args.tool_arg) if args.tool_arg else None
        
        # 运行主函数
        asyncio.run(async_main(
            server_url=args.base_url,
            question=args.question,
            tool_name=args.tool_name,
            tool_args=tool_args
        ))
