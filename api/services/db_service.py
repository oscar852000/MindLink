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

            # Mind 表（包含 user_id 字段）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS minds (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL DEFAULT 1,
                    title TEXT NOT NULL,
                    north_star TEXT,
                    crystal_json TEXT,
                    summary TEXT,
                    narrative TEXT,
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
                    cleaned_content TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (mind_id) REFERENCES minds(id)
                )
            """)

            # 检查并添加 cleaned_content 字段（兼容旧数据库）
            cursor.execute("PRAGMA table_info(feed_items)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'cleaned_content' not in columns:
                cursor.execute("ALTER TABLE feed_items ADD COLUMN cleaned_content TEXT")

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

            # Prompts 表（提示词管理）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prompts (
                    key TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    description TEXT,
                    updated_at TEXT NOT NULL
                )
            """)

            # Tags 表（全局标签库）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # Mind-Tags 关联表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mind_tags (
                    mind_id TEXT NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY (mind_id, tag_id),
                    FOREIGN KEY (mind_id) REFERENCES minds(id),
                    FOREIGN KEY (tag_id) REFERENCES tags(id)
                )
            """)

            # Chat 消息表（对话记录）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mind_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    model TEXT,
                    style TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (mind_id) REFERENCES minds(id)
                )
            """)

            # 检查并添加 minds.summary 字段（兼容旧数据库）
            cursor.execute("PRAGMA table_info(minds)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'summary' not in columns:
                cursor.execute("ALTER TABLE minds ADD COLUMN summary TEXT")

            # 检查并添加 minds.user_id 字段（兼容旧数据库）
            if 'user_id' not in columns:
                cursor.execute("ALTER TABLE minds ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
                # 将现有数据归属给管理员（user_id=1）
                cursor.execute("UPDATE minds SET user_id = 1 WHERE user_id IS NULL")
                logger.info("数据库迁移：已添加 user_id 字段，现有数据归属管理员")

            conn.commit()
            logger.info("数据库初始化完成")

    # ========== Mind 操作 ==========

    def create_mind(self, mind_id: str, title: str, user_id: int, north_star: Optional[str] = None) -> Dict[str, Any]:
        """创建 Mind"""
        now = datetime.now().isoformat()
        initial_crystal = {
            "core_goal": north_star or "",
            "current_knowledge": [],
            "highlights": [],
            "pending_notes": [],
            "evolution": []
        }

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO minds (id, user_id, title, north_star, crystal_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (mind_id, user_id, title, north_star, json.dumps(initial_crystal, ensure_ascii=False), now, now))
            conn.commit()

            # 记录事件
            self._add_timeline_event(conn, mind_id, "create", f"创建 Mind: {title}")

        return {
            "id": mind_id,
            "user_id": user_id,
            "title": title,
            "north_star": north_star,
            "crystal": initial_crystal,
            "created_at": now,
            "updated_at": now
        }

    def get_mind(self, mind_id: str, user_id: int = None) -> Optional[Dict[str, Any]]:
        """获取 Mind（可选验证 user_id）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if user_id is not None:
                cursor.execute("SELECT * FROM minds WHERE id = ? AND user_id = ?", (mind_id, user_id))
            else:
                cursor.execute("SELECT * FROM minds WHERE id = ?", (mind_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return {
                "id": row["id"],
                "user_id": row["user_id"] if "user_id" in row.keys() else 1,
                "title": row["title"],
                "north_star": row["north_star"],
                "crystal": json.loads(row["crystal_json"]) if row["crystal_json"] else None,
                "summary": row["summary"],
                "narrative": row["narrative"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }

    def list_minds(self, user_id: int = None) -> List[Dict[str, Any]]:
        """获取 Mind 列表（可选按 user_id 过滤）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if user_id is not None:
                cursor.execute("SELECT * FROM minds WHERE user_id = ? ORDER BY updated_at DESC", (user_id,))
            else:
                cursor.execute("SELECT * FROM minds ORDER BY updated_at DESC")
            rows = cursor.fetchall()

            return [{
                "id": row["id"],
                "user_id": row["user_id"] if "user_id" in row.keys() else 1,
                "title": row["title"],
                "north_star": row["north_star"],
                "crystal": json.loads(row["crystal_json"]) if row["crystal_json"] else None,
                "summary": row["summary"] if "summary" in row.keys() else None,
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            } for row in rows]

    def delete_mind(self, mind_id: str, user_id: int = None) -> bool:
        """删除 Mind 及其所有关联数据（可选验证 user_id）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 如果指定了 user_id，先验证归属
            if user_id is not None:
                cursor.execute("SELECT id FROM minds WHERE id = ? AND user_id = ?", (mind_id, user_id))
                if not cursor.fetchone():
                    return False

            # 删除关联的 feed_items
            cursor.execute("DELETE FROM feed_items WHERE mind_id = ?", (mind_id,))

            # 删除关联的 timeline_events
            cursor.execute("DELETE FROM timeline_events WHERE mind_id = ?", (mind_id,))

            # 删除关联的 output_tasks
            cursor.execute("DELETE FROM output_tasks WHERE mind_id = ?", (mind_id,))

            # 删除关联的 mind_tags
            cursor.execute("DELETE FROM mind_tags WHERE mind_id = ?", (mind_id,))

            # 删除关联的 chat_messages
            cursor.execute("DELETE FROM chat_messages WHERE mind_id = ?", (mind_id,))

            # 删除 Mind 本身
            cursor.execute("DELETE FROM minds WHERE id = ?", (mind_id,))

            conn.commit()
            return cursor.rowcount > 0

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
                "cleaned_content": row["cleaned_content"],
                "created_at": row["created_at"]
            } for row in rows]

    def update_feed_cleaned(self, feed_id: str, cleaned_content: str) -> bool:
        """更新投喂的去噪内容"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE feed_items SET cleaned_content = ? WHERE id = ?
            """, (cleaned_content, feed_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_feed_content(self, feed_id: str, content: str) -> bool:
        """更新投喂内容（同时更新原始内容和去噪内容）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE feed_items SET content = ?, cleaned_content = ? WHERE id = ?
            """, (content, content, feed_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_feed(self, feed_id: str) -> bool:
        """删除投喂"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM feed_items WHERE id = ?", (feed_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_all_cleaned_feeds(self, mind_id: str) -> List[Dict[str, Any]]:
        """获取所有已去噪的投喂（用于生成叙事视图）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, cleaned_content, created_at FROM feed_items
                WHERE mind_id = ? AND cleaned_content IS NOT NULL
                ORDER BY created_at ASC
            """, (mind_id,))
            rows = cursor.fetchall()

            return [{
                "id": row["id"],
                "cleaned_content": row["cleaned_content"],
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

    # ========== Prompt 操作 ==========

    def get_prompt(self, key: str) -> Optional[str]:
        """获取提示词内容"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM prompts WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["content"] if row else None

    def get_all_prompts(self) -> List[Dict[str, Any]]:
        """获取所有提示词"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM prompts ORDER BY key")
            rows = cursor.fetchall()
            return [{
                "key": row["key"],
                "name": row["name"],
                "content": row["content"],
                "description": row["description"],
                "updated_at": row["updated_at"]
            } for row in rows]

    def upsert_prompt(self, key: str, name: str, content: str, description: str = "") -> Dict[str, Any]:
        """创建或更新提示词"""
        now = datetime.now().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO prompts (key, name, content, description, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    name = excluded.name,
                    content = excluded.content,
                    description = excluded.description,
                    updated_at = excluded.updated_at
            """, (key, name, content, description, now))
            conn.commit()

        return {
            "key": key,
            "name": name,
            "content": content,
            "description": description,
            "updated_at": now
        }

    # ========== 概述和标签操作 ==========

    def update_mind_summary(self, mind_id: str, summary: str) -> bool:
        """更新 Mind 概述"""
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE minds SET summary = ?, updated_at = ? WHERE id = ?
            """, (summary, now, mind_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_mind_narrative(self, mind_id: str, narrative: str) -> bool:
        """更新 Mind 叙事"""
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE minds SET narrative = ?, updated_at = ? WHERE id = ?
            """, (narrative, now, mind_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_all_tags(self) -> List[Dict[str, Any]]:
        """获取全局标签库"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tags ORDER BY name")
            rows = cursor.fetchall()
            return [{
                "id": row["id"],
                "name": row["name"],
                "created_at": row["created_at"]
            } for row in rows]

    def get_or_create_tag(self, tag_name: str) -> int:
        """获取或创建标签，返回标签 ID"""
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            return self._get_or_create_tag_with_conn(conn, tag_name, now)

    def _get_or_create_tag_with_conn(self, conn, tag_name: str, now: str) -> int:
        """内部方法：在已有连接中获取或创建标签"""
        cursor = conn.cursor()
        # 先尝试获取
        cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
        row = cursor.fetchone()
        if row:
            return row["id"]
        # 不存在则创建
        cursor.execute("""
            INSERT INTO tags (name, created_at) VALUES (?, ?)
        """, (tag_name, now))
        conn.commit()
        return cursor.lastrowid

    def get_mind_tags(self, mind_id: str) -> List[str]:
        """获取 Mind 的标签列表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.name FROM tags t
                JOIN mind_tags mt ON t.id = mt.tag_id
                WHERE mt.mind_id = ?
                ORDER BY t.name
            """, (mind_id,))
            rows = cursor.fetchall()
            return [row["name"] for row in rows]

    def set_mind_tags(self, mind_id: str, tag_names: List[str]) -> None:
        """设置 Mind 的标签（替换现有标签）"""
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 删除现有标签关联
            cursor.execute("DELETE FROM mind_tags WHERE mind_id = ?", (mind_id,))
            # 添加新标签（使用同一连接）
            for tag_name in tag_names[:5]:  # 最多 5 个标签
                tag_id = self._get_or_create_tag_with_conn(conn, tag_name.strip(), now)
                cursor.execute("""
                    INSERT OR IGNORE INTO mind_tags (mind_id, tag_id) VALUES (?, ?)
                """, (mind_id, tag_id))
            conn.commit()

    # ========== Chat 消息操作 ==========

    def add_chat_message(self, mind_id: str, role: str, content: str,
                         model: str = None, style: str = None) -> Dict[str, Any]:
        """添加对话消息"""
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO chat_messages (mind_id, role, content, model, style, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (mind_id, role, content, model, style, now))
            conn.commit()
            return {
                "id": cursor.lastrowid,
                "mind_id": mind_id,
                "role": role,
                "content": content,
                "model": model,
                "style": style,
                "created_at": now
            }

    def get_chat_history(self, mind_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取对话历史"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM chat_messages
                WHERE mind_id = ?
                ORDER BY created_at ASC
                LIMIT ?
            """, (mind_id, limit))
            rows = cursor.fetchall()
            return [{
                "id": row["id"],
                "role": row["role"],
                "content": row["content"],
                "model": row["model"],
                "style": row["style"],
                "created_at": row["created_at"]
            } for row in rows]

    def clear_chat_history(self, mind_id: str) -> int:
        """清空对话历史，返回删除的消息数"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_messages WHERE mind_id = ?", (mind_id,))
            conn.commit()
            return cursor.rowcount


# 全局数据库实例
db = Database()
