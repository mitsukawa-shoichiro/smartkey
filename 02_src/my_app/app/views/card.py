import flet as ft
import app.models.db_manager as db


def cardView(page: ft.Page):
    page.title = "DataTable + Checkbox 削除"

    checkbox_refs = {}  # id: checkbox
    selected_ids = []

    confirm_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("削除の確認"),
        content=ft.Text(""),
        actions_alignment=ft.MainAxisAlignment.END,
    )

    table = ft.DataTable(
        columns=[
            
            ft.DataColumn(ft.Text("ID")),
            ft.DataColumn(ft.Text("名前")),
            ft.DataColumn(ft.Text("カード番号")),
            ft.DataColumn(ft.Text("登録日")),
            ft.DataColumn(ft.Text("選択")),
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
                    ]
                )
            )
        page.update()

    def open_confirm_dialog(e):
        nonlocal selected_ids
        selected_ids = [card_id for card_id, cb in checkbox_refs.items() if cb.value]
        if not selected_ids:
            page.snack_bar = ft.SnackBar(ft.Text("何も選択されていません"))
            page.snack_bar.open = True
            page.update()
            return

        confirm_dialog.content = ft.Text(f"{len(selected_ids)} 件を削除しますか？")
        confirm_dialog.actions = [
            ft.TextButton("キャンセル", on_click=lambda e: page.close(confirm_dialog)),
            ft.TextButton("はい", on_click=confirm_delete),
        ]
        page.open(confirm_dialog)

    def confirm_delete(e):
        db.deleteByIds(selected_ids)
        page.close(confirm_dialog)
        page.snack_bar = ft.SnackBar(ft.Text("削除しました"))
        page.snack_bar.open = True
        load_table()

    load_table()
    return ft.View(
            "/card",
            [
                table,
                ft.ElevatedButton("選択した行を削除", on_click=open_confirm_dialog),
                ft.ElevatedButton("戻る", on_click=lambda e: page.go("/index")),
                
            ],
        )
   