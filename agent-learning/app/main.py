from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import chat
from app.api.v1 import oss
from app.common.logger import setup_logging
from app.rag import ensure_collection_initialized

# 初始化日志配置
setup_logging()

# 初始化 RAG 知识库（启动时自动检查并索引预置菜谱）
ensure_collection_initialized()

app = FastAPI(
    title="Personal Chief API",
    description="私厨",
    version="0.1.0"
)

# 1. 配置跨域资源共享 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议指定前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 挂载路由
app.include_router(chat.router, prefix="/api/v1", tags=["对话"])
app.include_router(oss.router, prefix="/api/v1", tags=["申请上传签名url"])

if __name__ == "__main__":
    import uvicorn
    # 启动命令：python -m app.main
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=True)
