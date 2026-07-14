"""
sqlの実行をまとめたモジュール
完全に内部で完結してる変数を引数にとるときは(f"__sql__",(__name__))で渡しているが、
ユーザーが自由に書き込める値はSQLインジェクション対策でバインド変数で埋めている、ハズ
with get_connection()でDB接続の安全化を図っています。
db_managerにDB接続を一任しています。
リポジトリ層の責務はSQLの実行とエンティティ詰め込みまでとします。
その他業務的な判断はサービス層で行うようにしてください。
"""
import logging  # ログ用
import sqlite3  # 本来知らなくて良いが、ログのExceptionの為導入
from .db_manager import get_connection  # データベース接続用
from my_app.models.ENUMS import EventType, CardType  # Enum
from my_app.models.entity.access_log import AccessLog  # データクラス
from my_app.models.entity.face import Face  # データクラス
from my_app.models.entity.user import User  # データクラス
from my_app.models.entity.card import Card
from datetime import datetime, timedelta  # 入退室ログの時間用に

logger = logging.getLogger(__name__)


# ===================================================
# ユーザーテーブル
# ===================================================

def insert_user(user_name, user_kana):
    """
    ユーザーをデータベースに挿入する関数

    Args:
        user_name (str): ユーザー名(漢字)
        user_kana (str): ユーザー名(カナ)

    Returns:
        int: 挿入されたユーザーのID
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'INSERT INTO user (user_name, user_kana) VALUES (?, ?)',
                (user_name, user_kana)
            )
            return c.lastrowid  # 挿入されたユーザーのIDを返す
    except sqlite3.Error:
        logger.exception("ユーザー挿入エラー: %s, %s", user_name, user_kana)
        raise


def update_user(user_id, user_name, user_kana):
    """
    ユーザー情報を更新する関数

    Args:
        user_id (int): 更新するユーザーのID
        user_name (str): 新しいユーザー名(漢字)
        user_kana (str): 新しいユーザー名(カナ)
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'UPDATE user SET user_name = ?, user_kana = ? WHERE id = ?',
                (user_name, user_kana, user_id)
            )
    except sqlite3.Error:
        logger.exception("ユーザー更新エラー: id=%s, %s, %s", user_id, user_name, user_kana)
        raise


def delete_user(user_id):
    """
    ユーザーを削除する関数
    (card, faceはON DELETE CASCADEにより連動して自動削除される。写真はservice/face_storageで)

    Args:
        user_id (int): 削除するユーザーのID
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute('DELETE FROM user WHERE id = ?', (user_id,))
    except sqlite3.Error:
        logger.exception("ユーザー削除エラー: id=%s", user_id)
        raise


def get_user_by_id(user_id):
    """
    ユーザーIDからユーザー情報を取得する関数

    Args:
        user_id (int): 取得するユーザーのID

    Returns:
        User: ユーザー情報（存在する場合）またはNone（存在しない場合）
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT id, user_name, user_kana FROM user WHERE id = ?', (user_id,))
            row = c.fetchone()
            if row:
                return User(id=row[0], user_name=row[1], user_kana=row[2])
            return None
    except sqlite3.Error:
        logger.exception("ユーザー取得エラー: id=%s", user_id)
        raise


def get_all_users():
    """
    全ユーザーの一覧を取得する関数(Autocomplete表示用など)

    Returns:
        list[User]: 全ユーザーのリスト
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT id, user_name, user_kana FROM user')
            rows = c.fetchall()
            return [
                User(id=row[0], user_name=row[1], user_kana=row[2])
                for row in rows
            ]
    except sqlite3.Error:
        logger.exception("ユーザー全件取得エラー")
        raise


# ===================================================
# カードテーブル
# ===================================================

def check_card(cardIDM):
    """
    指定されたカード番号がデータベースに存在するかチェックします。

    Args:
        cardIDM (str): カード番号

    Returns:
        int: カードID（存在する場合）またはNone（存在しない場合）
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT id FROM card WHERE card_number = ?', (cardIDM,))
            card_id = c.fetchone()
            return card_id[0] if card_id else None
    except sqlite3.Error:
        logger.exception("カード検索エラー: id=%s", cardIDM)
        raise


