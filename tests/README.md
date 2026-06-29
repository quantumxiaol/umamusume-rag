# 测试说明

按顺序运行测试：

## 1. 测试 RAG 构建
```bash
python tests/test_1_rag_build.py
```

测试内容：
- RAG 管理器初始化
- 目录扫描
- PDF 转换状态
- Markdown 加载
- 向量数据库构建
- 向量搜索

## 2. 测试 RAG MCP
```bash
# 先启动 RAG MCP 服务器
python -m umamusume_rag.server.rag_mcp --http -p 7778

# 方式 1: 运行 pytest 测试
pytest tests/test_3_rag_mcp.py -v -s

# 方式 2: 列出可用工具
python tests/test_3_rag_mcp.py

# 方式 3: 直接调用工具
python tests/test_3_rag_mcp.py \
    --tool-name rag \
    --tool-arg "question=这个文档主要讲什么？"

python tests/test_3_rag_mcp.py \
    --tool-name search_documents \
    --tool-arg "query=测试查询" \
    --tool-arg "k=3"

# 方式 4: 直接使用 rag 工具
python tests/test_3_rag_mcp.py \
    -q "请告诉我文档中的主要内容"
```

测试内容：
- MCP 服务器连接和工具列表
- RAG 查询工具（直接调用）
- 文档搜索工具（直接调用）

## 3. 测试 Grep RAG MCP

```bash
# 先启动 Grep RAG MCP 服务器
python -m umamusume_rag.server.grep_rag_mcp --http -p 7779

# 方式 1: 运行 pytest 测试
pytest tests/test_5_grep_rag_mcp.py -v -s

# 方式 2: 列出可用工具
python tests/test_5_grep_rag_mcp.py

# 方式 3: 查看语料结构
python tests/test_5_grep_rag_mcp.py \
    --tool-name grep_corpus_overview

# 方式 4: 解析角色名到专属剧情文件
python tests/test_5_grep_rag_mcp.py \
    --tool-name grep_lookup_character \
    --tool-arg "character=东海帝王"

# 方式 5: 直接调用单词检索
python tests/test_5_grep_rag_mcp.py \
    --tool-name grep_search \
    --tool-arg "query=スペシャルウィーク" \
    --tool-arg "max_results=5"

# 方式 6: 直接调用多关键词检索
python tests/test_5_grep_rag_mcp.py \
    --tool-name grep_search_many \
    --tool-arg 'queries=["スペシャルウィーク","メジロマックイーン"]'

# 方式 7: 按角色专属剧情文件检索
python tests/test_5_grep_rag_mcp.py \
    --tool-name grep_character_search \
    --tool-arg "character=东海帝王" \
    --tool-arg "query=菊花賞"
```

测试内容：
- Grep MCP 服务器连接和工具列表
- 语料结构说明与角色名解析
- 安全 ripgrep 单词检索
- 多关键词批量检索
- 按角色文件范围检索，避免客串污染

## MCP 协议

本项目使用 StreamHTTP 协议：
- RAG MCP: http://127.0.0.1:7778/mcp/
- Grep RAG MCP: http://127.0.0.1:7779/mcp/

**注意：** 端点路径必须带斜杠 `/mcp/`

## PDF 转 Markdown 测试脚本

```bash
python tests/pdf_to_md_mineru.py --pdf /path/to/file.pdf
python tests/pdf_to_md_markitdown.py --pdf /path/to/file.pdf
python tests/pdf_to_md_qwen_vl.py --pdf /path/to/file.pdf --max-pages 3
python tests/pdf_to_md_docling.py --pdf /path/to/file.pdf
```

说明：
- Qwen2.5-VL PDF 测试依赖 `pymupdf`，并需要先下载 Qwen2.5-VL 权重到 `models/`。
- Docling PDF 测试可选设置 `DOCLING_ARTIFACTS_PATH` 指向已下载的 Docling 模型目录。
