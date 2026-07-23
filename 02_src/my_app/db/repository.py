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
from my_app.models.entity.access_log import AccessLog, AccessLogWithCard  # データクラス
from my_app.models.entity.face_with_user import FaceWithUser  # データクラス
from my_app.models.entity.user import User  # データクラス
from my_app.models.entity.card_with_user import CardWithUser
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

_USER_COLUMNS = "id, user_name, user_kana"

def find_users_with_total(search_text, asc: bool, limit, offset):
    """
    検索したユーザー件数(条件がNoneなら全検索)、件数を返す関数

    args:
        search_text: 検索用キーワード
        limit: 取得件数
        offset: ページ分けの為の区分
        asc: 昇順 -> true 降順 -> false
    """
    order = "ASC" if asc else "DESC"
    where = ""
    params =[]
    if search_text is not None:
        where = " AND (user_name LIKE ? OR user_kana LIKE ?)"
        like = f"%{search_text}%"
        params += [like, like]

    sql = f"""
        SELECT COUNT(*) OVER () AS total, {_USER_COLUMNS}
        FROM user
        WHERE 1=1{where}
        ORDER BY id {order}
        LIMIT ? OFFSET ?
    """

    params += [limit, offset]

    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(sql, params)
            rows = c.fetchall()

            total = rows[0][0] if rows else 0
            return [
                User(id=row[1], user_name=row[2], user_kana=row[3])
                for row in rows
            ], total
    except sqlite3.Error:
        logger.exception("ユーザー検索エラー: search_text=%s", search_text)
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

# cardカラム一覧(userとJOINするため、id/user_idが曖昧にならないよう修飾する)
_CARD_COLUMNS = (
    "card.id, card.card_type, card.card_number, card.register_date, "
    "card.user_id, user.user_name"
)


def find_cards_with_total(user_id, asc: bool, limit: int, offset: int):
    """
    カードを検索し、(一覧, 総件数) を返す。

    user_id が None なら全件、値があればそのユーザーのカードだけに絞る。
    userをLEFT JOINして所有者名も一緒に取得する。
    総件数は COUNT(*) OVER () で、LIMITで絞る前の件数が各行に付いてくるため、
    件数用のクエリを別に投げる必要がない。

    Args:
        user_id (int | None): 絞り込むユーザーID。Noneなら全件。
        asc (bool): 昇順 -> True / 降順 -> False
        limit (int): 取得件数
        offset (int): ページ送り用のオフセット

    Returns:
        tuple[list[CardWithUser], int]: (カード一覧, 条件に合う総件数)
    """
    order = "ASC" if asc else "DESC"

    where = ""
    params = []
    if user_id is not None:
        where = " AND card.user_id = ?"
        params.append(user_id)

    sql = f"""
        SELECT COUNT(*) OVER () AS total, {_CARD_COLUMNS}
        FROM card
        LEFT JOIN user ON card.user_id = user.id
        WHERE 1 = 1{where}
        ORDER BY card.id {order}
        LIMIT ? OFFSET ?
    """
    params += [limit, offset]

    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(sql, params)
            rows = c.fetchall()

            # COUNT(*) OVER () が row[0] を占めるので、以降のindexが1つずれる
            total = rows[0][0] if rows else 0
            return [
                CardWithUser(
                    id=row[1],
                    card_type=CardType(row[2]),
                    card_number=row[3],
                    register_date=row[4],
                    user_id=row[5],
                    user_name=row[6],
                )
                for row in rows
            ], total
    except sqlite3.Error:
        logger.exception("カード検索エラー: user_id=%s", user_id)
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
                SELECT card.id, card_type, card_number, register_date, user_id, user.user_name
                FROM card
                LEFT JOIN user ON user_id = user.id
                WHERE user_id = ?
                ORDER BY card.id {order} LIMIT 100 OFFSET ?
                """,
                (user_id, offset)
            )
            rows = c.fetchall()
            return [
                CardWithUser(id=row[0], card_type=CardType(row[1]), card_number=row[2],
                    register_date=row[3], user_id=row[4], user_name=row[5])
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


def find_cards_with_total(search_text, asc: bool, limit: int, offset: int):
    """氏名・カナ氏名の部分一致でカードと総件数を取得する"""
    order = "ASC" if asc else "DESC"
    where = ""
    params = []

    if search_text:
        where = " AND (user.user_name LIKE ? OR user.user_kana LIKE ?)"
        like = f"%{search_text}%"
        params.extend([like, like])

    sql = f"""
        SELECT
            COUNT(*) OVER () AS total,
            card.id,
            card.card_type,
            card.card_number,
            card.register_date,
            card.user_id,
            user.user_name
        FROM card
        LEFT JOIN user ON card.user_id = user.id
        WHERE 1=1{where}
        ORDER BY card.id {order}
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    try:
        with get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()

        total = rows[0][0] if rows else 0
        cards = [
            CardWithUser(
                id=row[1],
                card_type=CardType(row[2]),
                card_number=row[3],
                register_date=row[4],
                user_id=row[5],
                user_name=row[6],
            )
            for row in rows
        ]
        return cards, total

    except sqlite3.Error:
        logger.exception(
            "カード検索エラー: search_text=%s",
            search_text,
        )
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


