"""
カード登録フロー(GUI)

出口リーダーに新規カードをかざしてもらい、IDmを取得したうえで
ユーザー・カード種別を選んで登録する一連の画面。

判断ロジック(daemonとの通信、IDm待機、重複チェック、DB登録)は
service/card_register_service.py が担う。このファイルはその結果を見て
画面(ダイアログ・遷移)を組み立てることに専念する。
"""
import asyncio
import logging
import threading

import flet as ft

import db.repository as repo
from my_app.app.service import card_register_service as register_service
from my_app.app.service.daemon_bridge import thread_state
from my_app.app.service.daemon_bridge import register_listener
from my_app.models.ENUMS import CardType
from my_app.app.views.common import show_error_dialog, filter_user_options

logger = logging.getLogger(__name__)


# ===================================================
# 登録待機画面
# ===================================================

def registering(page: ft.Page):
    """「カードをかざしてください」の待機画面。表示と同時に登録モードへ切り替える。"""
    try:
        def stop_loop(e):
            """キャンセルボタン: 登録モードを抜けて索引画面へ戻る"""
            register_service.cancel_registration_session()
            page.go("/index")

        register_service.start_registration_session()

        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.title = "ICカード情報読み込み中"

        loading_text = ft.Text(
            "30秒以内に登録したいカードを\n出口のカードリーダーにかざしてください",
            size=35, text_align=ft.TextAlign.CENTER
        )
        loading_spinner = ft.CupertinoActivityIndicator(
            radius=50, color=ft.Colors.LIGHT_BLUE_ACCENT, animating=True,
        )
        stop_btn = ft.Container(
            content=ft.TextButton(
                text="キャンセル", icon=ft.Icons.STOP, on_click=stop_loop,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=10),
                    color=ft.Colors.RED,
                    overlay_color=ft.Colors.RED_100,
                )
            )
        )
        img = ft.Image(src="img/card_reader.JPG", height=100, width=200, fit=ft.ImageFit.CONTAIN)

        return ft.View(
            "/register",
            controls=[
                ft.Container(
                    expand=True,
                    alignment=ft.alignment.center,
                    content=ft.Column(
                        controls=[
                            ft.Container(content=loading_text, padding=10),
                            ft.Container(content=img),
                            ft.Container(content=loading_spinner),
                            ft.Container(height=40),
                            stop_btn
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        tight=True,
                    ),
                )
            ],
        )
    except Exception:
        logger.exception("カード登録画面の表示中にエラーが発生しました")
        page.go("/index?error=カード登録画面の表示中にエラーが発生しました")
    finally:
        page.update()


# ===================================================
# IDm受信待ちのポーリングループ(別スレッドで動く)
# ===================================================

async def delayed_transition(page: ft.Page):
    """
    service層の wait_for_new_card の結果を見て、画面を組み立てるだけの関数。
    判断ロジック(何秒待つか、重複かどうか等)は一切持たない。
    """
    result = await register_service.wait_for_new_card(timeout_total_s=30)

    dialog = ft.AlertDialog(modal=True)

    if result.status == register_service.STATUS_CANCELLED:
        return

    if result.status == register_service.STATUS_DUPLICATE:
        dialog.title = ft.Text("エラー")
        dialog.content = ft.Text("このカードは既に登録されています")
        dialog.actions = [
            ft.TextButton("戻る", autofocus=True, on_click=lambda e: page.go("/index"))
        ]
        page.open(dialog)
        return

    if result.status == register_service.STATUS_SUCCESS:
        page.go("/register/input")
        return

    # STATUS_TIMEOUT
    dialog.title = ft.Text("タイムアウト")
    dialog.content = ft.Column(
        controls=[
            ft.Container(height=10),
            ft.Text("30秒経ったため処理を中断しました。"),
            ft.Text("リトライしますか。")
        ],
        height=70
    )

    def retry(e):
        page.views.pop()  # 古い待機Viewを取り除いてから積み直す
        page.views.append(registering(page))
        thread_state.thread_handle = threading.Thread(
            target=lambda: run_async_delayed_transition(page))
        thread_state.thread_handle.daemon = True
        thread_state.thread_handle.start()
        page.close(dialog)
        page.update()

    dialog.actions = [
        ft.TextButton("はい", autofocus=True, on_click=retry),
        ft.TextButton("いいえ", on_click=lambda e: page.go("/index"))
    ]
    page.open(dialog)


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
    card_number = register_listener.get_card_number()

    dialog = ft.AlertDialog(modal=True)

    # ユーザー選択用Autocomplete(face_view.pyと同じパターン)
    users = repo.get_all_users()

    def on_user_selected(e: ft.ControlEvent):
        nonlocal selected_user_id
        selected_user_id = int(e.selection.key)

    def on_user_search_change(e: ft.ControlEvent):
        user_field.suggestions = filter_user_options(users, e.control.value)
        user_field.update()

    user_field = ft.AutoComplete(
        suggestions=filter_user_options(users, ""),
        on_select=on_user_selected,
        on_change=on_user_search_change,
    )

    card_type_dropdown = ft.Dropdown(
        label="カードの種類",
        width=320,
        options=[
            ft.dropdown.Option(key=str(CardType.EMPLOYEE.value), text="社員証"),
            ft.dropdown.Option(key=str(CardType.VISITOR.value), text="来客証"),
        ],
    )

    card_number_display = ft.TextField(
        label="読み取ったカード番号", value=card_number or "(未取得)",
        width=320, read_only=True,
    )

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

    def open_cancel_confirm_dialog(e):
        dialog.title = ft.Text("キャンセル確認")
        dialog.content = ft.Text("登録をキャンセルしますか?")
        dialog.actions = [
            ft.TextButton("はい", on_click=complete_cancel_confirm_dialog),
            ft.TextButton("いいえ", autofocus=True, on_click=lambda e: page.close(dialog)),
        ]
        page.open(dialog)

    def complete_cancel_confirm_dialog(e):
        register_listener.clear_card_number()
        page.close(dialog)
        dialog.title = ft.Text("キャンセル完了")
        dialog.content = ft.Text("カードの登録がキャンセルされました。")
        dialog.actions = [
            ft.TextButton("OK", autofocus=True, on_click=lambda e: page.go("/index")),
        ]
        page.open(dialog)

    def execute_register(e):
        if not card_number:
            logger.critical("カード番号を取得できませんでした")
            page.close(dialog)
            dialog.title = ft.Text("エラー")
            dialog.content = ft.Text("カード番号を取得できませんでした")
            dialog.actions = [
                ft.TextButton("OK", autofocus=True, on_click=lambda e: page.go("/index")),
            ]
            page.open(dialog)
            return

        try:
            card_type = CardType(int(card_type_dropdown.value))
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
            ft.TextButton("OK", autofocus=True, on_click=lambda e: page.go("/index")),
        ]
        page.open(dialog)

    button_column = ft.Column(
        controls=[
            ft.ElevatedButton(
                "登録", icon=ft.Icons.CHECK, width=200,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
                on_click=open_add_confirm_dialog,
            ),
            ft.ElevatedButton(
                "キャンセル", icon=ft.Icons.ARROW_BACK, width=200, color=ft.Colors.RED,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
                on_click=open_cancel_confirm_dialog,
            ),
        ],
        spacing=20,
        alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    return ft.View(
        "/register/input",
        controls=[
            ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text("カード登録", size=28, weight=ft.FontWeight.BOLD),
                                card_number_display,
                                user_field,
                                card_type_dropdown,
                                ft.Container(height=20),
                                button_column,
                            ],
                            spacing=40,
                            alignment=ft.MainAxisAlignment.START,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        margin=ft.margin.only(top=120),
                        width=400,
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                expand=True,
            )
        ]
    )