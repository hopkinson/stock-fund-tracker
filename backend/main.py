from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.models.database import init_db
from app.api.endpoints import router as api_router
from app.services.scheduler_service import start_scheduler, shutdown_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    print("[PortfolioHub] 正在初始化数据库...")
    init_db()
    print("[PortfolioHub] 正在启动后台定时调度器...")
    start_scheduler()
    yield
    # 停止时执行
    print("[PortfolioHub] 正在关闭后台定时调度器...")
    shutdown_scheduler()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="支持雪球基金、天天基金、东方财富股票的个人多账户聚合监控与预警系统",
    version="1.0.0",
    lifespan=lifespan
)

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

# 挂载前端静态文件 (如果已构建)
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/")
    def read_root():
        return {
            "status": "online",
            "app": settings.PROJECT_NAME,
            "docs": "/docs"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
