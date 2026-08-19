from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import qingheng
from app.common.logger import setup_logging
from app.database import close_database, initialize_database


setup_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await asyncio.to_thread(initialize_database)
    try:
        yield
    finally:
        await asyncio.to_thread(close_database)


def _cors_origins() -> list[str]:
    configured = os.getenv("CORS_ORIGINS")
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return ["http://localhost:5173", "http://127.0.0.1:5173"]


app = FastAPI(
    title="轻衡 API",
    description="本地单用户饮食记录与今日热量缺口助手",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.include_router(qingheng.router, prefix="/api/v1", tags=["轻衡"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=True)
