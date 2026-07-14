"""
入退室履歴管理画面(GUI)

入退室履歴の一覧表示・ユーザー(プルダウン選択)/認証方式/入退室区分/日時での
絞り込み検索・ページ遷移を行う画面。

削除されたユーザーのログも表示できるよう、access_logs自体にログ記録時点の
ユーザー名(user_name)をスナップショットとして持たせている。
ユーザー名はuser_idを使用
"""
from datetime import datetime, date, time, timedelta
import flet as ft
import db.repository as repo
import asyncio
import logging
from app.models.ENUMS import EventType
from app.views.common import filter_user_options

# テーブルの1ページが表示する件数
ITEMS_PER_PAGE = 100
logger = logging.getLogger(__name__)


def accesslogs(page: ft.Page):
    try:
        page.title = "ログ閲覧画面"

        # ===================================================
        # 状態変数
        # ===================================================
        current_page = 0           # 現在のページ（0‑origin）
        total_pages = 1            # 総ページ数（動的に計算）
        search_mode = False        # False: 全件モード / True: 検索モード
        selected_user_id = None    # プルダウンで選択中のユーザーID(未選択ならNone=全ユーザー対象)
        search_params = {          # 検索条件を保持(検索ボタン押下時にまとめて確定させる)
            "user_id": None,
            "method": None,
            "event_type": None,
            "start_dt": None,
            "end_dt": None,
        }

        # エラーの際に表示するダイアログの初期設定
        dialog = ft.AlertDialog(modal=True)

        # ===================================================
        # ページ数計算
        # ===================================================

        def calc_total_pages(count: int):
            nonlocal total_pages
            total_pages = max(1, (count + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

        # ===================================================
        # 日付ピッカー関連
        # ===================================================

        # 開始日付変更関数
        def change_start_date(e):
            if start_date.value:
                start_time.open = True
                open_timepicker(start_time)
                page.update()

        # 終了日付変更関数
        def change_end_date(e):
            if end_date.value:
                end_time.open = True
                open_timepicker(end_time)
                page.update()


        page.locale_configuration = ft.LocaleConfiguration(
            supported_locales=[ft.Locale("ja", "JP"), ft.Locale("en", "US")],
            current_locale=ft.Locale("ja", "JP")
        )

        # ===================================================
        # ユーザー検索用プルダウンの候補データ
        # ===================================================

        # 画面表示のたびに最新のユーザー一覧を取得する
        users = repo.get_all_users()

        def on_user_selected(e: ft.ControlEvent):
            """
            プルダウンでユーザーが選択された時: user_idだけ保持しておく。
            他の検索条件(認証方式・入退室区分・日時)と同様、実際の検索は
            検索ボタン押下時(search_logs)にまとめて確定させる。
            """
            nonlocal selected_user_id
            selected_user_id = int(e.selection.key)

        def on_user_search_change(e: ft.ControlEvent):
            """
            入力が変化するたびにフィルタ関数を呼んでプルダウン候補を絞り込み直す関数
            fletのバージョン次第で呼ばれなかったりするらしい。

            Args:
                e (ft.ControlEvent): イベントオブジェクト

            """
            search_user.suggestions = filter_user_options(users, e.control.value)
            search_user.update()

        # 選択されたユーザー
        search_user = ft.AutoComplete(
            suggestions=filter_user_options(users, ""),
            on_select=on_user_selected,
            on_change=on_user_search_change,
        )




        # ===================================================
        # 検索フィールドの定義
        # ===================================================

        # 認証方式の選択ラベル
        method_dropdown = ft.DropdownM2(label="認証   方式", value=None, width=85, height=45)

        # プルダウン(検索なし)
        method_dropdown.options = [
            ft.DropdownOption("カード", "カード"),
            ft.DropdownOption("Web", "Web"),
        ]

        # 今日の日付取得
        today = date.today()

        # 開始日付
        start_date = ft.DatePicker(
            on_change=change_start_date, date_picker_entry_mode=ft.DatePickerEntryMode.INPUT,
            first_date=today - timedelta(days=365), last_date=today
        )

        # 終了日付
        end_date = ft.DatePicker(
            on_change=change_end_date, date_picker_entry_mode=ft.DatePickerEntryMode.INPUT,
            first_date=today - timedelta(days=365), last_date=today
        )

        # 開始時
        start_time = ft.TimePicker(
            value=time(0, 0), on_change=lambda e: update_start_textbox(),
            time_picker_entry_mode=ft.TimePickerEntryMode.INPUT
        )

        # 終了時
        end_time = ft.TimePicker(
            value=time(23, 59), on_change=lambda e: update_end_textbox(),
            time_picker_entry_mode=ft.TimePickerEntryMode.INPUT
        )

        #ラベル
        start_text = ft.TextField(label="開始日時", width=200, height=48)
        end_text = ft.TextField(label="終了日時", width=200, height=48)

        #入退室
        search_eventtype = ft.DropdownM2(label="入室/  退室", value=None, width=85, height=45)

        #ドロップダウンの値定義
        search_eventtype.options = [
            ft.DropdownOption("0", "入室"),
            ft.DropdownOption("1", "退室"),
        ]

        # ===================================================
        # 検索実行
        # ===================================================

        def search_logs(e):
            """
            検索ボタン: 各検索欄(ユーザー・認証方式・入退室区分・日時)の値を
            まとめてsearch_paramsに確定させ、1ページ目から検索結果を表示する。
            """
            # 状態変数を扱う宣言
            nonlocal current_page, search_mode, search_params

            # 各パラメータの設定
            search_method = method_dropdown.value.strip() if method_dropdown.value else None
            search_event_type = int(search_eventtype.value.strip()) if search_eventtype.value else None

            start_dt = None
            end_dt = None
            first_date = today - timedelta(days=365)
            last_date = today

            try:
                # 開始日時が入力された場合はフォーマットに直す（秒数は00秒）
                if start_text.value:
                    start_dt = datetime.strptime(start_text.value, "%Y-%m-%d %H:%M")
                    start_dt = start_dt.replace(second=0)

                # 終了日時が入力された場合はフォーマットに直す（秒数は59秒）
                if end_text.value:
                    end_dt = datetime.strptime(end_text.value, "%Y-%m-%d %H:%M")
                    end_dt = end_dt.replace(second=59)

                # 終了日時が開始日時より前に設定された場合にエラー表示
                if start_dt and end_dt and end_dt < start_dt:
                    dialog.title = ft.Text("エラー")
                    dialog.content = ft.Text("終了日時が開始日時以降にされていません。")
                    dialog.actions = [ft.TextButton("閉じる", on_click=lambda e: page.close(dialog))]
                    page.open(dialog)
                    return

                # 開始日時が一年以上前または本日以降の場合にエラー表示
                if start_dt and (start_dt.date() < first_date or start_dt.date() > last_date):
                    dialog.title = ft.Text("エラー")
                    dialog.content = ft.Text(
                        f"開始日時が範囲外です。\n検索範囲は {first_date.strftime('%Y-%m-%d 00:00')} から"
                        f"{last_date.strftime('%Y-%m-%d 23:59')}までです。"
                    )
                    dialog.actions = [ft.TextButton("閉じる", on_click=lambda e: page.close(dialog))]
                    page.open(dialog)
                    return

                # 終了日時が一年以上前または本日以降の場合にエラー表示
                if end_dt and (end_dt.date() > last_date or end_dt.date() < first_date):
                    dialog.title = ft.Text("エラー")
                    dialog.content = ft.Text(
                        f"終了日時が範囲外です。 \n検索範囲は{first_date.strftime('%Y-%m-%d 00:00')} から"
                        f"{last_date.strftime('%Y-%m-%d 23:59')}までです。"
                    )
                    dialog.actions = [ft.TextButton("閉じる", on_click=lambda e: page.close(dialog))]
                    page.open(dialog)
                    return

            except ValueError:
                # フォーマットに沿っていない入力がされた場合、エラー表示
                dialog.title = ft.Text("エラー")
                dialog.content = ft.Text("日時のフォーマットが正しくありません。")
                dialog.actions = [ft.TextButton("閉じる", on_click=lambda e: page.close(dialog))]
                page.open(dialog)
                return

            search_params = {
                "user_id": selected_user_id,
                "method": search_method,
                "event_type": search_event_type,
                "start_dt": start_dt,
                "end_dt": end_dt,
            }
            search_mode = True
            current_page = 0

            try:
                # 件数を取得
                cnt = repo.count_filtered_logs(
                    search_params["method"], search_params["event_type"],
                    search_params["start_dt"], search_params["end_dt"],
                    search_params["user_id"]
                )
            except Exception:
                logger.exception("ログ件数の取得に失敗しました")
                dialog.title = ft.Text("エラー")
                dialog.content = ft.Text("ログの検索に失敗しました。しばらくしてから再度お試しください。")
                dialog.actions = [ft.TextButton("閉じる", on_click=lambda e: page.close(dialog))]
                page.open(dialog)
                return

            # 件数からページ数計算
            calc_total_pages(cnt)
            # テーブル読み込み
            load_table(current_page)
            # ページを遷移
            scroll_table.scroll_to(offset=0, duration=0)

        # ===================================================
        # ソート
        # ===================================================

        async def toggle_sort(e):
            """ソートを切り替え、ページをリセットし、新しい順で再描画"""
            nonlocal current_page
            table.sort_ascending = not table.sort_ascending
            current_page = 0
            scroll_table.visible = False
            scroll_table.update()
            await asyncio.sleep(0.01)
            scroll_table.visible = True
            scroll_table.update()
            load_table(current_page)

        async def on_sort(e):
            await toggle_sort(e)

        # ===================================================
        # 全件表示・検索欄の開閉
        # ===================================================

        def show_all_logs(e):
            """全件検索してテーブルに表示(検索条件を全てクリアする)"""
            nonlocal current_page, search_params
            current_page = 0
            search_params = {
                "user_id": None, "method": None, "event_type": None,
                "start_dt": None, "end_dt": None,
            }
            reset(e)
            calc_total_pages(repo.count_filtered_logs())
            load_table(current_page)

        def open_datepicker(picker: ft.DatePicker):
            page.dialog = picker
            picker.open = True
            page.update()

        def open_timepicker(picker: ft.TimePicker):
            page.dialog = picker
            picker.open = True
            page.update()

        def reset(e):
            """検索欄のリセット(ユーザー選択も含む)"""
            nonlocal selected_user_id
            selected_user_id = None
            search_user.value = ""
            method_dropdown.value = None
            search_eventtype.value = None
            start_text.value = ""
            end_text.value = ""
            start_date.value = None
            end_date.value = None
            start_time.value = time(0, 0)
            end_time.value = time(23, 59)
            page.update()

        def update_start_textbox():
            """日時ピッカーで入力された値をテキストボックスに反映する（日付・時刻どちらも入力された場合のみ）"""
            if start_date.value and start_time.value:
                dt = datetime.combine(start_date.value, start_time.value)
                start_text.value = dt.strftime("%Y-%m-%d %H:%M")
            else:
                start_text.value = ""
            page.update()

        def update_end_textbox():
            if end_date.value and end_time.value:
                dt = datetime.combine(end_date.value, end_time.value)
                end_text.value = dt.strftime("%Y-%m-%d %H:%M")
            else:
                end_text.value = ""
            page.update()

        start_date.on_change = change_start_date
        end_date.on_change = change_end_date

        # ===================================================
        # ボタン定義
        # ===================================================

        # 現在ページ
        page_label = ft.Text("")  # load_table内で更新

        # 前ページ遷移ボタン
        prev_btn = ft.ElevatedButton(
            "⬅ 前へ", on_click=lambda e: prev_page(e),
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6))
        )

        # 次ページ遷移ボタン
        next_btn = ft.ElevatedButton(
            "次へ ➡", on_click=lambda e: next_page(e),
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6))
        )

        # 下部ボタン群グループ化
        pagination_controls = ft.Row([prev_btn, page_label, next_btn], alignment=ft.MainAxisAlignment.CENTER)

        # 検索ボタン
        search_btn = ft.ElevatedButton(
            text="検索", icon=ft.Icons.SEARCH, on_click=search_logs, width=80, height=40,
            bgcolor=ft.Colors.GREY_50,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6), padding=ft.padding.all(0)),
        )

        # 全件取得ボタン
        show_all_btn = ft.ElevatedButton(
            text="全件表示", on_click=show_all_logs, width=80, height=40,
            bgcolor=ft.Colors.GREY_50,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6), padding=ft.padding.all(0)),
        )

        # 開始日時ボタン
        startdate_btn = ft.ElevatedButton(
            text="開始日時を選択", icon=ft.Icons.DATE_RANGE,
            on_click=lambda e: open_datepicker(start_date),
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
        )

        # 終了日時ボタン
        enddate_btn = ft.ElevatedButton(
            text="終了日時を選択", icon=ft.Icons.DATE_RANGE,
            on_click=lambda e: open_datepicker(end_date),
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
        )

        # リセットボタン
        reset_btn = ft.ElevatedButton(
            text="クリア", on_click=reset, width=80, height=40,
            bgcolor=ft.Colors.GREY_50,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=6),
                color=ft.Colors.RED, overlay_color=ft.Colors.RED_100, padding=ft.padding.all(0)
            ),
        )

        # ホーム画面に戻るボタン
        back_btn = ft.ElevatedButton(
            "戻る", icon=ft.Icons.ARROW_BACK,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
            on_click=lambda e: page.go("/index"),
        )

        # ソートに使用する項目
        timestamp_row = ft.Row([ft.Text("入退室の日時", weight="bold", size=14)])

        # ===================================================
        # テーブル定義
        # ===================================================

        # テーブル定義
        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ユーザー名_カード種別", weight="bold", size=14)),
                ft.DataColumn(ft.Text("認証方式", weight="bold", size=14)),
                ft.DataColumn(timestamp_row, on_sort=on_sort),  # 入退室の日時でソート
                ft.DataColumn(ft.Text("区分", weight="bold", size=14)),
            ],
            rows=[],
            sort_column_index=2,
            sort_ascending=False,
        )

        def load_table(page_num: int):
            """
            search_params(検索条件)に基づいてログを取得し、テーブルへ反映する。
            search_modeがFalse(全件モード)の場合はsearch_paramsは全てNoneのまま。
            """
            table.rows.clear()
            offset = page_num * ITEMS_PER_PAGE

            try:
                logs = repo.find_log(
                    search_params["method"], search_params["event_type"],
                    search_params["start_dt"], search_params["end_dt"],
                    ITEMS_PER_PAGE, offset, table.sort_ascending,
                    search_params["user_id"]
                )
            except Exception:
                logger.exception("ログの読み込みに失敗しました")
                dialog.title = ft.Text("エラー")
                dialog.content = ft.Text("ログの取得に失敗しました。しばらくしてから再度お試しください。")
                dialog.actions = [ft.TextButton("閉じる", on_click=lambda e: page.close(dialog))]
                page.open(dialog)
                return

            # ここで行ごとに埋める
            for log in logs:
                event_str = "入室" if log.event_type == EventType.ENTRY else "退室"
                # card_idが無い(顔認証等)場合はカード種別欄を空にする
                card_type = repo.find_card_type_by_id(log.card_id) if log.card_id else ""
                user_label = log.user_name or "(削除済みユーザー)"
                table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(f"{user_label}_{card_type}", width=280)),
                        ft.DataCell(ft.Text(log.method, width=80)),
                        ft.DataCell(ft.Text(log.timestamp, width=140)),
                        ft.DataCell(ft.Text(event_str, width=80)),
                    ])
                )

            # 各種ページ遷移設定
            page_label.value = f"{current_page + 1} / {total_pages} ページ"
            prev_btn.disabled = current_page == 0
            next_btn.disabled = (current_page + 1) >= total_pages
            page.update()

        if not search_mode:
            calc_total_pages(repo.count_filtered_logs())

        # テーブル読み込み
        load_table(current_page)

        # ===================================================
        # ページ送り
        # ===================================================

        def next_page(e):
            nonlocal current_page
            if (current_page + 1) < total_pages:
                current_page += 1
                load_table(current_page)
                scroll_table.scroll_to(offset=0, duration=0)

        def prev_page(e):
            nonlocal current_page
            if current_page > 0:
                current_page -= 1
                load_table(current_page)
                scroll_table.scroll_to(offset=0, duration=0)

        # ===================================================
        # レイアウト
        # ===================================================

        page.overlay.append(start_date)
        page.overlay.append(end_date)
        page.overlay.append(start_time)
        page.overlay.append(end_time)

        search_area = ft.Container(
            content=ft.Column(
                [
                    ft.Row([search_user, method_dropdown,
                            ft.Container(search_eventtype, margin=ft.margin.only(right=56)), reset_btn]),
                    ft.Row([startdate_btn,
                            ft.Container(start_text, margin=ft.margin.only(right=98)), search_btn]),
                    ft.Row([enddate_btn,
                            ft.Container(end_text, margin=ft.margin.only(right=98)), show_all_btn]),
                ],
                spacing=5,
                horizontal_alignment=ft.CrossAxisAlignment.START
            ),
            padding=30,
            bgcolor=ft.Colors.GREY_200,
            border_radius=12,
            width=600,
            visible=False
        )
        scroll_table = ft.Column(controls=[table], scroll=ft.ScrollMode.ALWAYS, expand=True)

        def toggle_search_area(e):
            search_area.visible = not search_area.visible
            toggle_btn.text = "検索オプションを閉じる" if search_area.visible else "検索オプションを開く"
            page.update()

        toggle_btn = ft.ElevatedButton(
            "検索オプションを表示", on_click=toggle_search_area,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6), padding=ft.padding.all(0))
        )

        return ft.View(
            "/accesslogs",
            controls=[
                ft.Text("入/退室ログ閲覧画面", size=30, weight=ft.FontWeight.BOLD),
                toggle_btn,
                search_area,
                ft.Container(height=30),
                scroll_table,
                pagination_controls,
                back_btn,
            ],
            padding=ft.Padding(left=70, top=20, right=0, bottom=20)
        )
    except Exception as e:
        logger.exception("ログ閲覧画面の表示中にエラーが発生しました: %s", e)
        page.go("/index?error=ログ閲覧画面の表示中にエラーが発生しました")
    finally:
        page.update()
