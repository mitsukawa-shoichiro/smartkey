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
from my_app.app.views.common import show_error_dialog, build_user_autocomplete

logger = logging.getLogger(__name__)


# ===================================================
# カード登録待機画面
# ===================================================

def registering(page: ft.Page):
    try:

        def stop_loop(e):                               #stop_buttonをクリックした際のみここに来る

            register_service.cancel_registration_session()
            page.go("/index")

        register_service.start_registration_session()

        page.vertical_alignment = ft.MainAxisAlignment.CENTER       #上下方向(vertical)は中央寄せで表示
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER    #水平方向(horizontal)も中央寄せで表示
        page.title = "ICカード情報読み込み中"

        loading_text = ft.Text(
            "30秒以内に登録したいカードを\n出口のカードリーダーにかざしてください",
            size=35,
            text_align=ft.TextAlign.CENTER
        )

        loading_spinner = ft.CupertinoActivityIndicator(
            radius=50,
            color=ft.Colors.LIGHT_BLUE_ACCENT,
            animating=True,
        )
        #ローディング画面でくるくる回る演出が入る

        stop_btn = ft.Container(
            content=ft.TextButton(
                text="キャンセル",
                icon=ft.Icons.STOP,
                on_click=stop_loop,                 #クリックされた時のみstop_loopを呼ぶため()をつけない
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=10),
                    color=ft.Colors.RED,
                    overlay_color=ft.Colors.RED_100,
                )
            )
        )
        img = ft.Image(
            src=f"img/card_reader.JPG",
            height=100,
            width=200,
            fit=ft.ImageFit.CONTAIN,
            #画像ファイルの表示

        )
        return ft.View(                                                     #登録画面(View)を返す
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
    except Exception as e:
        logger.exception("カード登録画面の表示中にエラーが発生しました: %s", e)     #スタックトレースも含めて出力される
        page.go("/index?error=カード登録画面の表示中にエラーが発生しました")

    finally:                #例外の有無にかかわらず実行される
        page.update()


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
        dialog.title = ft.Text("エラー")
        dialog.content = ft.Text("このカードは既に登録されています")
        dialog.actions = [
            ft.TextButton("戻る", autofocus=True, on_click=lambda e: page.go("/index"))
        ]
        page.open(dialog)
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

    # リトライ確認ダイアログ
    dialog.actions = [
        ft.TextButton("はい", autofocus=True, on_click=retry),
        ft.TextButton("いいえ", on_click=lambda e: page.go("/index"))
    ]
    # ダイアログ表示
    page.open(dialog)

    #待機ページ開始
def run_async_delayed_transition(page):
    """別スレッドから delayed_transition(async) を回すためのラッパー"""
    asyncio.run(delayed_transition(page))


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

    # ユーザーID保存
    def on_user_selected(e: ft.ControlEvent):
        nonlocal selected_user_id
        selected_user_id = int(e.selection.key)

    # 検索内容反映関数
    def on_user_search_change(e: ft.ControlEvent):
        user_field.suggestions = filter_user_options(users, e.control.value)
        user_field.update()

    # プルダウン定義
    user_field = ft.AutoComplete(
        suggestions=filter_user_options(users, ""),
        on_select=on_user_selected,
        on_change=on_user_search_change,
    )

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
            ft.TextButton("OK", autofocus=True, on_click=lambda e: page.go("/index")),
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
                ft.TextButton("OK", autofocus=True, on_click=lambda e: page.go("/index")),
            ]
            page.open(dialog)
            return

        try:
            card_type = CardType(card_type_dropdown.value)
            register_service.register_card(card_number, card_type, selected_user_id)
        except Exception:
            logger.exception("カード登録に失敗しました: card_number=%s, user_id=%s",
                            card_number, selected_user_id)
            show_error_dialog(page, "カードの登録に失敗しました。しばらくしてから再度お試しください。")
            return

        page.close(dialog)

        dialog.title = ft.Text("登録完了")
        dialog.content = ft.Text("カードの登録が完了しました。")
        dialog.actions = [
            ft.TextButton("OK", autofocus=True, on_click=lambda e: page.go("/index")),
        ]
        page.open(dialog)

    # ボタン群定義
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

    # ページにする
    return ft.View(
        "/register/input",
        controls=[
            ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text("カード登録", size=28, weight=ft.FontWeight.BOLD),
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