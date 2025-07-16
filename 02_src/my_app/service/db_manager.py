import os
import sqlite3


BASE_DIR = os.path.dirname(os.path.abspath(__file__))+"/.."+"/db"
DB_PATH = os.path.join(BASE_DIR, 'dataBase.db')
print(BASE_DIR)
# region


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


# endregion
if __name__ == '__main__':

    print("カード:", get_cards())
    print("アクセスログ:", get_access_logs())
    print("カード情報付きアクセスログ:", get_access_logs_with_card_info())