"""
動的検索の為のパラメータ設定変数、関数
今回cardと表結合する為テーブルを明記
"""


# access_logカラム一覧
_LOG_COLUMNS = (
    "access_logs.id, "
    "datetime(access_logs.timestamp, 'localtime'), "
    "access_logs.method, access_logs.event_type, "
    "access_logs.user_id, access_logs.user_name, "
    "access_logs.card_id, access_logs.face_id, card.card_type"
)

# 条件名 → SQL部品 の対応表
_LOG_FILTERS = {
    "method": "access_logs.method = ?",
    "event_type": "access_logs.event_type = ?",
    "user_id": "access_logs.user_id = ?",
    "start_dt": "datetime(access_logs.timestamp, 'localtime') >= ?",
    "end_dt": "datetime(access_logs.timestamp, 'localtime') <= ?",
}

def _build_log_filter(**conditions):
    """Noneでない条件をWHEREに詰めるビルダー"""
    clauses = []
    params = []
    for name, value in conditions.items():
        if value is not None:
            clauses.append(_LOG_FILTERS[name])
            params.append(value)
    return ("".join(f" AND {c}" for c in clauses), params)


def find_access_log(
    method,
    event_type,
    start_dt,
    end_dt,
    limit,
    offset,
    user_id=None,
    asc: bool = True,
    search_text=None,
):
    """
    入退室ログを条件検索、一覧と総件数を返す関数

    cardと表結合しcard_typeまで持ってくる想定

    args:
        method: 認証方法
        event_type: 入退室区分
        start_dt: 日時指定(開始)
        end_dt: 日時指定(終了)
        limit: 取得件数
        offset: ページ分けの為の区分
        asc: 昇順 -> true 降順 -> false

    return tuple[list[AccessLogWithCard], int]: 入退室ログリストと件数。AccessLogWithCard のリストで返す。
    """
    order = "ASC" if asc else "DESC"

    method_aliases = None

    if method in ("顔", "顔認証", "face"):
        method_aliases = ("顔", "顔認証", "face")
    elif method in ("カード", "card"):
        method_aliases = ("カード", "card")

    where, params = _build_log_filter(
        method=None if method_aliases else method,
        event_type=event_type,
        user_id=user_id,
        start_dt=start_dt,
        end_dt=end_dt,
    )

    if method_aliases:
        placeholders = ", ".join("?" for _ in method_aliases)
        where += f" AND access_logs.method IN ({placeholders})"
        params.extend(method_aliases)

    if search_text:
        name_filter = (
            " AND ("
            "access_logs.user_name LIKE ? "
            "OR current_user.user_name LIKE ? "
            "OR current_user.user_kana LIKE ?"
            ")"
        )
        like = f"%{search_text}%"
        where += name_filter
        params.extend([like, like, like])

    sql = f"""
        SELECT
            COUNT(*) OVER () AS total,
            {_LOG_COLUMNS}
        FROM access_logs
        LEFT JOIN card
            ON access_logs.card_id = card.id
        LEFT JOIN user AS current_user
            ON access_logs.user_id = current_user.id
        WHERE 1=1{where}
        ORDER BY access_logs.timestamp {order}
        LIMIT ? OFFSET ?
    """

    params.extend([limit, offset])

    try:
        with get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()

        total = rows[0][0] if rows else 0

        logs = [
            AccessLogWithCard(
                id=row[1],
                timestamp=row[2],
                method=row[3],
                event_type=EventType(row[4]),
                user_id=row[5],
                user_name=row[6],
                card_id=row[7],
                face_id=row[8],
                card_type=row[9],
            )
            for row in rows
        ]

        return logs, total

    except sqlite3.Error:
        logger.exception(
            "アクセスログ検索エラー: search_text=%s method=%s event_type=%s",
            search_text,
            method,
            event_type,
        )
        raise


