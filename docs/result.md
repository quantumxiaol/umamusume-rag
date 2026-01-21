# 测试结果与日志

## FastAPI Server

### 启动命令

```bash
python main.py
```

### 启动日志

```text
(umamusume-rag) quantumxiaol@quantumxiaoldeMacBook-Pro umamusume-rag % python main.py
objc[25223]: Class AVFFrameReceiver is implemented in both /Users/quantumxiaol/Desktop/dev/umamusume-rag/.venv/lib/python3.12/site-packages/av/.dylibs/libavdevice.62.1.100.dylib (0x133a543a8) and /Users/quantumxiaol/Desktop/dev/umamusume-rag/.venv/lib/python3.12/site-packages/cv2/.dylibs/libavdevice.61.3.100.dylib (0x1689503a8). This may cause spurious casting failures and mysterious crashes. One of the duplicates must be removed or renamed.
objc[25223]: Class AVFAudioReceiver is implemented in both /Users/quantumxiaol/Desktop/dev/umamusume-rag/.venv/lib/python3.12/site-packages/av/.dylibs/libavdevice.62.1.100.dylib (0x133a543f8) and /Users/quantumxiaol/Desktop/dev/umamusume-rag/.venv/lib/python3.12/site-packages/cv2/.dylibs/libavdevice.61.3.100.dylib (0x1689503f8). This may cause spurious casting failures and mysterious crashes. One of the duplicates must be removed or renamed.
INFO:umamusume_rag.rag.download_models:Models not found, downloading to: /Users/quantumxiaol/Desktop/dev/umamusume-rag/models/hub
INFO:umamusume_rag.rag.download_models:Model directory prepared: /Users/quantumxiaol/Desktop/dev/umamusume-rag/models/hub
INFO:umamusume_rag.rag.download_models:MinerU will download models automatically on first use if needed.
INFO:umamusume_rag.pdf_processors.mineru_processor:MinerU model directory: /Users/quantumxiaol/Desktop/dev/umamusume-rag/models/hub
INFO:umamusume_rag.pdf_processors.mineru_processor:设备模式: mps
INFO:umamusume_rag.pdf_processors.mineru_processor:✅ MinerU Python API 初始化完成
INFO:umamusume_rag.pdf_processors.mineru_processor:MinerU PDF processor initialized successfully
INFO:umamusume_rag.rag.rag:PDF processor initialized (engine=mineru, model_dir=/Users/quantumxiaol/Desktop/dev/umamusume-rag/models/hub)
INFO:umamusume_rag.rag.rag:RAG Manager initialized with directory: /Users/quantumxiaol/Desktop/dev/umamusume-rag/resources/docs
INFO:umamusume_rag.rag.rag:PDF processing: Using mineru for PDF to Markdown conversion
INFO:     Started server process [25223]
INFO:     Waiting for application startup.
INFO:umamusume_rag.server.rag_query:正在初始化本地知识库 (RAG)...
INFO:faiss.loader:Loading faiss.
INFO:faiss.loader:Successfully loaded faiss.
INFO:faiss:Failed to load GPU Faiss: name 'GpuIndexIVFFlat' is not defined. Will not load constructor refs for GPU indexes. This is only an error if you're trying to use GPU Faiss.
INFO:umamusume_rag.rag.rag:已从本地缓存加载向量数据库
INFO:umamusume_rag.rag.rag:使用缓存的向量数据库
INFO:umamusume_rag.server.rag_query:RAG 初始化完成。
INFO:umamusume_rag.server.rag_query:RAG 服务已就绪。
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:7777 (Press CTRL+C to quit)
INFO:     127.0.0.1:62362 - "POST /search HTTP/1.1" 200 OK
INFO:     127.0.0.1:62421 - "POST /search HTTP/1.1" 200 OK
INFO:httpx:HTTP Request: POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions "HTTP/1.1 200 OK"
INFO:     127.0.0.1:62552 - "POST /ask HTTP/1.1" 200 OK
^CINFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
```

### /search 示例（query=米浴）