def insert_card(card_number: str, CARD_TYPE: CardType, user_id: int):
    """
    カードをデータベースに挿入する関数

    Args:
        card_number (str): カード番号(IDm)
        CARD_TYPE (CardType): カードタイプ
        user_id (int): 所有者のユーザーID

    Returns:
        int: 挿入されたカードのID
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'INSERT INTO card (card_number, card_type, user_id) VALUES (?, ?, ?)',
                (card_number, CARD_TYPE.value, user_id)
            )
            return c.lastrowid
    except sqlite3.Error:
        logger.exception("カード挿入エラー: card_number=%s, card_type=%s, user_id=%s",
                        card_number, CARD_TYPE.value, user_id)
        raise


def delete_card(card_id):
    """
    カードを削除する関数

    Args:
        card_id (int): 削除するカードのID
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute('DELETE FROM card WHERE id = ?', (card_id,))
    except sqlite3.Error:
        logger.exception("カード削除エラー: id=%s", card_id)
        raise


def find_all_cards(asc: bool, offset: int):
    """
    カード情報を全件、ページングして取得する関数(ユーザー未選択時のGUI表示用)

    Args:
        asc (bool): 昇順 -> true, 降順 -> false
        offset (int): GUIで表示するためのページ区分

    Returns:
        list[Card]: カード情報のリスト
    """
    order = "ASC" if asc else "DESC"
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                f"""
                SELECT id, card_type, card_number, register_date, user_id
                FROM card
                ORDER BY id {order} LIMIT 100 OFFSET ?
                """,
                (offset,)
            )
            rows = c.fetchall()
            return [
                Card(id=row[0], card_type=CardType(row[1]), card_number=row[2],
                    register_date=row[3], user_id=row[4])
                for row in rows
            ]
    except sqlite3.Error:
        logger.exception("カード全件取得エラー")
        raise


def count_all_card():
    """
    find_all_cards()をGUIで表示する際の全体件数を取得する関数

    Returns:
        int: 件数
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM card")
            return c.fetchone()[0]
    except sqlite3.Error:
        logger.exception("カード件数取得エラー")
        raise


def find_cards_by_user_id(user_id: int, asc: bool, offset: int):
    """
    指定されたユーザーIDに関連するカード情報を、ページングして取得する関数
    (Autocompleteでユーザーが選択された時のGUI表示用)

    Args:
        user_id (int): 取得するカード情報に関連するユーザーのID
        asc (bool): 昇順 -> true, 降順 -> false
        offset (int): GUIで表示するためのページ区分

    Returns:
        list[Card]: カード情報のリスト
    """
    order = "ASC" if asc else "DESC"
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                f"""
                SELECT id, card_type, card_number, register_date, user_id
                FROM card
                WHERE user_id = ?
                ORDER BY id {order} LIMIT 100 OFFSET ?
                """,
                (user_id, offset)
            )
            rows = c.fetchall()
            return [
                Card(id=row[0], card_type=CardType(row[1]), card_number=row[2],
                    register_date=row[3], user_id=row[4])
                for row in rows
            ]
    except sqlite3.Error:
        logger.exception("カード取得エラー: user_id=%s", user_id)
        raise


def count_cards_by_user_id(user_id: int):
    """
    find_cards_by_user_id()をGUIで表示する際の件数を取得する関数

    Args:
        user_id (int): ユーザーID

    Returns:
        int: 件数
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM card WHERE user_id = ?", (user_id,))
            return c.fetchone()[0]
    except sqlite3.Error:
        logger.exception("カード件数取得エラー: user_id=%s", user_id)
        raise