def get_main_menu_access_summary():
    """本日の入退室件数と、直近の入退室ログを取得する"""
    try:
        with get_connection() as conn:
            counts = conn.execute(
                """
                SELECT
                    COALESCE(
                        SUM(CASE WHEN event_type = ? THEN 1 ELSE 0 END),
                        0
                    ),
                    COALESCE(
                        SUM(CASE WHEN event_type = ? THEN 1 ELSE 0 END),
                        0
                    )
                FROM access_logs
                WHERE timestamp >= datetime(
                    'now', 'localtime', 'start of day', 'utc'
                )
                AND timestamp < datetime(
                    'now', 'localtime', 'start of day', '+1 day', 'utc'
                )
                """,
                (
                    EventType.ENTRY.value,
                    EventType.EXIT.value,
                ),
            ).fetchone()

            latest = conn.execute(
                """
                SELECT
                    datetime(timestamp, 'localtime'),
                    event_type,
                    user_name
                FROM access_logs
                WHERE event_type IN (?, ?)
                ORDER BY timestamp DESC, id DESC
                LIMIT 1
                """,
                (
                    EventType.ENTRY.value,
                    EventType.EXIT.value,
                ),
            ).fetchone()

        latest_log = None

        if latest is not None:
            try:
                local_timestamp = datetime.fromisoformat(
                    latest[0]
                )
            except (TypeError, ValueError):
                local_timestamp = None

            latest_log = {
                "timestamp": local_timestamp,
                "event_type": EventType(latest[1]),
                "user_name": (
                    latest[2]
                    or "不明なユーザー"
                ),
            }

        return {
            "entry_count": int(counts[0]),
            "exit_count": int(counts[1]),
            "latest": latest_log,
        }

    except sqlite3.Error:
        logger.exception(
            "メインメニュー用入退室状況取得エラー"
        )
        raise

