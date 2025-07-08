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
    
    # カード名、認証方式、イベントタイプでアクセスログを検索
    # card_nameとmethodは部分一致検索、eventtypeは完全一致検索
    # COALESCEを使用して、eventtypeがNoneの場合は全てのeventtypeを対象とする
    logs = cursor.execute("""
                          SELECT id, card.card_name, method, timestamp, eventtype 
                          FROM access_logs JOIN card ON access_logs.card_id = card.card_id 
                          WHERE card.card_name LIKE ? AND method LIKE ? 
                          AND COALESCE(?, access_logs.eventtype) = access_logs.eventtype
                          """, (f"%{card_name}%", f"%{method}%", eventtype)
                          ).fetchall()
    
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