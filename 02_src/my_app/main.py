import os
import sys
import logs.log_config_app
import flet as ft
from app.views.router import route
import logging
import json
from flet.core.page import Page

# region logs
# logs ディレクトリのパスを sys.path に追加
LOGS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'logs'))
if LOGS_PATH not in sys.path:
    sys.path.insert(0, LOGS_PATH)
# endregion


def main(page: ft.Page):
    print(Page._Page__on_page_change_event)
    page.window.width = 1024
    page.window.height = 768
    page.window.resizable = False
    page.title = "ドア開閉システム"
    route(page)
    page.go("/")

    logging.info("フロントが起動されました")


ft.app(target=main)
