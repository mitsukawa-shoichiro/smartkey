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
import my_app.db.repository as repo
import my_app.service.face_service as face_service
import sqlite3
from my_app.app.utils.pagination import Pagination
from my_app.app.views.common import (
    show_error_dialog, build_user_autocomplete,
    Theme, card, section_title, empty_state,
    centered_cell, app_view, pager,
    secondary_button, danger_button,
    show_confirm_dialog, show_info_dialog,
)

logger = logging.getLogger(__name__)

def build_face_row(face, check_box) -> ft.DataRow:
    """

    Args:
        face (Face): 顔情報が入ったデータクラス
        check_box (ft.CheckBox): IDと紐づくチェックボックスオブジェクト

    Returns:
        ft.DataRow: _description_
    """
    return ft.DataRow(cells=[
        ft.DataCell(centered_cell(ft.Text(f"{face.id:05d}", color=Theme.TEXT_MUTED), 100)),
        ft.DataCell(centered_cell(ft.Text(str(face.register_date), color=Theme.TEXT_MUTED), 140)),
        ft.DataCell(centered_cell(ft.Text(face.user_name or "(未設定)"), 140)),
        ft.DataCell(centered_cell(check_box, 140)),
        ])


def faceView(page: ft.Page):
    # ===================================================
    # 状態変数(宣言と初期値バインド)
    # ===================================================
    pg = Pagination(100)           # ページ状態管理クラス
    selected_user_id = None        # Autocompleteで選択中のユーザーID(未選択ならNone=全件表示)
    selected_ids = []              # チェックボックスで選択されたface_idのリスト
    checkbox_refs = {}             # {face_id: Checkboxコントロール} の対応表

    page.title = "顔認証管理画面"
    page.bgcolor = Theme.BG

    # ===================================================
    # ユーザー検索用プルダウンボックスの候補リスト
    # ===================================================

    # 画面表示のたびに最新のユーザー一覧を取得
    users = repo.get_all_users()

    def on_user_selected(user_id: int):
        """Autocompleteでユーザーが選択された時: そのuser_idで絞り込み検索する"""
        nonlocal selected_user_id
        selected_user_id = user_id
        pg.reset()
        load_table()
        scroll_table.scroll_to(offset=0, duration=0)

    user_search = build_user_autocomplete(users, on_user_selected)

    # ===================================================
    # UIコントロールの定義
    # ===================================================

    # リセットボタン定義
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

    # 検索窓定義
    search_zone = ft.Row(
        controls=[user_search],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=0
    )

    # リセットボタン含めグループ化
    search_zone_row = ft.Row(
        controls=[search_zone, reset_btn],
        alignment=ft.MainAxisAlignment.START,
        spacing=50
    )

    # 前ページ遷移ボタン定義
    prev_btn = secondary_button("⬅ 前へ", lambda e: prev_page(e))

    # 現在ページ定義
    page_label = ft.Text("")  # load_table内で更新

    # 次ページ遷移ボタン定義
    next_btn = secondary_button("次へ ➡", lambda e: next_page(e))

    # ボタン群をまとめて再定義
    btn_zone = pager(prev_btn, page_label, next_btn)


    # テーブル本体, カラムヘッダーの定義
    table = ft.DataTable(
        columns=[
            ft.DataColumn( # セル中央揃えもcommon.centered_cellに外注
                centered_cell(ft.Text("ID", weight=ft.FontWeight.BOLD), 100),
                on_sort=lambda e: page.run_task(sort_table, e),
            ),
            ft.DataColumn(
                centered_cell(
                    ft.Text("登録日", weight=ft.FontWeight.BOLD),
                    140
                )
            ),
            ft.DataColumn(
                centered_cell(
                    ft.Text("ユーザー名", weight=ft.FontWeight.BOLD),
                    140
                )
            ),
            ft.DataColumn(
                centered_cell(
                    danger_button("行を削除", lambda e: open_confirm_dialog(e), ft.Icons.DELETE_OUTLINE),
                    140
                )
            ),
        ],

        rows=[],
        #sort_column_index=0, ソート用矢印を最初だけ消すためにコメントアウト

        # 各種設定
        sort_ascending=True,
        heading_row_color=Theme.HEADING_BG,
        heading_row_height=48,
        data_row_min_height=52,
        data_row_max_height=52,
        divider_thickness=1,
        horizontal_lines=ft.BorderSide(1, Theme.BORDER),
        column_spacing=20,
    )

    # ===================================================
    # リセット、ソート関数
    # ===================================================

    async def refresh(e):
        """リセットボタン: 検索条件・並び順・ページを全部初期状態に戻す"""
        #スコープ外のグローバル変数を扱う
        nonlocal selected_user_id, user_search
        reset_btn.disabled = True
        page.update()

        selected_user_id = None
        table.sort_ascending = True
        pg.reset()

        # プルダウンはvalueだけリセットしても表示が変わらないので都度作り直し
        user_search = build_user_autocomplete(users, on_user_selected)
        search_zone.controls = [user_search]
        search_zone.update()

        load_table()
        scroll_table.scroll_to(offset=0, duration=0)

        await asyncio.sleep(0.2)
        reset_btn.disabled = False
        page.update()

    async def sort_table(e):
        """IDカラムのヘッダークリック: 昇順/降順を切り替えて再読込"""
        #スコープ外のグローバル変数を扱う
        table.sort_column_index = 0
        table.sort_ascending = not table.sort_ascending
        pg.reset()
        # ここは処理が重いのか何なのかついていたもの、ちかちかするのでコメントアウト
        # scroll_table.visible = False
        # scroll_table.update()
        # await asyncio.sleep(0.01)
        # scroll_table.visible = True
        # scroll_table.update()
        load_table()

    # ===================================================
    # ページ遷移関数
    # ===================================================

    def prev_page(e):
        """前ページへ遷移"""
        if pg.prev():
            load_table()
            scroll_table.scroll_to(offset=0, duration=0)

    def next_page(e):
        """次ページへ遷移"""
        if pg.next():
            load_table()
            scroll_table.scroll_to(offset=0, duration=0)

    # ===================================================
    # テーブル読み込み関数
    # ===================================================

    def load_table():
        """
        選択中のuser_id(無ければ全件)に基づいて顔情報を取得し、
        テーブル・チェックボックスを再構築する。
        """
        try:
            faces , total = repo.find_faces_with_total(selected_user_id, table.sort_ascending, pg.per_page, pg.offset)
        except sqlite3.Error:
            logger.exception("顔情報の読み込みに失敗しました")
            show_error_dialog(page, "顔情報の取得に失敗しました。しばらくしてから再度お試しください。")
            return

        pg.update_total(total)

        #初期化
        checkbox_refs.clear()
        table.rows.clear()

        #テーブル表示関数をヒットした件数分回す
        for face in faces:
            #チェックボックス定義、ID埋め込み
            cb = ft.Checkbox()
            checkbox_refs[face.id] = cb

            #テーブル一行の表示
            table.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(centered_cell(ft.Text(f"{face.id:05d}", color=Theme.TEXT_MUTED), 100)),
                    ft.DataCell(centered_cell(ft.Text(str(face.register_date), color=Theme.TEXT_MUTED), 140)),
                    ft.DataCell(centered_cell(ft.Text(face.user_name or "(未設定)"), 140)),
                    ft.DataCell(centered_cell(cb, 140)),
                ])
            )

        #その他項目の設定
        page_label.value = pg.label
        prev_btn.disabled = pg.is_first
        next_btn.disabled = pg.is_last

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
            show_info_dialog(page, "削除する行が選択されていません。", title="削除の確認")
            return
        show_confirm_dialog(
            page,
            f"{len(selected_ids)} 件を削除しますか?",
            on_confirm=lambda: confirm_delete(),
            title="削除の確認",
        )


    def confirm_delete():
        """
        削除確定: 選択されたface_idを1件ずつ face_service.remove_face に渡す。
        (画像ファイルとDB行の両方をまたぐ後始末はservice層の責務のため)
        """

        #削除処理、ログ出力
        try:
            for face_id in selected_ids:
                face_service.remove_face(face_id)
                logger.info(f"face_id={face_id}が削除されました")
        except (OSError, sqlite3.Error):
            logger.exception("顔情報の削除に失敗しました")
            show_error_dialog(page, "画像の削除に失敗しました。しばらくしてから再度お試しください")
            load_table()
            return

        # 削除後読み込み
        load_table()

        show_info_dialog(page, f"{len(selected_ids)} 件を削除しました。", title="削除完了")


    # ===================================================
    # レイアウト定義、実際に配置
    # ===================================================

    # データテーブルはそのままだと中央ぞろえできないためRow化
    table_row = ft.Row(
        [table],
        alignment=ft.MainAxisAlignment.CENTER,
    )

    #スクロール可能の定義
    scroll_table = ft.Column(
        controls=[table_row],
        scroll=ft.ScrollMode.ALWAYS,
        expand=True,
    )

    #テーブル本体
    load_table()

    # ===================================================
    # commonスタイル適用
    # ===================================================

    # 検索欄用カード(土台のパネル)
    search_card = card(
        ft.Column(
            controls=[ # サブタイトル入れたかったのに泣く泣く断念；；カンマ入れた後に文字列で小っちゃく薄く下に文字書けるます！
                section_title("ユーザー名で検索",),
                ft.Container(height=4),
                search_zone_row,
            ],
            spacing=8,
        )
    )

    # テーブル用カード(土台のパネル)
    table_card = card(
        ft.Column(
            controls=[# 上に同じ
                section_title("顔画像一覧"),
                ft.Container(height=8),
                scroll_table,
                ft.Container(height=8),
                btn_zone,
            ],
            spacing=8,
            expand=True,
        )
    )



    # ===================================================
    # 実際にページに
    # ===================================================


    #ここでページ統合して表示
    return app_view("/face", page, [
        search_card,
        ft.Container(height=16),
        table_card,
    ])