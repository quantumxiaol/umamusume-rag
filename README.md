---
title: Umamusume RAG
emoji: 🐎
colorFrom: pink
colorTo: blue
sdk: docker
app_port: 7860
short_description: RAG Umamusume roleplay chat.
---

# umamusume-rag - RAG 知识库工具集

一个专注本地知识库检索（RAG）的项目：支持 PDF 转 Markdown、向量化构建与问答服务（HTTP + MCP）。

## 核心特性

- 本地知识库检索：PDF / Markdown / CSV / TXT
- 多种 PDF 处理：MinerU / MarkItDown / Qwen2.5-VL（OCR）
- 向量检索：FAISS + HuggingFace Embeddings
- 服务方式：HTTP API 与 MCP Server

## 效果

在[运行结果](./docs/result.md)可以看到FastAPI和MCP的结果。
在[赛马娘设定集](./examples/赛马娘设定集.md)可以看到使用QwenVL处理扫描件的效果。

当前Embedding采用的是Qwen/Qwen3-Embedding-0.6B。

## 快速开始

### 环境要求

- Python 3.12+
- uv（推荐的 Python 包管理器）

### 安装

```bash
uv venv --python 3.12
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv sync
```

可选依赖（按需安装）。基础安装只包含本地向量库构建/检索；服务、LLM、PDF 处理都拆成可选层：

```bash
# HTTP / MCP 服务
uv sync --extra server

# LLM 问答（/ask、MCP rag、后续 query expansion）
uv sync --extra llm

# PDF/文档解析能力（按需选择一个或多个）
uv sync --extra pdf-markitdown
uv sync --extra pdf-docling
uv sync --extra pdf-mineru
uv sync --extra pdf-qwen-vl

# 全部 PDF 引擎
uv sync --extra pdf

# 开发与测试工具
uv sync --extra dev

# 全功能开发环境
uv sync --extra all

# 如修改了 pyproject.toml 的依赖，建议更新锁文件
uv lock
```

### 配置

```bash
cp .env.template .env
```

编辑 `.env`。只做 `/search` 或本地向量检索时不需要 LLM API Key：

```env
RAG_DIRECTORY=./resources/docs
HF_EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B
EMBEDDING_DEVICE=cpu
CHUNK_SIZE=500
CHUNK_OVERLAP=100

HF_HOME=./models
HUGGINGFACE_HUB_CACHE=./models/hub

# 仅 /ask / MCP rag 需要
INFO_LLM_MODEL_NAME=qwen-max-latest
INFO_LLM_MODEL_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
INFO_LLM_MODEL_API_KEY=your_api_key_here

# 默认禁用 PDF 处理；如需处理 PDF 再改成 markitdown/mineru/docling/qwen-vl
PDF_PROCESSOR_ENGINE=none
AUTO_CONVERT_PDF_TO_MD=false
PREFER_MARKDOWN_FILES=true
```

### 准备知识库

将文档放入 `resources/docs` 后，使用工具构建向量库：

```bash
python rag_tools.py scan
python rag_tools.py convert
python rag_tools.py build

# 导出可上传到 Hugging Face Dataset 的 FAISS 索引
python rag_tools.py export-faiss --output resources/faiss
# 兼容 flag 写法
python rag_tools.py --export-faiss --output resources/faiss
```

使用 `rag_tools.py` 的常见流程（选择引擎/查看状态/构建/强制重建）：

```bash
# 1) 查看 PDF/MD 状态（是否已转换、MD 是否为空）
python rag_tools.py scan

# 2) 选择 PDF 转换引擎（临时指定）
PDF_PROCESSOR_ENGINE=markitdown python rag_tools.py convert
PDF_PROCESSOR_ENGINE=mineru python rag_tools.py convert
PDF_PROCESSOR_ENGINE=qwen-vl QWEN_VL_DEVICE=mps python rag_tools.py convert

# 3) 转换指定 PDF（输出同目录同名 .md）
PDF_PROCESSOR_ENGINE=qwen-vl python rag_tools.py convert-file --file /path/to/file.pdf

# 4) 构建向量数据库
python rag_tools.py build

# 5) 强制重新转换 + 重新构建数据库
python rag_tools.py build --force-convert --force-rebuild
```

单个 PDF 转换（可选）：

```bash
python rag_tools.py convert-file --file /path/to/file.pdf
python rag_tools.py convert-file --file /path/to/file.pdf --force-ocr
```

Qwen2.5-VL PDF 转换（适合扫描件）：

```python
from umamusume_rag.pdf_processors import QwenVLProcessor

processor = QwenVLProcessor()
md_path = processor.process_pdf_to_markdown(
    "/path/to/file.pdf",
    max_pages=3,
)
print(md_path)
```

选择 PDF 处理引擎（MinerU/MarkItDown/Qwen-VL）：

```env
PDF_PROCESSOR_ENGINE=markitdown
# PDF_PROCESSOR_ENGINE=mineru
# PDF_PROCESSOR_ENGINE=docling
# PDF_PROCESSOR_ENGINE=qwen-vl
AUTO_CONVERT_PDF_TO_MD=true
```

PDF 处理说明：
- `mineru`：结构化提取，适合复杂版式
- `markitdown`：轻量转换，适合文本型 PDF
- `qwen-vl`：OCR 场景，适合扫描件（依赖 `pymupdf`）

