from datetime import datetime
import flet as ft
import app.models.db_manager as db

# ログ閲覧画面
def accesslogs(page: ft.Page):

    dialog = ft.AlertDialog(
        modal=True,
    )
    # 日付の入力値を変換するフォーマット
    def change_start_date(e):
        if start_date.value:
            startdate_btn.text = f"{start_date.value.strftime('%Y-%m-%d')}"
            page.update()
        
    def change_end_date(e):
        if end_date.value:
            enddate_btn.text = f"{end_date.value.strftime('%Y-%m-%d')}"
            page.update()
        
    # 時刻の入力値を変換するフォーマット
    def change_start_time(e):
        if start_time.value:
            starttime_btn.text = f"{start_time.value.strftime('%H:%M')}"
            page.update()
        
    def change_end_time(e):
        if end_time.value:
            endtime_btn.text = f"{end_time.value.strftime('%H:%M')}"
            page.update()
        
    # 日付入力のロケール設定
    page.locale_configuration = ft.LocaleConfiguration(
        supported_locales=[
            ft.Locale("ja", "JP"),
            ft.Locale("en", "US")
        ], 
        current_locale=ft.Locale("ja", "JP")
    )
    
    page.title = "ログ閲覧画面"

    # 検索フィールドの定義
    searchcardname = ft.TextField(label="カード名",width=200,height=40)
    searchmethod = ft.Dropdown(label="認証方式")
    searchmethod.options = [
        ft.DropdownOption("カード", "カード"),
        ft.DropdownOption("Web", "Web"),
    ]
    
    start_date = ft.DatePicker(on_change=change_start_date)
    end_date = ft.DatePicker(on_change=change_end_date)

    start_time = ft.TimePicker(on_change=change_start_time)
    end_time = ft.TimePicker(on_change=change_end_time)

    searcheventtype = ft.Dropdown(label="入室/退室")
    searcheventtype.options = [
        ft.DropdownOption("0", "入室"),
        ft.DropdownOption("1", "退室"),
    ]

    # 入力された日付と時刻を結合してdatetimeオブジェクトを生成する関数
    def get_datetime(date_picker, time_picker, is_start=True):

        date = date_picker.value
        time = time_picker.value

        if date is None and time is not None:

            dialog.title = ft.Text("エラー")
            dialog.content = ft.Text("日付が選択されていません。")
            dialog.actions = [
                ft.TextButton("閉じる", on_click=lambda e: page.close(dialog)),
            ]
            page.open(dialog)
            return None
        
        elif date is None:
            return None
        
        if time is None:
            hour = 0 if is_start else 23
            minute = 0 if is_start else 59
            second = 0 if is_start else 59
            time = datetime.strptime(f"{hour}:{minute}:{second}", "%H:%M:%S").time()

        return datetime.combine(date, time)

    # 検索結果を表示するためのテーブル
    def search_logs(e):
        
        search_method = searchmethod.value.strip() if searchmethod.value else None
        search_cardname = searchcardname.value.strip() if searchcardname.value else None
        search_eventtype = int(searcheventtype.value.strip()) if searcheventtype.value else None

        start_dt = get_datetime(start_date, start_time,is_start=True)
        end_dt = get_datetime(end_date, end_time,is_start=False)

        # 入力された日時の検証
        if start_dt and end_dt and end_dt < start_dt:
            dialog.title = ft.Text("エラー")
            dialog.content = ft.Text("終了日時が開始日時以降にされていません。")
            dialog.actions = [
                ft.TextButton("閉じる", on_click=lambda e: page.close(dialog)),
            ]
            page.open(dialog)
            return
    
        logs = db.findLog(search_cardname, search_method, search_eventtype,start_dt,end_dt)

        table.rows.clear()
        for log in logs:
            id, cardname, method,timestamp, eventtype = log
            event_str = "入室" if eventtype == 0 else "退室"
            
            table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(id))),
                        ft.DataCell(ft.Text(cardname)),
                        ft.DataCell(ft.Text(method)),
                        ft.DataCell(ft.Text(timestamp)),
                        ft.DataCell(ft.Text(event_str)),
                    ]
                )
            )

        page.update()
        
    def open_datepicker(picker: ft.DatePicker):
        page.dialog = picker
        picker.open = True
        page.update()

    def open_timepicker(picker: ft.TimePicker):
        page.dialog = picker
        picker.open = True
        page.update()
    
    def show_all_logs(e):
        load_table()

    # ボタン定義
    search_btn = ft.ElevatedButton("検索", on_click=search_logs)
    show_all_btn = ft.ElevatedButton("全件表示", on_click=show_all_logs)
    startdate_btn = ft.ElevatedButton(text = "開始日を選択", on_click=lambda e: open_datepicker(start_date))
    enddate_btn = ft.ElevatedButton(text = "終了日を選択", on_click=lambda e: open_datepicker(end_date))
    starttime_btn = ft.ElevatedButton(text="開始時刻を選択", on_click=lambda e: open_timepicker(start_time))
    endtime_btn = ft.ElevatedButton(text="終了時刻を選択", on_click=lambda e: open_timepicker(end_time))

    # テーブル定義
    table = ft.DataTable(
        columns=[
                    ft.DataColumn(ft.Text("ログID", weight="bold", size=14)),
                    ft.DataColumn(ft.Text("カード名", weight="bold", size=14)),
                    ft.DataColumn(ft.Text("認証方式", weight="bold", size=14)),
                    ft.DataColumn(ft.Text("入退室の日時", weight="bold", size=14)),
                    ft.DataColumn(ft.Text("区分", weight="bold", size=14)),
        ],
        rows=[]
    )
     
    # テーブルの行をロードする関数
    def load_table():

        table.rows.clear()
        logs = db.findAllLog()
        for id, card_name, method, timestamp, eventtype in logs:
        
            if eventtype == 0:
                event_str = "入室"
            elif eventtype == 1:
                event_str = "退室"
            table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(id)),
                        ft.DataCell(ft.Text(card_name)),
                        ft.DataCell(ft.Text(method)),
                        ft.DataCell(ft.Text(timestamp)),
                        ft.DataCell(ft.Text(event_str)),
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
    # 日付と時刻の入力フィールド
    page.overlay.append(start_date)
    page.overlay.append(end_date)
    page.overlay.append(start_time)
    page.overlay.append(end_time)
    
     # 検索エリアの Column（非表示で初期化）
    search_area = ft.Container(
        content=ft.Column(
            [
                ft.Row([searchcardname, searchmethod, searcheventtype], spacing=20),
                ft.Row([ft.Text("開始日時:", width=80), startdate_btn, starttime_btn], spacing=10),
                ft.Row([ft.Text("終了日時:", width=80), enddate_btn, endtime_btn], spacing=10),
                ft.Row([search_btn,show_all_btn], alignment=ft.MainAxisAlignment.END, spacing=20),
            ],
            spacing=15,
            horizontal_alignment=ft.CrossAxisAlignment.START
        ),
        padding=20,
        bgcolor=ft.Colors.GREY_100,
        border_radius=12,
        width=800,
        visible=False
    )

    # トグルボタンで表示/非表示切り替え
    def toggle_search_area(e):
        search_area.visible = not search_area.visible
        toggle_btn.text = "検索オプションを隠す" if search_area.visible else "🔍 検索オプション表示"
        page.update()

    toggle_btn = ft.ElevatedButton("🔍 検索オプションを表示", on_click=toggle_search_area)
   
    return ft.View(
        "/accesslogs",
         controls=[
            ft.Text("入/退室ログ閲覧画面", size=24, weight="bold"),
            toggle_btn,
            search_area,
            scroll_table,
            ft.ElevatedButton("戻る", on_click=lambda e: page.go("/index")),
        ]
    )
 