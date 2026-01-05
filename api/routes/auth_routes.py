"""
认证API路由
"""
import httpx
import logging
from fastapi import APIRouter, HTTPException, Response, Cookie, Header
from pydantic import BaseModel
from typing import Optional
from api.auth import get_auth_manager, is_admin
from api.config import WX_APPID, WX_APPSECRET
from api.services.db_service import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    user: dict = None
    token: str = None  # 小程序使用


class UserInfo(BaseModel):
    id: int
    username: str
    is_admin: bool


class WxLoginRequest(BaseModel):
    code: str  # wx.login() 获取的 code


class WxBindRequest(BaseModel):
    code: str  # wx.login() 获取的 code
    username: str
    password: str


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, response: Response):
    """用户登录"""
    auth = get_auth_manager()
    user = auth.verify_password(request.username, request.password)

    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 创建Token并设置Cookie
    token = auth.create_access_token(user['id'])
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=7 * 24 * 60 * 60,  # 7天
        samesite="lax",
        path="/"  # 确保 Cookie 对整个站点有效
    )

    return LoginResponse(
        success=True,
        message="登录成功",
        user={
            "id": user['id'],
            "username": user['username'],
            "is_admin": is_admin(user)
        }
    )


@router.post("/logout")
async def logout(response: Response):
    """用户登出"""
    response.delete_cookie(key="session_token", path="/")
    return {"success": True, "message": "已退出登录"}


@router.get("/me")
async def get_current_user_info(session_token: Optional[str] = Cookie(None)):
    """获取当前用户信息"""
    if not session_token:
        return {"logged_in": False}

    auth = get_auth_manager()
    user = auth.verify_token(session_token)

    if not user:
        return {"logged_in": False}

    return {
        "logged_in": True,
        "user": {
            "id": user['id'],
            "username": user['username'],
            "is_admin": is_admin(user)
        }
    }


# ========== 微信小程序认证 ==========

async def get_wx_openid(code: str) -> Optional[str]:
    """通过 code 换取 openid"""
    if not WX_APPSECRET:
        logger.error("WX_APPSECRET 未配置")
        return None

    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": WX_APPID,
        "secret": WX_APPSECRET,
        "js_code": code,
        "grant_type": "authorization_code"
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            data = resp.json()

            if "openid" in data:
                return data["openid"]
            else:
                logger.error(f"微信登录失败: {data}")
                return None
    except Exception as e:
        logger.error(f"调用微信API异常: {e}")
        return None


@router.post("/wx-login")
async def wx_login(request: WxLoginRequest):
    """微信小程序登录

    流程：
    1. code 换取 openid
    2. 查询绑定关系
    3. 已绑定：返回 token
    4. 未绑定：返回 needs_bindung
    """
    openid = await get_wx_openid(request.code)
    if not openid:
        raise HTTPException(status_code=400, detail="微信登录失败，请重试")

    # 查询绑定关系
    binding = db.get_wx_binding(openid)

    if binding:
        # 已绑定，创建 token
        auth = get_auth_manager()
        user = auth.get_user_by_id(binding["user_id"])
        if not user:
            # 用户已删除，清理绑定
            db.delete_wx_binding(openid)
            return {
                "success": False,
                "needs_bindung": True,
                "message": "账号已失效，请重新绑定"
            }

        token = auth.create_access_token(user['id'])
        return {
            "success": True,
            "token": token,
            "user": {
                "id": user['id'],
                "username": user['username'],
                "is_admin": is_admin(user)
            }
        }
    else:
        # 未绑定
        return {
            "success": False,
            "needs_binding": True,
            "message": "请绑定账号"
        }


@router.post("/wx-bind")
async def wx_bind(request: WxBindRequest):
    """微信账号绑定

    流程：
    1. code 换取 openid
    2. 验证用户名密码
    3. 检查是否已绑定其他微信
    4. 创建绑定关系
    5. 返回 token
    """
    openid = await get_wx_openid(request.code)
    if not openid:
        raise HTTPException(status_code=400, detail="微信登录失败，请重试")

    # 验证用户名密码
    auth = get_auth_manager()
    user = auth.verify_password(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 检查该 openid 是否已绑定
    existing_binding = db.get_wx_binding(openid)
    if existing_binding:
        if existing_binding["user_id"] == user['id']:
            # 已绑定到同一账号，直接返回 token
            token = auth.create_access_token(user['id'])
            return {
                "success": True,
                "token": token,
                "user": {
                    "id": user['id'],
                    "username": user['username'],
                    "is_admin": is_admin(user)
                }
            }
        else:
            raise HTTPException(status_code=400, detail="此微信已绑定其他账号")

    # 检查该用户是否已绑定其他微信
    user_binding = db.get_wx_binding_by_user(user['id'])
    if user_binding:
        # 已有绑定，先解绑旧的
        db.delete_wx_binding(user_binding["openid"])

    # 创建新绑定
    db.create_wx_binding(openid, user['id'])

    # 返回 token
    token = auth.create_access_token(user['id'])
    return {
        "success": True,
        "token": token,
        "message": "绑定成功",
        "user": {
            "id": user['id'],
            "username": user['username'],
            "is_admin": is_admin(user)
        }
    }


@router.get("/wx-me")
async def wx_get_current_user(authorization: Optional[str] = Header(None)):
    """小程序获取当前用户信息（Token 认证）"""
    if not authorization:
        return {"logged_in": False}

    # 支持 "Bearer token" 格式
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization

    auth = get_auth_manager()
    user = auth.verify_token(token)

    if not user:
        return {"logged_in": False}

    return {
        "logged_in": True,
        "user": {
            "id": user['id'],
            "username": user['username'],
            "is_admin": is_admin(user)
        }
    }
