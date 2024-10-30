# utils/cache.py

import sqlite3
import json
import time
from pathlib import Path
from typing import Optional, Any, Dict
from dataclasses import asdict
from ..config.settings import CacheConfig

class AnalysisCache:
    def __init__(self, config: CacheConfig):
        self.config = config
        self.db_path = Path(config.path).expanduser() / "analysis_cache.db"
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_cache (
                    file_path TEXT PRIMARY KEY,
                    content_hash TEXT,
                    analysis_data TEXT,
                    timestamp INTEGER,
                    file_size INTEGER
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON analysis_cache(timestamp)
            """)

    def get(self, file_path: str, content_hash: str) -> Optional[Dict]:
        """Get cached analysis if valid"""
        if not self.config.enabled:
            return None
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT analysis_data, timestamp 
                FROM analysis_cache 
                WHERE file_path = ? AND content_hash = ?
                """,
                (file_path, content_hash)
            )
            result = cursor.fetchone()
            
            if result:
                data, timestamp = result
                # Check if cache is still valid
                if time.time() - timestamp <= self.config.ttl * 60:
                    return json.loads(data)
                    
        return None

    def set(self, file_path: str, content_hash: str, analysis_data: Dict):
        """Cache analysis results"""
        if not self.config.enabled:
            return
            
        self._cleanup_if_needed()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO analysis_cache 
                (file_path, content_hash, analysis_data, timestamp, file_size)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    file_path,
                    content_hash,
                    json.dumps(analysis_data),
                    int(time.time()),
                    len(json.dumps(analysis_data))
                )
            )

    def _cleanup_if_needed(self):
        """Clean up old cache entries if size limit exceeded"""
        with sqlite3.connect(self.db_path) as conn:
            # Get total cache size
            cursor = conn.execute("SELECT SUM(file_size) FROM analysis_cache")
            total_size = cursor.fetchone()[0] or 0
            
            if total_size > self.config.max_size * 1024 * 1024:  # Convert MB to bytes
                # Delete oldest entries until under limit
                conn.execute(
                    """
                    DELETE FROM analysis_cache 
                    WHERE file_path IN (
                        SELECT file_path FROM analysis_cache 
                        ORDER BY timestamp ASC 
                        LIMIT ?
                    )
                    """,
                    (int(total_size * 0.2),)  # Remove oldest 20% of entries
                )

    def invalidate(self, file_path: str):
        """Invalidate cache entry for a file"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM analysis_cache WHERE file_path = ?",
                (file_path,)
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as entry_count,
                    SUM(file_size) as total_size,
                    MIN(timestamp) as oldest,
                    MAX(timestamp) as newest
                FROM analysis_cache
            """)
            stats = cursor.fetchone()
            
            return {
                "entry_count": stats[0],
                "total_size_mb": (stats[1] or 0) / (1024 * 1024),
                "oldest_entry": time.strftime(
                    '%Y-%m-%d %H:%M:%S',
                    time.localtime(stats[2] or 0)
                ),
                "newest_entry": time.strftime(
                    '%Y-%m-%d %H:%M:%S',
                    time.localtime(stats[3] or 0)
                )
            }