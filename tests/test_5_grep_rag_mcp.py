#!/usr/bin/env python3
"""
Test Grep RAG MCP server.

Usage:
    python tests/test_5_grep_rag_mcp.py
    python tests/test_5_grep_rag_mcp.py --tool-name grep_lookup_character --tool-arg "character=东海帝王"
    python tests/test_5_grep_rag_mcp.py --tool-name grep_character_search --tool-arg "character=东海帝王" --tool-arg "query=菊花賞"
    python tests/test_5_grep_rag_mcp.py --tool-name grep_search --tool-arg "query=スペシャルウィーク"
    python tests/test_5_grep_rag_mcp.py --tool-name grep_search_many --tool-arg 'queries=["スペシャルウィーク","メジロマックイーン"]'
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Optional

import pytest
from dotenv import load_dotenv
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

pytest_plugins = ("pytest_asyncio",)

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

load_dotenv()


def parse_tool_args(args_str_list: list[str]) -> dict[str, Any]:
    result = {}
    for item in args_str_list or []:
        if "=" not in item:
            raise ValueError(f"Invalid tool-arg format: {item}, expected key=value")
        key, value = item.split("=", 1)
        try:
            value = json.loads(
                value.lower() if value.lower() in ("true", "false", "null") else value
            )
        except json.JSONDecodeError:
            pass
        result[key] = value
    return result


class TestGrepRAGMCP:
    @pytest.fixture
    def server_url(self):
        return "http://127.0.0.1:7779/mcp"

    @pytest.mark.asyncio
    async def test_mcp_connection_and_list_tools(self, server_url):
        try:
            async with streamablehttp_client(server_url) as (
                read_stream,
                write_stream,
                get_session_id,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools = await load_mcp_tools(session)
                    tool_names = [tool.name for tool in tools]
                    assert "grep_corpus_overview" in tool_names
                    assert "grep_lookup_character" in tool_names
                    assert "grep_search" in tool_names
                    assert "grep_search_many" in tool_names
                    assert "grep_character_search" in tool_names
        except Exception as exc:
            pytest.skip(f"Grep RAG MCP server is not running: {exc}")

    @pytest.mark.asyncio
    async def test_grep_search_tool_direct_call(self, server_url):
        try:
            async with streamablehttp_client(server_url) as (
                read_stream,
                write_stream,
                get_session_id,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools = await load_mcp_tools(session)
                    tool_dict = {tool.name: tool for tool in tools}
                    result = await tool_dict["grep_search"].ainvoke(
                        {
                            "query": "スペシャルウィーク",
                            "max_results": 5,
                            "context_lines": 1,
                        }
                    )
                    assert result is not None
        except Exception as exc:
            pytest.skip(f"Grep RAG MCP server is not running: {exc}")


async def async_main(
    server_url: str,
    tool_name: Optional[str] = None,
    tool_args: Optional[dict[str, Any]] = None,
):
    async with streamablehttp_client(server_url) as (
        read_stream,
        write_stream,
        get_session_id,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print("✓ Grep RAG MCP server session initialized")

            tools = await load_mcp_tools(session)
            tool_dict = {tool.name: tool for tool in tools}
            print(f"✓ Tools: {[tool.name for tool in tools]}")

            for tool in tools:
                print(f"\nTool: {tool.name}")
                print(f"  Args Schema: {tool.args}")
                print(f"  Description: {tool.description}")

            if not tool_name:
                return
            if tool_name not in tool_dict:
                print(f"Tool not found: {tool_name}")
                return

            tool_args = tool_args or {}
            print(f"\nCalling tool: {tool_name}, args: {tool_args}")
            result = await tool_dict[tool_name].ainvoke(tool_args)
            print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Grep RAG MCP Server")
    parser.add_argument(
        "-u",
        "--base_url",
        type=str,
        default="http://127.0.0.1:7779/mcp",
        help="Grep RAG MCP server base URL",
    )
    parser.add_argument("--tool-name", type=str, default=None)
    parser.add_argument(
        "--tool-arg",
        action="append",
        default=[],
        help="Tool argument in key=value format",
    )
    parser.add_argument("--pytest", action="store_true")
    args = parser.parse_args()

    if args.pytest:
        pytest.main([__file__, "-v", "-s"])
    else:
        asyncio.run(
            async_main(
                server_url=args.base_url,
                tool_name=args.tool_name,
                tool_args=parse_tool_args(args.tool_arg),
            )
        )
