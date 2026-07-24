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



def create_database():
    """
    テーブル作成関数
    注意点:
        user削除時に紐づく情報はCASCADE削除されます。
        ただし、access_logsにはユーザー名のコピーを文字列で保存し、
        削除されたユーザーでも名前が何だったのか辿れるようにしています。

    """
    conn = get_connection()
    c = conn.cursor()

    # userテーブル作成(既に存在する場合は作成しない)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name_jpn TEXT NOT NULL,
            user_name_roma TEXT NOT NULL
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
            user_name_jpn TEXT,           -- ログ作成時点の名前のコピー(消えても残る)
            card_id INTEGER,
            face_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE SET NULL,
            FOREIGN KEY (card_id) REFERENCES card(id) ON DELETE SET NULL,
            FOREIGN KEY (face_id) REFERENCES face(id) ON DELETE SET NULL
        )
    """)

    # サンプルデータ
    c.execute("INSERT INTO card (card_name, card_number) VALUES (?, ?)", ("Sample Card", "1234567890123456"))
    c.execute("INSERT INTO access_logs (card_id, method, event_type) VALUES (?, ?, ?)", (1, "Web", 1))

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

    # サンプルデータを1件追加（初回のみ）
    c.execute(
        "INSERT INTO face (face_name, face_name_roma) VALUES (?, ?)",
        ("山田太郎", "taro_yamada"),
    )

    conn.commit()
    conn.close()



def insert_sameplelog_face(card_name, card_number):

    c.execute(
    "INSERT INTO access_logs (face_id, method, event_type) VALUES (?, ?, ?)",
    (1, "顔認証", 1)
    )

def main():#バック開始に呼び出されるinit作業
    create_database()


if __name__ == "__main__":
    main()
