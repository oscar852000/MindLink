"""
用户认证模块 - 共享AIIMAGE用户数据库
只读模式，不影响AIIMAGE和XHS的正常运行
"""
import sqlite3
import hashlib
import jwt
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import HTTPException, Cookie, status

# 共享AIIMAGE用户数据库（只读）
SHARED_USER_DB = "/root/AIIMAGE/data/users.db"

# JWT配置（与AIIMAGE/XHS保持一致）
SECRET_KEY = "replace-me-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7


class SharedUserAuth:
    """共享AIIMAGE用户认证（只读模式）"""

    def __init__(self, db_path: str = SHARED_USER_DB):
        self.db_path = db_path
        if not Path(db_path).exists():
            raise FileNotFoundError(f"用户数据库不存在: {db_path}")

    def _get_connection(self):
        """获取只读数据库连接"""
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def hash_password(password: str) -> str:
        """哈希密码（与AIIMAGE一致）"""
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """验证密码"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            conn.close()

            if row and dict(row)['password_hash'] == self.hash_password(password):
                return dict(row)
            return None
        except Exception as e:
            print(f"验证密码失败: {e}")
            return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """通过ID获取用户"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            print(f"获取用户失败: {e}")
            return None

    def create_access_token(self, user_id: int) -> str:
        """创建JWT Token"""
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
        payload = {
            "sub": user_id,
            "exp": expire
        }
        encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        # 兼容旧版PyJWT（返回bytes）和新版（返回str）
        if isinstance(encoded_jwt, bytes):
            return encoded_jwt.decode('utf-8')
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证JWT Token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                return self.get_user_by_id(user_id)
            return None
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


# 全局实例（延迟初始化，避免启动时报错）
_auth_manager = None


def get_auth_manager() -> SharedUserAuth:
    """获取认证管理器实例"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = SharedUserAuth()
    return _auth_manager


def get_current_user(session_token: Optional[str] = Cookie(None)) -> Dict[str, Any]:
    """
    从Cookie获取当前用户（中间件依赖）
    如果未登录，抛出401异常
    """
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录，请先登录"
        )

    auth = get_auth_manager()
    user = auth.verify_token(session_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已过期，请重新登录"
        )

    return user


def get_current_user_optional(session_token: Optional[str] = Cookie(None)) -> Optional[Dict[str, Any]]:
    """
    可选的用户验证（用于兼容未登录用户访问的接口）
    """
    if not session_token:
        return None
    auth = get_auth_manager()
    return auth.verify_token(session_token)


# ===== 管理员权限 =====

def is_admin(user: Dict[str, Any]) -> bool:
    """判断用户是否为管理员"""
    # 支持 is_admin 字段或 user_id=1
    return user.get('is_admin', 0) == 1 or user.get('id') == 1


def require_admin(session_token: Optional[str] = Cookie(None)) -> Dict[str, Any]:
    """
    要求管理员权限的依赖
    如果不是管理员，抛出403异常
    """
    user = get_current_user(session_token)
    if not is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return user
