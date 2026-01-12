"""
MindLink API - 主入口
"""
import os
import re
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import logging

from api.routes import mind, feed, admin, chat, auth_routes, memory
from api.auth import get_current_user_optional, is_admin

# 项目根目录（api 目录的父目录）
BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"

# 移动端 User-Agent 正则
MOBILE_PATTERN = re.compile(
    r'Mobile|Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini',
    re.IGNORECASE
)

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
app.include_router(auth_routes.router, prefix="/api", tags=["Auth"])
app.include_router(mind.router, prefix="/api/minds", tags=["Mind"])
app.include_router(feed.router, prefix="/api", tags=["Feed"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(memory.router, prefix="/api", tags=["Memory"])

# 静态文件
app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")


def is_mobile(request: Request) -> bool:
    """检测是否为移动设备"""
    user_agent = request.headers.get("user-agent", "")
    return bool(MOBILE_PATTERN.search(user_agent))


@app.get("/")
async def root(request: Request):
    """首页 - 检查登录状态，未登录则跳转登录页"""
    session_token = request.cookies.get("session_token")
    user = get_current_user_optional(session_token)

    if not user:
        # 未登录，跳转登录页
        if is_mobile(request):
            return FileResponse(str(WEB_DIR / "login-mobile.html"))
        return FileResponse(str(WEB_DIR / "login.html"))

    # 已登录，返回主页面
    if is_mobile(request):
        return FileResponse(str(WEB_DIR / "mobile.html"))
    return FileResponse(str(WEB_DIR / "index.html"))


@app.get("/mobile")
async def mobile_page():
    """强制访问移动端页面（调试用）"""
    return FileResponse(str(WEB_DIR / "mobile.html"))


@app.get("/desktop")
async def desktop_page():
    """强制访问桌面端页面（调试用）"""
    return FileResponse(str(WEB_DIR / "index.html"))


@app.get("/admin")
async def admin_page(request: Request):
    """管理后台 - 仅管理员可访问"""
    session_token = request.cookies.get("session_token")
    user = get_current_user_optional(session_token)

    if not user:
        # 未登录，跳转登录页
        if is_mobile(request):
            return FileResponse(str(WEB_DIR / "login-mobile.html"))
        return FileResponse(str(WEB_DIR / "login.html"))

    if not is_admin(user):
        # 非管理员，返回403或跳转首页
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/", status_code=302)

    return FileResponse(str(WEB_DIR / "admin.html"))


@app.get("/login")
async def login_page(request: Request):
    """登录页面"""
    # 如果已登录，跳转首页
    session_token = request.cookies.get("session_token")
    user = get_current_user_optional(session_token)
    if user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/", status_code=302)

    if is_mobile(request):
        return FileResponse(str(WEB_DIR / "login-mobile.html"))
    return FileResponse(str(WEB_DIR / "login.html"))


@app.get("/memory")
async def memory_page(request: Request):
    """晶体底层记忆查看页面"""
    session_token = request.cookies.get("session_token")
    user = get_current_user_optional(session_token)
    if not user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login", status_code=302)
    return FileResponse(str(WEB_DIR / "memory.html"))


@app.get("/mindmap_demo")
async def mindmap_demo_page():
    """思维导图演示页面（旧版）"""
    return FileResponse(str(WEB_DIR / "mindmap_demo.html"))


@app.get("/mindmap")
async def mindmap_page():
    """思维导图页面（新版 - 独立样式）"""
    return FileResponse(str(WEB_DIR / "mindmap.html"))


@app.get("/chat-demo")
async def chat_demo_page():
    """对话界面 Demo 页面"""
    return FileResponse(str(WEB_DIR / "chat-demo.html"))


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "service": "MindLink"}
