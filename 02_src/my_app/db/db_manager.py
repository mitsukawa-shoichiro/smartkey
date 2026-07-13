"""
db接続とテーブル作成を行うモジュール
DB接続は必ずこのモジュールから行うようにしてください
DB接続、テーブル作成のみをこのモジュールの責務としています。
"""

import sqlite3
import os
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()





