"""
db接続とテーブル作成を行うモジュール

"""

import sqlite3
import os
import logging

db_path = os.path.join(os.path.dirname(__file__), "database.db")
conn = sqlite3.connect(db_path)
c = conn.cursor()
logger = logging.getLogger(__name__)

#db作成
def create_database():

    """
    データベースとテーブルを作成する関数(存在しない場合のみ)

    userテーブル:
    id, user_name_jpn, user_name_roma

    cardテーブル:
    id, card_type, card_number, register_date

    access_logsテーブル:
    id, timestamp, method, event_type, user_id(user.id)

    faceテーブル:
    id, face_name, face_name_roma, register_date, user_id(user.id)

    """

    # 外部キー有効化
    c.execute('PRAGMA foreign_keys = ON;')

    # userテーブルが存在するか確認
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user';")
    exists = c.fetchone() is not None

    # テーブル作成
    if not exists:
        logger.info("userテーブルが存在しないので作成")
        c.execute(
            '''
            CREATE TABLE user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name_jpn TEXT NOT NULL,
            user_name_roma TEXT NOT NULL
            )
            '''
        )

    # cardテーブルが存在するか確認
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='card';")
    exists = c.fetchone() is not None

    # テーブル作成
    if not exists:
        logger.info("cardテーブルが存在しないので作成")
        c.execute('''
        CREATE TABLE card (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_type TEXT NOT NULL,
            card_number TEXT NOT NULL,
            register_date TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            )
        ''')

    # access_logsテーブルが存在するか確認
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='access_log';")
    exists = c.fetchone() is not None

    if not exists:
        logger.info("access_logテーブルが存在しないので作成")
        c.execute('''
        CREATE TABLE access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT (datetime('now', 'localtime')),
            method VARCHAR(32) NOT NULL,
            event_type INTEGER,
            user_id INTEGER FOREIGN KEY REFERENCES user(id)
        )
        ''')

    # サンプルデータ
    c.execute("INSERT INTO card (card_name, card_number) VALUES (?, ?)", ("Sample Card", "1234567890123456"))
    c.execute("INSERT INTO access_logs (card_id, method, event_type) VALUES (?, ?, ?)", (1, "Web", 1))

    # faceテーブルが存在するか確認
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='face';")
    exists = c.fetchone() is not None

    if not exists:
        logger.info("faceテーブルが存在しないので作成")
        c.execute(
            """
            CREATE TABLE face (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                face_name TEXT NOT NULL,
                face_name_roma TEXT NOT NULL,
                register_date TIMESTAMP DEFAULT (datetime('now', 'localtime'))
                user_id INTEGER FOREIGN KEY REFERENCES user(id)
            );
            """
        )

        # サンプルデータを1件追加（初回のみ）
        c.execute(
            "INSERT INTO face (face_name, face_name_roma) VALUES (?, ?)",
            ("山田太郎", "taro_yamada"),
        )
        print("[OK] face テーブルを作成しました。")
    else:
        print("[INFO] face テーブルは既に存在します。何もしません。")

    conn.commit()
    conn.close()


def get_connection():
    """
    データベースへの接続を取得する関数
    Returns:
        sqlite3.Connection: データベースへの接続オブジェクト
    """
    return sqlite3.connect(db_path)