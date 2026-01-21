#!/usr/bin/env python3
"""
项目入口：启动 RAG HTTP 服务。
"""

from __future__ import annotations

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Start RAG HTTP service")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="监听地址")
    parser.add_argument("-p", "--port", type=int, default=7777, help="监听端口")
    args = parser.parse_args()

    uvicorn.run("umamusume_rag.server.rag_query:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
