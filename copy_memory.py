"""
文案记忆库：记录生成数据、语义检索、Skill 优化
"""
import sqlite3
import json
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional

DB_PATH = "data/collected.db"


class CopyMemory:
    """文案记忆库"""
    
    def __init__(self):
        self._init_table()
    
    def _init_table(self):
        """初始化 copy_embeddings 表"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS copy_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feed_id TEXT UNIQUE,
                school_name TEXT,
                material_type TEXT,
                quality_grade TEXT,
                original_text TEXT,
                generated_copy TEXT,
                published_copy TEXT,
                embedding TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def save_record(self, feed_id: str, school_name: str, material_type: str,
                    quality_grade: str, original_text: str, generated_copy: str,
                    published_copy: Optional[str] = None, embedding: Optional[List[float]] = None):
        """保存生成记录"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 检查是否已存在
        cursor.execute("SELECT id FROM copy_embeddings WHERE feed_id = ?", (feed_id,))
        exists = cursor.fetchone()
        
        if exists:
            cursor.execute("""
                UPDATE copy_embeddings 
                SET school_name=?, material_type=?, quality_grade=?, 
                    original_text=?, generated_copy=?, published_copy=?, 
                    embedding=?, updated_at=?
                WHERE feed_id=?
            """, (school_name, material_type, quality_grade,
                  original_text, generated_copy, published_copy,
                  json.dumps(embedding) if embedding else None, now, feed_id))
        else:
            cursor.execute("""
                INSERT INTO copy_embeddings 
                (feed_id, school_name, material_type, quality_grade, 
                 original_text, generated_copy, published_copy, embedding, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (feed_id, school_name, material_type, quality_grade,
                  original_text, generated_copy, published_copy,
                  json.dumps(embedding) if embedding else None, now))
        
        conn.commit()
        conn.close()
    
    def update_published_copy(self, feed_id: str, published_copy: str):
        """更新发布稿（用户在飞书修改后同步）"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE copy_embeddings 
            SET published_copy=?, updated_at=?
            WHERE feed_id=?
        """, (published_copy, now, feed_id))
        conn.commit()
        conn.close()
    
    def get_all_records(self) -> List[Dict]:
        """获取所有记录"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT feed_id, school_name, material_type, quality_grade,
                   original_text, generated_copy, published_copy, embedding,
                   created_at, updated_at
            FROM copy_embeddings
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        
        records = []
        for row in rows:
            records.append({
                "feed_id": row[0],
                "school_name": row[1],
                "material_type": row[2],
                "quality_grade": row[3],
                "original_text": row[4],
                "generated_copy": row[5],
                "published_copy": row[6],
                "embedding": json.loads(row[7]) if row[7] else None,
                "created_at": row[8],
                "updated_at": row[9]
            })
        return records
    
    def get_records_with_published(self) -> List[Dict]:
        """获取有发布稿的记录（用于分析反馈）"""
        records = self.get_all_records()
        return [r for r in records if r.get("published_copy")]
    
    def count_records(self) -> int:
        """获取记录总数"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM copy_embeddings")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def count_with_published(self) -> int:
        """获取有发布稿的记录数"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM copy_embeddings WHERE published_copy IS NOT NULL AND published_copy != ''")
        count = cursor.fetchone()[0]
        conn.close()
        return count
