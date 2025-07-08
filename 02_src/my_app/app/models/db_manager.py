import sqlite3
import os

dir_path = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

DB_PATH = os.path.join(dir_path, "db", "database.db")

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

def findLog(card_name,method,eventtype):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    card_name = f"%{card_name}%"
    method = f"%{method}%"
    
    if eventtype is None:
        query = """
            SELECT id, card.card_name, method, timestamp, eventtype
            FROM access_logs 
            JOIN card ON access_logs.card_id = card.card_id 
            WHERE card.card_name LIKE ? AND method LIKE ?
        """
        params = (card_name, method)
    else:
        query = """
            SELECT id, card.card_name, method, timestamp, eventtype
            FROM access_logs 
            JOIN card ON access_logs.card_id = card.card_id 
            WHERE card.card_name LIKE ? AND method LIKE ? 
            AND access_logs.eventtype LIKE ?
        """
        params = (card_name, method, f"%{eventtype}%")
    cursor.execute(query, params)
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