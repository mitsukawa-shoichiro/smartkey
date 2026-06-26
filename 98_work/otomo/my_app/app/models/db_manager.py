from ast import List
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional, Dict
dir_path = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)
"""

db_managerはservice側に統合、一応残しておきます

"""



DB_PATH = os.path.join(dir_path, "db", "database.db")
FACEDB_PATH=    os.path.join(dir_path, "db", "Facelib")
# region Card

def delete_card_by_ids(ids):

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executemany("DELETE FROM card WHERE card_id = ?", [(i,) for i in ids])
    conn.commit()
    conn.close()

def find_by_card_name(card_name, asc: bool, offset):
    # カード名でカード情報を取得
    order = "ASC" if asc else "DESC"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM card WHERE card_name LIKE ? ORDER BY card_id {order} LIMIT 100 OFFSET ?",
                   (f"%{card_name}%", offset))
    cards = cursor.fetchall()
    conn.close()
    return cards


def count_all_card(card_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM card WHERE card_name LIKE ?",
                   (f"%{card_name}%", ))
    count = cursor.fetchall()
    conn.close()
    return count[0]


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

#endregion

# region Log
def delete_old_logs():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now()

    c.execute("DELETE FROM access_logs WHERE timestamp < ?", (now - timedelta(days=365),))
    conn.commit()
    conn.close()
    print("1年以上前のログを削除しました")

def insert_samplelogs(card_id,eventtype,timestamp):
    # サンプルログを挿入
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO access_logs (card_id, method, eventtype,timestamp) VALUES (?, ?, ?,?)", (card_id,"カード" ,eventtype,timestamp))
    conn.commit()
    conn.close()

def find_log(card_name,face_name, method, eventtype, start_datetime, end_datetime, limit, offset, asc: bool = True):
    order = "ASC" if asc else "DESC"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now()

    card_name = f"%{card_name}%" if card_name else "%"
    face_name = f"%{face_name}%" if face_name else "%"

    method = f"%{method}%" if method else "%"

    start_datetime = start_datetime or (now - timedelta(days=365))
    end_datetime = end_datetime or now

    start_datetime_str = start_datetime.strftime("%Y-%m-%d %H:%M:%S")
    end_datetime_str = end_datetime.strftime("%Y-%m-%d %H:%M:%S")

    # カード名、認証方式、イベントタイプでアクセスログを検索
    # card_nameとmethodは部分一致検索、eventtypeは完全一致検索
    # COALESCEを使用して、eventtypeがNoneの場合は全てのeventtypeを対象とする
    logs = cursor.execute(f"""
        SELECT
            al.id,
            c.card_name,
            f.face_name,
            al.method,
            al.timestamp,
            al.eventtype
        FROM access_logs AS al
        LEFT JOIN card AS c ON al.card_id = c.card_id
        LEFT JOIN face AS f ON al.face_id = f.face_id
        WHERE (COALESCE(c.card_name, '') LIKE ?
          OR  COALESCE(f.face_name, '') LIKE ?)
        AND al.method LIKE ?
        AND (? IS NULL OR al.eventtype = ?)
        AND al.timestamp BETWEEN ? AND ?
        ORDER BY al.timestamp {order}
        LIMIT ? OFFSET ?
    """, (
        card_name,
        face_name,
        method,
        eventtype, eventtype,
        start_datetime_str, end_datetime_str,
        limit, offset
    )).fetchall()

    conn.close()
    return logs

def count_filtered_logs(
    card_name=None,
    face_name=None,
    method=None,
    eventtype=None,
    start_datetime=None,
    end_datetime=None
):
    """
    指定条件で access_logs の件数をカウントします。
    card_name, face_name, method は部分一致検索。
    eventtype は完全一致。
    期間(start_datetime～end_datetime)で絞り込みます。
    """

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    now = datetime.now()
    card_name = f"%{card_name}%" if card_name else "%"
    face_name = f"%{face_name}%" if face_name else "%"
    method = f"%{method}%" if method else "%"

    start_datetime = start_datetime or (now - timedelta(days=365))
    end_datetime = end_datetime or now
    start_datetime_str = start_datetime.strftime("%Y-%m-%d %H:%M:%S")
    end_datetime_str = end_datetime.strftime("%Y-%m-%d %H:%M:%S")

    query = """
        SELECT COUNT(*)
        FROM access_logs AS al
        LEFT JOIN card AS c ON al.card_id = c.card_id
        LEFT JOIN face AS f ON al.face_id = f.face_id
        WHERE (COALESCE(c.card_name, '') LIKE ?
          OR  COALESCE(f.face_name, '') LIKE ?)
          AND al.method LIKE ?
          AND (? IS NULL OR al.eventtype = ?)
          AND al.timestamp BETWEEN ? AND ?
    """

    cursor.execute(query, (
        card_name,
        face_name,
        method,
        eventtype,
        eventtype,
        start_datetime_str,
        end_datetime_str
    ))
    (count,) = cursor.fetchone()
    print(count)
    conn.close()
    return count


#endregion

# region Face
def find_all_faces():
    # 全ての顔情報を取得
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM face ORDER BY face_id ASC")
    faces = cursor.fetchall()
    conn.close()
    return faces