```bash
curl -X POST http://127.0.0.1:7777/search \
  -H "Content-Type: application/json" \
  -d '{"query":"米浴","top_k":4}'
```

```json
{"documents":[{"content":"赛马娘中文名: 米浴\n赛马娘英语名: Rice Shower\n赛马娘日语名: ライスシャワー\n赛马娘生日: 3月5日\n三围: B75·W51·H76\n身高(cm): 145\n声优(cv): 石见舞菜香\n赛马娘特殊称号(二つ名)(中文名): 漆黑刺客\n赛马娘特殊称号(二つ名)(日语名): 黒い刺客\n赛马娘特殊称号获取条件: 重赏比赛出战23次以上,其中在人气第二以上的情况下取得菊花賞 、天皇賞(春)的胜利;粉丝数达到320,000以上","source":"/Users/quantumxiaol/Desktop/dev/umamusume-rag/resources/docs/umamusume_character_baseinfo.csv","score":0.8472387790679932},{"content":"---","source":"/Users/quantumxiaol/Desktop/dev/umamusume-rag/resources/docs/赛马娘设定集.md","score":1.1041345596313477},{"content":"赛马娘中文名: 目白多伯\n赛马娘英语名: Mejiro Dober\n赛马娘日语名: メジロドーベル\n赛马娘生日: 5月6日\n三围: B83·W57·H81\n身高(cm): 157\n声优(cv): 久保田光\n赛马娘特殊称号(二つ名)(中文名): 高冷的美人\n赛马娘特殊称号(二つ名)(日语名): クールビューティー\n赛马娘特殊称号获取条件: 以\"差马\"策略且人气第一的状态下赢得阪神ジュベナイルフィリーズ、桜花賞、オークス、秋華賞;赢得エリザベス女王杯两连冠;粉丝数24万人以上","source":"/Users/quantumxiaol/Desktop/dev/umamusume-rag/resources/docs/umamusume_character_baseinfo.csv","score":1.1284749507904053},{"content":"赛马娘中文名: 谷野美酒\n赛马娘英语名: Tanino Gimlet\n赛马娘日语名: タニノギムレット\n赛马娘生日: 5月4日\n三围: B77·W56·H79\n身高(cm): 166\n声优(cv): 松冈美里\n赛马娘特殊称号(二つ名)(中文名): 唯美系破坏神\n赛马娘特殊称号(二つ名)(日语名): 耽美系破壊神\n赛马娘特殊称号获取条件: 赢得比赛皐月賞、NHKマイルC、日本ダービー;基础能力力量达到1200以上","source":"/Users/quantumxiaol/Desktop/dev/umamusume-rag/resources/docs/umamusume_character_baseinfo.csv","score":1.134601354598999}]}
```

### /search 示例（query=ウマ娘 プリティーダービー）

```bash
curl -X POST http://127.0.0.1:7777/search \
  -H "Content-Type: application/json" \
  -d '{"query":"ウマ娘 プリティーダービー","top_k":4}'
```

