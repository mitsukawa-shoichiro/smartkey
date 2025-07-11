import os
import sqlite3
import sys


BASE_DIR = os.path.dirname(os.path.abspath(__file__))+"/.."+"/db"
DB_PATH = os.path.join(BASE_DIR, 'dataBase.db')
print(BASE_DIR)
#region
def init_db():
    """
    データベースとテーブル(access_logs, card)を初期化します。
    既存のテーブルがあれば削除し、新しく作成し直します。
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 既存テーブルの削除
    cursor.execute('DROP TABLE IF EXISTS access_logs')
    cursor.execute('DROP TABLE IF EXISTS card')
    
    # card表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS card (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_name VARCHAR NOT NULL,
        card_number VARCHAR NOT NULL,
        register_date DATETIME
    )
    ''')

    # access_logs表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS access_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id INTEGER,
        timestamp TIMESTAMP,
        method VARCHAR,
        eventtype INTEGER,
        FOREIGN KEY (card_id) REFERENCES card(id)
    );
    ''')

    conn.commit()
    conn.close()

def insert_sample_data():
    """
    サンプルデータ（カード・アクセスログ）を挿入します。
    テストやデモ用に利用してください。
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # サンプルカードデータ
    cursor.execute("INSERT INTO card (card_name, card_number, register_date) VALUES (?, ?, ?)",
                   ("山田太郎_suica", "1234567890", "2024-06-01 10:00:00"))
    cursor.execute("INSERT INTO card (card_name, card_number, register_date) VALUES (?, ?, ?)",
                   ("佐藤花子_pasmo", "0987654321", "2024-06-02 11:00:00"))
    cursor.execute("INSERT INTO card (card_name, card_number, register_date) VALUES (?, ?, ?)",
                   ("jcb", "57329E5A", "2024-06-02 11:00:00"))
    # サンプルアクセスログデータ
    cursor.execute("INSERT INTO access_logs (card_id, timestamp, method, eventtype) VALUES (?, ?, ?, ?)", 
                   (1, "2024-06-10 08:00:00", "カード", 0))
    cursor.execute("INSERT INTO access_logs (card_id, timestamp, method, eventtype) VALUES (?, ?, ?, ?)", 
                   (1, "2024-06-10 18:00:00", "カード", 1))
    cursor.execute("INSERT INTO access_logs (card_id, timestamp, method, eventtype) VALUES (?, ?, ?, ?)", 
                   (1, "2024-06-11 08:10:00", "カード", 0))
    cursor.execute("INSERT INTO access_logs (card_id, timestamp, method, eventtype) VALUES (?, ?, ?, ?)", 
                   (1, "2024-06-11 18:00:00", "カード", 1))
    cursor.execute("INSERT INTO access_logs (card_id, timestamp, method, eventtype) VALUES (?, ?, ?, ?)", 
                   (2, "2024-06-10 09:00:00", "カード", 0))
    cursor.execute("INSERT INTO access_logs (card_id, timestamp, method, eventtype) VALUES (?, ?, ?, ?)", 
                   (2, "2024-06-10 17:30:00", "カード", 1))

    conn.commit()
    conn.close()

def clear_db():
    """
    データベース内の全データ(access_logs, card)を削除します。
    テーブル構造は残ります。
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM access_logs")
    cursor.execute("DELETE FROM card")
    conn.commit()
    conn.close()

def get_cards():
    """
    カード情報(cardテーブル)を全件取得します。
    Returns:
        list[dict]: カード情報のリスト
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cards = conn.execute('SELECT * FROM card').fetchall()
    conn.close()
    return [dict(c) for c in cards]

def get_access_logs():
    """
    アクセスログ(access_logsテーブル)を全件取得します。
    Returns:
        list[dict]: アクセスログのリスト
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    logs = conn.execute('SELECT * FROM access_logs').fetchall()
    conn.close()
    return [dict(l) for l in logs]

def add_access_log(card_id, timestamp, method, eventtype):
    """
    新しいアクセスログを追加します。
    
    Args:
        card_id (int): カードID
        timestamp (str): タイムスタンプ
        method (str): 認証方式（カード、web）
        eventtype (int): 入室＝0、退室＝1
    
    Returns:
        dict: 追加したログの情報
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        INSERT INTO access_logs (card_id, timestamp, method, eventtype) 
        VALUES (?, ?, ?, ?)
        ''', (card_id, timestamp, method, eventtype))
        
        log_id = cursor.lastrowid
        conn.commit()
        
        # 追加したログ情報を返す
        added_log = {
            'id': log_id,
            'card_id': card_id,
            'timestamp': timestamp,
            'method': method,
            'eventtype': eventtype
        }
        
        return added_log
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_access_logs_with_card_info():
    """
    カード情報と結合したアクセスログを全件取得します。
    Returns:
        list[dict]: カード情報付きアクセスログのリスト
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT al.id, al.card_id, c.card_name, c.card_number, al.timestamp, al.method, al.eventtype
    FROM access_logs al
    JOIN card c ON al.card_id = c.id
    ORDER BY al.timestamp DESC
    ''')
    
    logs = cursor.fetchall()
    conn.close()
    return [dict(l) for l in logs]

def check_card(cardIDM):
    """
    指定されたカード番号がデータベースに存在するかチェックします。
    
    Args:
        cardIDM (str): カード番号
    
    Returns:
        dict: カード情報（存在する場合）またはNone（存在しない場合）
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT * FROM card WHERE card_number = ?', (cardIDM,))
        card = cursor.fetchone()
        
        if card:
            return True
        else:
            return False
            
    except Exception as e:
        print(f"カード検索エラー: {e}")
        return False
    finally:
        conn.close()

#endregion

if __name__ == '__main__':
    init_db()
    insert_sample_data()
    print("カード:", get_cards())
    print("アクセスログ:", get_access_logs())
    print("カード情報付きアクセスログ:", get_access_logs_with_card_info())
