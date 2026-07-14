import atexit
import logging
import os
import socket
import sys

import flet as ft

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import logs.log_config_app
from app.views.router import route
from ui.theme import apply_page_theme


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
