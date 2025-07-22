import flet as ft
import asyncio
import app.models.db_manager as db
import logging
from service.card_sys import set_state, get_state, get_card
from app.utils.thread_state import thread_handle, stop_event
import service.db_manager as service_db


def registering(page: ft.Page):
    global stop_event, thread_handle

    def stop_loop(e):

        stop_event.set()
        set_state("authenticating")
        logging.info("set_stateの返り値：%s", get_state())
        page.go("/index")

    set_state("registering")
    print("set_stateの返り値：", get_state())

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
                shape=ft.RoundedRectangleBorder(radius=10),
                color=ft.Colors.RED,
                overlay_color=ft.Colors.RED_100,
            )
        )
    )
    return ft.View(
        "/register",
        controls=[
            ft.Container(
                expand=True,
                alignment=ft.alignment.center,
                content=ft.Column(
                    controls=[
                        ft.Container(content=loading_text, padding=10),
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


async def delayed_transition(page: ft.Page):

    global stop_event
    dialog = ft.AlertDialog(
        modal=True,
        content=ft.Text("このカードは既に登録されています"),
        actions=[
            ft.TextButton("戻る", autofocus=True,
                          on_click=lambda e: page.go("/index"))
        ]
    )

    while not stop_event.is_set():
        card_number = get_card()
        print("カード番号：", card_number)
        if card_number != "":
            if not service_db.check_card(card_number):
                set_state("authenticating")
                logging.info("set_stateの返り値：%s", get_state())
                page.go("/register/input")
                break
            else:
                page.open(dialog)
                set_state("authenticating")
                logging.info("set_stateの返り値：%s", get_state())
                break

        await asyncio.sleep(1)


def run_async_delayed_transition(page):
    asyncio.run(delayed_transition(page))


def register_input(page: ft.Page):
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    button_column = ft.Column(
        controls=[
            ft.ElevatedButton(
                "登録",
                icon=ft.Icons.CHECK,
                width=200,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=6),
                ),
                on_click=lambda e: open_add_confirm_dialog(e),
            ),
            ft.ElevatedButton(
                "キャンセル",
                icon=ft.Icons.ARROW_BACK,
                width=200,
                color=ft.Colors.RED,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=6),
                ),
                on_click=lambda e: open_cancel_confirm_dialog(e),
            ),
        ],
        spacing=20,
        alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    add_confirm_dialog = ft.AlertDialog(
        modal=True,
    )

    card_number = get_card()

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

        db.insert_card(
            (card_name.value + '_' + card_name_type.value), card_number)

        page.close(add_confirm_dialog)
        complete_add_confirm_dialog(e)

    card_name = ft.TextField(
        label="ユーザー名", autofocus=True, width=320, border_radius=8, on_submit=lambda e: card_name_type.focus())
    card_name_type = ft.TextField(
        label="カードの種類", width=320, border_radius=8, on_submit=lambda e: open_add_confirm_dialog(e))

    return ft.View(
        "/register/input",
        controls=[
            ft.Row(  # 横方向の中央寄せ用
                controls=[
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text("ユーザー登録", size=28,
                                        weight=ft.FontWeight.BOLD),
                                card_name,
                                card_name_type,
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
                alignment=ft.MainAxisAlignment.CENTER,  # 横中央
                expand=True,
            )
        ]
    )
