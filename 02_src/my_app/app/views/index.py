import flet as ft

def index_view(page: ft.Page):

    return ft.View(
            "/index",
            [
                ft.Text("ドア開閉システム管理画面", style="headlineMedium"),
                ft.ElevatedButton("カード管理", on_click=lambda e: page.go("/card")),
                ft.ElevatedButton("ログ管理", on_click=lambda e: page.go("/accesslogs")),
                ft.ElevatedButton("カード登録", on_click=lambda e: page.go("/register")),
                ft.ElevatedButton("ログアウト", on_click=lambda e: page.go("/")),
            ]
        )