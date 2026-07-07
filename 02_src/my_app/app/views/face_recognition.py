import logging
import flet as ft
import service.db_manager as repo
import asyncio

logger = logging.getLogger(__name__)#logに書き込む用

# card管理画面

def faceView(page: ft.Page):
    #region UI
    offset = 0
    all_page = 1

    search_word = ""

    page.title = "顔認証管理画面"

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

    face_name = ft.TextField(label="登録者検索", autofocus=True,
                            on_submit=lambda e: search(e),
                            max_length=50)
    # endregion
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

    #region Refresh
    async def refresh(e):
        nonlocal search_word, offset, reset_btn
        reset_btn.disabled = True
        page.update()

        search_word = ""
        table.sort_ascending = True
        face_name.value = ""
        face_name.focus()
        offset = 0
        load_table()
        scroll_table.scroll_to(offset=0, duration=0)

        await asyncio.sleep(0.2)

        reset_btn.disabled = False
        page.update()

    async def on_refresh(e):
        await refresh(e)

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
    #endregion

    #region Search
    def search(e):
        nonlocal search_word, offset
        search_word = search_zone.controls[0].value
        offset = 0
        load_table()
        scroll_table.scroll_to(offset=0, duration=0)

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
            face_name,
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
            ft.DataColumn(ft.Text("名前_ローマ字")),
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
        nonlocal search_word, offset, all_page
        faces = repo.find_by_face_name(
            search_word, table.sort_ascending, offset * 100)
        all_page = int(((repo.count_all_face(search_word) - 1) / 100) + 1)
        checkbox_refs.clear()
        table.rows.clear()
        column.controls.clear()
        column.controls.append(ft.Container(height=-2))
        column.controls.append(ft.ElevatedButton(text="登録者名編集",
                                                data=radio_group.value, on_click=open_edit_dialog, style=ft.ButtonStyle(
                                                    shape=ft.RoundedRectangleBorder(
                                                        radius=0),)))

        for face_id, face_name, face_name_roma, register_date in faces:
            cb = ft.Checkbox()
            column.controls.append(
                ft.Radio(value=str(face_id)))

            checkbox_refs[face_id] = cb
            table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(f"{face_id:05d}", width=40)),
                        ft.DataCell(ft.Text(face_name, width=140)),
                        ft.DataCell(ft.Text(face_name_roma, width=140)),
                        ft.DataCell(ft.Text(register_date, width=80)),
                        ft.DataCell(cb),
                    ]
                )
            )

        radio_group.value = faces[0][0] if faces else None
        page_label.value = f"{offset+1} / {all_page} ページ"
        prev_btn.disabled = offset == 0
        next_btn.disabled = (offset + 1) == all_page
        page.update()
        print(f"tables!{table.sort_ascending}")
        return
    #endregion

    # 選択した行を削除するための確認ダイアログを開く関数

    #region edit
    def open_confirm_dialog(e):

        nonlocal selected_ids
        selected_ids = [face_id for face_id,
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
    # 削除の確認ダイアログのアクション
    def confirm_delete(e):
        face_datas = [repo.find_face_name_and_roma_by_id(
            face_id) for face_id in selected_ids]
        page.open(dialog)
        repo.delete_face_by_ids(selected_ids)
        page.close(dialog)
        load_table()
        dialog.title = ft.Text("削除完了")
        dialog.content = ft.Text(f"{len(selected_ids)} 件を削除しました。")
        dialog.actions = [
            ft.TextButton("閉じる", autofocus=True,
                        on_click=lambda e:  page.close(dialog)),
        ]
        for face_data in face_datas:
            logger.info(f"{face_data[1]}が削除されました")

        page.open(dialog)

    # TODO 编辑记得把图片名字也改了
    def open_edit_dialog(e):
        face_id = int(radio_group.value)
        dialog.title = ft.Text("登録者名編集")
        face_data_tuple = repo.find_face_name_and_roma_by_id(
            face_id)
        user_name = ft.TextField(
            label="登録者名", value=face_data_tuple[0], autofocus=True, max_length=50,  on_submit=lambda e: card_type.focus())
        card_type = ft.TextField(
            label="登録者名(ローマ字)", value=face_data_tuple[1], data=face_id, max_length=50, on_submit=lambda e: confirm_edit(e))

        dialog.content = ft.Column(
            [
                user_name,
                card_type

            ],
            height=80,

        )
        dialog.actions = [
            ft.TextButton("キャンセル", on_click=lambda e: page.close(dialog)),
            ft.TextButton("保存", data=face_id,
                        on_click=lambda e: confirm_edit(e)),
        ]
        page.open(dialog)




    # 変更　二つ
    def confirm_edit(e):
        face_id = e.control.data
        if not dialog.content.controls[0].value or not dialog.content.controls[1].value:
            page.close(dialog)
            dialog.content = ft.Text("入力漏れがあります")
            dialog.actions = [
                ft.TextButton(
                    "閉じる", autofocus=True, on_click=lambda e: return_edit(e)),
            ]
            page.open(dialog)
            return

        new_face_name = dialog.content.controls[0].value
        new_face_name_roma = dialog.content.controls[1].value
        old_face_data = repo.find_face_name_and_roma_by_id(face_id)
        repo.update_face_name(face_id, new_face_name,new_face_name_roma)
        page.close(dialog)
        # 編集後のテーブルを再読み込み
        load_table()

        # ダイアログを更新して完了メッセージを表示
        dialog.title = ft.Text("編集完了")
        dialog.content = ft.Text(
            f"登録者名を '{old_face_data[0]}'から'{new_face_name}' に変更しました\n" +
            f"登録者名ローマ字を '{old_face_data[1]}'から'{new_face_name_roma}' に変更しました"
        )
        dialog.actions = [
            ft.TextButton("閉じる", autofocus=True,
                        on_click=lambda e: page.close(dialog)),
        ]
        logging.info(
            f"登録者名を '{old_face_data[0]}'から'{new_face_name}' に変更しました")
        page.open(dialog)

    def return_edit(e):
        page.close(dialog)
        open_edit_dialog(e)
    # 検索ボタンのクリックイベント
    #endregion


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


    load_table()
    return ft.View(
        "/face_recognition",
        controls=[
            search_zone_row,
            ft.Text("登録者一覧", size=30, weight=ft.FontWeight.BOLD),
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
