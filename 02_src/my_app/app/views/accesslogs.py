from datetime import datetime,date,time,timedelta
import flet as ft
import db.repository as repo
import asyncio
import logging
from app.models.ENUMS import EventType

# テーブルの1ページが表示する件数
ITEMS_PER_PAGE = 100
logger = logging.getLogger(__name__)
# ログ閲覧画面
def accesslogs(page: ft.Page):
    try:
        page.title = "ログ閲覧画面"

        current_page = 0           # 現在のページ（0‑origin）
        total_pages = 1            # 総ページ数（動的に計算）
        search_mode = False        # False: 全件モード / True: 検索モード
        search_params = {          # 検索条件を保持
            "user_name": None,
            "method": None,
            "eventtype": None,
            "start_dt": None,
            "end_dt": None,
        }

        # エラーの際に表示するダイアログの初期設定
        dialog = ft.AlertDialog(
            modal=True,
        )

        # 総ページ数の計算
        def calc_total_pages(count: int):
            nonlocal total_pages
            total_pages = max(1, (count + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

        # 日付の入力値を変換するフォーマット
        def change_start_date(e):
            if start_date.value:
                start_time.open = True
                open_timepicker(start_time)
                page.update()

        def change_end_date(e):
            if end_date.value:
                end_time.open = True
                open_timepicker(end_time)
                page.update()

        # 日付入力のロケール設定
        page.locale_configuration = ft.LocaleConfiguration(
            supported_locales=[
                ft.Locale("ja", "JP"),
                ft.Locale("en", "US")
            ],
            current_locale=ft.Locale("ja", "JP")
        )

        # 検索フィールドの定義
        searchcardname = ft.TextField(label="カード名",width=200,height=48)
        searchmethod = ft.DropdownM2(label="認証   方式",value=None,width=85,height=45)
        searchmethod.options = [
            ft.DropdownOption("カード", "カード"),
            ft.DropdownOption("Web", "Web"),
        ]
        today = date.today()
        start_date = ft.DatePicker(on_change=change_start_date,date_picker_entry_mode=ft.DatePickerEntryMode.INPUT
                                ,first_date=today - timedelta(days=365),last_date=today)
        end_date = ft.DatePicker(on_change=change_end_date,date_picker_entry_mode=ft.DatePickerEntryMode.INPUT
                                ,first_date=today - timedelta(days=365),last_date=today)

        start_time = ft.TimePicker(value=time(0, 0), on_change=lambda e: update_start_textbox(),time_picker_entry_mode=ft.TimePickerEntryMode.INPUT)
        end_time = ft.TimePicker(value=time(23, 59), on_change=lambda e: update_end_textbox(),time_picker_entry_mode=ft.TimePickerEntryMode.INPUT)

        start_text = ft.TextField(label="開始日時", width=200, height=48)
        end_text = ft.TextField(label="終了日時", width=200, height=48)

        searcheventtype = ft.DropdownM2(label="入室/  退室",value=None,width=85,height=45)
        searcheventtype.options = [
            ft.DropdownOption("0", "入室"),
            ft.DropdownOption("1", "退室"),
        ]

        # 検索結果を表示するためのテーブル
        def search_logs(e):
            nonlocal current_page, search_mode, search_params

            # 値が入力されなかった場合はNoneを返す
            search_method = searchmethod.value.strip() if searchmethod.value else None
            search_user_name = searchcardname.value.strip() if searchcardname.value else None
            search_eventtype = int(searcheventtype.value.strip()) if searcheventtype.value else None

            start_dt = None
            end_dt = None
            first_date=today - timedelta(days=365)
            last_date=today

            try: #開始日時が入力された場合はフォーマットに直す（秒数は00秒）
                if  start_text.value:
                    start_dt = datetime.strptime(start_text.value, "%Y-%m-%d %H:%M")
                    start_dt = start_dt.replace(second=0)

                #終了日時が入力された場合はフォーマットに直す（秒数は00秒）
                if  end_text.value:
                    end_dt = datetime.strptime(end_text.value, "%Y-%m-%d %H:%M")
                    end_dt = end_dt.replace(second=59)

                #終了日時が開始日時より前に設定された場合にエラー表示
                if start_dt and end_dt and end_dt < start_dt:
                    dialog.title = ft.Text("エラー")
                    dialog.content = ft.Text("終了日時が開始日時以降にされていません。")
                    dialog.actions = [
                        ft.TextButton("閉じる", on_click=lambda e: page.close(dialog)),
                    ]
                    page.open(dialog)
                    return

                #開始日時が一年以上前または本日以降の場合にエラー表示
                if start_dt and (start_dt.date() < first_date or start_dt.date() > last_date):
                    dialog.title = ft.Text("エラー")
                    dialog.content = ft.Text(f"開始日時が範囲外です。\n検索範囲は {first_date.strftime('%Y-%m-%d 00:00')} から{last_date.strftime('%Y-%m-%d 23:59')}までです。")
                    dialog.actions = [
                        ft.TextButton("閉じる", on_click=lambda e: page.close(dialog)),
                    ]
                    page.open(dialog)
                    return

                #終了日時が一年以上前または本日以降の場合にエラー表示
                if end_dt and (end_dt.date() > last_date or end_dt.date() < first_date):
                    dialog.title = ft.Text("エラー")
                    dialog.content = ft.Text(f"終了日時が範囲外です。 \n検索範囲は{first_date.strftime('%Y-%m-%d 00:00')} から{last_date.strftime('%Y-%m-%d 23:59')}までです。")
                    dialog.actions = [
                        ft.TextButton("閉じる", on_click=lambda e: page.close(dialog)),
                    ]
                    page.open(dialog)
                    return

            #フォーマットに沿っていない入力がされた場合、エラー表示
            except ValueError:
                dialog.title = ft.Text("エラー")
                dialog.content = ft.Text("日時のフォーマットが正しくありません。")
                dialog.actions = [
                    ft.TextButton("閉じる", on_click=lambda e: page.close(dialog)),
                ]
                page.open(dialog)
                return

            #検索条件に値を保持
            search_params = {
                "user_name": search_user_name,
                "method": search_method,
                "eventtype": search_eventtype,
                "start_dt": start_dt,
                "end_dt": end_dt,
            }
            #検索モードに切り替え
            search_mode = True
            current_page = 0

            # 件数取得→総ページ
            cnt = repo.count_filtered_logs(search_user_name, search_method,search_eventtype, start_dt, end_dt)
            calc_total_pages(cnt)

            # テーブルロード
            load_table(current_page)
            scroll_table.scroll_to(offset=0, duration=0)

        #ソートを切り替え、ページをリセットし、新しい順で再描画
        async def toggle_sort(e):
            nonlocal current_page
            table.sort_ascending = not table.sort_ascending
            current_page = 0
            scroll_table.visible=False
            scroll_table.update()
            await asyncio.sleep(0.01)
            scroll_table.visible=True
            scroll_table.update()
            load_table(current_page)

        #toggle_sortの呼び出し
        async def on_sort(e):
            await toggle_sort(e)

        #全件検索してテーブルに表示
        def show_all_logs(e):
            nonlocal current_page,search_params
            current_page = 0
            search_params = {          # 検索条件を保持
            "user_name": None,
            "method": None,
            "eventtype": None,
            "start_dt": None,
            "end_dt": None,
            }
            reset(e)
            calc_total_pages(repo.count_filtered_logs())
            load_table(current_page)

        #日時入力のピッカーを開く処理
        def open_datepicker(picker: ft.DatePicker):
            page.dialog = picker
            picker.open = True
            page.update()

        def open_timepicker(picker: ft.TimePicker):
            page.dialog = picker
            picker.open = True
            page.update()

        #検索欄のリセット
        def reset(e):
            searchcardname.value = ""
            searchmethod.value = None
            searcheventtype.value = None
            start_text.value = ""
            end_text.value = ""
            start_date.value = None
            end_date.value = None
            start_time.value = time(0,0)
            end_time.value = time(23,59)
            page.update()

        #日時で入力された値をテキストボックスに表示する（日時どちらも入力された場合のみ）
        def update_start_textbox():
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

        #フォーマットの変換
        start_date.on_change = change_start_date
        end_date.on_change = change_end_date

        # ボタン定義
            #ページ遷移用のボタン
        page_label = ft.Text("")  # 後で更新
        prev_btn = ft.ElevatedButton("⬅ 前へ",   on_click=lambda e: prev_page(e),style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)))
        next_btn = ft.ElevatedButton("次へ ➡",   on_click=lambda e: next_page(e),style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)))
        pagination_controls = ft.Row([prev_btn, page_label, next_btn], alignment=ft.MainAxisAlignment.CENTER)

            #検索ボタン
        search_btn = ft.ElevatedButton(
            text="検索",
            icon=ft.Icons.SEARCH,
            on_click=search_logs,
            width=80,
            height=40,
            bgcolor=ft.Colors.GREY_50,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=6),
                padding=ft.padding.all(0)
            ),
        )
            #全件検索ボタン
        show_all_btn = ft.ElevatedButton(
            text="全件表示",
            on_click=show_all_logs,
            width=80,
            height=40,
            bgcolor=ft.Colors.GREY_50,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=6),
                padding=ft.padding.all(0)
            ),
        )
            #開始日時入力ボタン
        startdate_btn = ft.ElevatedButton(text = "開始日時を選択",
                                        icon=ft.Icons.DATE_RANGE,
                                        on_click=lambda e: open_datepicker(start_date),
                                        style=ft.ButtonStyle(
                                            shape=ft.RoundedRectangleBorder(radius=6),
                                        )
                    )
            #終了日時入力ボタン
        enddate_btn = ft.ElevatedButton(text = "終了日時を選択",
                                        icon=ft.Icons.DATE_RANGE,
                                        on_click=lambda e: open_datepicker(end_date),
                                        style=ft.ButtonStyle(
                                            shape=ft.RoundedRectangleBorder(radius=6),
                                        )
                    )
            #クリアボタン
        reset_btn = ft.ElevatedButton(
            text="クリア",
            on_click=reset,
            width=80,
            height=40,
            bgcolor=ft.Colors.GREY_50,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=6),
                color=ft.Colors.RED,
                overlay_color=ft.Colors.RED_100,
                padding=ft.padding.all(0)
            ),
        )
            #戻るボタン
        back_btn = ft.ElevatedButton(
                        "戻る",
                        icon=ft.Icons.ARROW_BACK,
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=6),
                        ),
                        on_click=lambda e: page.go("/index"),
                    )

        #ソートに使用する項目
        timestamp_row = ft.Row([ft.Text("入退室の日時", weight="bold", size=14)])

        # テーブル定義
        table = ft.DataTable(
            columns=[
                        # ft.DataColumn(ft.Text("ログID", weight="bold", size=14)),
                        ft.DataColumn(ft.Text("ユーザー名_カード名", weight="bold", size=14)),
                        ft.DataColumn(ft.Text("認証方式", weight="bold", size=14)),
                        ft.DataColumn(timestamp_row, on_sort=on_sort),  #入退室の日時でソート
                        ft.DataColumn(ft.Text("区分", weight="bold", size=14)),
            ],
            rows=[],
            sort_column_index=2,
            sort_ascending=False,
        )

        # テーブルの行をロードする関数
        def load_table(page_num: int):

            table.rows.clear()  #テーブルをクリア
            offset = page_num * ITEMS_PER_PAGE  #取得する項目の先頭を計算

            #取得する件数と場所、順番を考慮し検索
            logs = repo.find_log(
                    search_params["method"], search_params["eventtype"],
                    search_params["start_dt"], search_params["end_dt"],
                    ITEMS_PER_PAGE, offset,table.sort_ascending
            )
            #テーブル表示 todo 怪しい香り、後回し
            for log in logs:
                event_str = "入室" if log.event_type == EventType.ENTRY else "退室"
                card_type = repo.find_card_type_by_id(log.card_id) if log.card_id else ""
                table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(log.user_name + "_" + card_type, width=280)),
                        ft.DataCell(ft.Text(log.method, width=80)),
                        ft.DataCell(ft.Text(log.timestamp, width=140)),
                        ft.DataCell(ft.Text(event_str, width=80)),
                    ])
                )

            #全体ページ数と現在のページを表示し、前へボタンと次へボタンを押下可能にするか判断
            page_label.value = f"{current_page+1} / {total_pages} ページ"
            prev_btn.disabled = current_page == 0
            next_btn.disabled = (current_page+1) >= total_pages
            page.update()

        if not search_mode:
            calc_total_pages(repo.count_filtered_logs())

        #該当ページのログを取得
        load_table(current_page)

        #合計ページ数を計算
        def calc_total_pages(count: int):
            nonlocal total_pages
            total_pages = max(1, (count + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

        #次のページの先頭へ移動
        def next_page(e):
            nonlocal current_page
            if (current_page + 1) < total_pages:
                current_page += 1
                load_table(current_page)
                scroll_table.scroll_to(offset=0, duration=0)

        #前のページの先頭へ移動
        def prev_page(e):
            nonlocal current_page
            if current_page > 0:
                current_page -= 1
                load_table(current_page)
                scroll_table.scroll_to(offset=0, duration=0)

        # 日付と時刻の入力フィールド
        page.overlay.append(start_date)
        page.overlay.append(end_date)
        page.overlay.append(start_time)
        page.overlay.append(end_time)

        # 検索エリアの Column（非表示で初期化）
        search_area = ft.Container(
            content=ft.Column(
                [
                    ft.Row([searchcardname, searchmethod,
                            ft.Container(searcheventtype, margin=ft.margin.only(right=56)),reset_btn
                    ]),
                    ft.Row([startdate_btn,
                            ft.Container(start_text, margin=ft.margin.only(right=98)),search_btn
                    ]),
                    ft.Row([enddate_btn,
                            ft.Container(end_text, margin=ft.margin.only(right=98)),show_all_btn
                    ])
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
        scroll_table = ft.Column(
            controls=[table],
            scroll=ft.ScrollMode.ALWAYS,
            expand=True
        )

        # トグルボタンで表示/非表示切り替え
        def toggle_search_area(e):
            search_area.visible = not search_area.visible
            toggle_btn.text = "検索オプションを閉じる" if search_area.visible else "検索オプションを開く"
            page.update()

        toggle_btn = ft.ElevatedButton("検索オプションを表示",
                                    on_click=toggle_search_area,
                                    style=ft.ButtonStyle(
                                            shape=ft.RoundedRectangleBorder(radius=6),
                                            padding=ft.padding.all(0)
                                        )
                    )

        #ビューの設定
        return ft.View(
            "/accesslogs",
            controls=[
                ft.Text("入/退室ログ閲覧画面",size=30, weight=ft.FontWeight.BOLD),
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