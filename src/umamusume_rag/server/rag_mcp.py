"""
RAG MCP server.

Start with:
  python -m umamusume_rag.server.rag_mcp --http -p 7778
"""

from __future__ import annotations

import argparse
import contextlib
import sys
from collections.abc import AsyncIterator

import uvicorn
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from mcp.server import FastMCP, Server
from mcp.server.sse import SseServerTransport
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
from starlette.types import Receive, Scope, Send

from ..rag import initialize_rag, rag_manager
from ..config import config

config.validate()

llm = ChatOpenAI(
    model_name=config.INFO_LLM_MODEL_NAME,
    api_key=config.INFO_LLM_MODEL_API_KEY or config.DASHSCOPE_API_KEY,
    base_url=config.INFO_LLM_MODEL_BASE_URL,
)

# 初始化RAG系统
print("正在初始化RAG系统...")
initialize_rag(mode="auto", force_rebuild=False)

if rag_manager.vectorstore is None:
    raise RuntimeError("RAG 初始化失败，未找到向量数据库。请检查文档目录和配置。")

def _build_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "你是一个专业的知识查询助手。\n"
                    "你的任务是根据下述给定的已知信息回答用户问题。\n"
                    "确保你的回复完全依据下述已知信息，不要编造答案。\n"
                    "如果已知信息不足以回答问题，请明确告知用户。\n"
                    "请用中文回答用户问题。\n\n"
                    "已知信息:\n{context}"
                ),
            ),
            ("user", "{question}"),
        ]
    )


def _retrieve_documents(query: str, k: int = 4, max_snippet_chars: int = 500):
    docs_with_scores = rag_manager.search_with_scores(query, k=k)
    documents = []
    for doc, score in docs_with_scores:
        snippet = doc.page_content.strip()
        if len(snippet) > max_snippet_chars:
            snippet = snippet[: max_snippet_chars - 3] + "..."
        documents.append(
            {
                "content": snippet,
                "source": doc.metadata.get("source", "Unknown"),
                "score": float(score) if score is not None else None,
            }
        )
    return documents


def _build_context(documents, max_context_chars: int = 2000) -> str:
    context_parts = []
    total_chars = 0
    for idx, doc in enumerate(documents, start=1):
        part = f"[DOC {idx}] 来源: {doc.get('source', 'Unknown')}\n内容: {doc['content']}"
        if context_parts and total_chars + len(part) > max_context_chars:
            break
        context_parts.append(part)
        total_chars += len(part)
    return "\n\n".join(context_parts)


prompt_template = _build_prompt()


mcp = FastMCP("RAG Search MCP")


@mcp.tool(description="""
            Use Local Vector Database (RAG) to answer questions based on your knowledge base.
            This tool searches through indexed documents and provides accurate, context-aware answers.
            
            Parameters:
                question (str): The question to ask about the knowledge base
            
            Returns:
                dict: Contains status and result fields
                    - status: "success" or "error"
                    - result: The answer based on the knowledge base
            
            Example:
                Input: {"question": "What is the main topic of the document?"}
                Output: {"status": "success", "result": "The document discusses..."}

""")

async def rag(
    question: str,
    top_k: int = 4,
    max_context_chars: int = 2000,
    max_snippet_chars: int = 500,
):
    try:
        # 获取用户问题
        user_question = question.strip()
        if not user_question:
            return {"status": "error", "message": "问题不能为空"}
        print(user_question)

        documents = _retrieve_documents(
            user_question, k=top_k, max_snippet_chars=max_snippet_chars
        )
        if not documents:
            return {"status": "error", "message": "知识库中未找到相关内容。"}

        context_text = _build_context(
            documents, max_context_chars=max_context_chars
        )
        if not context_text:
            return {"status": "error", "message": "上下文构建失败。"}

        messages = prompt_template.format_messages(
            context=context_text, question=user_question
        )
        completion = llm.invoke(messages)
        answer_text = (
            completion.content if hasattr(completion, "content") else str(completion)
        )

        # 返回答案
        print(answer_text)
        return {
            "status":"success",
            "result":str(answer_text)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }        

@mcp.tool(description="""
    搜索相关的文档片段。
    
    参数:
        query (str): 搜索查询
        k (int): 返回的文档数量，默认为3
    
    返回:
        dict: 包含搜索结果的字典
""")
async def search_documents(query: str, k: int = 3):
    try:
        # 使用RAG管理器进行搜索
        results = rag_manager.search(query, k=k)
        
        search_results = []
        for i, doc in enumerate(results, 1):
            search_results.append({
                "id": i,
                "content": doc.page_content,
                "source": doc.metadata.get("source", "Unknown"),
                "metadata": doc.metadata
            })
        
        return {
            "status": "success",
            "results": search_results
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@mcp.tool(description="""
    重新加载RAG系统。
    
    参数:
        force_rebuild (bool): 是否强制重建向量数据库，默认为True
    
    返回:
        dict: 操作结果
""")
async def reload_rag(force_rebuild: bool = True):
    try:
        initialize_rag(mode="auto", force_rebuild=force_rebuild)
        if rag_manager.vectorstore is None:
            return {"status": "error", "message": "RAG 初始化失败，向量数据库为空"}
        return {
            "status": "success",
            "message": "RAG系统已重新加载"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    sse = SseServerTransport("/messages/")
    session_manager = StreamableHTTPSessionManager(
        app=mcp_server,
        event_store=None,
        json_response=True,
        stateless=True,
    )

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    async def handle_streamable_http(
        scope: Scope, receive: Receive, send: Send
    ) -> None:
        await session_manager.handle_request(scope, receive, send)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        """Context manager for session manager."""
        async with session_manager.run():
            print("Application started with StreamableHTTP session manager!")
            try:
                yield
            finally:
                print("Application shutting down...")

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/mcp", app=handle_streamable_http),
            Mount("/messages/", app=sse.handle_post_message),
        ],
        lifespan=lifespan,
    )

rag_mcp_app = create_starlette_app(mcp._mcp_server, debug=True)
# Main entry point
def main():
    mcp_server = mcp._mcp_server

    parser = argparse.ArgumentParser(description="Run RAG MCP server")

    parser.add_argument(
        "--http",
        action="store_true",
        help="Run the server with Streamable HTTP and SSE transport rather than STDIO (default: False)",
    )
    parser.add_argument(
        "--sse",
        action="store_true",
        help="(Deprecated) An alias for --http (default: False)",
    )
    parser.add_argument(
        "--host", default=None, help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port","-p", type=int, default=None, help="Port to listen on (default: 8887)"
    )
    args = parser.parse_args()
    print(f"🚀 Starting server on port {args.port}")
    use_http = args.http or args.sse

    if not use_http and (args.host or args.port):
        parser.error(
            "Host and port arguments are only valid when using streamable HTTP or SSE transport (see: --http)."
        )
        sys.exit(1)

    if use_http:
        starlette_app = create_starlette_app(mcp_server, debug=True)
        uvicorn.run(
            starlette_app,
            host=args.host if args.host else "127.0.0.1",
            port=args.port if args.port else 7778,
        )
    else:
        mcp.run()


if __name__ == "__main__":
    main()
