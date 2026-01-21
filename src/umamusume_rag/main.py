import argparse

import uvicorn

from umamusume_rag.server.rag_query import app

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", type=int, default=7777)
    args = parser.parse_args()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=args.port,
        # reload=True
    )
