"""
Grep RAG MCP server.

Start with:
  python -m umamusume_rag.server.grep_rag_mcp --http -p 7779
"""

from __future__ import annotations

import argparse
import contextlib
import sys
from collections.abc import AsyncIterator

import uvicorn
from mcp.server import FastMCP, Server
from mcp.server.sse import SseServerTransport
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
from starlette.types import Receive, Scope, Send

from ..grep import (
    CorpusInspector,
    CorpusPolicyError,
    GrepPolicyError,
    RipgrepSearcher,
)

searcher: RipgrepSearcher | None = None
inspector: CorpusInspector | None = None


def _get_searcher() -> RipgrepSearcher:
    global searcher
    if searcher is None:
        searcher = RipgrepSearcher()
    return searcher


def _get_inspector() -> CorpusInspector:
    global inspector
    if inspector is None:
        inspector = CorpusInspector()
    return inspector


mcp = FastMCP("Grep RAG MCP")


@mcp.tool(
    description="""
    Describe the local corpus layout for retrieval planning.

    Use this first when the model needs to understand what can be searched.
    The corpus normally contains a character index CSV and many per-character
    plot markdown files under plot/*.md.

    Parameters:
        sample_limit: number of sample plot files to return
    """
)
async def grep_corpus_overview(sample_limit: int = 20):
    try:
        return _get_inspector().overview(sample_limit=sample_limit)
    except (CorpusPolicyError, FileNotFoundError, NotADirectoryError) as exc:
        return {"status": "error", "message": str(exc)}
    except Exception as exc:
        return {"status": "error", "message": f"corpus overview failed: {exc}"}


@mcp.tool(
    description="""
    Resolve a character name to canonical aliases and plot-file globs.

    Use this when the user names a character in Chinese, English, or Japanese.
    Then pass the returned file_globs to grep_search or grep_search_many to
    avoid cameo pollution from other characters' plot files.

    Parameters:
        character: character name or alias, for example "东海帝王" or "Tokai Teio"
        max_results: maximum character candidates to return
    """
)
async def grep_lookup_character(character: str, max_results: int = 5):
    try:
        return _get_inspector().lookup_character(character, max_results=max_results)
    except (CorpusPolicyError, FileNotFoundError, NotADirectoryError) as exc:
        return {"status": "error", "message": str(exc)}
    except Exception as exc:
        return {"status": "error", "message": f"character lookup failed: {exc}"}


@mcp.tool(
    description="""
    Search local knowledge-base text files with safe ripgrep fixed-string search.

    The model may pass only a search term and constrained options. This tool
    never executes arbitrary shell commands and never interprets the query as
    a regular expression.

    Parameters:
        query: literal search term
        max_results: maximum returned matches, clamped to a safe limit
        context_lines: surrounding lines per match, clamped to a safe limit
        file_globs: optional comma-separated relative globs, e.g. "*.md,plot/*.md"
        ignore_case: case-insensitive matching
    """
)
async def grep_search(
    query: str,
    max_results: int = 20,
    context_lines: int = 2,
    file_globs: str = "",
    ignore_case: bool = False,
):
    try:
        return _get_searcher().search(
            query=query,
            max_results=max_results,
            context_lines=context_lines,
            file_globs=file_globs,
            ignore_case=ignore_case,
        )
    except (GrepPolicyError, FileNotFoundError, NotADirectoryError, RuntimeError) as exc:
        return {"status": "error", "message": str(exc)}
    except Exception as exc:
        return {"status": "error", "message": f"grep search failed: {exc}"}


