import atexit
import os
import sys
import my_app.logs.log_config_app
import flet as ft
from my_app.app.views.router import route
import logging
import json
from my_app.service.cardsystem import set_state, get_state
from my_app.app.utils.thread_state import stop_event
import socket

HOST = '127.0.0.1'
PORT = 10000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# region logs
# logs ディレクトリのパスを sys.path に追加
LOGS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'logs'))
if LOGS_PATH not in sys.path:
    sys.path.insert(0, LOGS_PATH)

logger = logging.getLogger(__name__)
# endregion


from my_app.app.utils.front_camera_moduel import send_message

def main(page: ft.Page):
    page.window.width = 1024
    page.window.height = 768
    page.window.min_width = 1024
    page.window.min_height = 768
    page.window.resizable = True
    page.title = "ドア開閉システム"
    route(page)
    page.go("/")
    send_message("startRegisting")
    logging.info("GUIが起動されました")


ft.app(target=main, assets_dir="app")


@atexit.register
def _on_exit():
    global stop_event
    try:
        try:

            sock.connect((HOST, PORT))
            msg = "authenticating"
            sock.sendall(msg.encode('utf-8'))
            logging.info(f"Sent message: {msg}")
        except Exception as e:
            logging.error(f"通信エラー: {e}")

        send_message("finishRegisting")
        logger.info("GUIを終了しました")
    except Exception:
        print("失敗")
        pass