def find_user_name_jpn_and_user_id_by_user_name_kana(user_name_kana, asc: bool, offset):
    """
    カナ氏名からユーザーIDと名前を検索する関数

    Args:
        user_name_jpn (str): 名前
        user_id (int): ユーザーID
        asc (bool): 昇順 -> true, 降順 -> false
        offset (int): GUIで表示するためのページ区分

    Returns:
        list: ユーザーID,名前（存在する場合）またはNone（存在しない場合）
    """
    order = "ASC" if asc else "DESC"
    
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(
            f"SELECT * FROM user WHERE user_name_kana LIKE ? ORDER BY id {order} LIMIT 100 OFFSET ?",
            (f"%{user_name_kana}%", offset)
        )
        rows = c.fetchall()
        return rows
    
def update_user(user_id, user_name_jpn, user_name_kana):
    with get_connection() as conn:
        conn.execute( """
        UPDATE user
        SET
            user_name_jpn = ?,
            user_name_kana = ?
        WHERE user_id = ?
        """,
        (user_name_jpn, user_name_kana, user_id))
        conn.commit()

def find_user_id_by_card_id(card_id):
    """
    カードIDからユーザーIDを検索する関数

    Args:
        card_id (int): カードID

    Returns:
        int: ユーザーID（存在する場合）またはNone（存在しない場合）
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'SELECT user_id FROM card WHERE id = ?',
                (card_id,)
            )
            row = c.fetchone()
            return row[0] if row else None
    except sqlite3.Error:
        logger.exception("カードIDからユーザーID検索でエラー: card_id=%s", card_id)
        raise


# ===================================================
# 入退室ログテーブル
# ===================================================

def get_last_date_time(card_id, event_type: EventType):
    """
    指定されたカードIDの最新の入退室ログの日時を取得します。

    Args:
        card_id (int): カードID
        event_type (EventType): イベントタイプ

    Returns:
        str: 最新の入退室ログの日時（存在する場合）またはNone（存在しない場合）
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'SELECT timestamp FROM access_logs '
                'WHERE card_id = ? AND event_type = ? '
                'ORDER BY timestamp DESC LIMIT 1',
                (card_id, event_type)
            )
            last_timestamp = c.fetchone()
            return last_timestamp[0] if last_timestamp else None
    except sqlite3.Error:
        logger.exception("入退室ログ取得エラー: card_id=%s", card_id)
        raise