```json
{"documents":[{"content":"——今のお話にもありましたが、走る姿勢など、「ウマ娘」の絵は細部までこだわって描いていますね。\n\nゲーム内でも、ウマ娘ごとに走っている時の手の形がそれぞれ設定されているので、それに沿うように描いています。ですが、中にはレギュラーな子もいて、例えばトウカイティオーは、ゲーム内のイラストではその時々で走行中の手の形がバーだったりグーだったり、どちらも存在しています。スペシャ\n\nルウィークはゲーム内ではずっとグーですが、TVアニメ版「ウマ娘 プリティーダービー」では途中でサイレンススズカに走法を教えてもらって、その後にパーで走るようにになっています。基本的に走法は固定なのですが、アニメやその他媒体の特性に合わせ、その時々でももっと演出上の見栄えを良くするため、あえて手の形を定めない場合もあります。\n\n——実在する競走馬をモチーフとしたキャラクターという、ともすればネタ的な設定だけに、あの迫力感は衝撃的でした。","source":"/Users/quantumxiaol/Desktop/dev/umamusume-rag/resources/docs/赛马娘设定集.md","score":0.7914277911186218},{"content":"赛马娘中文名: 伏特加\n赛马娘英语名: Vodka\n赛马娘日语名: ウオッカ\n赛马娘生日: 4月4日\n三围: B76·W55·H78\n身高(cm): 165\n声优(cv): 大桥彩香\n赛马娘特殊称号(二つ名)(中文名): 打破常识的女帝\n赛马娘特殊称号(二つ名)(日语名): 常識破りの女帝\n赛马娘特殊称号获取条件: 在包括東京優駿(日本ダービー)、安田記念、ジャパンカップ、天皇賞(秋)、ヴィクトリアマイル的G1赛事中取得7次以上胜利","source":"/Users/quantumxiaol/Desktop/dev/umamusume-rag/resources/docs/umamusume_character_baseinfo.csv","score":0.8138980865478516},{"content":"赛马娘中文名: 新宇宙\n赛马娘英语名: Neo Universe\n赛马娘日语名: ネオユニヴァース\n赛马娘生日: 5月21日\n三围: B79·W52·H77\n身高(cm): 160\n声优(cv): 白石晴香\n赛马娘特殊称号(二つ名)(中文名): 宇宙诗篇\n赛马娘特殊称号(二つ名)(日语名): コズミックヴァース\n赛马娘特殊称号获取条件: 皐月賞、日本ダービー、宝塚記念(第二年)、菊花賞、ジャパンC(第二年)、大阪杯、天皇賞(春)获胜;基础能力\"智力\"达到1200以上","source":"/Users/quantumxiaol/Desktop/dev/umamusume-rag/resources/docs/umamusume_character_baseinfo.csv","score":0.8293012380599976},{"content":"ウマ娘はアスリートであり、同時にアイドルでもあります。それぞれがライブにかける想いがあり、いいことも悪いこともあった末に、勝利者だけがそのステージに立てる。ゲーム内のイラストではそうした想いを前面にした絵を描くことが多いですが、ライブのキービジュアルでは、とにかくアイド\nルとしての可愛らしさを出すように意識しました。学園キービジュアルの場合は彼女たちのゆったりとした日常感を演出し、真剣なところだけではなく、普通の女の子の側面を見せたいと考えています。今回例にしているキービジュアルに関してはそこまでではありませんが、ゲーム内で日常のイラストを描く時は世界観をより表現するために、この作品にしかない小物を盛り込んだりしているんですよ。例えば、ヘッドホンが人間とウマ娘の両用になっているだとか、服屋の看板にはズボンの裾上げの様にしっぽや帽子に穴を空けるサービスがあります、と記載されているだとか。そんな風に、レースは彼女たちの真剣な側面、ライブはアイドルとしての側面、学園は日常の側面というのを意識しています。\n```","source":"/Users/quantumxiaol/Desktop/dev/umamusume-rag/resources/docs/赛马娘设定集.md","score":0.8397496938705444}]}
```

### /ask 示例（question=米浴是谁）

```bash
curl -X POST http://127.0.0.1:7777/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"米浴是谁","top_k":4,"max_context_chars":2000}'
```

```json
{"answer":"根据参考资料，米浴是赛马娘（Umamusume）中的一名角色，具体信息如下：\n\n**基本信息：**\n- 中文名：米浴\n- 英语名：Rice Shower\n- 日语名：ライスシャワー\n- 生日：3月5日\n- 身高：145cm\n- 三围：B75·W51·H76\n- 声优：石见舞菜香\n\n**特殊称号：**\n- 中文称号：漆黑刺客\n- 日语称号：黒い刺客\n- 获取条件：重赏比赛出战23次以上，其中在人气第二以上的情况下取得菊花賞、天皇賞(春)的胜利；粉丝数达到320,000以上","documents":[{"content":"赛马娘中文名: 米浴\n赛马娘英语名: Rice Shower\n赛马娘日语名: ライスシャワー\n赛马娘生日: 3月5日\n三围: B75·W51·H76\n身高(cm): 145\n声优(cv): 石见舞菜香\n赛马娘特殊称号(二つ名)(中文名): 漆黑刺客\n赛马娘特殊称号(二つ名)(日语名): 黒い刺客\n赛马娘特殊称号获取条件: 重赏比赛出战23次以上,其中在人气第二以上的情况下取得菊花賞 、天皇賞(春)的胜利;粉丝数达到320,000以上","source":"/Users/quantumxiaol/Desktop/dev/umamusume-rag/resources/docs/umamusume_character_baseinfo.csv","score":0.7796891927719116},{"content":"赛马娘中文名: 目白善信\n赛马娘英语名: Mejiro Palmer\n赛马娘日语名: メジロパーマー\n赛马娘生日: 3月21日\n三围: B84·W57·H86\n身高(cm): 160\n声优(cv): 野口百合\n赛马娘特殊称号(二つ名)(中文名): 变化不定的逃马娘\n赛马娘特殊称号(二つ名)(日语名): 波乱の逃げウマ娘\n赛马娘特殊称号获取条件: 以\"逃马\"策略且人气第四以下赢得(一场)GⅠ;以\"逃马\"策略赢得第三年的天皇賞(春)、宝塚記念、有馬記念;\"逃马\"适应性S以上","source":"/Users/quantumxiaol/Desktop/dev/umamusume-rag/resources/docs/umamusume_character_baseinfo.csv","score":1.0997028350830078},{"content":"赛马娘中文名: 目白多伯\n赛马娘英语名: Mejiro Dober\n赛马娘日语名: メジロドーベル\n赛马娘生日: 5月6日\n三围: B83·W57·H81\n身高(cm): 157\n声优(cv): 久保田光\n赛马娘特殊称号(二つ名)(中文名): 高冷的美人\n赛马娘特殊称号(二つ名)(日语名): クールビューティー\n赛马娘特殊称号获取条件: 以\"差马\"策略且人气第一的状态下赢得阪神ジュベナイルフィリーズ、桜花賞、オークス、秋華賞;赢得エリザベス女王杯两连冠;粉丝数24万人以上","source":"/Users/quantumxiaol/Desktop/dev/umamusume-rag/resources/docs/umamusume_character_baseinfo.csv","score":1.1090927124023438},{"content":"这是一个关于赛马娘角色信息的表格，包含以下字段：\n- 赛马娘中文名: 角色的中文名称\n- 赛马娘英语名 / 日语名: 对应英文和日文名\n- 生日: 出生日期\n- 三围: BWH 尺寸\n- 身高(cm): 单位厘米\n- 声优(cv): 配音演员\n- 赛马娘特殊称号(中文名/日语名): 特殊称号及日文名，也叫专属称号，或二つ名、别称\n- 赛马娘特殊称号获取条件: 获取该称号的具体游戏内条件\n\n例如：米浴的称号“漆黑刺客”的获取条件是：\n重赏比赛出战23次以上，在人气第二以上的情况下取得菊花賞、天皇賞(春)的胜利；粉丝数达到320,000以上。","source":"/Users/quantumxiaol/Desktop/dev/umamusume-rag/resources/docs/umamusume_character_baseinfo.md","score":1.111185073852539}]}
```

## MCP Server

### 启动命令

```bash
python -m umamusume_rag.server.rag_mcp --http -p 7778
```

### 启动日志

```text
(umamusume-rag) quantumxiaol@quantumxiaoldeMacBook-Pro umamusume-rag % python -m umamusume_rag.server.rag_mcp --http -p 7778
objc[26349]: Class AVFFrameReceiver is implemented in both /Users/quantumxiaol/Desktop/dev/umamusume-rag/.venv/lib/python3.12/site-packages/av/.dylibs/libavdevice.62.1.100.dylib (0x12c8783a8) and /Users/quantumxiaol/Desktop/dev/umamusume-rag/.venv/lib/python3.12/site-packages/cv2/.dylibs/libavdevice.61.3.100.dylib (0x13f5d03a8). This may cause spurious casting failures and mysterious crashes. One of the duplicates must be removed or renamed.
objc[26349]: Class AVFAudioReceiver is implemented in both /Users/quantumxiaol/Desktop/dev/umamusume-rag/.venv/lib/python3.12/site-packages/av/.dylibs/libavdevice.62.1.100.dylib (0x12c8783f8) and /Users/quantumxiaol/Desktop/dev/umamusume-rag/.venv/lib/python3.12/site-packages/cv2/.dylibs/libavdevice.61.3.100.dylib (0x13f5d03f8). This may cause spurious casting failures and mysterious crashes. One of the duplicates must be removed or renamed.
INFO:umamusume_rag.rag.download_models:Models not found, downloading to: /Users/quantumxiaol/Desktop/dev/umamusume-rag/models/hub
INFO:umamusume_rag.rag.download_models:Model directory prepared: /Users/quantumxiaol/Desktop/dev/umamusume-rag/models/hub
INFO:umamusume_rag.rag.download_models:MinerU will download models automatically on first use if needed.
INFO:umamusume_rag.pdf_processors.mineru_processor:MinerU model directory: /Users/quantumxiaol/Desktop/dev/umamusume-rag/models/hub
INFO:umamusume_rag.pdf_processors.mineru_processor:设备模式: mps
INFO:umamusume_rag.pdf_processors.mineru_processor:✅ MinerU Python API 初始化完成
INFO:umamusume_rag.pdf_processors.mineru_processor:MinerU PDF processor initialized successfully
INFO:umamusume_rag.rag.rag:PDF processor initialized (engine=mineru, model_dir=/Users/quantumxiaol/Desktop/dev/umamusume-rag/models/hub)
INFO:umamusume_rag.rag.rag:RAG Manager initialized with directory: /Users/quantumxiaol/Desktop/dev/umamusume-rag/resources/docs
INFO:umamusume_rag.rag.rag:PDF processing: Using mineru for PDF to Markdown conversion
正在初始化RAG系统...
INFO:faiss.loader:Loading faiss.
INFO:faiss.loader:Successfully loaded faiss.
INFO:faiss:Failed to load GPU Faiss: name 'GpuIndexIVFFlat' is not defined. Will not load constructor refs for GPU indexes. This is only an error if you're trying to use GPU Faiss.
INFO:umamusume_rag.rag.rag:已从本地缓存加载向量数据库
INFO:umamusume_rag.rag.rag:使用缓存的向量数据库
🚀 Starting server on port 7778
INFO:     Started server process [26349]
INFO:     Waiting for application startup.
INFO:mcp.server.streamable_http_manager:StreamableHTTP session manager started
Application started with StreamableHTTP session manager!
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:7778 (Press CTRL+C to quit)
INFO:     127.0.0.1:62877 - "POST /mcp HTTP/1.1" 307 Temporary Redirect
INFO:     127.0.0.1:62879 - "POST /mcp/ HTTP/1.1" 200 OK
INFO:mcp.server.streamable_http:Terminating session: None
INFO:     127.0.0.1:62881 - "POST /mcp HTTP/1.1" 307 Temporary Redirect
INFO:     127.0.0.1:62883 - "POST /mcp/ HTTP/1.1" 202 Accepted
INFO:mcp.server.streamable_http:Terminating session: None
INFO:     127.0.0.1:62885 - "POST /mcp HTTP/1.1" 307 Temporary Redirect
INFO:mcp.server.lowlevel.server:Processing request of type ListToolsRequest
INFO:     127.0.0.1:62887 - "POST /mcp/ HTTP/1.1" 200 OK
INFO:mcp.server.streamable_http:Terminating session: None
INFO:     127.0.0.1:62889 - "POST /mcp HTTP/1.1" 307 Temporary Redirect
INFO:mcp.server.lowlevel.server:Processing request of type CallToolRequest
请告诉我文档中的主要内容
INFO:httpx:HTTP Request: POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions "HTTP/1.1 200 OK"
根据提供的文档信息，我可以告诉您以下主要内容：

