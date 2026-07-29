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

from my_app.app.utils.front_camera_moduel import (
    send_message as send_camera_message,
)

HOST = '127.0.0.1'
PORT = 10000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_PATH = os.path.abspath(os.path.join(BASE_DIR, "logs"))
if LOGS_PATH not in sys.path:
    sys.path.insert(0, LOGS_PATH)

logger = logging.getLogger(__name__)

from my_app.ui.theme import apply_page_theme
def main(page: ft.Page):
    apply_page_theme(page)
    page._app_closing = False
    page.title = "ドア開閉システム"

    route(page)
    page.go("/")

    create_database()

    logger.info("GUI起動")
    async def on_disconnect(_):
        page._app_closing = True
        page._index_summary_generation = (
            getattr(page, "_index_summary_generation", 0) + 1
        )

        task = getattr(page, "_index_summary_task", None)
        if task is not None and not task.done():
            task.cancel()

        send_camera_message("finishRegistering")

    page.on_disconnect = on_disconnect


@atexit.register
def _on_exit():
    send_camera_message(
        "finishRegistering"
    )
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