# todo:
# 退室の時は必ずカードにするように！！！
def insert_access_log(log: AccessLog):
    """
    入退室ログをデータベースに挿入する関数
    カード認証・顔認証どちらの記録もこの関数で受け付ける。
    使わない側のid(card_idまたはface_id)はNoneのままで。

    Args:
        log (AccessLog): 入退室ログのデータ

    Returns:
        AccessLog: id・user_nameのスナップショットを埋めた状態のlog
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()

            # repository層: ここでスナップショットを埋めてからINSERT
            c.execute("SELECT user_name FROM user WHERE id = ?", (log.user_id,))
            row = c.fetchone()
            log.user_name = row[0] if row else None

            c.execute(
                "INSERT INTO access_logs (method, event_type, user_id, user_name, card_id, face_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (log.method, log.event_type, log.user_id, log.user_name, log.card_id, log.face_id)
            )
            log.id = c.lastrowid  # 書き戻し(update)に備えてidも埋めておく
            return log
    except sqlite3.Error:
        logger.exception("アクセスログ登録エラー: user_id=%s", log.user_id)
        raise


def update_access_log(log: AccessLog):
    """
    既存の入退室ログを更新する関数。
    find_log() で取得した AccessLog をそのまま渡す
    log.id が必須(どの行を更新するかの特定に使う)。

    Args:
        log (AccessLog): 更新後の内容を反映したログ(id必須)

    Returns:
        AccessLog: 渡されたlogをそのまま返す
    """
    if log.id is None:
        raise ValueError("update_access_logにはlog.idが必須です")

    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE access_logs SET method = ?, event_type = ?, card_id = ?, face_id = ? "
                "WHERE id = ?",
                (log.method, log.event_type, log.card_id, log.face_id, log.id)
            )
            return log
    except sqlite3.Error:
        logger.exception("アクセスログ更新エラー: id=%s", log.id)
        raise


def find_log(method, event_type, start_datetime, end_datetime, limit, offset, asc: bool = True):
    """
    入退室ログを条件検索する関数
    めんどいので表結合してないです

    args:
        method: 認証方法
        event_type: 入退室区分
        start_datetime: 日時指定(開始)
        end_datetime: 日時指定(終了)
        limit: 取得件数
        offset: ページ分けの為の区分
        asc: 昇順 -> true 降順 -> false

    return list[AccessLog]: 入退室ログリスト。書き戻し(update_access_log)に
        そのまま渡せるよう AccessLog のリストで返す。
    """
    order = "ASC" if asc else "DESC"
    try:
        with get_connection() as conn:
            c = conn.cursor()

            now = datetime.now()

            method = f"%{method}%" if method else "%"

            start_datetime = start_datetime or (now - timedelta(days=365))
            end_datetime = end_datetime or now

            start_datetime_str = start_datetime.strftime("%Y-%m-%d %H:%M:%S")
            end_datetime_str = end_datetime.strftime("%Y-%m-%d %H:%M:%S")

            # methodは部分一致検索、event_typeは完全一致検索
            # event_typeがNoneの場合は全てのevent_typeが対象
            c.execute(
                f"""
                SELECT id, timestamp, method, event_type, user_id, user_name, card_id, face_id
                FROM access_logs
                WHERE method LIKE ?
                AND (? IS NULL OR event_type = ?)
                AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp {order} LIMIT ? OFFSET ?
                """,
                (method, event_type, event_type,
                start_datetime_str, end_datetime_str, limit, offset)
            )
            rows = c.fetchall()
            return [
                AccessLog(
                    id=row[0],
                    timestamp=row[1],
                    method=row[2],
                    event_type=row[3],
                    user_id=row[4],
                    user_name=row[5],
                    card_id=row[6],
                    face_id=row[7],
                )
                for row in rows
            ]
    except sqlite3.Error:
        logger.exception(
            "アクセスログ検索エラー: method=%s, event_type=%s",
            method, event_type
        )
        raise


def count_filtered_logs(method=None, event_type=None, start_datetime=None, end_datetime=None):
    """
    GUIでログ表示する際の件数を検索する関数

    args:
        method: 認証方法
        event_type: 入退室区分
        start_datetime: 日時指定(開始)
        end_datetime: 日時指定(終了)

    return: 件数
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()

            now = datetime.now()
            method = f"%{method}%" if method else "%"
            start_datetime = start_datetime or (now - timedelta(days=365))
            end_datetime = end_datetime or now

            start_datetime_str = start_datetime.strftime("%Y-%m-%d %H:%M:%S")
            end_datetime_str = end_datetime.strftime("%Y-%m-%d %H:%M:%S")

            query = """
                SELECT COUNT(*)
                FROM access_logs
                WHERE method LIKE ?
                AND (? IS NULL OR event_type = ?)
                AND timestamp BETWEEN ? AND ?
            """

            c.execute(query, (
                method, event_type, event_type,
                start_datetime_str, end_datetime_str
            ))
            return c.fetchone()[0]
    except sqlite3.Error:
        logger.exception(
            "アクセスログ件数取得エラー: method=%s, event_type=%s",
            method, event_type
        )
        raise


# ===================================================
# 顔テーブル
# ===================================================

def find_all_faces(asc: bool, offset: int):
    """
    顔情報を全件、ページ毎に取得する関数(プルダウン未選択時のGUI表示用)

    Args:
        asc (bool): 昇順 -> true, 降順 -> false
        offset (int): GUIで表示するためのページ区分

    Returns:
        list[Face]: 顔情報のリスト
    """
    order = "ASC" if asc else "DESC"
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                f"""
                SELECT id, register_date, user_id
                FROM face
                ORDER BY id {order} LIMIT 100 OFFSET ?
                """,
                (offset,)
            )
            rows = c.fetchall()
            return [
                Face(id=row[0], register_date=row[1], user_id=row[2])
                for row in rows
            ]
    except sqlite3.Error:
        logger.exception("顔情報全件取得エラー")
        raise