**背景美术设计方面：**
- 文档提到了"グラウンド（ダート）"（草地/泥地）背景的设计，强调在满足必要要素的同时注重绘画完成度，具有深刻的背景世界
- 提及了背景美术制作的理念，即抓住空间的本质，在满足观看者接受范围的同时呈现有吸引力的差异

**游戏界面设计：**
- 涉及游戏中的用户界面配置和特有的屏幕构成
- 提到了"ウマ娘"游戏中存在纵向和横向两种屏幕显示模式，其中横向画面时背景几乎完整显示

**角色设计理念：**
- 强调要保留原有角色的优点，并在此基础上提出其他优点

不过需要注意的是，文档中有很多内容被标记为"--"或"——"，实际的详细内容有限，以上是基于现有信息能够提取的主要内容。
INFO:     127.0.0.1:62891 - "POST /mcp/ HTTP/1.1" 200 OK
INFO:mcp.server.streamable_http:Terminating session: None
INFO:     127.0.0.1:62914 - "POST /mcp HTTP/1.1" 307 Temporary Redirect
INFO:     127.0.0.1:62916 - "POST /mcp/ HTTP/1.1" 200 OK
INFO:mcp.server.streamable_http:Terminating session: None
INFO:     127.0.0.1:62918 - "POST /mcp HTTP/1.1" 307 Temporary Redirect
INFO:     127.0.0.1:62920 - "POST /mcp/ HTTP/1.1" 202 Accepted
INFO:mcp.server.streamable_http:Terminating session: None
INFO:     127.0.0.1:62922 - "POST /mcp HTTP/1.1" 307 Temporary Redirect
INFO:mcp.server.lowlevel.server:Processing request of type ListToolsRequest
INFO:     127.0.0.1:62924 - "POST /mcp/ HTTP/1.1" 200 OK
INFO:mcp.server.streamable_http:Terminating session: None
INFO:     127.0.0.1:62926 - "POST /mcp HTTP/1.1" 307 Temporary Redirect
INFO:mcp.server.lowlevel.server:Processing request of type CallToolRequest
INFO:     127.0.0.1:62928 - "POST /mcp/ HTTP/1.1" 200 OK
INFO:mcp.server.streamable_http:Terminating session: None
```

### 测试脚本（rag 工具提问）

```bash
python tests/test_3_rag_mcp.py -q "请告诉我文档中的主要内容"
```

```text
✓ RAG MCP server session已初始化
✓ 可用工具: ['rag', 'search_documents', 'reload_rag']

