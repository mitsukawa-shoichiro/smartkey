import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "database.db")
conn = sqlite3.connect(db_path)
c = conn.cursor()

# 外部キー有効化
c.execute('PRAGMA foreign_keys = ON;')

# テーブルを削除（存在していれば）
c.execute("DROP TABLE IF EXISTS access_logs")
c.execute("DROP TABLE IF EXISTS card")


# テーブル作成
c.execute('''
CREATE TABLE card (
    card_id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_name TEXT NOT NULL,
    card_number TEXT NOT NULL,
    register_date TIMESTAMP DEFAULT (datetime('now', 'localtime'))
    )
''')

c.execute('''
CREATE TABLE access_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT (datetime('now', 'localtime')),
    method VARCHAR(32) NOT NULL,
    card_id INTEGER,
    eventtype INTEGER,
    FOREIGN KEY(card_id) REFERENCES card(card_id)
)
''')

# サンプルデータ
c.execute("INSERT INTO card (card_name, card_number) VALUES (?, ?)", ("Sample Card", "1234567890123456"))
c.execute("INSERT INTO access_logs (card_id, method, eventtype) VALUES (?, ?, ?)", (1, "Web", 1))

conn.commit()
conn.close()
