"""
MindLink API - 主入口
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import logging

from api.routes import mind, feed, admin, chat

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("MindLink 服务启动")
    yield
    logger.info("MindLink 服务关闭")


# 创建应用
app = FastAPI(
    title="MindLink",
    description="一个只会聆听、整理、表达的超能力助手",
    version="0.1.0",
    lifespan=lifespan
)

# 注册路由
app.include_router(mind.router, prefix="/api/minds", tags=["Mind"])
app.include_router(feed.router, prefix="/api", tags=["Feed"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

# 静态文件
app.mount("/static", StaticFiles(directory="web/static"), name="static")


@app.get("/")
async def root():
    """首页"""
    return FileResponse("web/index.html")


@app.get("/admin")
async def admin():
    """管理后台"""
    return FileResponse("web/admin.html")


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "service": "MindLink"}
