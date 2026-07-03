import sqlite3
import os
from DataBase import create_database
db_path = os.path.join(os.path.dirname(__file__), "database.db")

import sqlite3

def CreateFaceTable():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # 外部キーを有効化（SQLiteではデフォルトOFF）
    c.execute("PRAGMA foreign_keys = ON;")

    # faceテーブルが存在するか確認
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='face';")
    exists = c.fetchone() is not None

    if not exists:
        print("[INFO] face テーブルが存在しません。新規作成します。")
        c.execute(
            """
            CREATE TABLE face (
                face_id INTEGER PRIMARY KEY AUTOINCREMENT,
                face_name TEXT NOT NULL,
                face_name_roma TEXT NOT NULL,
                register_date TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            );
            """
        )

        # サンプルデータを1件追加（初回のみ）
        c.execute(
            "INSERT INTO face (face_name, face_name_roma) VALUES (?, ?)",
            ("山田太郎", "taro_yamada"),
        )
        conn.commit()
        print("[OK] face テーブルを作成しました。")
    else:
        print("[INFO] face テーブルは既に存在します。何もしません。")

    conn.close()

def DBUpdate():
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 外部キーを有効化（この接続に対してのみ有効）
    cur.execute("PRAGMA foreign_keys = ON;")

    # access_logs テーブルの列情報を取得
    cur.execute("PRAGMA table_info(access_logs);")
    cols = {row[1] for row in cur.fetchall()}

    # すでに face_id 列が存在する場合は、何もせず終了
    if "face_id" in cols:
        print("[INFO] access_logs は既に新しい構造です（face_id あり）。処理をスキップします。")
        conn.close()
        return

    # ---- 以下は旧構造（face_id が存在しない）場合のみ実行 ----
    try:
        # テーブル再構築中は一時的に外部キー制約を無効化
        cur.execute("PRAGMA foreign_keys = OFF;")
        conn.commit()

        # 旧テーブルをリネーム
        cur.execute("ALTER TABLE access_logs RENAME TO access_logs_old;")

        # 新しい構造の access_logs テーブルを作成（face_id 外部キーを追加）
        cur.execute("""
            CREATE TABLE access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                method VARCHAR(32) NOT NULL,
                card_id INTEGER,
                face_id INTEGER,
                eventtype INTEGER,
                FOREIGN KEY(card_id) REFERENCES card(card_id),
                FOREIGN KEY(face_id) REFERENCES face(face_id)
            );
        """)

        # 古いテーブルのデータを新しいテーブルへ移行（face_id は NULL で補完）
        cur.execute("""
            INSERT INTO access_logs (id, timestamp, method, card_id, eventtype, face_id)
            SELECT
                id,
                timestamp,
                method,
                card_id,
                eventtype,
                NULL
            FROM access_logs_old;
        """)

        # 古いテーブルを削除し、外部キー制約を再有効化
        cur.execute("DROP TABLE access_logs_old;")
        cur.execute("PRAGMA foreign_keys = ON;")
        conn.commit()

        print("[OK] access_logs をアップグレードし、face(face_id) 外部キーを追加しました。")
    finally:
        conn.close()


def insert_sameplelog_face(card_name, card_number):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
    "INSERT INTO access_logs (face_id, method, eventtype) VALUES (?, ?, ?)",
    (1, "顔認証", 1)
    )

def main():#バック開始に呼び出されるinit作業
    CreateFaceTable()
    DBUpdate()
    create_database()


if __name__ == "__main__":
    main()
