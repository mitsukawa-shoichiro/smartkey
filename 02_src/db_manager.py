import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

def findAllCard():
    # 全てのカード情報を取得
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM card")
    cards =  cursor.fetchall()
    conn.close()
    return cards

def deleteByIds(ids):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executemany("DELETE FROM card WHERE card_id = ?", [(i,) for i in ids])
    conn.commit()
    conn.close()

def findAllLog():
    # 全てのアクセスログを取得
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM access_logs")
    logs = cursor.fetchall()
    conn.close()
    return logs