def get_today_entry_ranking(limit: int = 10):
    """本日の入室回数ランキングを取得する"""
    safe_limit = max(1, min(int(limit), 100))

    try:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    COALESCE(
                        user.user_name,
                        access_logs.user_name,
                        '不明なユーザー'
                    ) AS display_name,
                    COUNT(*) AS entry_count,
                    datetime(
                        MAX(access_logs.timestamp),
                        'localtime'
                    ) AS last_entry
                FROM access_logs
                LEFT JOIN user
                    ON user.id = access_logs.user_id
                WHERE access_logs.event_type = ?
                AND access_logs.timestamp >= datetime(
                    'now', 'localtime', 'start of day', 'utc'
                )
                AND access_logs.timestamp < datetime(
                    'now', 'localtime', 'start of day',
                    '+1 day', 'utc'
                )
                GROUP BY
                    CASE
                        WHEN access_logs.user_id IS NOT NULL
                        THEN 'id:' || CAST(access_logs.user_id AS TEXT)
                        ELSE 'name:' || COALESCE(
                            access_logs.user_name,
                            ''
                        )
                    END
                ORDER BY
                    entry_count DESC,
                    MAX(access_logs.timestamp) DESC,
                    display_name COLLATE NOCASE ASC
                LIMIT ?
                """,
                (
                    EventType.ENTRY.value,
                    safe_limit,
                ),
            ).fetchall()

        ranking = []
        previous_count = None
        current_rank = 0

        for position, row in enumerate(rows, start=1):
            entry_count = int(row[1])

            # 同じ入室回数なら同順位
            if entry_count != previous_count:
                current_rank = position
                previous_count = entry_count

            try:
                last_entry = datetime.fromisoformat(row[2])
            except (TypeError, ValueError):
                last_entry = None

            ranking.append(
                {
                    "rank": current_rank,
                    "user_name": row[0],
                    "entry_count": entry_count,
                    "last_entry": last_entry,
                }
            )

        return ranking

    except sqlite3.Error:
        logger.exception("本日の入室ランキング取得エラー")
        raise


# ===================================================
# 顔テーブル
# ===================================================


# 顔ユーザー結合カラム一覧、明示しないとインデックスがわかりずらいので示しておく。
_FACE_COLUMNS = "face.id, face.register_date, face.user_id, user.user_name"

def find_faces_with_totals(user_id, asc: bool, limit: int, offset: int):
    """
    顔 + ユーザー情報のリストと、総件数を返す関数、
    user_idがNoneの場合は全検索する
    Args:
        user_id (int): ユーザーID

    Returns:
        tuple[list[FaceWithUser], int]: 顔 + ユーザー情報のリストと、総件数
    """
    order = "ASC" if asc else "DESC"

    where = ""
    params = ""
    if user_id is not None:
        where = "AND face.user_id = ?"
        params.append(user_id)
    sql = f"""
        SELECT COUNT(*) OVER () AS total, {_FACE_COLUMNS}
        FROM face
        LEFT JOIN user ON face.face_id = user.id
        WHERE 1 = 1 {where}
        ORDER BY face.id {order}
        LIMIT ? OFFSET ?
    """
    params += [limit, offset]

    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(sql, params)
            rows = c.fetchall()

            total = rows[0][0] if rows else 0
            return [
                FaceWithUser(
                    id=row[1],
                    register_date=row[2],
                    user_id=row[3],
                    user_name=row[4],
                )
                for row in rows
            ], total
    except sqlite3.Error:
        logger.exception("顔情報検索エラー: user_id=%s", user_id)
        raise


def find_faces_with_total(search_text, asc: bool, limit: int, offset: int):
    """氏名・カナ氏名の部分一致で顔情報と総件数を取得する"""
    order = "ASC" if asc else "DESC"
    where = ""
    params = []

    if search_text:
        where = " AND (user.user_name LIKE ? OR user.user_kana LIKE ?)"
        like = f"%{search_text}%"
        params.extend([like, like])

    sql = f"""
        SELECT
            COUNT(*) OVER () AS total,
            face.id,
            face.register_date,
            face.user_id,
            user.user_name
        FROM face
        LEFT JOIN user ON face.user_id = user.id
        WHERE 1=1{where}
        ORDER BY face.id {order}
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    try:
        with get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()

        total = rows[0][0] if rows else 0
        faces = [
            FaceWithUser(
                id=row[1],
                register_date=row[2],
                user_id=row[3],
                user_name=row[4],
            )
            for row in rows
        ]
        return faces, total

    except sqlite3.Error:
        logger.exception(
            "顔情報検索エラー: search_text=%s",
            search_text,
        )
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

def get_all_faces_for_authentication():
    """
    顔認証で使用する全face_idとユーザー情報を取得する。
    画像・特徴量ファイルはservice層で読み込む。
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    face.id,
                    face.register_date,
                    face.user_id,
                    user.user_name
                FROM face
                INNER JOIN user
                    ON user.id = face.user_id
                WHERE face.user_id IS NOT NULL
                ORDER BY face.user_id ASC, face.id ASC
            """)

            return [
                FaceWithUser(
                    id=row[0],
                    register_date=row[1],
                    user_id=row[2],
                    user_name=row[3],
                )
                for row in cursor.fetchall()
            ]

    except sqlite3.Error:
        logger.exception("顔認証用データ取得エラー")
        raise


def get_all_face_ids():
    """DBに登録されている全face_idを取得する"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM face")
            return [row[0] for row in cursor.fetchall()]

    except sqlite3.Error:
        logger.exception("顔ID一覧取得エラー")
        raise

def get_management_registration_counts():
    """
    管理画面に表示する登録件数を取得する
    """
    try:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    (SELECT COUNT(DISTINCT user_id)
                    FROM card WHERE user_id IS NOT NULL),
                    (SELECT COUNT(*) FROM card),
                    (SELECT COUNT(DISTINCT user_id)
                    FROM face WHERE user_id IS NOT NULL),
                    (SELECT COUNT(*) FROM face),
                    (SELECT COUNT(*) FROM user)
                """
            ).fetchone()

        return {
            "card_users": int(row[0]),
            "cards": int(row[1]),
            "face_users": int(row[2]),
            "faces": int(row[3]),
            "users": int(row[4]),
        }
    except sqlite3.Error:
        logger.e