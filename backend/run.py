"""本地开发启动入口：uvicorn 热重载。支持 --port 参数。"""
import argparse

import uvicorn

from app.config import settings

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KnowledgeGraph AI 后端开发服务器")
    parser.add_argument("--port", type=int, default=8000, help="监听端口（默认 8000）")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="监听地址")
    args = parser.parse_args()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=settings.DEBUG,
    )
