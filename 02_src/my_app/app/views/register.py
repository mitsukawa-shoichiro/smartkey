import flet as ft
import asyncio

def registering(page: ft.Page):
    return ft.View(
        "/register",
        [
            ft.Text("登録中...", style="headlineMedium"),
        ]
    )

async def delayed_transition(page: ft.Page):
    for count in range(5):
        print(f"{count + 1}回目のチェック")
        await asyncio.sleep(3)
    page.go("/register/input")

def run_async_delayed_transition(page):
    asyncio.run(delayed_transition(page))

def register_input(page: ft.Page):
    
    card_name = ft.TextField(label="カード名", autofocus=True, on_submit= lambda e: card_name_type.focus(e))
    card_name_type = ft.TextField(label="カードの種類", value="ICカード", on_submit= lambda e: page.go("/index"))
    
    return ft.View(
        "/register/input",
        [
            ft.Text("カード登録画面", style="headlineMedium"),
            ft.Text("カード名を入力してください"),
            card_name,
            card_name_type,
            ft.ElevatedButton("登録完了", on_click=lambda e: page.go("/index")),
            ft.ElevatedButton("戻る", on_click=lambda e: page.go("/index")),
        ]
    )