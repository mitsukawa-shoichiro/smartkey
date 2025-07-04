import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

def findAllCard():
    # 全てのカード情報を取得
    cursor.execute("SELECT * FROM card")
    return cursor.fetchall()

def findAllLog():
    # 全てのアクセスログを取得
    cursor.execute("SELECT * FROM access_logs")
    return cursor.fetchall()