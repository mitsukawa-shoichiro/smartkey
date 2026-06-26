import logging
import flet as ft
import service.db_manager as db
import asyncio
import sqlite3
# card管理画面

logger = logging.getLogger(__name__)

def cardView(page: ft.Page):

    try:

        offset = 0
        all_page = 1

        serch_word = ""

        page.title = "card管理画面"

        # チェックボックスの参照を保持する辞書
        checkbox_refs = {}

        # 選択されたカードのIDを保持するリスト
        selected_ids = []

        dialog = ft.AlertDialog(
            modal=True,
        )

        column = ft.Column(
            controls=[],
            spacing=16,
            expand=True,
        )

        radio_group = ft.RadioGroup(
            content=column,
            on_change=lambda e: print(f"選ばれたID: {radio_group.value}")
        )

        card_name = ft.TextField(label="カード名検索", autofocus=True,
                                on_submit=lambda e: search(e),
                                max_length=50)
        search_btn = ft.ElevatedButton(
            content=ft.Icon(ft.Icons.SEARCH, size=30, color=ft.Colors.WHITE),
            on_click=lambda e: search(e),
            width=40,
            height=48,
            bgcolor=ft.Colors.LIGHT_BLUE,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(
                    radius=0),
                padding=ft.padding.all(0)
            ),
        )

        async def reflesh(e):
            nonlocal serch_word, offset, reset_btn
            reset_btn.disabled = True
            page.update()

            serch_word = ""
            table.sort_ascending = True
            card_name.value = ""
            card_name.focus()
            offset = 0
            load_table()
            scroll_table.scroll_to(offset=0, duration=0)

            await asyncio.sleep(0.2)

            reset_btn.disabled = False
            page.update()

        async def on_refresh(e):
            await reflesh(e)

        async def sort_table(e):
            nonlocal offset
            table.sort_ascending = not table.sort_ascending
            offset = 0
            scroll_table.visible = False
            scroll_table.update()
            await asyncio.sleep(0.01)
            scroll_table.visible = True
            scroll_table.update()
            load_table()

        async def on_sort(e):
            await sort_table(e)

        reset_btn = ft.ElevatedButton(content=ft.Text(value="リセット", size=14, color=ft.Colors.RED),
                                    on_click=on_refresh,
                                    bgcolor=ft.Colors.RED_50,
                                    width=60,
                                    height=30,
                                    style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(
                radius=0),
            padding=ft.padding.all(0)
        ),)

        search_zone = ft.Row(
            controls=[
                card_name,
                search_btn
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=0
        )
        search_zone_row = ft.Row(
            controls=[
                search_zone,
                reset_btn,
            ],
            alignment=ft.MainAxisAlignment.START,
            spacing=50

        )
        prev_btn = ft.ElevatedButton("⬅ 前へ",   on_click=lambda e: prev_page(
            e), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)))
        page_label = ft.Text("")  # 後で更新
        next_btn = ft.ElevatedButton("次へ ➡",   on_click=lambda e: next_page(
            e), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)))
        btn_zone = ft.Row([prev_btn, page_label, next_btn],
                        alignment=ft.MainAxisAlignment.CENTER)

        # カードの一覧を表示するためのテーブル
        table = ft.DataTable(
            columns=[

                ft.DataColumn(ft.Text("ID"), on_sort=on_sort),
                ft.DataColumn(ft.Text("名前")),
                # ft.DataColumn(ft.Text("カード番号")),
                ft.DataColumn(ft.Text("登録日")),
                ft.DataColumn(ft.ElevatedButton(
                    "行を削除", on_click=lambda e: open_confirm_dialog(e), style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(
                            radius=0),)))
            ],
            rows=[],

            sort_column_index=0,
            sort_ascending=True,
        )

        def prev_page(e):
            nonlocal offset, all_page
            if offset != 0:
                offset -= 1
            load_table()
            scroll_table.scroll_to(offset=0, duration=0)

        def next_page(e):
            nonlocal offset, all_page
            if (offset + 1) != all_page:
                offset += 1
            load_table()
            scroll_table.scroll_to(offset=0, duration=0)

        # テーブルの行をロードする関数

        def load_table():
            nonlocal serch_word, offset, all_page
            cards = db.find_by_card_name(
                serch_word, table.sort_ascending, offset * 100)
            all_page = int(((db.count_all_card(serch_word)[0] - 1) / 100) + 1)
            checkbox_refs.clear()
            table.rows.clear()
            column.controls.clear()
            column.controls.append(ft.Container(height=-2))
            column.controls.append(ft.ElevatedButton(text="カード名編集",
                                                    data=radio_group.value, on_click=open_edit_dialog, style=ft.ButtonStyle(
                                                        shape=ft.RoundedRectangleBorder(
                                                            radius=0),)))

            for card_id, card_name, card_number, register_date in cards:
                cb = ft.Checkbox()
                column.controls.append(
                    ft.Radio(value=str(card_id)))

                checkbox_refs[card_id] = cb
                table.rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(f"{card_id:05d}", width=40)),
                            ft.DataCell(ft.Text(card_name, width=280)),
                            ft.DataCell(ft.Text(register_date, width=80)),
                            ft.DataCell(cb),
                        ]
                    )
                )

            radio_group.value = cards[0][0] if cards else None
            page_label.value = f"{offset+1} / {all_page} ページ"
            prev_btn.disabled = offset == 0
            next_btn.disabled = (offset + 1) == all_page
            page.update()
            print(f"tables!{table.sort_ascending}")
            return

        # 選択した行を削除するための確認ダイアログを開く関数

        def open_confirm_dialog(e):

            nonlocal selected_ids
            selected_ids = [card_id for card_id,
                            cb in checkbox_refs.items() if cb.value]

            if not selected_ids:
                dialog.title = ft.Text("削除の確認")
                dialog.content = ft.Text("削除する行が選択されていません。")
                dialog.actions = [
                    ft.TextButton("閉じる", autofocus=True,
                                on_click=lambda e: page.close(dialog)),
                ]
                page.open(dialog)

            else:
                dialog.title = ft.Text("削除の確認")
                dialog.content = ft.Text(f"{len(selected_ids)} 件を削除しますか？")
                dialog.actions = [
                    ft.TextButton("キャンセル", autofocus=True,
                                on_click=lambda e: page.close(dialog)),
                    ft.TextButton("はい", on_click=confirm_delete),
                ]
                page.open(dialog)

        # カード名を編集するためのダイアログを開く関数
        def open_edit_dialog(e):
            card_id = int(radio_group.value)
            dialog.title = ft.Text("カード名編集")
            card_name = db.find_card_name_by_id(
                card_id)
            name_and_type = card_name[0].split("_")
            user_name = ft.TextField(
                label="ユーザー名", value=name_and_type[0], autofocus=True, max_length=50,  on_submit=lambda e: card_type.focus())
            card_type = ft.TextField(
                label="カードの種類", value=name_and_type[1], data=card_id, max_length=50, on_submit=lambda e: confirm_edit(e))

            dialog.content = ft.Column(
                [
                    user_name,
                    card_type

                ],
                height=80,

            )
            dialog.actions = [
                ft.TextButton("キャンセル", on_click=lambda e: page.close(dialog)),
                ft.TextButton("保存", data=card_id,
                            on_click=lambda e: confirm_edit(e)),
            ]
            page.open(dialog)

        # 削除の確認ダイアログのアクション
        def confirm_delete(e):
            card_names = [db.find_card_name_by_id(
                card_id) for card_id in selected_ids]
            page.open(dialog)
            db.delete_card_by_ids(selected_ids)
            page.close(dialog)
            load_table()
            dialog.title = ft.Text("削除完了")
            dialog.content = ft.Text(f"{len(selected_ids)} 件を削除しました。")
            dialog.actions = [
                ft.TextButton("閉じる", autofocus=True,
                            on_click=lambda e:  page.close(dialog)),
            ]
            for card_name in card_names:
                logger.info(f"{card_name[0]}が削除されました")

            page.open(dialog)

        # カード名を編集するためのダイアログのアクション
        def confirm_edit(e):
            card_id = e.control.data
            if not dialog.content.controls[0].value or not dialog.content.controls[1].value:
                page.close(dialog)
                dialog.content = ft.Text("入力漏れがあります")
                dialog.actions = [
                    ft.TextButton(
                        "閉じる", autofocus=True, on_click=lambda e: return_edit(e)),
                ]
                page.open(dialog)
                return

            new_card_name = dialog.content.controls[0].value + \
                "_" + dialog.content.controls[1].value
            old_card_name = db.find_card_name_by_id(card_id)
            db.update_card_name(card_id, new_card_name)
            page.close(dialog)
            # 編集後のテーブルを再読み込み
            load_table()

            # ダイアログを更新して完了メッセージを表示
            dialog.title = ft.Text("編集完了")
            dialog.content = ft.Text(
                f"カード名を '{old_card_name[0]}'から'{new_card_name}' に変更しました")
            dialog.actions = [
                ft.TextButton("閉じる", autofocus=True,
                            on_click=lambda e: page.close(dialog)),
            ]
            logger.info(
                f"カード名を '{old_card_name[0]}'から'{new_card_name}' に変更しました")
            page.open(dialog)

        def return_edit(e):
            page.close(dialog)
            open_edit_dialog(e)
        # 検索ボタンのクリックイベント

        def search(e):
            nonlocal serch_word, offset
            serch_word = search_zone.controls[0].value
            offset = 0
            load_table()
            scroll_table.scroll_to(offset=0, duration=0)

        table_radio_box = ft.Row([
            table,
            ft.Container(width=0),  # テーブルとラジオボタンの間のスペース
            radio_group
        ], vertical_alignment=ft.CrossAxisAlignment.START)

        scroll_table = ft.Column(
            controls=[table_radio_box],
            scroll=ft.ScrollMode.ALWAYS,
            expand=True,

        )

        try:
            load_table()
        except sqlite3.Error as e:
            logger.error(f"カードテーブルの読み込みに失敗しました: {e}")
            page.go("/index?error=カードテーブルの読み込みに失敗しました")

        return ft.View(
            "/card",
            controls=[
                search_zone_row,
                ft.Text("カード一覧", size=30, weight=ft.FontWeight.BOLD),
                ft.Container(height=10),
                scroll_table,
                btn_zone,
                ft.Container(height=10),
                ft.ElevatedButton(
                    "戻る",
                    icon=ft.Icons.ARROW_BACK,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=6),
                    ),
                    on_click=lambda e: page.go("/index"),
                )

            ],
            padding=ft.Padding(left=120, top=20, right=0, bottom=50)


        )
    except Exception as e:
        logger.exception("カード管理画面の表示中にエラーが発生しました: %s", e)
        page.go("/index?error=カード管理画面の表示中にエラーが発生しました")
    finally:
        page.update()