import sqlite3
import os
import FaceDataBase

# --- FaceData テーブルの初期化 ---
# 注意: FaceDataBase.DBInit() 内では FaceData テーブルが毎回 DROP されます（開発用）
FaceDataBase.DBInit()

# --- データベース接続設定 ---
db_path = os.path.join(os.path.dirname(__file__), "database.db")
conn = sqlite3.connect(db_path)
c = conn.cursor()

# --- 外部キーを有効化（SQLiteではデフォルトでOFF） ---
c.execute("PRAGMA foreign_keys = ON;")

# --- 既存テーブルを削除（開発用。本番環境では実行しないこと） ---
c.execute("DROP TABLE IF EXISTS access_logs;")
c.execute("DROP TABLE IF EXISTS card;")

# --- card テーブルの作成 ---
c.execute("""
CREATE TABLE card (
    card_id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_name TEXT NOT NULL,
    card_number TEXT NOT NULL,
    register_date TIMESTAMP DEFAULT (datetime('now', 'localtime'))
);
""")

# --- access_logs テーブルの作成 ---
# card_id → card.card_id
# face_id → FaceData.face_id に外部キーを設定
c.execute("""
CREATE TABLE access_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT (datetime('now', 'localtime')),
    method VARCHAR(32) NOT NULL,
    card_id INTEGER,
    face_id INTEGER,
    eventtype INTEGER,
    FOREIGN KEY(card_id) REFERENCES card(card_id),
    FOREIGN KEY(face_id) REFERENCES FaceData(face_id)
);
""")

# --- サンプルデータの追加 ---
c.execute(
    "INSERT INTO card (card_name, card_number) VALUES (?, ?)",
    ("Sample Card", "1234567890123456")
)
c.execute(
    "INSERT INTO access_logs (card_id, method, eventtype) VALUES (?, ?, ?)",
    (1, "Web", 1)
)

# --- コミットして接続を閉じる ---
conn.commit()
conn.close()
