import os
import sqlite3
from datetime import datetime, timedelta


BASE_DIR = os.path.dirname(os.path.abspath(__file__))+"/.."+"/db"
DB_PATH = os.path.join(BASE_DIR, 'dataBase.db')
print(BASE_DIR)


def check_card(cardIDM):
    """
    指定されたカード番号がデータベースに存在するかチェックします。

    Args:
        cardIDM (str): カード番号

    Returns:
        dict: カード情報（存在する場合）またはNone（存在しない場合）
    """
    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    try:
        cursor.execute(
            'SELECT card_id FROM card WHERE card_number = ?', (cardIDM,))
        card_id = cursor.fetchone()

        return card_id[0]
    except Exception as e:
        print(f"カード検索エラー: {e}")
        return None
    finally:
        conn.close()


def get_last_date_time(card_id, card_leader_id):
    dt = None
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT timestamp FROM access_logs where card_id = ? AND eventtype = ? ORDER BY timestamp DESC LIMIT 1", (card_id, card_leader_id))
    row = cursor.fetchone()
    if row:
        ts_str = row[0]
        dt = datetime.fromisoformat(ts_str)
    return dt


def insert_card_id(card_id, card_leader_id):
    # カードIDをaccess_logsテーブルに挿入します。
    dt = get_last_date_time(card_id, card_leader_id)
    if dt:
        now = datetime.now()

        if now - dt <= timedelta(seconds=10):
            print("10秒以内に登録されています")
            return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO access_logs (method, card_id, eventtype) VALUES(?,?,?)", ('カード', card_id, card_leader_id))
    conn.commit()
    conn.close()
