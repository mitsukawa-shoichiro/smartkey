import sqlite3
import os
from datetime import datetime, timedelta

dir_path = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

DB_PATH = os.path.join(dir_path, "db", "database.db")


def delete_card_by_ids(ids):

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executemany("DELETE FROM card WHERE card_id = ?", [(i,) for i in ids])
    conn.commit()
    conn.close()


def find_log(card_name, method, eventtype, start_datetime, end_datetime, limit, offset, asc: bool = True):
    order = "ASC" if asc else "DESC"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now()

    card_name = f"%{card_name}%" if card_name else "%"
    method = f"%{method}%" if method else "%"

    start_datetime = start_datetime or (now - timedelta(days=365))
    end_datetime = end_datetime or now

    start_datetime_str = start_datetime.strftime("%Y-%m-%d %H:%M:%S")
    end_datetime_str = end_datetime.strftime("%Y-%m-%d %H:%M:%S")

    # カード名、認証方式、イベントタイプでアクセスログを検索
    # card_nameとmethodは部分一致検索、eventtypeは完全一致検索
    # COALESCEを使用して、eventtypeがNoneの場合は全てのeventtypeを対象とする
    logs = cursor.execute(f"""
                          SELECT id, card.card_name, method, timestamp, eventtype 
                          FROM access_logs JOIN card ON access_logs.card_id = card.card_id 
                          WHERE card.card_name LIKE ? AND method LIKE ? 
                          AND (? IS NULL OR access_logs.eventtype = ?) 
                          AND access_logs.timestamp BETWEEN ? AND ? ORDER BY timestamp {order} LIMIT ? OFFSET ?
                          """, (card_name, method, eventtype, eventtype, start_datetime_str, end_datetime_str, limit, offset)
                          ).fetchall()

    conn.close()
    return logs


def count_filtered_logs(card_name=None, method=None, eventtype=None, start_datetime=None, end_datetime=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    now = datetime.now()
    card_name = f"%{card_name}%" if card_name else "%"
    method = f"%{method}%" if method else "%"
    start_datetime = start_datetime or (now - timedelta(days=365))
    end_datetime = end_datetime or now

    start_datetime_str = start_datetime.strftime("%Y-%m-%d %H:%M:%S")
    end_datetime_str = end_datetime.strftime("%Y-%m-%d %H:%M:%S")

    query = """
        SELECT COUNT(*) 
        FROM access_logs 
        JOIN card ON access_logs.card_id = card.card_id 
        WHERE card.card_name LIKE ? 
          AND method LIKE ? 
          AND (? IS NULL OR access_logs.eventtype = ?) 
          AND access_logs.timestamp BETWEEN ? AND ?
    """
    cursor.execute(query, (
        card_name, method, eventtype, eventtype,
        start_datetime_str, end_datetime_str
    ))
    count = cursor.fetchone()[0]

    conn.close()
    return count


def find_by_card_name(card_name):
    # カード名でカード情報を取得
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM card WHERE card_name LIKE ?",
                   (f"%{card_name}%",))
    cards = cursor.fetchall()
    conn.close()
    return cards


def update_card_name(card_id, new_name):
    # カード名を更新
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE card SET card_name = ? WHERE card_id = ?", (new_name, card_id))
    conn.commit()
    conn.close()


def find_card_name_by_id(card_id):
    # カードIDからカード名を取得
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT card_name FROM card WHERE card_id = ?", (card_id,))
    card_name = cursor.fetchone()
    conn.close()
    return card_name


def insert_card(card_name, card_number):
    # カードを新規登録
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO card (card_name, card_number) VALUES (?, ?)", (card_name, card_number))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    import random

    hiragana = 'あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん'

    def generate_random_hiragana(length):
        return ''.join(random.choices(hiragana, k=length))

    for i in range(1000):

        moji = generate_random_hiragana(5)
        suuji = random.randint(10000, 1000000)

        insert_card(moji, suuji)