PDF 处理资源占用（粗略参考，单页 A4/200-300dpi）：
- `markitdown`：CPU 即可，内存约 0.5-1.5GB，速度最快
- `mineru`：CPU 可用但更慢，内存约 2-6GB；若用 GPU，建议 4-8GB 显存起步
- `qwen-vl`：计算最重，模型权重约 15-18GB（磁盘），推理内存常见 16-24GB + 图像分辨率占用；MPS/显存不足时请降分辨率（建议长边 <= 1280）

图片 OCR（Qwen2.5-VL，输出 Markdown）：

```python
from umamusume_rag.pdf_processors import QwenOCR

ocr = QwenOCR()
markdown = ocr.image_to_markdown("/path/to/image.png")
print(markdown)
```

### 启动服务

#### 1) HTTP RAG 服务

```bash
uv sync --extra server
python main.py
```

默认地址：`http://127.0.0.1:7777`

典型用法（先检索再生成）：

```bash
curl -X POST http://127.0.0.1:7777/search \
  -H "Content-Type: application/json" \
  -d '{"query":"你的问题","top_k":4}'

curl -X POST http://127.0.0.1:7777/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"你的问题","top_k":4,"max_context_chars":2000}'
```

`/ask` 还需要安装 LLM extra 并配置 API Key：

```bash
uv sync --extra llm
```

FastAPI 接口测试（脚本）：

```bash
python tests/test_2_rag_fastapi.py
python tests/test_2_rag_fastapi.py --base-url http://127.0.0.1:7777 --query "测试" --question "这个文档主要讲什么？"
python tests/test_2_rag_fastapi.py --skip-ask
```

#### 2) MCP RAG 服务

```bash
uv sync --extra server --extra llm
python -m umamusume_rag.server.rag_mcp --http -p 7778
```

默认地址：`http://127.0.0.1:7778/mcp/`

MCP 接口测试：

```bash
# 列出工具
python tests/test_3_rag_mcp.py

# 直接提问（rag 工具）
python tests/test_3_rag_mcp.py -q "请告诉我文档中的主要内容"

# 直接调用工具
python tests/test_3_rag_mcp.py --tool-name rag --tool-arg "question=这个文档主要讲什么？"
python tests/test_3_rag_mcp.py --tool-name search_documents --tool-arg "query=测试" --tool-arg "k=3"

# 指定 MCP 地址
python tests/test_3_rag_mcp.py --base_url http://127.0.0.1:7778/mcp -q "测试问题"
```

## 代码使用

```python
from umamusume_rag.rag import RAGManager

rag = RAGManager(rag_directory="./resources/docs")
rag.initialize(force_rebuild=False)

results = rag.search("你的问题", k=4)
for doc in results:
    print(doc.page_content)
```

## 项目结构

```
umamusume-rag/
├── main.py                              # 主启动脚本（HTTP RAG 服务）
├── rag_tools.py                         # RAG 工具脚本（scan/convert/build）
├── download_models.py                   # 模型下载入口（MinerU/Qwen-VL/Embedding）
├── pyproject.toml                       # 依赖和配置
├── docs/
│   └── result.md                        # 运行结果与日志
├── examples/
│   └── 赛马娘设定集.md                  # Qwen-VL OCR 结果示例
├── tests/
│   ├── test_1_rag_build.py              # RAG 构建测试
│   ├── test_2_rag_fastapi.py            # FastAPI 接口测试
│   ├── test_3_rag_mcp.py                # MCP 接口测试
│   ├── pdf_to_md_markitdown.py          # MarkItDown 转换脚本
│   ├── pdf_to_md_mineru.py              # MinerU 转换脚本
│   └── pdf_to_md_qwen_vl.py             # Qwen-VL 转换脚本
├── src/umamusume_rag/                   # 源代码
│   ├── config.py                        # 配置管理（含 HF 缓存路径）
│   ├── rag/
│   │   ├── rag.py                       # RAG 管理器（核心）
│   │   └── download_models.py           # MinerU 模型下载工具
│   ├── pdf_processors/
│   │   ├── mineru_processor.py          # MinerU PDF 处理器
│   │   ├── markitdown_processor.py      # MarkItDown 处理器
│   │   └── qwen_vl_ocr.py               # Qwen2.5-VL OCR
│   └── server/
│       ├── rag_query.py                 # FastAPI RAG 服务
│       └── rag_mcp.py                   # MCP RAG 服务器
├── resources/
│   ├── docs/                            # 知识库文档（PDF/MD/CSV/TXT）
│   └── vector/                          # 向量数据库缓存
└── models/
    ├── hub/                             # HF 缓存（MinerU/Embedding）
    └── Qwen2.5-VL-7B-Instruct           # Qwen2.5-VL 权重
```

## 其他

模型下载（可选）：

```bash
python download_models.py --mineru
python download_models.py --qwen-vl
python download_models.py --embedding
python download_models.py --embedding --embedding-dir ./models/hub/Qwen3-Embedding-0.6B
python download_models.py --all
```

说明：
- 设置 `HF_HOME`/`HUGGINGFACE_HUB_CACHE` 后，Embedding 默认会下载到项目内 `./models/hub`（缓存结构）。
- 如果显式使用 `--embedding-dir`，会将模型文件直接写入该目录；此时需将 `HF_EMBEDDING_MODEL` 改为该本地路径。
