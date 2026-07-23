import sqlite3
import os
db_name = "database.db"

def DBInit():
    db_path = os.path.join(os.path.dirname(__file__), db_name)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS face")

    # 外部キーを有効化（SQLiteではデフォルトOFF）
    c.execute("PRAGMA foreign_keys = ON;")

    # --- faceテーブルが存在するか確認 ---
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
        print("[INFO] face テーブルは既に存在します。作成をスキップします。")

    conn.close()

def insert_sameplelog_face(face_id, method, eventtype):
    db_path = os.path.join(os.path.dirname(__file__), db_name)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
    "INSERT INTO access_logs (face_id, method, eventtype) VALUES (?, ?, ?)",
    (face_id, method, eventtype)
    )
    conn.commit()
    conn.close()

if __name__=="__main__":
    # DBInit()
    insert_sameplelog_face(1, "顔認証", 1)