"""
顔認証管理画面(GUI)

顔情報(face)の一覧表示・ユーザー名でのAutocomplete(プルダウン)検索・
ページ管理・複数選択削除を行う画面。

face自体は名前を持たない設計(名前はuserテーブル側)のため、
「登録者名の編集」機能はこの画面には存在しません。飛ばしもしません。編集するものもないので致しません。
"""
import logging
import asyncio
import flet as ft
import db.repository as repo
import service.face_service as face_service

logger = logging.getLogger(__name__)


def faceView(page: ft.Page):
    # ===================================================
    # 状態変数(宣言と初期値バインド)
    # ===================================================
    offset = 0                     # 現在のページ番号(0から)
    all_page = 1                   # 全ページ数
    selected_user_id = None        # Autocompleteで選択中のユーザーID(未選択ならNone=全件表示)
    selected_ids = []              # チェックボックスで選択されたface_idのリスト
    checkbox_refs = {}             # {face_id: Checkboxコントロール} の対応表

    page.title = "顔認証管理画面"

    # ===================================================
    # ユーザー検索用プルダウンボックスの候補リスト
    # ===================================================
    # 画面表示のたびに最新のユーザー一覧を取得
    users = repo.get_all_users()
    #プルダウンに変換
    autocomplete_options = [
        ft.AutoCompleteOption(key=str(u.id), text=f"{u.user_name}({u.user_kana})")
        for u in users
    ]

    # ===================================================
    # UIコントロールの定義
    # ===================================================
    #ダイアログ定義
    dialog = ft.AlertDialog(modal=True)

    #カラム定義
    column = ft.Column(controls=[], spacing=16, expand=True)

    #ラジオボタン定義
    radio_group = ft.RadioGroup(
        content=column,
        on_change=lambda e: print(f"選ばれたID: {radio_group.value}")
    )

    def on_user_selected(e: ft.ControlEvent):
        """Autocompleteでユーザーが選択された時: そのuser_idで絞り込み検索する"""

        #スコープ外のグローバル変数を扱う
        nonlocal selected_user_id, offset
        #選択したIDをファイル内グローバル変数にバインド
        selected_user_id = int(e.selection.key)
        #ページ区切り再定義
        offset = 0
        #表を検索条件反映させた状態で再読み込み
        load_table()
        #遷移ページの再定義
        scroll_table.scroll_to(offset=0, duration=0)

    #プルダウン定義
    face_name = ft.AutoComplete(
        suggestions=autocomplete_options,
        on_select=on_user_selected,
    )

    #条件リセットボタン定義
    reset_btn = ft.ElevatedButton(
        content=ft.Text(value="リセット", size=14, color=ft.Colors.RED),
        on_click=lambda e: page.run_task(refresh, e),
        bgcolor=ft.Colors.RED_50,
        width=60,
        height=30,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=0),
            padding=ft.padding.all(0)
        ),
    )

    #検索窓定義
    search_zone = ft.Row(
        controls=[face_name],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=0
    )

    #リセットボタン含めグループ化
    search_zone_row = ft.Row(
        controls=[search_zone, reset_btn],
        alignment=ft.MainAxisAlignment.START,
        spacing=50
    )

    #前ページ遷移ボタン定義
    prev_btn = ft.ElevatedButton(
        "⬅ 前へ", on_click=lambda e: prev_page(e),
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6))
    )

    # 現在ページラベル定義：load_table内で更新
    page_label = ft.Text("")

    #次ページ遷移ボタン定義
    next_btn = ft.ElevatedButton(
        "次へ ➡", on_click=lambda e: next_page(e),
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6))
    )

    #ボタン群定義
    btn_zone = ft.Row([prev_btn, page_label, next_btn], alignment=ft.MainAxisAlignment.CENTER)

    # 顔情報の一覧を表示するためのテーブル
    table = ft.DataTable(
        columns=[#一行に入る情報たち
            ft.DataColumn(ft.Text("ID"), on_sort=lambda e: page.run_task(sort_table, e)),
            ft.DataColumn(ft.Text("登録日")),
            ft.DataColumn(ft.ElevatedButton(
                "行を削除", on_click=lambda e: open_confirm_dialog(e),
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=0))
            ))
        ],
        rows=[],
        sort_column_index=0,
        sort_ascending=True,
    )

    # ===================================================
    # リセット、ソート関数
    # ===================================================

    async def refresh(e):
        """リセットボタン: 検索条件・並び順・ページを全部初期状態に戻す"""
        #スコープ外のグローバル変数を扱う
        nonlocal selected_user_id, offset, reset_btn
        reset_btn.disabled = True
        page.update()

        selected_user_id = None
        table.sort_ascending = True
        face_name.value = ""  # プルダウン入力欄のクリア
        offset = 0
        load_table()
        scroll_table.scroll_to(offset=0, duration=0)

        await asyncio.sleep(0.2)
        reset_btn.disabled = False
        page.update()

    async def sort_table(e):
        """IDカラムのヘッダークリック: 昇順/降順を切り替えて再読込"""
        #スコープ外のグローバル変数を扱う
        nonlocal offset
        table.sort_ascending = not table.sort_ascending
        offset = 0
        scroll_table.visible = False
        scroll_table.update()
        await asyncio.sleep(0.01)
        scroll_table.visible = True
        scroll_table.update()
        load_table()

    # ===================================================
    # ページ送り関数
    # ===================================================

    def prev_page(e):
        #スコープ外のグローバル変数を扱う
        nonlocal offset
        if offset != 0:
            offset -= 1
        load_table()
        scroll_table.scroll_to(offset=0, duration=0)

    def next_page(e):
        #スコープ外のグローバル変数を扱う
        nonlocal offset
        if (offset + 1) != all_page:
            offset += 1
        load_table()
        scroll_table.scroll_to(offset=0, duration=0)

    # ===================================================
    # テーブル読み込み関数
    # ===================================================

    def load_table():
        """
        選択中のuser_id(無ければ全件)に基づいて顔情報を取得し、
        テーブル・チェックボックス・ラジオボタンを再構築する。
        """
        #スコープ外のグローバル変数を扱う
        nonlocal selected_user_id, offset, all_page

        #絞り込み条件なし
        if selected_user_id is None:
            faces = repo.find_all_faces(table.sort_ascending, offset * 100)
            total = repo.count_all_face()
        #絞り込み条件あり
        else:
            faces = repo.find_faces_by_user_id(
                selected_user_id, table.sort_ascending, offset * 100)
            total = repo.count_faces_by_user_id(selected_user_id)

        all_page = int(((total - 1) / 100) + 1)

        #初期化
        checkbox_refs.clear()
        table.rows.clear()
        column.controls.clear()
        column.controls.append(ft.Container(height=-2))

        #テーブル表示関数をヒットした件数分回す
        for face in faces:
            #チェックボックス定義、ID埋め込み
            cb = ft.Checkbox()
            column.controls.append(ft.Radio(value=str(face.id)))
            checkbox_refs[face.id] = cb

            #テーブル一行の表示
            table.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(f"{face.id:05d}", width=40)),
                    ft.DataCell(ft.Text(face.register_date, width=80)),
                    ft.DataCell(cb),
                ])
            )

        #その他項目の設定
        radio_group.value = str(faces[0].id) if faces else None
        page_label.value = f"{offset + 1} / {all_page} ページ"
        prev_btn.disabled = offset == 0
        next_btn.disabled = (offset + 1) == all_page

        #実際のページに
        page.update()

    # ===================================================
    # 削除
    # ===================================================

    def open_confirm_dialog(e):
        """「行を削除」クリック: チェック済みの行を確認してから削除ダイアログを開く"""

        #スコープ外のグローバル変数を扱う
        nonlocal selected_ids
        #チェックボックスから削除項目のID受け取り
        selected_ids = [face_id for face_id, cb in checkbox_refs.items() if cb.value]

        #削除項目無しで削除ボタンが押された
        if not selected_ids:
            dialog.title = ft.Text("削除の確認")
            dialog.content = ft.Text("削除する行が選択されていません。")
            #ここがページ遷移
            dialog.actions = [
                ft.TextButton("閉じる", autofocus=True, on_click=lambda e: page.close(dialog)),
            ]
            #実際のページに
            page.open(dialog)

        #削除確認
        else:
            dialog.title = ft.Text("削除の確認")
            dialog.content = ft.Text(f"{len(selected_ids)} 件を削除しますか?")
            #ページ遷移(分岐)
            dialog.actions = [
                ft.TextButton("キャンセル", autofocus=True, on_click=lambda e: page.close(dialog)),
                ft.TextButton("はい", on_click=confirm_delete),
            ]
            #実際のページに
            page.open(dialog)

    def confirm_delete(e):
        """
        削除確定: 選択されたface_idを1件ずつ face_service.remove_face に渡す。
        (画像ファイルとDB行の両方をまたぐ後始末はservice層の責務のため)
        """

        #削除処理、ログ出力
        for face_id in selected_ids:
            face_service.remove_face(face_id)
            logger.info(f"face_id={face_id}が削除されました")

        #削除後テーブル読み込み
        load_table()

        #ダイアログ表示
        dialog.title = ft.Text("削除完了")
        dialog.content = ft.Text(f"{len(selected_ids)} 件を削除しました。")
        #ダイアログ終了ボタン定義
        dialog.actions = [
            ft.TextButton("閉じる", autofocus=True, on_click=lambda e: page.close(dialog)),
        ]
        #実際のページに
        page.open(dialog)

    # ===================================================
    # レイアウト定義
    # ===================================================

    #ラジオボタンを含めテーブル行を再定義
    table_radio_box = ft.Row(
        [table, ft.Container(width=0), radio_group],
        vertical_alignment=ft.CrossAxisAlignment.START
    )

    #スクロール可能の定義
    scroll_table = ft.Column(
        controls=[table_radio_box],
        scroll=ft.ScrollMode.ALWAYS,
        expand=True,
    )

    #テーブル本体
    load_table()

    #ここでページ統合して表示
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
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
                on_click=lambda e: page.go("/index"),
            )
        ],
        padding=ft.Padding(left=120, top=20, right=0, bottom=50)
    )
