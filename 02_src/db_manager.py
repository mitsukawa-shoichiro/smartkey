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

    cursor.execute("""
                   SELECT id,card.card_name,method,timestamp,eventtype 
                   FROM access_logs JOIN card ON access_logs.card_id = card.card_id 
                   """)
    logs = cursor.fetchall()
    conn.close()
    return logs

def findLog(card_name,method,timestamp,eventtype):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    card_name = f"%{card_name}%"
    method = f"%{method}%"
    timestamp = f"%{timestamp}%"
    eventtype = f"%{eventtype}%"
    
    cursor.execute("""
                   SELECT id,card.card_name,method,timestamp,eventtype 
                   FROM access_logs JOIN card ON access_logs.card_id = card.card_id 
                   WHERE card.card_name LIKE ? AND method LIKE ? 
                   AND timestamp LIKE ? AND CAST(access_logs.eventtype AS TEXT) LIKE ?
                   """,(card_name,method,timestamp,eventtype))
    logs = cursor.fetchall()
    conn.close()
    return logs

def findByCardName(card_name):
    # カード名でカード情報を取得
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM card WHERE card_name LIKE ?", (f"%{card_name}%",))
    cards = cursor.fetchall()
    conn.close()
    return cards