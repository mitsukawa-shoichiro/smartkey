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
   
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT card_id FROM card WHERE card_number = ?', (cardIDM,))
        card_id = cursor.fetchone()

        # #if card_id:
        #    # card_id=((str)(card_id))
            
        
        #     print(card_id[0])#[1:len(card_id)-2])
       
        #     print('成功です')
        #     return card_id[0]
        # else:

        #     print(card_id[0])
        #     print('失敗です')
        #     return None
        return card_id[0]
    except Exception as e:
        print(f"カード検索エラー: {e}")
        return None
    finally:
        conn.close()


def insert_card_id(card_id):
    # カードIDをaccess_logsテーブルに挿入します。
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO access_logs(card_id) VALUES(?)", (card_id))
    conn.commit()
    conn.close()


# def gainCardIDwithCardname(card_name):

#     # カードネームをもとに、カードIDを取得します。
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()
#     cursor.execute("SELECT card_id FROM card WHERE card_name= ?", (card_name,))
#     card_id = cursor.fetchall()
#     conn.close()
#     print(card_id)
#     return card_id


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
 
    check_card(98765)
    check_card(1234567890123456)
    check_card(13579)
    check_card(123)
    check_card(45678)
    check_card(321)
    check_card(56789)
