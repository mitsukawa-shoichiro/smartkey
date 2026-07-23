"""
カード登録画面GUI作成モジュール

登録処理に関してはView側の負担は最低限にすべく
バックとのやり取り、ロジックはcard_register_service、
状態管理はthread_state、
カード番号受け取り、保管はregister_listener
これらに責務を切り分けています。

例外はrouterが受け止めてホームへ戻すため、この画面では
View全体を包むtry/exceptは持ちません。
"""
import asyncio
import logging
import threading

import flet as ft

import my_app.db.repository as repo
from my_app.service.daemon_bridge import card_register_service as register_service
from my_app.service.daemon_bridge import thread_state, register_listener
from my_app.models.ENUMS import CardType
from my_app.app.views.common import (
    show_error_dialog, show_info_dialog, show_confirm_dialog,
    build_user_autocomplete,
    Theme, card, section_title, primary_button, secondary_button,
)

logger = logging.getLogger(__name__)


# ===================================================
# カード登録待機画面
# ===================================================

def registering(page: ft.Page):
    """
    「カードをかざしてください」の待機画面。
    表示と同時にdaemonを登録モードへ切り替える。

    この画面には共通の「戻る」ボタン(app_view)を使わない。
    戻るで抜けるとdaemonへauthenticatingを送らずに離脱してしまうため、
    離脱はキャンセルボタン(cancel_registration_session)に限定する。
    """
    def stop_loop(e):
        """キャンセルボタン: 登録モードを抜けてホームへ戻る"""
        register_service.cancel_registration_session()
        page.go("/index")

    register_service.start_registration_session()

    page.title = "ICカード情報読み込み中"
    page.bgcolor = Theme.BG

    loading_text = ft.Text(
        "30秒以内に登録したいカードを\n出口のカードリーダーにかざしてください",
        size=28,
        color=Theme.TEXT,
        text_align=ft.TextAlign.CENTER,
    )

    # ローディング中にくるくる回る演出
    loading_spinner = ft.ProgressRing(
        width=64, height=64, stroke_width=5, color=Theme.PRIMARY,
    )

    img = ft.Image(
        src="img/card_reader.JPG",
        height=100,
        width=200,
        fit=ft.ImageFit.CONTAIN,
    )

    # 待機中の中身をカードに乗せる
    waiting_card = card(
        ft.Column(
            controls=[
                section_title("カード登録", "出口のカードリーダーで読み取ります"),
                ft.Container(height=16),
                loading_text,
                ft.Container(height=16),
                img,
                ft.Container(height=16),
                loading_spinner,
                ft.Container(height=24),
                secondary_button("キャンセル", stop_loop, ft.Icons.STOP),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
            tight=True,
        ),
        padding=40,
    )

    return ft.View(
        "/register",
        controls=[
            ft.Row(
                controls=[waiting_card],
                alignment=ft.MainAxisAlignment.CENTER,
                expand=True,
            )
        ],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        bgcolor=Theme.BG,
        padding=ft.Padding(left=40, top=24, right=40, bottom=24),
    )


# ===================================================
# カード番号ポーリングループ待機
# ===================================================

async def delayed_transition(page: ft.Page):
    """
    登録受信待機スレッドを立ち上げ、読み取り結果を受け取る関数。
    細かい動きはregister_serviceに任せ、ここは結果を見て画面を出すだけ。
    """
    # 30秒間読み取り結果を待機
    result = await register_service.wait_for_new_card(timeout_total_s=30)

    # キャンセル時: 既にホームへ遷移しているので何もしない
    if result.status == register_service.STATUS_CANCELLED:
        return

    # 二重登録時
    if result.status == register_service.STATUS_DUPLICATE:
        show_info_dialog(
            page, "このカードは既に登録されています", title="エラー",
            on_close=lambda: page.go("/index"),
        )
        return

    # 読み取り成功時
    if result.status == register_service.STATUS_SUCCESS:
        page.go("/register/input")
        return

    # タイムアウト時: リトライするか確認する
    def retry():
        """リトライ: 現在の待機ページを作り直して、再び30秒待機を回す"""
        page.views.pop()
        page.views.append(registering(page))
        page.run_task(delayed_transition, page)
        page.update()

    show_confirm_dialog(
        page,
        "30秒経過したためタイムアウトしました。\nリトライしますか?",
        on_confirm=retry,
        title="タイムアウト",
        confirm_label="はい",
        cancel_label="いいえ",
    )



# ===================================================
# カード情報入力画面
# ===================================================

def register_input(page: ft.Page):
    """検知済みのIDmに対して、所有者(user)とカード種別を選んで登録する画面"""
    page.title = "カード登録"
    page.bgcolor = Theme.BG

    selected_user_id = None

    # 読み取り結果(IDm)を取得
    card_number = register_listener.get_card_number()

    # ユーザー選択用Autocomplete(他画面と同じ共通部品)
    users = repo.get_all_users()

    def on_user_selected(user_id: int):
        nonlocal selected_user_id
        selected_user_id = user_id

    user_field = build_user_autocomplete(users, on_user_selected)

    # 読み取ったカード番号は編集させず、確認用に表示するだけ
    card_number_display = ft.TextField(
        label="読み取ったカード番号",
        value=card_number or "(未取得)",
        width=320,
        read_only=True,
    )

    card_type_dropdown = ft.Dropdown(
        label="カードの種類",
        width=320,
        options=[
            ft.dropdown.Option(key=ct.value, text=ct.value)
            for ct in CardType
        ],
    )

    def execute_register():
        """登録確定: service層に渡してDBへ挿入する"""
        if not card_number:
            logger.critical("カード番号を取得できませんでした")
            show_info_dialog(
                page, "カード番号を取得できませんでした", title="エラー",
                on_close=lambda: page.go("/index"),
            )
            return

        try:
            card_type = CardType(card_type_dropdown.value)
            register_service.register_card(card_number, card_type, selected_user_id)
        except Exception:
            logger.exception("カード登録に失敗しました: card_number=%s, user_id=%s",
                            card_number, selected_user_id)
            show_error_dialog(page, "カードの登録に失敗しました。しばらくしてから再度お試しください。")
            return

        show_info_dialog(
            page, "カードの登録が完了しました。", title="登録完了",
            on_close=lambda: page.go("/index"),
        )

    def open_add_confirm_dialog(e):
        """「登録」ボタン: 入力漏れを確認してから、登録確認ダイアログを出す"""
        if selected_user_id is None or not card_type_dropdown.value:
            show_info_dialog(page, "入力漏れがあります", title="エラー")
            return

        show_confirm_dialog(
            page, "このカードを登録しますか?",
            on_confirm=execute_register,
            title="カード登録の確認",
        )

    def complete_cancel():
        """キャンセル確定: 保持しているカード番号を捨ててホームへ戻る"""
        register_listener.clear_card_number()
        show_info_dialog(
            page, "カードの登録がキャンセルされました。", title="キャンセル完了",
            on_close=lambda: page.go("/index"),
        )

    def open_cancel_confirm_dialog(e):
        show_confirm_dialog(
            page, "登録をキャンセルしますか?",
            on_confirm=complete_cancel,
            title="キャンセル確認",
        )

    input_card = card(
        ft.Column(
            controls=[
                section_title("カード登録", "読み取ったカードの所有者と種別を選んでください"),
                ft.Container(height=16),
                card_number_display,
                user_field,
                card_type_dropdown,
                ft.Container(height=16),
                primary_button("登録", open_add_confirm_dialog, ft.Icons.CHECK),
                secondary_button("キャンセル", open_cancel_confirm_dialog, ft.Icons.ARROW_BACK),
            ],
            spacing=16,
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
        padding=40,
    )

    return ft.View(
        "/register/input",
        controls=[
            ft.Row(
                controls=[input_card],
                alignment=ft.MainAxisAlignment.CENTER,
                expand=True,
            )
        ],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        bgcolor=Theme.BG,
        padding=ft.Padding(left=40, top=24, right=40, bottom=24),
    )