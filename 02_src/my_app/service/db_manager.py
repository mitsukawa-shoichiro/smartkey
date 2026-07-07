import os
import sqlite3
import json
import logging
from datetime import datetime, timedelta

BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "db"))
DB_PATH = os.path.join(BASE_DIR, 'database.db')
#顔データベースへのパス
FACEDB_PATH=    os.path.join(BASE_DIR, "face_lib")
logger = logging.getLogger(__name__)


def load_config():
    base_dir = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )

    CONFIG_PATH = os.path.normpath(
        os.path.join(base_dir, "config", "usb_settings.json")
    )
    logger.info(f"USB設定ファイルのパス: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["devices"]


def check_card(cardIDM):
    """
    指定されたカード番号がデータベースに存在するかチェックします。

    Args:
        cardIDM (str): カード番号

    Returns:
        dict: カード情報（存在する場合）またはNone（存在しない場合）
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            'SELECT id FROM card WHERE card_number = ?', (cardIDM,))
        card_id = cursor.fetchone()

        return card_id[0] if card_id else None
    except sqlite3.Error as e:
        logger.exception("カード検索エラー: id=%s", cardIDM)
        raise
    finally:
        conn.close()

#怪しい香り、後回し
def get_last_date_time(card_id, reader_serial):
    dt = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT timestamp FROM access_logs where card_id = ? AND eventtype = ? ORDER BY timestamp DESC LIMIT 1", (card_id, reader_serial))
        row = cursor.fetchone()
        if row:
            ts_str = row[0]
            dt = datetime.fromisoformat(ts_str)
        return dt
    except sqlite3.Error as e:
        logger.exception("アクセスログ日時検索エラー: card_id=%s, reader_serial=%s", card_id, reader_serial)
        raise
    finally:
        conn.close()


#怪しい香り、後回し　移植完了
def insert_card_id(card_id, reader_serial):
    # カードIDをaccess_logsテーブルに挿入します。
    logger.info(f"カードIDを挿入: {card_id}, リーダーID: {reader_serial}")
    config = load_config()

    if config["出口"]["serial"] == reader_serial:
        eventtype = 1
    elif config["入口"]["serial"] == reader_serial:
        eventtype = 0
    else:
        logger.error("不明なリーダーIDです")
        raise ValueError("不明なリーダーIDです")
    dt = get_last_date_time(card_id, eventtype)
    if dt:
        now = datetime.now()

        if now - dt <= timedelta(seconds=10):
            logger.info("10秒以内に登録されています")
            return
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO access_logs (method, card_id, eventtype) VALUES(?,?,?)", ('カード', card_id, eventtype))
        conn.commit()
    except sqlite3.Error as e:
        logger.exception("アクセスログ登録エラー: card_id=%s, reader_serial=%s", card_id, reader_serial)
        raise
    finally:
        conn.close()

def delete_card_by_ids(ids):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        cur.executemany("DELETE FROM card WHERE id = ?", [(i,) for i in ids])
        conn.commit()
    except sqlite3.Error as e:
        logger.exception("カード削除エラー: ids=%s", ids)
        raise
    finally:
        conn.close()

#怪しい香り、後回し　移植完了
def find_log(card_name, method, eventtype, start_datetime, end_datetime, limit, offset, asc: bool = True):
    order = "ASC" if asc else "DESC"
    try:
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
    except sqlite3.Error as e:
        logger.exception("アクセスログ検索エラー: card_name=%s, method=%s, eventtype=%s", card_name, method, eventtype)
        raise
    finally:
        conn.close()
    return logs

#怪しい香り、後回し　移植完了
def count_filtered_logs(card_name=None, method=None, eventtype=None, start_datetime=None, end_datetime=None):
    try:
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
        cursor.execute(f"SELECT * FROM card WHERE card_name LIKE ? ORDER BY id {order} LIMIT 100 OFFSET ?",
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
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE card SET card_name = ? WHERE id = ?", (new_name, card_id))
        conn.commit()
    except sqlite3.Error as e:
        logger.exception("カード名更新エラー: id=%s, new_name=%s", card_id, new_name)
        raise
    finally:
        conn.close()


def find_card_name_by_id(card_id):
    # カードIDからカード名を取得
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT card_name FROM card WHERE id = ?", (card_id,))
        card_name = cursor.fetchone()
    except sqlite3.Error as e:
        logger.exception("カード名取得エラー: id=%s", card_id)
        raise
    finally:
        conn.close()
    return card_name

#怪しい香り、後回し
def insert_card(card_name, card_number):
    # カードを新規登録
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO card (card_name, card_number) VALUES (?, ?)", (card_name, card_number))
        conn.commit()
    except sqlite3.Error as e:
        logger.exception("カード登録エラー: card_name=%s, card_number=%s", card_name, card_number)
        raise
    finally:
        conn.close()

#怪しい香り、後回し
def insert_samplelogs(card_id,eventtype,timestamp):
    # サンプルログを挿入
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO access_logs (card_id, method, eventtype,timestamp) VALUES (?, ?, ?,?)", (card_id,"カード" ,eventtype,timestamp))
        conn.commit()
    except sqlite3.Error as e:
        logger.exception("サンプルログ挿入エラー: card_id=%s, eventtype=%s, timestamp=%s", card_id, eventtype, timestamp)
        raise
    finally:
        conn.close()


def find_all_faces():
    # 全ての顔情報を取得
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM face ORDER BY id ASC")
        faces = cursor.fetchall()
    except Exception as e:
        logger.info(f"[ERROR] 顔情報の取得中にエラーが発生しました: {e}")
        faces = []
    finally:
        conn.close()
    return faces

#怪しい香り、後回し
def insert_facedata(face_name, face_name_roma):
    # 顔情報を新規登録
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO face (face_name, face_name_roma) VALUES (?, ?)", (face_name, face_name_roma))
        conn.commit()
    except Exception as e:
        logger.info(f"[ERROR] 顔情報の登録中にエラーが発生しました: {e}")
    finally:
        conn.close()


#user_idでも一括で消せるようにメソッド作って
def delete_face_by_ids(ids):
    delete_face_lib_by_ids(ids)
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.executemany("DELETE FROM face WHERE id = ?", [(i,) for i in ids])
        conn.commit()
    except Exception as e:
        logger.info(f"[ERROR] 顔情報の削除中にエラーが発生しました: {e}")
    finally:
        conn.close()

#怪しい香り、後回し
def delete_face_lib_by_ids(ids):
    """
    DBのface_name_romaをもとに、該当する画像ファイルを削除する
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        for i in ids:
            # 1️⃣ DBから face_name_roma を取得
            cur.execute("SELECT face_name_roma FROM face WHERE id = ?", (i,))
            row = cur.fetchone()

            if not row:
                logger.info(f"[WARN] id={i} は存在しません。")
                continue

            face_name_roma = row[0]
            logger.info(f"[INFO] face_name_roma={face_name_roma}")

            # 2️⃣ ディレクトリ内で該当プレフィックスのファイルを削除
            for file in os.listdir(FACEDB_PATH):
                if file.startswith(face_name_roma):
                    try:
                        os.remove(os.path.join(FACEDB_PATH, file))
                        logger.info(f"[OK] 削除: {file}")
                    except Exception as e:
                        logger.info(f"[ERROR] {file} の削除失敗: {e}")
    except Exception as e:
        logger.info(f"[ERROR] 顔画像ファイルの削除中にエラーが発生しました: {e}")
    finally:
        conn.close()

#怪しい香り、後回し
def find_by_face_name(search_word: str, asc: bool, offset: int):
    """
    名前またはローマ字で顔データを検索します。

    Args:
        search_word (str): 検索キーワード（日本語またはローマ字）
        asc (bool): 昇順または降順
        offset (int): ページオフセット（100件ごと）

    Returns:
        list[tuple]: 該当する顔データのリスト
    """
    order = "ASC" if asc else "DESC"
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        like_word = f"%{search_word}%" if search_word else "%"

        cursor.execute(f"""
            SELECT *
            FROM face
            WHERE face_name LIKE ?
                OR face_name_roma LIKE ?
            ORDER BY face_id {order}
            LIMIT 100 OFFSET ?
        """, (like_word, like_word, offset))

        faces = cursor.fetchall()
    except Exception as e:
        logger.info(f"[ERROR] 顔データの検索中にエラーが発生しました: {e}")
        faces = []
    finally:
        conn.close()
    return faces

#怪しい香り、後回し
def count_all_face(search_word: str):
    """
    名前またはローマ字で検索結果の総件数をカウントします。

    Args:
        search_word (str): 検索キーワード（日本語またはローマ字）

    Returns:
        int: 該当件数
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        like_word = f"%{search_word}%" if search_word else "%"

        cursor.execute("""
            SELECT COUNT(*)
            FROM face
            WHERE face_name LIKE ?
                OR face_name_roma LIKE ?
        """, (like_word, like_word))

        count = cursor.fetchone()[0]
    except Exception as e:
        logger.info(f"[ERROR] 顔データの件数カウント中にエラーが発生しました: {e}")
        count = 0 #どゆこと？
    finally:
        conn.close()
    return count

#怪しい香り、後回し
#これは後でuser用のメソッドに変えよう
def update_face_name(face_id, face_name,face_name_roma):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE face SET face_name = ? WHERE face_id = ?", (face_name, face_id))

        cursor.execute("SELECT face_name_roma FROM face WHERE face_id = ?", (face_id,))
        row = cursor.fetchone()
        current_roma = row[0]

        if current_roma == face_name_roma:
            logger.info(f"[INFO] '{current_roma}' と '{face_name_roma}' は同じです。変更なし。")
        else:
            cursor.execute(
                "UPDATE face SET face_name_roma = ? WHERE face_id = ?", (face_name_roma, face_id))
            update_face_lib(current_roma,face_name_roma)

        conn.commit()
    except Exception as e:
        logger.info(f"[ERROR] 顔データの更新中にエラーが発生しました: {e}")
    finally:
        conn.close()

#怪しい香り、後回し
def update_face_lib(face_name_roma,face_name_roma_new):#try-exceptないけど大丈夫かわかんない関数くん

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

#怪しい香り、後回し
def find_face_name_and_roma_by_id(face_id):
    # カードIDからカード名を取得
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT face_name, face_name_roma FROM face WHERE face_id = ?", (face_id,))
        face_data = cursor.fetchone()
    except Exception as e:
        logger.info(f"[ERROR] 顔データの取得中にエラーが発生しました: {e}")
        face_data = None
    finally:
        conn.close()
    return face_data



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

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.executemany("DELETE FROM card WHERE card_id = ?",
                        [(i,) for i in range(500, 1050)])
        conn.commit()
    except sqlite3.Error as e:
        logger.exception("カード削除エラー")
        raise
    finally:
        conn.close()

