import os
import sys
# エントリーポイントで1回だけ、02_src(my_appの1つ上)をpathに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import atexit
import logging
import socket

import flet as ft

import my_app.logs.log_config_app
from my_app.app.views.router import route
from my_app.db.schema import create_database

HOST = '127.0.0.1'
PORT = 10000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

logger = logging.getLogger(__name__)


def main(page: ft.Page):
    page.window.width = 1024
    page.window.height = 768
    page.window.min_width = 1024
    page.window.min_height = 768
    page.window.resizable = True
    page.title = "ドア開閉システム"

    route(page)
    page.go("/")

    create_database()

    logger.info("GUIが起動されました")


@atexit.register
def _on_exit():
    try:
        sock.connect((HOST, PORT))
        msg = "authenticating"
        sock.sendall(msg.encode('utf-8'))
        logger.info(f"Sent message: {msg}")
    except Exception as e:
        logger.error(f"通信エラー: {e}")
    finally:
        logger.info("GUIを終了しました")


if __name__ == "__main__":
    ft.app(target=main, assets_dir="app")