def insert_facedata(face_name, face_name_roma):
    # 顔情報を新規登録
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO face (face_name, face_name_roma) VALUES (?, ?)", (face_name, face_name_roma))
    conn.commit()
    conn.close()


def delete_face_by_ids(ids):
    delete_face_lib_by_ids(ids)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executemany("DELETE FROM face WHERE face_id = ?", [(i,) for i in ids])
    conn.commit()
    conn.close()

def delete_face_lib_by_ids(ids):
    """
    DBのface_name_romaをもとに、該当する画像ファイルを削除する
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for i in ids:
        # 1️⃣ DBから face_name_roma を取得
        cur.execute("SELECT face_name_roma FROM face WHERE face_id = ?", (i,))
        row = cur.fetchone()

        if not row:
            print(f"[WARN] face_id={i} は存在しません。")
            continue

        face_name_roma = row[0]
        print(f"[INFO] face_name_roma={face_name_roma}")

        # 2️⃣ ディレクトリ内で該当プレフィックスのファイルを削除
        for file in os.listdir(FACEDB_PATH):
            if file.startswith(face_name_roma):
                try:
                    os.remove(os.path.join(FACEDB_PATH, file))
                    print(f"[OK] 削除: {file}")
                except Exception as e:
                    print(f"[ERROR] {file} の削除失敗: {e}")

    conn.close()


def find_by_face_name(searchword: str, asc: bool, offset: int):
    """
    名前またはローマ字で顔データを検索します。

    Args:
        searchword (str): 検索キーワード（日本語またはローマ字）
        asc (bool): 昇順または降順
        offset (int): ページオフセット（100件ごと）

    Returns:
        list[tuple]: 該当する顔データのリスト
    """
    order = "ASC" if asc else "DESC"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    like_word = f"%{searchword}%" if searchword else "%"

    cursor.execute(f"""
        SELECT *
        FROM face
        WHERE face_name LIKE ?
           OR face_name_roma LIKE ?
        ORDER BY face_id {order}
        LIMIT 100 OFFSET ?
    """, (like_word, like_word, offset))

    faces = cursor.fetchall()
    conn.close()
    return faces


def count_all_face(searchword: str):
    """
    名前またはローマ字で検索結果の総件数をカウントします。

    Args:
        searchword (str): 検索キーワード（日本語またはローマ字）

    Returns:
        int: 該当件数
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    like_word = f"%{searchword}%" if searchword else "%"

    cursor.execute("""
        SELECT COUNT(*)
        FROM face
        WHERE face_name LIKE ?
           OR face_name_roma LIKE ?
    """, (like_word, like_word))

    count = cursor.fetchall()[0]
    conn.close()
    return count



def update_face_name(face_id, face_name,face_name_roma):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE face SET face_name = ? WHERE face_id = ?", (face_name, face_id))

    cursor.execute("SELECT face_name_roma FROM face WHERE face_id = ?", (face_id,))
    row = cursor.fetchone()
    current_roma = row[0]

    if current_roma == face_name_roma:
        print(f"[INFO] '{current_roma}' と '{face_name_roma}' は同じです。変更なし。")
    else:
        cursor.execute(
            "UPDATE face SET face_name_roma = ? WHERE face_id = ?", (face_name_roma, face_id))
        update_face_lib(current_roma,face_name_roma)

    conn.commit()
    conn.close()

def update_face_lib(face_name_roma,face_name_roma_new):

    '''
    TODO 我要改文件名
    '''
    """
    指定フォルダ内で人脸データファイルをリネームする。

    Args:
        folder_path (str): 画像ファイルが保存されているフォルダパス
        face_name_roma (str): 旧ローマ字名（例: "me"）
        face_name_roma_new (str): 新しいローマ字名（例: "taro"）

    Returns:
        bool: True = 成功, False = 同名ファイルがすでに存在 or エラー
    """

    # --- 1️⃣ まず、face_name_roma_new で始まるファイルが存在するかチェック ---
    for file in os.listdir(FACEDB_PATH):
        name, ext = os.path.splitext(file)
        if name.startswith(face_name_roma_new):
            print(f"[WARN] '{face_name_roma_new}' で始まるファイルがすでに存在: {file}")
            return False  # すでに存在する → リネーム中止

    # --- 2️⃣ face_name_roma で始まるファイルを検索してリネーム ---
    renamed = False
    for file in os.listdir(FACEDB_PATH):
        name, ext = os.path.splitext(file)
        if name.startswith(face_name_roma):
            new_name = file.replace(face_name_roma, face_name_roma_new, 1)
            old_path = os.path.join(FACEDB_PATH, file)
            new_path = os.path.join(FACEDB_PATH, new_name)

            os.rename(old_path, new_path)
            print(f"[OK] '{file}' → '{new_name}' にリネーム完了")
            renamed = True

    # --- 3️⃣ リネーム成功 or 該当なし ---
    if not renamed:
        print(f"[INFO] '{face_name_roma}' に一致するファイルは見つかりませんでした。")
        return False

    return True


def find_face_name_and_roma_by_id(face_id):
    # カードIDからカード名を取得
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT face_name,face_name_roma FROM face WHERE face_id = ?", (face_id,))
    face_data = cursor.fetchone()
    conn.close()
    return face_data

#endregion

if  __name__ == "__main__":
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