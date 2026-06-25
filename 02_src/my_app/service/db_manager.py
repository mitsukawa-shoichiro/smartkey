import os
import sqlite3
import json
import logging
from datetime import datetime, timedelta


BASE_DIR = os.path.dirname(os.path.abspath(__file__))+"/.."+"/db"
DB_PATH = os.path.join(BASE_DIR, 'dataBase.db')
print(BASE_DIR)
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
    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    try:
        cursor.execute(
            'SELECT card_id FROM card WHERE card_number = ?', (cardIDM,))
        card_id = cursor.fetchone()

        return card_id[0]
    except sqlite3.Error as e:
        logger.exception("カード検索エラー: card_id=%s", cardIDM)
        raise
    finally:
        conn.close()


def get_last_date_time(card_id, card_reader_id):
    dt = None
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT timestamp FROM access_logs where card_id = ? AND eventtype = ? ORDER BY timestamp DESC LIMIT 1", (card_id, card_reader_id))
        row = cursor.fetchone()
        if row:
            ts_str = row[0]
            dt = datetime.fromisoformat(ts_str)
        return dt
    except sqlite3.Error as e:
        logger.exception("アクセスログ日時検索エラー: card_id=%s, card_reader_id=%s", card_id, card_reader_id)
        raise
    finally:
        conn.close()
    


def insert_card_id(card_id, card_reader_id):
    # カードIDをaccess_logsテーブルに挿入します。
    logger.info(f"カードIDを挿入: {card_id}, リーダーID: {card_reader_id}")
    config = load_config()

    if config["出口"]["serial"] == card_reader_id:
        eventtype = 1
    elif config["入口"]["serial"] == card_reader_id:
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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO access_logs (method, card_id, eventtype) VALUES(?,?,?)", ('カード', card_id, eventtype))
        conn.commit()
    except sqlite3.Error as e:
        logger.exception("アクセスログ登録エラー: card_id=%s, card_reader_id=%s", card_id, card_reader_id)
        raise
    finally:
        conn.close()
