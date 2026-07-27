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
from my_app.app.views.common import (
    show_error_dialog,
    Theme, card, section_title, empty_state,
    centered_cell, app_view, pager,
    secondary_button, primary_button, danger_button,
    show_confirm_dialog, show_info_dialog,
    management_tabs,
)

logger = logging.getLogger(__name__)
ITEMS_PER_PAGE = 10


def faceView(page: ft.Page):
    # ===================================================
    # 状態変数(宣言と初期値バインド)
    # ===================================================
    offset = 0                     # 現在のページ番号(0から)
    all_page = 1                   # 全ページ数
    # selected_user_id = None      # Autocompleteで選択中のユーザーID(未選択ならNone=全件表示)
    search_text = ""               # 初期検索
    selected_ids = []              # チェックボックスで選択されたface_idのリスト
    checkbox_refs = {}             # {face_id: Checkboxコントロール} の対応表

    page.title = "顔認証管理画面"
    page.bgcolor = Theme.BG

    # ===================================================
    # ユーザー検索用プルダウンボックスの候補リスト
    # ===================================================
    # 画面表示のたびに最新のユーザー一覧を取得
    def search(e=None):
        nonlocal search_text, offset
        search_text = (search_box.value or "").strip()
        offset = 0
        load_table()
        scroll_table.scroll_to(offset=0, duration=0)

    search_box = ft.TextField(
        label="氏名・カナ氏名",
        hint_text="部分一致検索",
        width=320,
        height=52,
        filled=True,
        fill_color=Theme.SURFACE,
        border_color=Theme.BORDER,
        focused_border_color=Theme.LAVENDER,
        border_radius=8,
        prefix_icon=ft.Icons.SEARCH,
        on_submit=search,
    )

    search_button = secondary_button(
        "検索",
        search,
        ft.Icons.SEARCH,
    )

    reset_btn = secondary_button(
        "リセット",
        lambda e: page.run_task(refresh, e),
        ft.Icons.REFRESH,
    )

    search_zone_row = ft.Row(
        controls=[
            search_box,
            search_button,
            reset_btn,
        ],
        spacing=16,
        wrap=True,
        run_spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # ===================================================
    # UIコントロールの定義
    # ===================================================

    # ボタン定義
    prev_btn = secondary_button(
        "前へ",
        lambda e: prev_page(e),
        ft.Icons.CHEVRON_LEFT,
    )

    page_label = ft.Text("")

    next_btn = secondary_button(
        "次へ",
        lambda e: next_page(e),
        ft.Icons.CHEVRON_RIGHT,
    )

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
        nonlocal search_text, offset

        reset_btn.disabled = True
        page.update()

        search_box.value = ""
        search_text = ""
        table.sort_ascending = True
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
        nonlocal offset
        if offset != 0:
            offset -= 1
        load_table()
        scroll_table.scroll_to(offset=0, duration=0)

    def next_page(e):
        """次ページへ遷移"""
        nonlocal offset
        if (offset + 1) < all_page:
            offset += 1
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
        nonlocal search_text, offset, all_page

        faces, total = repo.find_faces_with_total(
            search_text,
            table.sort_ascending,
            ITEMS_PER_PAGE,
            offset * ITEMS_PER_PAGE,
        )

        while not faces and offset > 0:
            offset -= 1
            faces, total = repo.find_faces_with_total(
                search_text, table.sort_ascending,
                ITEMS_PER_PAGE, offset * ITEMS_PER_PAGE,
            )

        all_page = max(
            1,
            (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE,
        )

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
        page_label.value = (
            f"{offset + 1} / {all_page} ページ"
            f"（全{total}件）"
        )
        prev_btn.disabled = offset == 0
        next_btn.disabled = (offset + 1) >= all_page

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

        refresh_tabs = getattr(
            page,
            "_refresh_management_tabs",
            None,
        )

        if callable(refresh_tabs):
            refresh_tabs()

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
        scroll=ft.ScrollMode.HIDDEN,
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
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(
                            expand=True,
                            content=section_title(
                                "顔情報検索",
                                accent=Theme.LAVENDER,
                            ),
                        ),
                        primary_button(
                            "顔を登録",
                            lambda e: page.go("/face_register"),
                            ft.Icons.ADD_A_PHOTO,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=6),
                search_zone_row,
            ],
            spacing=10,
        ),
        accent=Theme.LAVENDER,
    )

    # テーブル用カード(土台のパネル)
    table_card = card(
        ft.Column(
            controls=[
                section_title(
                    "顔画像一覧",
                    accent=Theme.LAVENDER,
                ),
                ft.Container(height=10),
                scroll_table,
                ft.Container(height=10),
                btn_zone,
            ],
            spacing=10,
            expand=True,
        ),
        accent=Theme.LAVENDER,
    )



    # ===================================================
    # 実際にページに
    # ===================================================


    #ここでページ統合して表示
    return app_view(
        "/face",
        page,
        [
            management_tabs(page, "/face"),
            search_card,
            ft.Container(height=16),
            table_card,
        ],
        back_route="/index",
    )