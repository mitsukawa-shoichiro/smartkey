import flet as ft
import app.models.db_manager as db

# card管理画面
def cardView(page: ft.Page):
    page.title = "card管理画面"

    # チェックボックスの参照を保持する辞書
    checkbox_refs = {}

    # 選択されたカードのIDを保持するリスト  
    selected_ids = []

    dialog = ft.AlertDialog(
        modal=True,
    )
    # ユーザー名の入力フィールド
    username = ft.TextField(label="カード名", autofocus=True, on_submit=lambda e: search(e))

    # カードの一覧を表示するためのテーブル
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

    # テーブルの行をロードする関数
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

    # 選択した行を削除するための確認ダイアログを開く関数
    def open_confirm_dialog(e):
        
        nonlocal selected_ids
        selected_ids = [card_id for card_id, cb in checkbox_refs.items() if cb.value]
        
        if not selected_ids:
            dialog.title = ft.Text("削除の確認")
            dialog.content = ft.Text("削除する行が選択されていません。")
            dialog.actions = [
                ft.TextButton("閉じる", on_click=lambda e: page.close(dialog)),
            ]
            page.open(dialog)
            
        else:
            dialog.title = ft.Text("削除の確認")
            dialog.content = ft.Text(f"{len(selected_ids)} 件を削除しますか？")
            dialog.actions = [
                ft.TextButton("キャンセル", on_click=lambda e: page.close(dialog)),
                ft.TextButton("はい", on_click=confirm_delete),
            ]
            page.open(dialog)

    # カード名を編集するためのダイアログを開く関数
    def open_edit_dialog(e):
        card_id = e.control.data
        dialog.title = ft.Text("カード名編集")
        dialog.content = ft.Column(
            [
                ft.TextField(label="カード名", value=db.findCardNameById(card_id), data = card_id, autofocus=True, on_submit=lambda e: confirm_edit(e),),
            
            ],
            height=80,
            
        )
        dialog.actions = [
            ft.TextButton("キャンセル", on_click=lambda e: page.close(dialog)),
            ft.TextButton("保存", data = card_id, on_click=lambda e: confirm_edit(e)),
        ]
        page.open(dialog)

    # 削除の確認ダイアログのアクション
    def confirm_delete(e):
        db.deleteByIds(selected_ids)
        page.close(dialog)
        load_table()
        dialog.title = ft.Text("削除完了")
        dialog.content = ft.Text(f"{len(selected_ids)} 件を削除しました。")
        dialog.actions = [
            ft.TextButton("閉じる", on_click=lambda e: page.close(dialog)),
        ]
        page.open(dialog)

    # カード名を編集するためのダイアログのアクション
    def confirm_edit(e):
        card_id = e.control.data
        new_card_name = dialog.content.controls[0].value
        db.updateCardName(card_id, new_card_name)
        page.close(dialog)
        # 編集後のテーブルを再読み込み
        load_table()

        # ダイアログを更新して完了メッセージを表示
        dialog.title = ft.Text("編集完了")
        dialog.content = ft.Text(f"カード名を '{new_card_name}' に変更しました  。")
        dialog.actions = [
            ft.TextButton("閉じる", on_click=lambda e: page.close(dialog)),
        ]
        page.open(dialog)
        
    # 検索ボタンのクリックイベント
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
    scroll_table = ft.Column(
        controls=[table],
        scroll=ft.ScrollMode.ALWAYS,
        expand=True
    )

    return ft.View(
            "/card",
            [
                username,
                ft.ElevatedButton("検索", on_click=search),
                scroll_table,
                ft.ElevatedButton("選択した行を削除", on_click=open_confirm_dialog),
                ft.ElevatedButton("戻る", on_click=lambda e: page.go("/index")),
                
            ],
        )
   