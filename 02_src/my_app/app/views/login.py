import flet as ft
import json
import os
import logging


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
    page.title = "ログイン画面"

    username = ft.TextField(label="ユーザー名", autofocus=True,
                            on_submit=lambda e: password.focus(),
                            max_length=50)

    password = ft.TextField(label="パスワード", password=True,
                            on_submit=lambda e: do_login(e),
                            max_length=50)

    msg = ft.Text("", color=ft.Colors.RED)
    msg_container = ft.Container(
        visible=False,
        content=msg,
        bgcolor=ft.Colors.RED_50,
        border=ft.border.all(1, ft.Colors.RED),
        padding=10,
        border_radius=ft.border_radius.all(5),
    )

    def do_login(e):
        for account in load_accounts():
            print(len(username.value))
            if account["username"] == username.value and account["password"] == password.value:
                logging.info("ログイン成功")
                page.go("/index")
                page.update()
                return

            else:
                msg.value = "ユーザー名またはパスワードが間違っています。"
                msg_container.visible = True
                logging.warning("ログイン失敗")
                page.update()
                username.focus()

    login_btn = ft.ElevatedButton("ログイン",
                                  on_click=do_login,
                                  icon=ft.Icons.LOGIN,
                                  style=ft.ButtonStyle(
                                      shape=ft.RoundedRectangleBorder(
                                          radius=4),
                                      overlay_color=ft.Colors.BLUE_50,
                                  )
                                  )

    return ft.View(
        "/",
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("ログイン", style="headlineMedium"),
                        msg_container,
                        username,
                        password,
                        login_btn,
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20,
                ),
                width=400,
                height=300,
                padding=30,
                alignment=ft.alignment.center,
                margin=ft.Margin(0, -100, 0, 0),
            )
        ],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )
