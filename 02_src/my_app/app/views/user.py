"""
カードまたは顔写真を登録したユーザーの名前を一覧表示
ホーム画面に戻る機能の実装
"""
import flet as ft
import logging
import asyncio
import sqlite3
import db.repository as repo
from my_app.app.views.common import show_error_dialog, filter_user_options


logger = logging.getLogger(__name__)

        #UIコントロールの定義
def userView(page: ft.page):
    # ===================================================
    # 状態変数
    # ===================================================
    offset = 0                     # 現在のページ番号(0始まり)
    all_page = 1                   # 全ページ数

    selected_user_id = None


    page.title = "ユーザ管理画面"

    #============================================
    #ユーザー検索の候補データ
    #============================================
    #画面表示のたびに最新のユーザー一覧を取得する

    users = repo.get_all_users()

    def on_user_selected(e: ft.ControlEvent):
            """Autocompleteでユーザーが選択された時: そのuser_idで絞り込み検索する"""
            nonlocal selected_user_id, offset
            selected_user_id = int(e.selection.key)
            offset = 0
            load_table()
            scroll_table.scroll_to(offset=0, duration=0)

    def on_user_search_change(e: ft.ControlEvent):
        """
        入力のたびに候補を絞り込み直す。ひらがな/カタカナ/ローマ字の
        表記ゆれをjapanese_text.matchesで吸収する(Flet標準の絞り込みでは非対応)。
        """
        search_user.suggestions = filter_user_options(users, e.control.value)
        search_user.update()

    search_user = ft.AutoComplete(
        suggestions=filter_user_options(users, ""),
        on_select=on_user_selected,
        on_change=on_user_search_change,
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

    #選択されたユーザの定義
    def on_user_selected(e: ft.ControlEvent):
        #プルダウンでユーザーが選択された時、そのuser_idで絞り込み検索する
        nonlocal selected_user_id, offset
        selected_user_id = int(e.selection.key)
        offset = 0
        load_table()
        scroll_table.scroll_to(offset = 0, duration = 0)

    #プルダウン定義
    user_search = ft.AutoComplete(
        suggestions = autocomplete_options,
        on_select = on_user_selected,
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
        controls = [user_search],
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
        user_search.value = ""  #プルダウン入力をクリア
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
            offset -= -1
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
            if selected_user_id is None:
                users = repo.find_all_users(table.sort_ascending, offset * 100)
                total = repo.count_all_user()
            #条件検索の場合
            else:
                users = repo.find_users_by_user_id(
                    selected_user_id, table.sort_ascending, offset * 100
                )
                total = repo.count_users_by_user_id(selected_user_id)
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
            column.controls.append(ft.Ratio(value = str(user.id)))
            # checkbox_refs[user.id] = cb

            #テーブルに情報を埋め込み
            table.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(f"{user.id:05d}", width = 40)),
                    ft.DataCell(ft.Text(user.register_date, width = 80)),
                    ft.DataCell(cb),
                ])
            )

        radio_group.value = str(users[0].id) if users else None
        page_label.value = f"{offset + 1}/{all_page} ページ"
        prev_btn.disabled = offset == 0
        next_btn.disabled = (offset + 1) == all_page
        page.update()

        
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