def count_all_face():
    """
    find_all_faces()をGUIで表示する際の全体件数を取得する関数

    Returns:
        int: 件数
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM face")
            return c.fetchone()[0]
    except sqlite3.Error:
        logger.exception("顔情報件数取得エラー")
        raise


def find_faces_by_user_id(user_id: int, asc: bool, offset: int):
    """
    指定されたユーザーIDに関連する顔情報を、ページ毎に取得する関数
    (プルダウンでユーザーが選択された時のGUI表示用)

    Args:
        user_id (int): 取得する顔情報に関連するユーザーのID
        asc (bool): 昇順 -> true, 降順 -> false
        offset (int): GUIで表示するためのページ区分

    Returns:
        list[Face]: 顔情報のリスト
    """
    order = "ASC" if asc else "DESC"
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                f"""
                SELECT id, register_date, user_id
                FROM face
                WHERE user_id = ?
                ORDER BY id {order} LIMIT 100 OFFSET ?
                """,
                (user_id, offset)
            )
            rows = c.fetchall()
            return [
                Face(id=row[0], register_date=row[1], user_id=row[2])
                for row in rows
            ]
    except sqlite3.Error:
        logger.exception("顔情報取得エラー: user_id=%s", user_id)
        raise


def count_faces_by_user_id(user_id: int):
    """
    find_faces_by_user_id()をGUIで表示する際の件数を取得する関数

    Args:
        user_id (int): ユーザーID

    Returns:
        int: 件数
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM face WHERE user_id = ?", (user_id,))
            return c.fetchone()[0]
    except sqlite3.Error:
        logger.exception("顔情報件数取得エラー: user_id=%s", user_id)
        raise


def get_face_ids_by_user_id(user_id: int):
    """
    指定されたユーザーIDに関連する顔情報のIDだけを取得する関数。
    userのCASCADE削除に伴う画像ファイルの後始末など、IDだけあれば良いとき用

    Args:
        user_id (int): ユーザーID

    Returns:
        list[int]: face_idのリスト
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT id FROM face WHERE user_id = ?', (user_id,))
            rows = c.fetchall()
            return [row[0] for row in rows]
    except sqlite3.Error:
        logger.exception("顔ID取得エラー: user_id=%s", user_id)
        raise


def insert_face(user_id: int):
    """
    顔情報をデータベースに挿入する関数
    (画像ファイル自体はface_storage側で、確定したidを使って保存する)

    Args:
        user_id (int): ユーザーID

    Returns:
        int: 挿入された顔情報のID
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'INSERT INTO face (user_id) VALUES (?)',
                (user_id,)
            )
            return c.lastrowid
    except sqlite3.Error:
        logger.exception("顔情報挿入エラー: user_id=%s", user_id)
        raise


# ここでは画像の削除はしていません！！！(画像削除はface_storage/face_service)
def delete_face(face_id):
    """
    顔情報を顔idで指定して一枚削除する関数

    Args:
        face_id (int): 削除する顔情報のID
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute('DELETE FROM face WHERE id = ?', (face_id,))
    except sqlite3.Error:
        logger.exception("顔情報削除エラー: id=%s", face_id)
        raise


def delete_faces_by_user_id(user_id):
    """
    指定されたユーザーIDに関連するすべての顔情報を削除する関数。

    注意: userテーブルのCASCADE設定により、user削除時はこの関数を経由せず
    face行がDB側で自動的に削除される。ユーザーを残したいとき用

    Args:
        user_id (int): 削除する顔情報に関連するユーザーのID
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute('DELETE FROM face WHERE user_id = ?', (user_id,))
    except sqlite3.Error:
        logger.exception("顔情報削除エラー: user_id=%s", user_id)
        raise