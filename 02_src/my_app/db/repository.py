"""
sqlの実行をまとめたモジュール

"""
import logging  # ログ用
import sqlite3  # 本来知らなくて良いが、ログのExceptionの為導入
from .db_manager import get_connection  # データベース接続用
from app.models.ENUMS import EventType, CardType  # Enum
from app.models.access_log import AccessLog  # データクラス
from datetime import datetime, timedelta  # 入退室ログの時間用に

logger = logging.getLogger(__name__)


# ===================================================
# ユーザーテーブル
# ===================================================

def insert_user(user_name_jpn, user_name_roma):
    """
    ユーザーをデータベースに挿入する関数

    Args:
        user_name_jpn (str): ユーザーの日本語名
        user_name_roma (str): ユーザーのローマ字名

    Returns:
        int: 挿入されたユーザーのID
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'INSERT INTO user (user_name_jpn, user_name_roma) VALUES (?, ?)',
                (user_name_jpn, user_name_roma)
            )
            return c.lastrowid  # 挿入されたユーザーのIDを返す
    except sqlite3.Error:
        logger.exception("ユーザー挿入エラー: %s, %s", user_name_jpn, user_name_roma)
        raise


def update_user(user_id, user_name_jpn, user_name_roma):
    """
    ユーザー情報を更新する関数

    Args:
        user_id (int): 更新するユーザーのID
        user_name_jpn (str): 新しい日本語名
        user_name_roma (str): 新しいローマ字名
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'UPDATE user SET user_name_jpn = ?, user_name_roma = ? WHERE id = ?',
                (user_name_jpn, user_name_roma, user_id)
            )
    except sqlite3.Error:
        logger.exception("ユーザー更新エラー: id=%s, %s, %s", user_id, user_name_jpn, user_name_roma)
        raise


def delete_user(user_id):
    """
    ユーザーを削除する関数

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
        dict: ユーザー情報（存在する場合）またはNone（存在しない場合）
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM user WHERE id = ?', (user_id,))
            user = c.fetchone()
            if user:
                return {
                    "id": user[0],
                    "user_name_jpn": user[1],
                    "user_name_roma": user[2]
                }
            return None
    except sqlite3.Error:
        logger.exception("ユーザー取得エラー: id=%s", user_id)
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
            card_id = c.fetchone()  # 元は conn.fetchone() になっていたバグを修正
            return card_id[0] if card_id else None
    except sqlite3.Error:
        logger.exception("カード検索エラー: id=%s", cardIDM)
        raise


def insert_card(card_name, card_number, CARD_TYPE: CardType, user_id: int):
    """
    カードをデータベースに挿入する関数

    Args:
        card_name (str): カード名
        card_number (str): カード番号
        CARD_TYPE (CardType): カードタイプ
        user_id (int): 所有者のユーザーID

    Returns:
        int: 挿入されたカードのID
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'INSERT INTO card (card_name, card_number, card_type, user_id) VALUES (?, ?, ?, ?)',
                (card_name, card_number, CARD_TYPE.value, user_id)
            )
            return c.lastrowid  # 元は conn.lastrowid になっていたバグを修正
    except sqlite3.Error:
        logger.exception("カード挿入エラー: %s, %s, %s", card_name, card_number, CARD_TYPE.value)
        raise


