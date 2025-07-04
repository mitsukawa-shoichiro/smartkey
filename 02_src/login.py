
import flet as ft


def login(page: ft.Page):
    username = ft.TextField(label="ユーザー名")
    password = ft.TextField(label="パスワード", password=True)
    msg = ft.Text("")
    def do_login(e):
        if username.value == "admin" and password.value == "password":
            #ft.page.session.set("user", {"username": username.value})
            msg.value = "ログイン成功"
            page.go("/index")
            
            
        else:
            msg.value = "ログイン失敗"
            page.update()
    login_btn = ft.ElevatedButton("ログイン", on_click=do_login)

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

    