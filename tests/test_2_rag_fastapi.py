#!/usr/bin/env python3
"""
Simple FastAPI smoke test for the RAG service.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, Tuple
from urllib import request, error


def _request_json(
    method: str,
    url: str,
    payload: Dict[str, Any] | None = None,
    timeout: int = 60,
) -> Tuple[int, Dict[str, Any] | str]:
    headers = {"Content-Type": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            try:
                return response.status, json.loads(body)
            except json.JSONDecodeError:
                return response.status, body
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else ""
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, body


def main() -> int:
    parser = argparse.ArgumentParser(description="Test RAG FastAPI endpoints")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:7777",
        help="FastAPI base URL",
    )
    parser.add_argument(
        "--query",
        default="测试查询",
        help="Query for /search",
    )
    parser.add_argument(
        "--question",
        default="这个文档主要讲什么？",
        help="Question for /ask",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=4,
        help="Top K documents",
    )
    parser.add_argument(
        "--skip-ask",
        action="store_true",
        help="Skip /ask request",
    )
    parser.add_argument(
        "--skip-reload",
        action="store_true",
        help="Skip /reload request",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    print("== /health ==")
    status, payload = _request_json("GET", f"{base_url}/health")
    print(f"status={status} payload={payload}")
    if status != 200:
        return 1

    print("\n== /search ==")
    status, payload = _request_json(
        "POST",
        f"{base_url}/search",
        {
            "query": args.query,
            "top_k": args.top_k,
        },
    )
    print(f"status={status} payload={payload}")
    if status != 200:
        return 1

    if not args.skip_ask:
        print("\n== /ask ==")
        status, payload = _request_json(
            "POST",
            f"{base_url}/ask",
            {
                "question": args.question,
                "top_k": args.top_k,
                "include_documents": True,
            },
        )
        print(f"status={status} payload={payload}")
        if status != 200:
            return 1

    if not args.skip_reload:
        print("\n== /reload ==")
        status, payload = _request_json("POST", f"{base_url}/reload")
        print(f"status={status} payload={payload}")
        if status != 200:
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