def update_card(card_id, card_name, card_number, CARD_TYPE: CardType):
    """
    カード情報を更新する関数

    Args:
        card_id (int): 更新するカードのID
        card_name (str): 新しいカード名
        card_number (str): 新しいカード番号
        CARD_TYPE (CardType): 新しいカードタイプ
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'UPDATE card SET card_name = ?, card_number = ?, card_type = ? WHERE id = ?',
                (card_name, card_number, CARD_TYPE.value, card_id)
            )
    except sqlite3.Error:
        logger.exception("カード更新エラー: id=%s, %s, %s, %s", card_id, card_name, card_number, CARD_TYPE.value)
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


def find_by_card_name(card_name, asc: bool, offset):
    """
    カード名でカード情報を取得する関数

    Args:
        card_name (str): カード名
        asc (bool): 昇順 -> true, 降順 -> false
        offset (int): GUIで表示するためのページ区分

    Returns:
        list: カード情報
    """
    order = "ASC" if asc else "DESC"
    try:
        with get_connection() as conn:
            c = conn.cursor()
            # order は f-string で埋め込むが値は "ASC"/"DESC" のみに絞られており、
            # 外部入力をそのまま挿入しているわけではないので問題なし。
            c.execute(
                f"SELECT * FROM card WHERE card_name LIKE ? ORDER BY id {order} LIMIT 100 OFFSET ?",
                (f"%{card_name}%", offset)
            )
            return c.fetchall()
    except sqlite3.Error:
        logger.exception("カード検索エラー: card_name=%s", card_name)
        raise


def count_all_card(card_name):
    """
    find_by_card_nameをGUIで表示する際の件数を検索する関数

    Args:
        card_name (str): カード名

    Returns:
        int: 件数
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT COUNT(*) FROM card WHERE card_name LIKE ?",
                (f"%{card_name}%",)
            )
            count = c.fetchone()  # 元は fetchall() で count[0] がタプルになっていたバグを修正
            return count[0]
    except sqlite3.Error:
        logger.exception("カード件数取得エラー: card_name=%s", card_name)
        raise


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


def find_card_type_by_id(card_id):
    """
    カードIDからカード名を検索する関数

    Args:
        card_id(int): カードID

    Returns:
        (str): カード名
    """

    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT card_type FROM card WHERE id = ?", (card_id,))
            row = c.fetchone()
            return row[0] if row else None

    except sqlite3.Error:
        logger.exception("カードIDでのカード名検索エラー: card_id=%s", card_id)
        raise



def delete_card_by_ids(ids):
    """
    カード一括削除関数

    Args:
        ids ([int]): 削除IDリスト
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.executemany("DELETE FROM card WHERE id = ?", [(i,) for i in ids])

    except sqlite3.Error:
        logger.exception("カード一括削除エラー: card_ids=%s", ids)
        raise








# ===================================================
# 入退室ログテーブル
# ===================================================

def get_last_date_time(card_id, EVENT_TYPE: EventType):
    """
    指定されたカードIDの最新の入退室ログの日時を取得します。

    Args:
        card_id (int): カードID
        EVENT_TYPE (EventType): イベントタイプ

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
                (card_id, EVENT_TYPE)
            )
            last_timestamp = c.fetchone()
            return last_timestamp[0] if last_timestamp else None
    except sqlite3.Error:
        logger.exception("入退室ログ取得エラー: card_id=%s", card_id)
        raise


