"""
RAG 服务：基于本地向量库的知识检索与问答
"""

from __future__ import annotations

import argparse
import logging
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ..config import config
from ..rag import initialize_rag, rag_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SearchRequest(BaseModel):
    query: str = Field(..., description="检索查询")
    top_k: int = Field(
        default=4, ge=1, le=10, description="返回的参考文档数量 (1-10)"
    )
    max_snippet_chars: int = Field(
        default=500, ge=100, le=2000, description="单条文档最大长度"
    )


class AskRequest(BaseModel):
    question: str = Field(..., description="用户问题")
    top_k: int = Field(
        default=4, ge=1, le=10, description="返回的参考文档数量 (1-10)"
    )
    max_context_chars: int = Field(
        default=2000, ge=200, le=8000, description="拼接上下文的最大长度"
    )
    max_snippet_chars: int = Field(
        default=500, ge=100, le=2000, description="单条文档最大长度"
    )
    include_documents: bool = Field(default=True, description="是否返回文档片段")


class RagDocument(BaseModel):
    content: str = Field(..., description="文档片段内容")
    source: Optional[str] = Field(None, description="文档来源")
    score: Optional[float] = Field(None, description="相似度分数，数值越小越相关")


class SearchResponse(BaseModel):
    documents: List[RagDocument] = Field(default_factory=list)


class RagAnswer(BaseModel):
    answer: str = Field(..., description="基于资料生成的回答")
    documents: List[RagDocument] = Field(
        default_factory=list, description="参考的文档片段"
    )


def _build_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "你是一名专业的知识检索助理。你将看到根据用户问题检索到的参考资料。\n"
                    "请严格依据这些资料进行回答，不要编造内容。\n"
                    "如果资料不足以回答问题，请明确说明。\n"
                    "回答请使用中文，并尽量简洁准确。\n\n"
                    "参考资料：\n{context}"
                ),
            ),
            ("user", "{question}"),
        ]
    )


def _build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model_name=config.INFO_LLM_MODEL_NAME,
        api_key=config.INFO_LLM_MODEL_API_KEY or config.DASHSCOPE_API_KEY,
        base_url=config.INFO_LLM_MODEL_BASE_URL,
    )


def _ensure_rag_initialized(force_rebuild: bool = False) -> None:
    logger.info("正在初始化本地知识库 (RAG)...")
    initialize_rag(force_rebuild=force_rebuild)
    if rag_manager.vectorstore is None:
        raise RuntimeError("RAG 初始化失败，未找到向量数据库。请检查文档目录和配置。")
    logger.info("RAG 初始化完成。")


def _retrieve_documents(
    query: str, top_k: int, max_snippet_chars: int
) -> List[RagDocument]:
    docs_with_scores = rag_manager.search_with_scores(query, k=top_k)
    documents: List[RagDocument] = []

    for doc, score in docs_with_scores:
        snippet = doc.page_content.strip()
        if len(snippet) > max_snippet_chars:
            snippet = snippet[: max_snippet_chars - 3] + "..."

        documents.append(
            RagDocument(
                content=snippet,
                source=doc.metadata.get("source"),
                score=float(score) if score is not None else None,
            )
        )
    return documents


def _build_context(
    documents: List[RagDocument], max_context_chars: int
) -> str:
    context_parts = []
    total_chars = 0

    for idx, doc in enumerate(documents, start=1):
        part = f"[DOC {idx}] 来源: {doc.source or 'Unknown'}\n内容: {doc.content}"
        if context_parts and total_chars + len(part) > max_context_chars:
            break
        context_parts.append(part)
        total_chars += len(part)

    return "\n\n".join(context_parts)


def create_app() -> FastAPI:
    config.validate()
    app = FastAPI(
        title="RAG Service",
        description="基于本地知识库的检索增强问答服务",
        version="2.1.0",
    )

    llm = _build_llm()
    prompt_template = _build_prompt()

    @app.on_event("startup")
    async def _prepare_retriever() -> None:
        _ensure_rag_initialized(force_rebuild=False)
        logger.info("RAG 服务已就绪。")

    @app.post("/search", response_model=SearchResponse, summary="检索相关文档")
    async def search_documents(request: SearchRequest) -> SearchResponse:
        if rag_manager.vectorstore is None:
            raise HTTPException(
                status_code=503, detail="RAG 未初始化，无法处理请求。"
            )
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="查询内容不能为空。")

        documents = _retrieve_documents(
            request.query, request.top_k, request.max_snippet_chars
        )
        if not documents:
            raise HTTPException(
                status_code=404, detail="知识库中未找到相关内容。"
            )
        return SearchResponse(documents=documents)

    @app.post("/ask", response_model=RagAnswer, summary="基于知识库生成回答")
    async def ask_question(request: AskRequest) -> RagAnswer:
        if rag_manager.vectorstore is None:
            raise HTTPException(
                status_code=503, detail="RAG 未初始化，无法处理请求。"
            )
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="问题不能为空。")

        documents = _retrieve_documents(
            request.question, request.top_k, request.max_snippet_chars
        )
        if not documents:
            raise HTTPException(
                status_code=404, detail="知识库中未找到相关内容。"
            )

        context_text = _build_context(documents, request.max_context_chars)
        if not context_text:
            raise HTTPException(
                status_code=500, detail="上下文构建失败，请调整参数。"
            )

        try:
            messages = prompt_template.format_messages(
                context=context_text, question=request.question
            )
            completion = llm.invoke(messages)
            answer_text = (
                completion.content
                if hasattr(completion, "content")
                else str(completion)
            )
        except Exception as exc:
            logger.exception("LLM 生成回答失败: %s", exc)
            raise HTTPException(
                status_code=500, detail=f"LLM 生成回答失败: {exc}"
            ) from exc

        return RagAnswer(
            answer=answer_text,
            documents=documents if request.include_documents else [],
        )

    @app.post("/reload", summary="重新加载知识库")
    async def reload_rag() -> dict:
        try:
            _ensure_rag_initialized(force_rebuild=True)
            return {"status": "success", "message": "RAG 系统已重新加载"}
        except Exception as exc:
            logger.exception("重新加载 RAG 失败: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/health", summary="健康检查")
    async def health_check() -> dict:
        return {
            "status": "healthy" if rag_manager.vectorstore else "unavailable",
            "rag_initialized": rag_manager.vectorstore is not None,
        }

    return app


app = create_app()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="启动本地 RAG 服务，用于知识库检索与问答"
    )
    parser.add_argument(
        "-p", "--port", type=int, default=7777, help="服务监听端口 (默认: 7777)"
    )
    args = parser.parse_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port)
