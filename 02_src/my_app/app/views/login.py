import flet as ft
import json
import os
import logging

from my_app.app.views.common import Theme, card, primary_button
from my_app.ui import theme as ui_theme

logger = logging.getLogger(__name__)

def load_accounts():
    dir_path = os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__)
            )
        )
    )

    ACCOUNT_PATH = os.path.join(dir_path, "config", "account.json")
    with open(ACCOUNT_PATH) as f:
        return json.load(f)


def login(page: ft.Page):
    page.title = "SmartKey ログイン"
    page.bgcolor = Theme.BG

    error_text = ft.Text(
        "",
        size=13,
        color=Theme.DANGER,
        font_family=ui_theme.FONT_FAMILY,
    )
    error_panel = ft.Container(
        visible=False,
        padding=12,
        bgcolor=ui_theme.DANGER_BG,
        border_radius=8,
        content=error_text,
    )

    username = ft.TextField(
        label="ユーザー名",
        autofocus=True,
        max_length=50,
        prefix_icon=ft.Icons.PERSON_OUTLINE,
        border_radius=8,
    )
    password = ft.TextField(
        label="パスワード",
        password=True,
        can_reveal_password=True,
        max_length=100,
        prefix_icon=ft.Icons.LOCK_OUTLINE,
        border_radius=8,
    )

    def show_error(message):
        error_text.value = message
        error_panel.visible = True
        page.update()

    def do_login(_):
        name = (username.value or "").strip()
        secret = password.value or ""

        if not name or not secret:
            show_error("ユーザー名とパスワードを入力してください")
            return

        try:
            account = load_accounts()
        except (OSError, json.JSONDecodeError, KeyError):
            logger.exception("ログイン設定を読み込めませんでした")
            show_error("ログイン設定を確認できませんでした")
            return

        if (
            account.get("username") == name
            and account.get("password") == secret
        ):
            logger.info("ログイン成功")
            error_panel.visible = False
            page.go("/index")
            return

        logger.warning("ログイン失敗")
        password.value = ""
        show_error("ユーザー名またはパスワードが間違っています")
        password.focus()

    username.on_submit = lambda _: password.focus()
    password.on_submit = do_login

    login_button = primary_button(
        "ログイン",
        do_login,
        ft.Icons.LOGIN,
    )
    login_button.width = 320

    login_panel = card(
        ft.Column(
            controls=[
                ft.Icon(
                    ft.Icons.LOCK_PERSON_OUTLINED,
                    size=42,
                    color=Theme.LAVENDER,
                ),
                ft.Text(
                    "SmartKey",
                    size=28,
                    color=Theme.TEXT,
                    weight=ui_theme.FONT_WEIGHT,
                    font_family=ui_theme.FONT_FAMILY,
                ),
                ft.Text(
                    "入退室管理システム",
                    size=13,
                    color=Theme.TEXT_MUTED,
                    font_family=ui_theme.FONT_FAMILY,
                ),
                ft.Container(height=8),
                error_panel,
                username,
                password,
                ft.Container(height=4),
                login_button,
            ],
            spacing=16,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=34,
        accent=Theme.LAVENDER,
    )
    login_panel.width = 430

    return ft.View(
        route="/",
        padding=0,
        bgcolor=Theme.BG,
        controls=[
            ft.Container(
                expand=True,
                alignment=ft.alignment.center,
                content=login_panel,
            )
        ],
    )