# todo:
# 退室の時は必ずカードにするように！！！
# サービスロジックこっちじゃなくて呼び出し側でやって！
# 詳細はservice.db_manager:L74参照
def insert_access_log(log: AccessLog):
    """
    入退室ログをデータベースに挿入する関数

    Args:
        log (AccessLog): 入退室ログのデータ

    Returns:
        AccessLog: user_name_jpnのスナップショットを埋めた状態のlog
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()

            # repository層: ここでスナップショットを埋めてからINSERT
            c.execute("SELECT user_name_jpn FROM user WHERE id = ?", (log.user_id,))
            row = c.fetchone()
            log.user_name_jpn = row[0] if row else None

            c.execute(
                "INSERT INTO access_logs (method, event_type, user_id, user_name_jpn, card_id, face_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (log.method, log.event_type, log.user_id, log.user_name_jpn, log.card_id, log.face_id)
            )
            log.id = c.lastrowid
            return log
    except sqlite3.Error:
        logger.exception("アクセスログ登録エラー: user_id=%s", log.user_id)
        raise


def find_log(method, event_type, start_datetime, end_datetime, limit, offset, asc: bool = True):
    """
    入退室ログを条件検索する関数

    args:
        card_name: カード名
        method: 認証方法
        event_type: 入退室区分
        start_datetime: 日時指定(開始)
        end_datetime: 日時指定(終了)
        limit: 取得件数
        offset: ページ分けの為の区分
        asc: 昇順 -> true 降順 -> false

    return 入退室ログリスト
    """
    order = "ASC" if asc else "DESC"
    try:
        with get_connection() as conn:
            c = conn.cursor()

            now = datetime.now()

            card_name = f"%{card_name}%" if card_name else "%"
            method = f"%{method}%" if method else "%"

            start_datetime = start_datetime or (now - timedelta(days=365))
            end_datetime = end_datetime or now

            start_datetime_str = start_datetime.strftime("%Y-%m-%d %H:%M:%S")
            end_datetime_str = end_datetime.strftime("%Y-%m-%d %H:%M:%S")

            # カード名、認証方式、イベントタイプでアクセスログを検索
            # card_nameとmethodは部分一致検索、event_typeは完全一致検索
            # event_typeがNoneの場合は全てのevent_typeを対象とする
            c.execute(
                f"""
                SELECT id, method, timestamp, event_type, card_id, user_name_jpn
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
                    user_name_jpn=row[5],
                    card_id=row[6],
                    face_id=row[7],
                )
                for row in rows
            ]

    except sqlite3.Error:
        logger.exception(
            "アクセスログ検索エラー: card_name=%s, method=%s, event_type=%s",
            card_name, method, event_type
        )
        raise


def count_filtered_logs(card_name=None, method=None, event_type=None, start_datetime=None, end_datetime=None):
    """
    find_log()をGUIで表示する際の件数を検索する関数

    args:
        card_name: カード名
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
            card_name = f"%{card_name}%" if card_name else "%"
            method = f"%{method}%" if method else "%"
            start_datetime = start_datetime or (now - timedelta(days=365))
            end_datetime = end_datetime or now

            start_datetime_str = start_datetime.strftime("%Y-%m-%d %H:%M:%S")
            end_datetime_str = end_datetime.strftime("%Y-%m-%d %H:%M:%S")

            query = """
                SELECT COUNT(*)
                FROM access_logs
                JOIN card ON access_logs.card_id = card.id
                WHERE card.card_name LIKE ?
                AND method LIKE ?
                AND (? IS NULL OR access_logs.event_type = ?)
                AND access_logs.timestamp BETWEEN ? AND ?
            """

            c.execute(query, (
                card_name, method, event_type, event_type,
                start_datetime_str, end_datetime_str
            ))
            return c.fetchone()[0]
    except sqlite3.Error:
        logger.exception(
            "アクセスログ件数取得エラー: card_name=%s, method=%s, event_type=%s",
            card_name, method, event_type
        )
        raise


# ===================================================
# 顔テーブル
# ===================================================

def get_faces_by_user_id(user_id):
    """
    指定されたユーザーIDに関連するすべての顔情報を取得する関数

    Args:
        user_id (int): 取得する顔情報に関連するユーザーのID

    Returns:
        list: 顔情報のリスト
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM face WHERE user_id = ?', (user_id,))
            return c.fetchall()
    except sqlite3.Error:
        logger.exception("顔情報取得エラー: user_id=%s", user_id)
        raise


def insert_face(face_name_jpn, face_name_roma, user_id):
    """
    顔情報をデータベースに挿入する関数

    Args:
        face_name_jpn (str): 顔の名前（日本語）
        face_name_roma (str): 顔の名前のローマ字表記
        user_id (int): ユーザーID
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                'INSERT INTO face (face_name_jpn, face_name_roma, user_id) VALUES (?, ?, ?)',
                (face_name_jpn, face_name_roma, user_id)
            )
    except sqlite3.Error:
        logger.exception(
            "顔情報挿入エラー: face_name_jpn=%s, face_name_roma=%s, user_id=%s",
            face_name_jpn, face_name_roma, user_id
        )
        raise


# ここでは画像の削除はしていません！！！
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
    指定されたユーザーIDに関連するすべての顔情報を削除する関数

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