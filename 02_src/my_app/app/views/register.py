import flet as ft
import asyncio
import app.models.db_manager as db
import requests
from app.utils.thread_state import thread_handle, stop_event


def registering(page: ft.Page):
    global stop_event, thread_handle

    def stop_loop(e):

        stop_event.set()
        print("停止フラグを送信しました")
        page.go("/index")

    url = "http://127.0.0.1:5000/api/card/set_state"
    data = {"state": "registering"}
    response = requests.post(url, json=data)
    print("set_stateの返り値：", response.json())

    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.title = "ICカード情報読み込み中"

    loading_text = ft.Text("ICカード情報読み込み中", size=60,
                           text_align=ft.TextAlign.CENTER)
    loading_spinner = ft.CupertinoActivityIndicator(
        radius=50,
        color=ft.Colors.LIGHT_BLUE_ACCENT,
        animating=True,
    )

    stop_btn = ft.Container(
        content=ft.TextButton(
            text="キャンセル",
            icon=ft.Icons.STOP,
            on_click=stop_loop,
            style=ft.ButtonStyle(
                padding=ft.padding.symmetric(horizontal=20, vertical=10),
                shape=ft.RoundedRectangleBorder(radius=10),

            )
        )
    )
    return ft.View(
        "/home",
        controls=[
            ft.Container(
                expand=True,
                alignment=ft.alignment.center,
                content=ft.Column(
                    controls=[
                        ft.Container(content=loading_text, padding=10),
                        ft.Container(content=loading_spinner),
                        stop_btn

                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True,
                ),
            )
        ],
    )


async def delayed_transition(page: ft.Page):

    global stop_event

    requests.get("http://127.0.0.1:5000/api/card/get_card",
                 params={"card_id": "0"})
    while not stop_event.is_set():
        res = requests.get("http://127.0.0.1:5000/api/card/get_card")
        card_id = res.json().get("card_id", "0")
        print("カードID：", card_id)
        if card_id != None:

            url = "http://127.0.0.1:5000/api/card/set_state"
            data = {"state": "authenticating"}
            requests.post(url, json=data)
            page.go("/register/input")
            break
        await asyncio.sleep(0.5)


def run_async_delayed_transition(page):
    asyncio.run(delayed_transition(page))


def register_input(page: ft.Page):

    add_confirm_dialog = ft.AlertDialog(
        modal=True,
    )
    res = requests.get(
        "http://127.0.0.1:5000/api/card/get_card")
    card_number = res.json().get("card_id", "0")

    def open_add_confirm_dialog(e):
        add_confirm_dialog.title = ft.Text("カード登録の確認")
        add_confirm_dialog.content = ft.Text(
            f"ユーザー名: {card_name.value}、カードの種類: {card_name_type.value} を登録しますか？")
        add_confirm_dialog.actions = [
            ft.TextButton("はい", on_click=lambda e: execute_register(e)),
            ft.TextButton("いいえ", autofocus=True,
                          on_click=lambda e: page.close(add_confirm_dialog)),
        ]
        page.open(add_confirm_dialog)

    def open_cancel_confirm_dialog(e):
        add_confirm_dialog.title = ft.Text("キャンセル確認")
        add_confirm_dialog.content = ft.Text("登録をキャンセルしますか？")
        add_confirm_dialog.actions = [
            ft.TextButton(
                "はい", on_click=lambda e: complete_cancel_confirm_dialog(e)),
            ft.TextButton("いいえ", autofocus=True,
                          on_click=lambda e: page.close(add_confirm_dialog)),
        ]
        page.open(add_confirm_dialog)

    def complete_add_confirm_dialog(e):
        add_confirm_dialog.title = ft.Text("登録完了")
        add_confirm_dialog.content = ft.Text("カードの登録が完了しました。")
        add_confirm_dialog.actions = [
            ft.TextButton("OK", autofocus=True,
                          on_click=lambda e: page.go("/index")),
        ]
        page.open(add_confirm_dialog)

    def complete_cancel_confirm_dialog(e):
        page.close(add_confirm_dialog)
        add_confirm_dialog.title = ft.Text("キャンセル完了")
        add_confirm_dialog.content = ft.Text("カードの登録がキャンセルされました。")
        add_confirm_dialog.actions = [
            ft.TextButton("OK", autofocus=True,
                          on_click=lambda e: page.go("/index")),
        ]
        page.open(add_confirm_dialog)

    def execute_register(e):

        db.insertCard(
            (card_name.value + '_' + card_name_type.value), card_number)

        page.close(add_confirm_dialog)
        complete_add_confirm_dialog(e)

    card_name = ft.TextField(
        label="ユーザー名", autofocus=True, on_submit=lambda e: card_name_type.focus())
    card_name_type = ft.TextField(
        label="カードの種類", value="ICカード", on_submit=lambda e: open_add_confirm_dialog(e))

    return ft.View(
        "/register/input",
        [
            ft.Text("カード登録画面", style="headlineMedium"),
            ft.Text("カード名を入力してください"),
            card_name,
            card_name_type,
            ft.ElevatedButton(
                "登録", on_click=lambda e: open_add_confirm_dialog(e)),
            ft.ElevatedButton("キャンセル", on_click=lambda e: open_cancel_confirm_dialog(
                e), color=ft.Colors.RED),
            # ft.ElevatedButton("戻る", on_click=lambda e: page.go("/index")),
        ]
    )
