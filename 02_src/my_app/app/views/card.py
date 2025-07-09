import flet as ft
import app.models.db_manager as db

def cardView(page: ft.Page):
    page.title = "card管理画面"

    username = ft.TextField(label="ユーザー名" , on_submit=lambda e: search(e))

    checkbox_refs = {}  # id: checkbox
    selected_ids = []

    confirm_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("削除の確認"),
        content=ft.Text(""),
        actions_alignment=ft.MainAxisAlignment.END,
    )

    edit_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("カード名編集"),
        content=ft.Column(
            
            spacing=3,
        ), 
        actions=[
        ],
        
    )

    table = ft.DataTable(
        columns=[
            
            ft.DataColumn(ft.Text("ID")),
            ft.DataColumn(ft.Text("名前")),
            ft.DataColumn(ft.Text("カード番号")),
            ft.DataColumn(ft.Text("登録日")),
            ft.DataColumn(ft.Text("選択")),
            ft.DataColumn(ft.Text("")),
        ],
        rows=[],
    )

    def load_table():
        checkbox_refs.clear()
        table.rows.clear()
        cards = db.findAllCard()

        for card_id, card_name, card_number, register_date in cards:
            cb = ft.Checkbox()
            checkbox_refs[card_id] = cb
            table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(card_id))),
                        ft.DataCell(ft.Text(card_name)),
                        ft.DataCell(ft.Text(card_number)),
                        ft.DataCell(ft.Text(register_date)),
                        ft.DataCell(cb),
                        ft.DataCell(ft.TextButton(text="カード名編集",data=card_id, on_click = open_edit_dialog)),
                    ]
                )
            )
        page.update()

    def open_confirm_dialog(e):
        nonlocal selected_ids
        selected_ids = [card_id for card_id, cb in checkbox_refs.items() if cb.value]
        if not selected_ids:
            snack = ft.SnackBar(ft.Text("何も選択されていません"))
            page.open(snack)
            page.update()
            return

        confirm_dialog.content = ft.Text(f"{len(selected_ids)} 件を削除しますか？")
        confirm_dialog.actions = [
            ft.TextButton("キャンセル", on_click=lambda e: page.close(confirm_dialog)),
            ft.TextButton("はい", on_click=confirm_delete),
        ]
        page.open(confirm_dialog)

    def open_edit_dialog(e):
        card_id = e.control.data
        
        edit_dialog.content = ft.Column(
            [
                ft.TextField(label="カード名", value=db.findCardNameById(card_id), data = card_id, autofocus=True, on_submit=lambda e: confirm_edit(e)),
            ],
            spacing=10,
        )
        edit_dialog.actions = [
            ft.TextButton("キャンセル", on_click=lambda e: page.close(edit_dialog)),
            ft.TextButton("保存", data = card_id, on_click=lambda e: confirm_edit(e)),
        ]
        page.open(edit_dialog)

    def confirm_delete(e):
        db.deleteByIds(selected_ids)
        page.close(confirm_dialog)
        snack = ft.SnackBar(ft.Text("削除しました"))
        page.open(snack)
        load_table()

    def confirm_edit(e):
        card_id = e.control.data
        new_card_name = edit_dialog.content.controls[0].value
        db.updateCardName(card_id, new_card_name)
        page.close(edit_dialog)
        snack = ft.SnackBar(ft.Text("カード名を更新しました"))
        page.open(snack)
        load_table()

    def search(e):
        card_name = username.value.strip()
       
        cards = db.findByCardName(card_name)
        table.rows.clear()
        for card_id, card_name, card_number, register_date in cards:
            cb = ft.Checkbox()
            checkbox_refs[card_id] = cb
            table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(card_id))),
                        ft.DataCell(ft.Text(card_name)),
                        ft.DataCell(ft.Text(card_number)),
                        ft.DataCell(ft.Text(register_date)),
                        ft.DataCell(cb),
                        ft.DataCell(ft.TextButton(text="カード名編集",data=card_id, on_click = open_edit_dialog)),
                    ]
                )
            )
        page.update()
        
    load_table()

    return ft.View(
            "/card",
            [
                username,
                ft.ElevatedButton("検索", on_click=search),
                table,
                ft.ElevatedButton("選択した行を削除", on_click=open_confirm_dialog),
                ft.ElevatedButton("戻る", on_click=lambda e: page.go("/index")),
                
            ],
        )
   