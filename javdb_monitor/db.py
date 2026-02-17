"""
SQLite 数据库模块 - 用于记录已获取的影片，实现去重
"""
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class HistoryDB:
    """影片抓取历史记录数据库"""

    def __init__(self, db_path='./data/history.db'):
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        logger.info(f'数据库已连接: {db_path}')

    def _create_tables(self):
        self.conn.executescript('''
            CREATE TABLE IF NOT EXISTS videos (
                video_id    TEXT PRIMARY KEY,
                title       TEXT,
                url         TEXT,
                tags        TEXT,
                date        TEXT,
                created_at  TEXT
            );

            CREATE TABLE IF NOT EXISTS magnets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id    TEXT NOT NULL,
                magnet      TEXT NOT NULL,
                name        TEXT,
                size        TEXT,
                created_at  TEXT,
                FOREIGN KEY (video_id) REFERENCES videos(video_id),
                UNIQUE(video_id, magnet)
            );
        ''')
        self.conn.commit()

    def is_seen(self, video_id):
        """检查番号是否已经抓取过"""
        cur = self.conn.execute(
            'SELECT 1 FROM videos WHERE video_id = ?', (video_id,)
        )
        return cur.fetchone() is not None

    def add_video(self, video_id, title='', url='', tag='', date='', magnets=None):
        """
        添加影片记录及其磁力链接
        如果影片已存在但来自不同标签，更新 tags 字段
        """
        now = datetime.now().isoformat()

        # 检查是否已存在
        existing = self.conn.execute(
            'SELECT tags FROM videos WHERE video_id = ?', (video_id,)
        ).fetchone()

        if existing:
            # 已存在，合并标签
            existing_tags = set(existing['tags'].split(',')) if existing['tags'] else set()
            existing_tags.add(tag)
            merged_tags = ','.join(sorted(existing_tags))
            self.conn.execute(
                'UPDATE videos SET tags = ? WHERE video_id = ?',
                (merged_tags, video_id)
            )
        else:
            # 新记录
            self.conn.execute(
                'INSERT INTO videos (video_id, title, url, tags, date, created_at) '
                'VALUES (?, ?, ?, ?, ?, ?)',
                (video_id, title, url, tag, date, now)
            )

        # 添加磁力链接（去重）
        new_count = 0
        for m in (magnets or []):
            try:
                self.conn.execute(
                    'INSERT OR IGNORE INTO magnets (video_id, magnet, name, size, created_at) '
                    'VALUES (?, ?, ?, ?, ?)',
                    (video_id, m['magnet'], m.get('name', ''), m.get('size', ''), now)
                )
                if self.conn.total_changes:
                    new_count += 1
            except sqlite3.IntegrityError:
                pass

        self.conn.commit()
        return new_count

    def get_stats(self):
        """获取统计信息"""
        video_count = self.conn.execute('SELECT COUNT(*) FROM videos').fetchone()[0]
        magnet_count = self.conn.execute('SELECT COUNT(*) FROM magnets').fetchone()[0]
        return {'videos': video_count, 'magnets': magnet_count}

    def close(self):
        self.conn.close()
        logger.debug('数据库已关闭')
