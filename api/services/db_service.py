"""
数据库服务 - SQLite 持久化
"""
import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import os

logger = logging.getLogger(__name__)

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'mindlink.db')


class Database:
    """MindLink 数据库服务"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._ensure_dir()
        self._init_db()

    def _ensure_dir(self):
        """确保数据目录存在"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Mind 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS minds (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    north_star TEXT,
                    crystal_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # FeedItem 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feed_items (
                    id TEXT PRIMARY KEY,
                    mind_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (mind_id) REFERENCES minds(id)
                )
            """)

            # Timeline 表（事件记录）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS timeline_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mind_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    summary TEXT,
                    payload_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (mind_id) REFERENCES minds(id)
                )
            """)

            # OutputTask 表（输出记录）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS output_tasks (
                    id TEXT PRIMARY KEY,
                    mind_id TEXT NOT NULL,
                    instruction TEXT NOT NULL,
                    result TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (mind_id) REFERENCES minds(id)
                )
            """)

            conn.commit()
            logger.info("数据库初始化完成")

    # ========== Mind 操作 ==========

    def create_mind(self, mind_id: str, title: str, north_star: Optional[str] = None) -> Dict[str, Any]:
        """创建 Mind"""
        now = datetime.now().isoformat()
        initial_crystal = {
            "core_goal": north_star or "",
            "current_knowledge": [],
            "highlights": [],
            "pending_questions": [],
            "evolution": []
        }

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO minds (id, title, north_star, crystal_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (mind_id, title, north_star, json.dumps(initial_crystal, ensure_ascii=False), now, now))
            conn.commit()

            # 记录事件
            self._add_timeline_event(conn, mind_id, "create", f"创建 Mind: {title}")

        return {
            "id": mind_id,
            "title": title,
            "north_star": north_star,
            "crystal": initial_crystal,
            "created_at": now,
            "updated_at": now
        }

    def get_mind(self, mind_id: str) -> Optional[Dict[str, Any]]:
        """获取 Mind"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM minds WHERE id = ?", (mind_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return {
                "id": row["id"],
                "title": row["title"],
                "north_star": row["north_star"],
                "crystal": json.loads(row["crystal_json"]) if row["crystal_json"] else None,
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }

    def list_minds(self) -> List[Dict[str, Any]]:
        """获取所有 Mind"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM minds ORDER BY updated_at DESC")
            rows = cursor.fetchall()

            return [{
                "id": row["id"],
                "title": row["title"],
                "north_star": row["north_star"],
                "crystal": json.loads(row["crystal_json"]) if row["crystal_json"] else None,
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            } for row in rows]

    def update_crystal(self, mind_id: str, crystal: Dict[str, Any], summary: str = None) -> bool:
        """更新 Crystal"""
        now = datetime.now().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE minds SET crystal_json = ?, updated_at = ? WHERE id = ?
            """, (json.dumps(crystal, ensure_ascii=False), now, mind_id))
            conn.commit()

            # 记录事件
            self._add_timeline_event(conn, mind_id, "organize", summary or "更新 Crystal")

            return cursor.rowcount > 0

    # ========== Feed 操作 ==========

    def add_feed(self, feed_id: str, mind_id: str, content: str) -> Dict[str, Any]:
        """添加投喂"""
        now = datetime.now().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO feed_items (id, mind_id, content, created_at)
                VALUES (?, ?, ?, ?)
            """, (feed_id, mind_id, content, now))

            # 更新 Mind 的 updated_at
            cursor.execute("""
                UPDATE minds SET updated_at = ? WHERE id = ?
            """, (now, mind_id))

            conn.commit()

            # 记录事件
            preview = content[:50] + "..." if len(content) > 50 else content
            self._add_timeline_event(conn, mind_id, "feed", f"投喂: {preview}")

        return {
            "id": feed_id,
            "mind_id": mind_id,
            "content": content,
            "created_at": now
        }

    def get_feeds(self, mind_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """获取 Mind 的投喂列表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM feed_items WHERE mind_id = ?
                ORDER BY created_at DESC LIMIT ?
            """, (mind_id, limit))
            rows = cursor.fetchall()

            return [{
                "id": row["id"],
                "mind_id": row["mind_id"],
                "content": row["content"],
                "created_at": row["created_at"]
            } for row in rows]

    # ========== Timeline 操作 ==========

    def _add_timeline_event(self, conn, mind_id: str, event_type: str, summary: str, payload: Dict = None):
        """添加时间线事件（内部方法）"""
        now = datetime.now().isoformat()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO timeline_events (mind_id, event_type, summary, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (mind_id, event_type, summary, json.dumps(payload, ensure_ascii=False) if payload else None, now))
        conn.commit()

    def get_timeline(self, mind_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取时间线"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM timeline_events WHERE mind_id = ?
                ORDER BY created_at DESC LIMIT ?
            """, (mind_id, limit))
            rows = cursor.fetchall()

            return [{
                "id": row["id"],
                "mind_id": row["mind_id"],
                "event_type": row["event_type"],
                "summary": row["summary"],
                "payload": json.loads(row["payload_json"]) if row["payload_json"] else None,
                "created_at": row["created_at"]
            } for row in rows]

    # ========== Output 操作 ==========

    def add_output(self, output_id: str, mind_id: str, instruction: str, result: str) -> Dict[str, Any]:
        """添加输出记录"""
        now = datetime.now().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO output_tasks (id, mind_id, instruction, result, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (output_id, mind_id, instruction, result, now))
            conn.commit()

            # 记录事件
            self._add_timeline_event(conn, mind_id, "output", f"输出: {instruction[:30]}...")

        return {
            "id": output_id,
            "mind_id": mind_id,
            "instruction": instruction,
            "result": result,
            "created_at": now
        }


# 全局数据库实例
db = Database()