@mcp.tool(
    description="""
    Search local knowledge-base text files with multiple literal terms.

    This searches each provided term one by one using the same safe fixed-string
    ripgrep wrapper as grep_search. Terms are not translated or expanded.

    Parameters:
        queries: list of literal search terms
        max_results_per_query: maximum returned matches for each term
        context_lines: surrounding lines per match
        file_globs: optional comma-separated relative globs
        ignore_case: case-insensitive matching
    """
)
async def grep_search_many(
    queries: list[str],
    max_results_per_query: int = 10,
    context_lines: int = 2,
    file_globs: str = "",
    ignore_case: bool = False,
):
    try:
        return _get_searcher().search_many(
            queries=queries,
            max_results_per_query=max_results_per_query,
            context_lines=context_lines,
            file_globs=file_globs,
            ignore_case=ignore_case,
        )
    except (GrepPolicyError, FileNotFoundError, NotADirectoryError, RuntimeError) as exc:
        return {"status": "error", "message": str(exc)}
    except Exception as exc:
        return {"status": "error", "message": f"grep search failed: {exc}"}


@mcp.tool(
    description="""
    Search a character's own plot file with literal keywords.

    This combines grep_lookup_character and grep_search_many. It first resolves
    the character into plot-file globs, then searches only inside those files.
    The character name can be Chinese, English, or Japanese via the character
    CSV index. Query terms are not translated or expanded and must match the
    corpus text literally.

    Parameters:
        character: character name or alias
        query: primary literal search term chosen by the caller
        extra_queries: optional additional literal search terms chosen by the caller
        max_results_per_query: maximum returned matches for each term
        context_lines: surrounding lines per match
    """
)
async def grep_character_search(
    character: str,
    query: str,
    extra_queries: list[str] | None = None,
    max_results_per_query: int = 10,
    context_lines: int = 2,
):
    try:
        scope = _get_inspector().best_character_scope(character)
        if scope.get("status") != "success":
            return scope

        queries = _unique_terms([query] + (extra_queries or []))
        file_globs = scope["file_globs"]
        search_result = _get_searcher().search_many(
            queries=queries,
            max_results_per_query=max_results_per_query,
            context_lines=context_lines,
            file_globs=file_globs,
        )
        return {
            "status": search_result.get("status", "success"),
            "character": scope["character"],
            "file_globs": file_globs,
            "queries": queries,
            "search": search_result,
        }
    except (
        CorpusPolicyError,
        GrepPolicyError,
        FileNotFoundError,
        NotADirectoryError,
        RuntimeError,
    ) as exc:
        return {"status": "error", "message": str(exc)}
    except Exception as exc:
        return {"status": "error", "message": f"character grep search failed: {exc}"}


def _unique_terms(queries: list[str]) -> list[str]:
    result = []
    seen = set()
    for query in queries:
        if not isinstance(query, str):
            continue
        term = query.strip()
        if term and term not in seen:
            result.append(term)
            seen.add(term)
    return result


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

    async def handle_streamable_http(scope: Scope, receive: Receive, send: Send) -> None:
        await session_manager.handle_request(scope, receive, send)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        async with session_manager.run():
            _get_inspector()
            _get_searcher()
            print("Grep RAG MCP server started with StreamableHTTP session manager.")
            try:
                yield
            finally:
                print("Grep RAG MCP server shutting down.")

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/mcp", app=handle_streamable_http),
            Mount("/messages/", app=sse.handle_post_message),
        ],
        lifespan=lifespan,
    )


grep_rag_mcp_app = create_starlette_app(mcp._mcp_server, debug=True)


def main():
    mcp_server = mcp._mcp_server

    parser = argparse.ArgumentParser(description="Run Grep RAG MCP server")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run with Streamable HTTP and SSE transport rather than STDIO",
    )
    parser.add_argument(
        "--sse",
        action="store_true",
        help="(Deprecated) An alias for --http",
    )
    parser.add_argument("--host", default=None, help="Host to bind to")
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=None,
        help="Port to listen on (default: 7779)",
    )
    args = parser.parse_args()
    use_http = args.http or args.sse

    if not use_http and (args.host or args.port):
        parser.error("Host and port arguments are only valid with --http")
        sys.exit(1)

    if use_http:
        starlette_app = create_starlette_app(mcp_server, debug=True)
        uvicorn.run(
            starlette_app,
            host=args.host if args.host else "127.0.0.1",
            port=args.port if args.port else 7779,
        )
    else:
        mcp.run()


if __name__ == "__main__":
    main()
