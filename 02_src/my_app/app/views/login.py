
import flet as ft
import json
import os

def load_accounts():
    dir_path = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

    ACCOUNT_PATH = os.path.join(dir_path,"config", "account.json")
    with open(ACCOUNT_PATH) as f:
        return json.load(f)
    
def login(page: ft.Page):
    page.title = "ログイン画面"

    # username = ft.TextField(label="ユーザー名" , autofocus=True, on_submit=lambda e: page.go("/index"))
    username = ft.TextField(label="ユーザー名", autofocus=True, on_submit=lambda e: password.focus())

    # password = ft.TextField(label="パスワード", password=True, on_submit=lambda e: page.go("/index"))
    password = ft.TextField(label="パスワード", password=True, on_submit=lambda e: do_login(e))
    msg = ft.Text("")
    def do_login(e):
        for account in load_accounts():
            if account["username"] == username.value and account["password"] == password.value:
                msg.value = "ログイン成功"
                page.go("/index")
                page.update()
                return
            
            else:
                msg.value = "ログイン失敗"
                page.update()
                username.focus()
    
    # login_btn = ft.ElevatedButton("ログイン", on_click=lambda e: page.go("/index"))
    login_btn = ft.ElevatedButton("ログイン", on_click=do_login)

    return ft.View(
            "/",
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("ログイン", style="headlineMedium"),
                        username,
                        password,
                        login_btn,
                        msg,
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
