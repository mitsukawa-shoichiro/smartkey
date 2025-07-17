import os
import sqlite3


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


def insert_card_id(card_id):
    # カードIDをaccess_logsテーブルに挿入します。
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO access_logs(card_id) VALUES(?)", (card_id))
    conn.commit()
    conn.close()


def gainCardIDwithCardname(card_name):

    # カードネームをもとに、カードIDを取得します。
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT card_id FROM card WHERE card_name= ?", (card_name,))
    card_id = cursor.fetchall()
    conn.close()
    print(card_id)
    return card_id


def insert_card_id(card_id):
    # カードIDをaccess_logsテーブルに挿入します。
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO access_logs (method, card_id, eventtype) VALUES(?,?,?)", ('Web', card_id, '0'))
    conn.commit()
    conn.close()


# endregion
if __name__ == '__main__':

    insert_card_id("1")
    gain_card_id_with_card_name("SampleCard")
