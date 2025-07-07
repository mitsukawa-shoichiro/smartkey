import sqlite3

def findAllCard():
    # 全てのカード情報を取得
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM card")
    cards =  cursor.fetchall()
    conn.close()
    return cards

def deleteByIds(ids):
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.executemany("DELETE FROM card WHERE id = ?", [(i,) for i in ids])
    conn.commit()
    conn.close()

def findAllLog():
    # 全てのアクセスログを取得
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM access_logs")
    logs = cursor.fetchall()
    conn.close()
    return logs