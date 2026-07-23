"""
DB接続を管理するモジュール

get_connection() は with 文で使うことを前提とした
コンテキストマネージャです。

    with get_connection() as conn:
        c = conn.cursor()
        c.execute(...)

- with ブロックが正常に終了したら自動で conn.commit()
- ブロック内で例外が起きたら自動で conn.rollback() してから re-raise
- どちらの場合も最後に必ず conn.close()

呼び出し側は commit / rollback / close を一切書く必要がありません。^^
"""


import os
import sqlite3
import logging
from .db_manager import get_connection

logger = logging.getLogger(__name__)





def create_database():


    """
    テーブル作成関数
    注意点:
        user削除時に紐づく情報はCASCADE削除されます。
        ただし、access_logsにはユーザー名のコピーを文字列で保存し、
        削除されたユーザーでも名前が何だったのか辿れるようにしています。

    """

    """
    テーブル詳細

    userテーブル:
    id, user_name, user_kana

    cardテーブル:
    id, card_type, card_number, register_date, user_id(user.id)

    access_logsテーブル:
    id, timestamp, method, event_type, user_name, card_id, face_id, user_id(user.id)

    faceテーブル:
    id, register_date, user_id(user.id)

    """
    with get_connection() as conn:
        c = conn.cursor()

        # userテーブル作成(既に存在する場合は作成しない)
        c.execute("""
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                user_kana TEXT NOT NULL
            )
        """)

        # cardテーブル作成(既に存在する場合は作成しない)
        c.execute("""
            CREATE TABLE IF NOT EXISTS card (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_type TEXT NOT NULL,
                card_number TEXT NOT NULL,
                register_date DATE DEFAULT (DATE('now')),
                user_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
            )
        """)

        # access_logsテーブル作成(既に存在する場合は作成しない)
        c.execute("""
            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                method VARCHAR(32) NOT NULL,
                event_type INTEGER,
                user_id INTEGER,              -- 生きているuserへの参照(消えたらNULLでよい)
                user_name TEXT,           -- ログ作成時点の名前のコピー(消えても残る)
                card_id INTEGER,
                face_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE SET NULL,
                FOREIGN KEY (card_id) REFERENCES card(id) ON DELETE SET NULL,
                FOREIGN KEY (face_id) REFERENCES face(id) ON DELETE SET NULL
            )
        """)

        c.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_access_logs_timestamp_event
            ON access_logs(timestamp, event_type)
        """)


        # faceテーブルが存在するか確認
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='face';")
        exists = c.fetchone() is not None

        # faceテーブル作成(既に存在する場合は作成しない)
        c.execute("""
            CREATE TABLE IF NOT EXISTS face (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                register_date DATE DEFAULT (DATE('now')),
                user_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
            )
        """)