Tool: rag
  Args Schema: {'question': {'title': 'Question', 'type': 'string'}, 'top_k': {'default': 4, 'title': 'Top K', 'type': 'integer'}, 'max_context_chars': {'default': 2000, 'title': 'Max Context Chars', 'type': 'integer'}, 'max_snippet_chars': {'default': 500, 'title': 'Max Snippet Chars', 'type': 'integer'}}
  Description:
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

Tool: search_documents
  Args Schema: {'query': {'title': 'Query', 'type': 'string'}, 'k': {'default': 3, 'title': 'K', 'type': 'integer'}}
  Description:
    搜索相关的文档片段。

    参数:
        query (str): 搜索查询
        k (int): 返回的文档数量，默认为3

    返回:
        dict: 包含搜索结果的字典

Tool: reload_rag
  Args Schema: {'force_rebuild': {'default': True, 'title': 'Force Rebuild', 'type': 'boolean'}}
  Description:
    重新加载RAG系统。

    参数:
        force_rebuild (bool): 是否强制重建向量数据库，默认为True

    返回:
        dict: 操作结果

使用 rag 工具处理问题: 请告诉我文档中的主要内容

✅ Final Answer:
[
  {
    "type": "text",
    "text": "{\n  \"status\": \"success\",\n  \"result\": \"根据提供的文档信息，我可以告诉您以下主要内容：\\n\\n**背景美术设计方面：**\\n- 文档提到了\\\"グラウンド（ダート）\\\"（草地/泥地）背景的设计，强调在满足必要要素的同时注重绘画完成度，具有深刻的背景世界\\n- 提及了背景美术制作的理念，即抓住空间的本质，在满足观看者接受范围的同时呈现有吸引力的差异\\n\\n**游戏界面设计：**\\n- 涉及游戏中的用户界面配置和特有的屏幕构成\\n- 提到了\\\"ウマ娘\\\"游戏中存在纵向和横向两种屏幕显示模式，其中横向画面时背景几乎完整显示\\n\\n**角色设计理念：**\\n- 强调要保留原有角色的优点，并在此基础上提出其他优点\\n\\n不过需要注意的是，文档中有很多内容被标记为\\\"--\\\"或\\\"——\\\"，实际的详细内容有限，以上是基于现有信息能够提取的主要内容。\"\n}",
    "id": "lc_04faf30d-8f8b-4071-8168-b3e9fb03c8e4"
  }
]
```

### 测试脚本（search_documents）

```bash
python tests/test_3_rag_mcp.py --tool-name search_documents --tool-arg "query=测试" --tool-arg "k=3"
```

```text
✓ RAG MCP server session已初始化
✓ 可用工具: ['rag', 'search_documents', 'reload_rag']

