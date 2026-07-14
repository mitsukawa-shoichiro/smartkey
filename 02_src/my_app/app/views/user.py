"""
カードまたは顔写真を登録したユーザーの名前を一覧表示
ホーム画面に戻る機能の実装
"""
import flet as ft
import logging
import asyncio
import sqlite3
import db.repository as repo
from my_app.app.views.common import show_error_dialog


logger = logging.getLogger(__name__)

        #UIコントロールの定義
def userView(page: ft.page):
    # ===================================================
    # 状態変数
    # ===================================================
    offset = 0                     # 現在のページ番号(0始まり)
    all_page = 1                   # 全ページ数

    selected_user_id = None
    search_text = ""


    page.title = "ユーザ管理画面"
    #=====================================================
    #ユーザー検索
    #=====================================================
    def search():
        nonlocal search_text, offset

        search_text = search_box.value.strip()
        offset = 0

        load_table()

    #検索窓
    search_box = ft.Textfield(
        label = "名前・カナ氏名",
        hint_text = "部分一致検索",
        width = 300,
        on_submit = lambda e: search(),
    )
    #検索ボタン
    search_button = ft.ElevatedButton(
        "検索",
        on_click=lambda e: search(),
    )

    #======================================================
    #UIコントロールの定義
    #======================================================

    #ダイアログの定義
    dialog = ft.AlertDialog(modal = True)

    #カラム定義
    column = ft.Column(controls = [], spacing = 16, expand = True)

    #ラジオボタングループの定義
    radio_group = ft.RadioGroup(
        content = column,
        on_change = lambda e:print(f"選ばれたID:{radio_group.value}")
    )


    #リセットボタン定義
    reset_btn = ft.ElevatedButton(
        content = ft.Text(value = "リセット", size = 14, color = ft.Colors.RED),
        on_click = lambda e: page.run_task(refresh, e),
        bgcolor = ft.Colors.RED_50,
        width = 60,
        height = 30,
        style = ft.ButtonStyle(
            shape = ft.RoundedRectangleBorder(radius = 0),
            padding = ft.padding.all(0)
        ),
    )

    #検索欄定義
    search_zone = ft.Row(
        controls = [search_box,search_button],
        alignment = ft.MainAxisAlignment.CENTER,
        spacing = 0
    )

    #リセットボタン含め検索欄を再定義
    search_zone_row = ft.Row(
        controls = [search_zone, reset_btn],
        alignment = ft.MainAxisAlignment.START,
        spacing = 50
    )

    #前ページ遷移ボタン定義
    prev_btn = ft.ElevatedButton(
        "← 前へ", on_click = lambda e:prev_page(e),
        style = ft.ButtonStyle(shape = ft.RoundedRectangleBorder(radius = 6))
    )

    #現在ページ定義
    page_label = ft.Text("")    #load_table内で更新

    #次ページ遷移ボタン定義
    next_btn = ft.ElevatedButton(
        "次へ →", on_click = lambda e: next_page(e),
        style = ft.ButtonStyle(shape = ft.RoundedRectangleBorder(radius = 6))
    )

    #ボタン群を再定義
    btn_zone = ft.Row([prev_btn, page_label, next_btn], alignment = ft.MainAxisAlignment.CENTER)

    #テーブル本体の定義
    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID"), on_sort = lambda e: page.run_task(sort_table, e)),
            ft.DataColumn(ft.Text("名前")),
            ft.DataColumn(ft.Text("カナ氏名")),
        ],
        rows = [],
        sort_column_index = 0,
        sort_ascending = True,
    )

    
    # =================================================
    # 更新、ソート関数
    # =================================================
    

    #リセットボタン（検索条件、並び順、ページを初期状態に戻す）
    async def refresh(e):
        nonlocal selected_user_id, offset, reset_btn
        reset_btn.disabled = True
        page.update()

        selected_user_id = None
        table.sort_ascending = True
        nonlocal search_text
        search_box.value = ""  #検索窓をクリア
        search_text = ""
        offset = 0
        load_table()
        scroll_table.scroll_to(offset = 0, duration = 0)

        await asyncio.sleep(0.2)
        reset_btn.disabled = False
        page.update()

    #IDカラムのヘッダークリック:昇順/降順を切り替えて再度読み込み
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

    
    # ======================================
    # ページ遷移関数
    # ======================================
    
    def prev_page(e):
        #前ページへ遷移
        nonlocal offset
        if offset != 0:
            offset -= 1
        load_table()
        scroll_table.scroll_to(offset = 0, duration = 0)

    def next_page(e):
        #次ページへ遷移
        nonlocal offset
        if (offset + 1) != all_page:
            offset += 1
        load_table()
        scroll_table.scroll_to(offset = 0, duration = 0)

        
        # =============================================
        # テーブル読み込み関数
        # =============================================
        

    def load_table():
        """
        選択中のuser_id(なければ全件検索)でカード情報を取得
        テーブル・チェックボックス・ラジオボタンを再構成
        """
        nonlocal selected_user_id, offset, all_page

        try:
            #全検索の場合
            if search_text == "":
                users = repo.find_all_users(table.sort_ascending, offset * 100)
                total = repo.count_all_user()
            #条件検索の場合
            else:
                users = repo.find_user_name_and_user_id_by_user_kana(
                    search_text, table.sort_ascending, offset * 100
                )
        except sqlite3.Error:
            logger.exception("ユーザー情報の読み込みに失敗しました")
            show_error_dialog(page, "ユーザー情報の取得に失敗しました。しばらくしてから再度お試しください。")
            return

        #諸パラメーター更新
        all_page = int(((total - 1)/100)+1)

        # checkbox_refs.clear()
        table.rows.clear()
        column.controls.clear()
        column.controls.append(ft.Container(height = -2))

        #該当ユーザー情報分繰り返し
        for user in users:
            #チェックボックスにユーザーIDを埋め込み
            cb = ft.Checkbox()
            column.controls.append(ft.Radio(value = str(user.user_id)))
            # checkbox_refs[user.id] = cb

            #テーブルに情報を埋め込み
            row = ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(user.user_id))),

                        ft.DataCell(
                            ft.TextField(
                                value=user.user_name_jpn,
                                border=ft.InputBorder.NONE,
                            )
                        ),

                        ft.DataCell(
                            ft.TextField(
                                value=user.user_kana,
                                border=ft.InputBorder.NONE,
                            )
                        ),
                    ]
                )
            row.cells[1].content.on_blur = \
                lambda e, r=row, uid=user.user_id: save_user(uid, r)

            row.cells[2].content.on_blur = \
                lambda e, r=row, uid=user.user_id: save_user(uid, r)

            table.rows.append(row)

        radio_group.value = str(users[0].id) if users else None
        page_label.value = f"{offset + 1}/{all_page} ページ"
        prev_btn.disabled = offset == 0
        next_btn.disabled = (offset + 1) == all_page
        page.update()

    #ユーザー情報が変更された時保存する
    def save_user(user_id, row):
        repo.update_user(
            user_id,    #user_idはセル番号0扱い
            row.cells[1].content.value,
            row.cells[2].content.value
        )

        
        # ==============================================
        # レイアウト定義と配置
        # ==============================================
        
    #ラジオボックスをテーブルの隣に
    table_radio_box = ft.Row(
        [table, ft.Container(width = 0), radio_group],
        vertical_alignment = ft.CrossAxisAlignment.START
    )

    #スクロール化
    scroll_table = ft.Column(
        controls = [table_radio_box],
        scroll = ft.ScrollMode.ALWAYS,
        expand = True,
    )

    #テーブル読み込み
    load_table()

    #実際のページにする
    return ft.View(
        "/user",
        controls = [
            search_zone_row,
            ft.Text("利用者一覧", size = 30, weight = ft.FrontWeight.BOLD),
            ft.Container(height = 10),
            scroll_table,
            btn_zone,
            ft.Container(height = 10),
            ft.ElevatedButton(
                "戻る",
                icon = ft.Icons.ARROW_BACK,
                style = ft.ButtonStyle(shape = ft.RoundedRectangleBorder(radius = 6)),
                on_click = lambda e: page.go("/index"),
            )
        ],
        padding = ft.Padding(left = 120, top = 20, right = 0, bottom = 50)
    )