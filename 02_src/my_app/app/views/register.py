"""
カード登録画面GUI作成モジュール
登録処理に関してはView側の負担は最低限にすべく
バックとのやり取り、ロジックはcard_register_service、
状態管理はthread_state、
カード番号受け取り、保管はregister_listener
これらに責務を切り分けています。

未対処リスク

"""


import flet as ft
import asyncio
import logging
import threading

import db.repository as repo
from my_app.service.daemon_bridge import card_register_service as register_service
from my_app.service.daemon_bridge import thread_state, register_listener
from my_app.models.ENUMS import CardType
from my_app.app.views.common import (
    show_error_dialog,
    build_user_autocomplete,
    Theme,
    app_view,
    card,
    section_title,
    primary_button,
    secondary_button,
    danger_button,
)
from my_app.ui import theme as ui_theme

logger = logging.getLogger(__name__)

# ===================================================
# カード登録待機画面
# ===================================================
def registering(page: ft.Page):
    def stop_loop(_=None):
        register_service.cancel_registration_session()
        page.go("/card")

    try:
        register_service.start_registration_session()

        loading_text = ft.Text(
            "登録するカードをカードリーダーにかざしてください",
            size=22,
            color=Theme.TEXT,
            weight=ui_theme.FONT_WEIGHT,
            font_family=ui_theme.FONT_FAMILY,
            text_align=ft.TextAlign.CENTER,
        )

        loading_spinner = ft.CupertinoActivityIndicator(
            radius=32,
            color=Theme.SKY,
            animating=True,
        )

        reader_image = ft.Image(
            src="img/card_reader.JPG",
            width=220,
            height=130,
            fit=ft.ImageFit.CONTAIN,
            border_radius=8,
        )

        cancel_button = danger_button(
            "キャンセル",
            stop_loop,
            ft.Icons.CLOSE,
        )
        cancel_button.width = 200

        waiting_card = card(
            ft.Column(
                controls=[
                    loading_text,
                    ft.Container(height=8),
                    reader_image,
                    loading_spinner,
                    ft.Text(
                        "残り時間: 30秒",
                        size=13,
                        color=Theme.TEXT_MUTED,
                        font_family=ui_theme.FONT_FAMILY,
                    ),
                    ft.Container(height=8),
                    cancel_button,
                ],
                spacing=16,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            accent=Theme.SKY,
            padding=32,
        )

        return app_view(
            "/register",
            page,
            [waiting_card],
            back_route="/card",
            on_back=stop_loop,
        )

    except Exception as ex:
        logger.exception(
            "カード登録画面の表示中にエラーが発生しました: %s",
            ex,
        )

        error_card = card(
            ft.Column(
                controls=[
                    ft.Icon(
                        ft.Icons.ERROR_OUTLINE,
                        size=42,
                        color=Theme.DANGER,
                    ),
                    ft.Text(
                        "カード登録を開始できませんでした",
                        color=Theme.DANGER,
                        weight=ui_theme.FONT_WEIGHT,
                        font_family=ui_theme.FONT_FAMILY,
                    ),
                ],
                spacing=14,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            accent=Theme.DANGER,
        )

        return app_view(
            "/register",
            page,
            [error_card],
            back_route="/card",
        )


# ===================================================
# カード番号ポーリングループ待機
# ===================================================

async def delayed_transition(page: ft.Page):

    """
    登録受信待機スレッドを立ち上げ、読み取り結果を受け取る関数
    細かい動きはregister_serviceに任せています。
    """
    # 30秒間読み取り結果を待機
    result = await register_service.wait_for_new_card(timeout_total_s=30)

    # ダイアログ定義
    dialog = ft.AlertDialog(modal=True)

    # キャンセル時
    if result.status == register_service.STATUS_CANCELLED:
        return

    # 二重登録時
    if result.status == register_service.STATUS_DUPLICATE:
        dialog.title = ft.Text("エラー")
        dialog.content = ft.Text("このカードは既に登録されています")
        dialog.actions = [
            ft.TextButton("戻る", autofocus=True, on_click=lambda e: page.go("/card"))
        ]
        page.open(dialog)
        return

    # 登録成功時
    if result.status == register_service.STATUS_SUCCESS:
        page.go("/register/input")
        return

    # タイムアウト時
    if result.status == register_service.STATUS_TIMEOUT:
        dialog.title = ft.Text("タイムアウト")
        dialog.content = ft.Column(
            controls=[
            ft.Container(height=10),
            ft.Text("30秒経過したためタイムアウトしました。"),
            ft.Text("リトライしますか？")
            ],
            height=70
        )

    def retry(e):
        "リトライ用関数：現在の状態をリフレッシュして再び30秒待機を回す関数"
        # 現在ページの破棄
        page.views.pop()
        # 新規ページの作成
        page.views.append(registering(page))
        # スレッドの作成、thread_stateに格納
        thread_state.thread_handle = threading.Thread(
            target=lambda: run_async_delayed_transition(page)
        )
        # スレッド開始
        thread_state.thread_handle.daemon = True
        thread_state.thread_handle.start()
        # ダイアログ終了
        page.close(dialog)
        # ページ更新
        page.update()

    # リトライ確認ダイアログ
    dialog.actions = [
        ft.TextButton("はい", autofocus=True, on_click=retry),
        ft.TextButton("いいえ", on_click=lambda e: page.go("/card"))
    ]
    # ダイアログ表示
    page.open(dialog)

    #待機ページ開始
def run_async_delayed_transition(page):
    asyncio.run(delayed_transition(page))

# ===================================================
# カード情報入力画面
# ===================================================

def register_input(page: ft.Page):
    """検知済みのIDmに対して、所有者(user)とカード種別を選んで登録する画面"""
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    selected_user_id = None
    # 読み取り結果を取得
    card_number = register_listener.get_card_number()

    dialog = ft.AlertDialog(modal=True)

    # ユーザー選択用Autocomplete(face_view.pyと同じパターン)
    users = repo.get_all_users()

    # ユーザーID保存
    def on_user_selected(user_id: int):
        nonlocal selected_user_id
        selected_user_id = user_id

    # プルダウン定義
    user_field = build_user_autocomplete(
        users,
        on_user_selected,
    )

    # カード種類プルダウン定義
    card_type_dropdown = ft.Dropdown(
        label="カードの種類",
        width=320,
        options=[
            ft.dropdown.Option(key=ct.value, text=ct.value)
            for ct in CardType
        ],
    )

    # 登録確認関数
    def open_add_confirm_dialog(e):
        if selected_user_id is None or not card_type_dropdown.value:
            dialog.title = ft.Text("エラー")
            dialog.content = ft.Text("入力漏れがあります")
            dialog.actions = [
                ft.TextButton("OK", autofocus=True, on_click=lambda e: page.close(dialog)),
            ]
            page.open(dialog)
            return

        dialog.title = ft.Text("カード登録の確認")
        dialog.content = ft.Text("このカードを登録しますか?")
        dialog.actions = [
            ft.TextButton("はい", on_click=execute_register),
            ft.TextButton("いいえ", autofocus=True, on_click=lambda e: page.close(dialog)),
        ]
        page.open(dialog)

    # キャンセル確認関数
    def open_cancel_confirm_dialog(e):
        dialog.title = ft.Text("キャンセル確認")
        dialog.content = ft.Text("登録をキャンセルしますか?")
        dialog.actions = [
            ft.TextButton("はい", on_click=complete_cancel_confirm_dialog),
            ft.TextButton("いいえ", autofocus=True, on_click=lambda e: page.close(dialog)),
        ]
        page.open(dialog)

    # キャンセル完了関数
    def complete_cancel_confirm_dialog(e):
        register_listener.clear_card_number()
        page.close(dialog)
        dialog.title = ft.Text("キャンセル完了")
        dialog.content = ft.Text("カードの登録がキャンセルされました。")
        dialog.actions = [
            ft.TextButton("OK", autofocus=True, on_click=lambda e: page.go("/card")),
        ]
        page.open(dialog)

    # カード登録関数
    def execute_register(e):
        # カード番号無い時(異常事態)
        if not card_number:
            logger.critical("カード番号を取得できませんでした")
            page.close(dialog)
            dialog.title = ft.Text("エラー")
            dialog.content = ft.Text("カード番号を取得できませんでした")
            dialog.actions = [
                ft.TextButton("OK", autofocus=True, on_click=lambda e: page.go("/card")),
            ]
            page.open(dialog)
            return

        try:
            card_type = CardType(card_type_dropdown.value)
            # 登録処理呼び出し
            register_service.register_card(card_number, card_type, selected_user_id)
        except Exception:
            logger.exception("カード登録に失敗しました: card_number=%s, user_id=%s",
                            card_number, selected_user_id)
            page.close(dialog)
            show_error_dialog(page, "カードの登録に失敗しました。しばらくしてから再度お試しください。")
            return

        page.close(dialog)

        dialog.title = ft.Text("登録完了")
        dialog.content = ft.Text("カードの登録が完了しました。")
        dialog.actions = [
            ft.TextButton("OK", autofocus=True, on_click=lambda e: page.go("/card")),
        ]
        page.open(dialog)

    register_button = primary_button(
        "登録",
        open_add_confirm_dialog,
        ft.Icons.CHECK,
    )
    register_button.width = 200

    cancel_button = danger_button(
        "キャンセル",
        open_cancel_confirm_dialog,
        ft.Icons.CLOSE,
    )
    cancel_button.width = 200

    form_content = ft.Column(
        controls=[
            section_title(
                "登録内容",
                accent=Theme.SKY,
            ),
            ft.Container(height=8),
            ft.Text(
                "ユーザー",
                size=13,
                color=Theme.TEXT_MUTED,
                weight=ui_theme.FONT_WEIGHT,
                font_family=ui_theme.FONT_FAMILY,
            ),
            ft.Container(
                width=340,
                content=user_field,
            ),
            card_type_dropdown,
            ft.Container(height=12),
            ft.Row(
                controls=[
                    register_button,
                    cancel_button,
                ],
                spacing=14,
                wrap=True,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        ],
        spacing=14,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    form_card = card(
        form_content,
        accent=Theme.SKY,
        padding=30,
    )

    return app_view(
        "/register/input",
        page,
        [form_card],
        back_route="/card",
        on_back=open_cancel_confirm_dialog,
    )