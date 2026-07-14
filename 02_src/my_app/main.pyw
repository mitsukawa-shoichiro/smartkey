import atexit
import logging
import os
import socket
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import atexit
import my_app.logs.log_config_app
import flet as ft
from my_app.app.views.router import route
import logging
import json
from my_app.service.card_sys import set_state, get_state
import socket

HOST = "127.0.0.1"
PORT = 10000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

LOGS_PATH = os.path.abspath(os.path.join(BASE_DIR, "logs"))
if LOGS_PATH not in sys.path:
    sys.path.insert(0, LOGS_PATH)

logger = logging.getLogger(__name__)


def main(page: ft.Page):
    apply_page_theme(page)
    page.window.resizable = True
    page.title = "ドア開閉システム"

    route(page)
    page.go("/")

    logger.info("GUI started")


@atexit.register
def _on_exit():
    try:
        sock.connect((HOST, PORT))
        msg = "authenticating"
        sock.sendall(msg.encode("utf-8"))
        logger.info("Sent message: %s", msg)
    except Exception as e:
        logger.error("Socket message failed: %s", e)
    finally:
        logger.info("GUI stopped")


if __name__ == "__main__":
    ft.app(target=main, assets_dir="app")
