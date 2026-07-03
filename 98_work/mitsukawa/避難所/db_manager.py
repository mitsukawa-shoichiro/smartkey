
#service.dbmanagerに統合済み、残しておきます↓元の住所
#C:\smartkey\02_src\my_app\app\models\db_manager.py

import sqlite3
import os
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


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
    try:
        cur.executemany("DELETE FROM card WHERE card_id = ?", [(i,) for i in ids])
        conn.commit()
    except sqlite3.Error as e:
        logger.exception("カード削除エラー: ids=%s", ids)
        raise
    finally:
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

    try:
        logs = cursor.execute(f"""
                            SELECT id, card.card_name, method, timestamp, eventtype
                            FROM access_logs JOIN card ON access_logs.card_id = card.card_id
                            WHERE card.card_name LIKE ? AND method LIKE ?
                            AND (? IS NULL OR access_logs.eventtype = ?)
                            AND access_logs.timestamp BETWEEN ? AND ? ORDER BY timestamp {order} LIMIT ? OFFSET ?
                            """, (card_name, method, eventtype, eventtype, start_datetime_str, end_datetime_str, limit, offset)
                            ).fetchall()
    except sqlite3.Error as e:
        logger.exception("アクセスログ検索エラー: card_name=%s, method=%s, eventtype=%s", card_name, method, eventtype)
        raise
    finally:
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
    try:

        cursor.execute(query, (
            card_name, method, eventtype, eventtype,
            start_datetime_str, end_datetime_str
        ))
        count = cursor.fetchone()[0]
    except sqlite3.Error as e:
        logger.exception("アクセスログ件数取得エラー: card_name=%s, method=%s, eventtype=%s", card_name, method, eventtype)
        raise
    finally:
        conn.close()
    return count


def find_by_card_name(card_name, asc: bool, offset):
    # カード名でカード情報を取得
    order = "ASC" if asc else "DESC"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT * FROM card WHERE card_name LIKE ? ORDER BY card_id {order} LIMIT 100 OFFSET ?",
                    (f"%{card_name}%", offset))
        cards = cursor.fetchall()
    except sqlite3.Error as e:
        logger.exception("カード検索エラー: card_name=%s", card_name)
        raise
    finally:
        conn.close()
    return cards


def count_all_card(card_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT COUNT(*) FROM card WHERE card_name LIKE ?",
                       (f"%{card_name}%", ))
        count = cursor.fetchall()
    except sqlite3.Error as e:
        logger.exception("カード件数取得エラー: card_name=%s", card_name)
        raise
    finally:
        conn.close()
    return count[0]


def update_card_name(card_id, new_name):
    # カード名を更新
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE card SET card_name = ? WHERE card_id = ?", (new_name, card_id))
        conn.commit()
    except sqlite3.Error as e:
        logger.exception("カード名更新エラー: card_id=%s, new_name=%s", card_id, new_name)
        raise
    finally:
        conn.close()


def find_card_name_by_id(card_id):
    # カードIDからカード名を取得
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT card_name FROM card WHERE card_id = ?", (card_id,))
        card_name = cursor.fetchone()
    except sqlite3.Error as e:
        logger.exception("カード名取得エラー: card_id=%s", card_id)
        raise
    finally:
        conn.close()
    return card_name


def insert_card(card_name, card_number):
    # カードを新規登録
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO card (card_name, card_number) VALUES (?, ?)", (card_name, card_number))
        conn.commit()
    except sqlite3.Error as e:
        logger.exception("カード登録エラー: card_name=%s, card_number=%s", card_name, card_number)
        raise
    finally:
        conn.close()

def insert_samplelogs(card_id,eventtype,timestamp):
    # サンプルログを挿入
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO access_logs (card_id, method, eventtype,timestamp) VALUES (?, ?, ?,?)", (card_id,"カード" ,eventtype,timestamp))
        conn.commit()
    except sqlite3.Error as e:
        logger.exception("サンプルログ挿入エラー: card_id=%s, eventtype=%s, timestamp=%s", card_id, eventtype, timestamp)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import random
    from datetime import datetime, timedelta


    hiragana = 'あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん'
    alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

    def generate_random_hiragana(length):
        return ''.join(random.choices(hiragana, k=length))

    def generate_random_alphabet(length):
        return ''.join(random.choices(alphabet, k=length))

    for i in range(299):

        moji = generate_random_hiragana(5)
        card = generate_random_alphabet(5)
        suuji = random.randint(10000, 1000000)
        name = moji + "_" + card
        insert_card(name, suuji)

    def generate_random_timestamp():

        end_date = datetime.now()
        start_date = (end_date - timedelta(days=365))

        delta_seconds = int((end_date - start_date).total_seconds())

        random_seconds = random.randint(0, delta_seconds)
        random_datetime = start_date + timedelta(seconds=random_seconds)

        timestamp = random_datetime.strftime("%Y-%m-%d %H:%M:%S")

        return timestamp

    for i in range(299):
        card_id = random.randint(1,150)
        eventtype = random.randint(0,1)
        timestamp = generate_random_timestamp()
        insert_samplelogs(card_id,eventtype,timestamp)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executemany("DELETE FROM card WHERE card_id = ?",
                    [(i,) for i in range(500, 1050)])
    conn.commit()
    conn.close()

