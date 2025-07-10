
import flet as ft


def login(page: ft.Page):
    page.title = "ログイン画面"

    username = ft.TextField(label="ユーザー名" , autofocus=True, on_submit=lambda e: page.go("/index"))
    # username = ft.TextField(label="ユーザー名", autofocus=True, on_submit=lambda e: password.focus())

    password = ft.TextField(label="パスワード", password=True, on_submit=lambda e: page.go("/index"))
    # password = ft.TextField(label="パスワード", password=True, on_submit=lambda e: do_login(e))
    msg = ft.Text("")
    def do_login(e):
        if username.value == "admin" and password.value == "password":
            msg.value = "ログイン成功"
            page.go("/index")
            
            
        else:
            msg.value = "ログイン失敗"
            page.update()
            username.focus()
    login_btn = ft.ElevatedButton("ログイン", on_click=lambda e: page.go("/index"))
    # login_btn = ft.ElevatedButton("ログイン", on_click=do_login)

    return ft.View(
            "/",
            [
                ft.Text("ログイン", style="headlineMedium"),
                username,
                password,
                login_btn,
                msg,
            ],
        )

    