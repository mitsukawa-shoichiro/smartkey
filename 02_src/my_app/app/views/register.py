import flet as ft
import asyncio
import app.models.db_manager as db
# デモのために乱数を使用
import random


def registering(page: ft.Page):
    return ft.View(
        "/register",
        [
            ft.Text("登録中...", style="headlineMedium"),
        ]
    )

async def delayed_transition(page: ft.Page):
    for count in range(1):
        print(f"{count + 1}回目のチェック")
        await asyncio.sleep(0.5)
    page.go("/register/input")

def run_async_delayed_transition(page):
    asyncio.run(delayed_transition(page))

def register_input(page: ft.Page):
    
    add_confirm_dialog = ft.AlertDialog(
        modal=True, 
        )
    card_number = random.randint(1000000000, 9999999999)  # デモ用のランダムなカード番号

    def open_add_confirm_dialog(e):
        add_confirm_dialog.title = ft.Text("カード登録の確認")
        add_confirm_dialog.content = ft.Text(f"ユーザー名: {card_name.value}、カードの種類: {card_name_type.value} を登録しますか？")
        add_confirm_dialog.actions = [
            ft.TextButton("はい", on_click=lambda e: execute_register(e)),
            ft.TextButton("いいえ", autofocus=True, on_click=lambda e: page.close(add_confirm_dialog)),
        ]
        page.open(add_confirm_dialog)

    def complete_add_confirm_dialog(e):
        add_confirm_dialog.title = ft.Text("登録完了")
        add_confirm_dialog.content = ft.Text("カードの登録が完了しました。")
        add_confirm_dialog.actions = [
            ft.TextButton("OK", autofocus=True, on_click=lambda e: page.go("/index")),
        ]
        page.open(add_confirm_dialog)

    def execute_register(e):
        
        db.insertCard((card_name.value + '_' + card_name_type.value), card_number)
        
        page.close(add_confirm_dialog)
        complete_add_confirm_dialog(e)

    card_name = ft.TextField(label="ユーザー名", autofocus=True, on_submit= lambda e: card_name_type.focus())
    card_name_type = ft.TextField(label="カードの種類", value="ICカード", on_submit= lambda e: open_add_confirm_dialog(e))
    
    return ft.View(
        "/register/input",
        [
            ft.Text("カード登録画面", style="headlineMedium"),
            ft.Text("カード名を入力してください"),
            card_name,
            card_name_type,
            ft.ElevatedButton("登録", on_click=lambda e: open_add_confirm_dialog(e)),
            ft.ElevatedButton("戻る", on_click=lambda e: page.go("/index")),
        ]
    )