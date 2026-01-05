"""
认证API路由
"""
from fastapi import APIRouter, HTTPException, Response, Cookie
from pydantic import BaseModel
from typing import Optional
from api.auth import get_auth_manager, is_admin

router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    user: dict = None


class UserInfo(BaseModel):
    id: int
    username: str
    is_admin: bool


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