正在调用工具: search_documents，参数: {'query': '测试', 'k': 3}
✅ 工具调用成功！返回结果:
[
  {
    "type": "text",
    "text": "{\n  \"status\": \"success\",\n  \"results\": [\n    {\n      \"id\": 1,\n      \"content\": \"---\",\n      \"source\": \"/Users/quantumxiaol/Desktop/dev/umamusume-rag/resources/docs/赛马娘设定集.md\",\n      \"metadata\": {\n        \"source\": \"/Users/quantumxiaol/Desktop/dev/umamusume-rag/resources/docs/赛马娘设定集.md\",\n        \"start_index\": 16247\n      }\n    },\n    {\n      \"id\": 2,\n      \"content\": \"团队卡需要以下属性：\\n友情加成\\n速度加成\\n耐力加成\\n力量加成\\n毅力加成\\n智力加成\\n初期羁绊计量格提升\\n赛后加成\\n粉丝数加成\\n技能Pt加成\\n事件回复量提升\\n事件效果提升\\n智力友情回复量提升\\n\\n友人卡、团队卡都有出行事件，事件可以回复部分体力，有时回复部分心情。速、耐、力、根、智卡可以在对应属性上进行友情训练，团队卡触发后也可以进行友情训练（任意属性）。\\n\\n# 训练\\n训练时的数值提升由7个因素决定：\\nA：基础训练值\\nB：友情加成\\nC：训练效果提升\\nD：干劲加成\\nE：赛马娘成长率\\nN：训练到场人数\\n最终加成=A*B*C*D*E*N\",\n      \"source\": \"/Users/quantumxiaol/Desktop/dev/umamusume-rag/resources/docs/umamusume_game_info.md\",\n      \"metadata\": {\n        \"source\": \"/Users/quantumxiaol/Desktop/dev/umamusume-rag/resources/docs/umamusume_game_info.md\",\n        \"start_index\": 1134\n      }\n    },\n    {\n      \"id\": 3,\n      \"content\": \"---\\n\\n```markdown\\n* \\\"グラウンド（ダート）\\\"。必要な要素を満たしながら絵的な完成度まで意識されている。脚けが聞くほど奥深い背景の世界。ゲームをプレイする時、改めて注目してみてはいかがだろう。※Vol.01 P.254に収録\\n```\",\n      \"source\": \"/Users/quantumxiaol/Desktop/dev/umamusume-rag/resources/docs/赛马娘设定集.md\",\n      \"metadata\": {\n        \"source\": \"/Users/quantumxiaol/Desktop/dev/umamusume-rag/resources/docs/赛马娘设定集.md\",\n        \"start_index\": 22470\n      }\n    }\n  ]\n}",
    "id": "lc_df23f5f7-a44c-480a-abed-b957e61f0f08"
  }
]
```
