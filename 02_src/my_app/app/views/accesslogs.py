from datetime import datetime
import flet as ft
import app.models.db_manager as db


def accesslogs(page: ft.Page):
    
    snack = ft.SnackBar(
           content=ft.Text("", color=ft.Colors.WHITE),
           bgcolor=ft.Colors.RED_400,
           duration=2000
        )
    page.snack_bar = snack
    
    def change_date(e):
        if start_date.value:
            startdate_btn.text = f"{start_date.value.strftime('%Y-%m-%d')}"
        if end_date.value:
            enddate_btn.text = f"{end_date.value.strftime('%Y-%m-%d')}"
        page.update()
        
    page.locale_configuration = ft.LocaleConfiguration(
        supported_locales=[
            ft.Locale("ja", "JP"),
            ft.Locale("en", "US")
        ], 
        current_locale=ft.Locale("ja", "JP")
    )
    
    page.title = "ログ閲覧画面"

    searchcardname = ft.TextField(label="カード名",width=200,height=40)
    searchmethod = ft.Dropdown(label="認証方式")
    searchmethod.options = [
        ft.DropdownOption("カード", "カード"),
        ft.DropdownOption("Web", "Web"),
    ]
    
    start_date = ft.DatePicker(on_change=change_date,)
    end_date = ft.DatePicker(on_change=change_date)

    hours = [str(i).zfill(2) for i in range(24)]
    minutes = [str(i).zfill(2) for i in range(0, 60, 1)]
    
    start_hour = ft.Dropdown(label="何時", options=[ft.DropdownOption(h, h) for h in hours],width=100,text_style=ft.TextStyle(size=12))
    start_minute = ft.Dropdown(label="何分", options=[ft.DropdownOption(m, m) for m in minutes],width=100,text_style=ft.TextStyle(size=12))

    end_hour = ft.Dropdown(label="何時", options=[ft.DropdownOption(h, h) for h in hours],width=100,text_style=ft.TextStyle(size=12))
    end_minute = ft.Dropdown(label="何分", options=[ft.DropdownOption(m, m) for m in minutes],width=100,text_style=ft.TextStyle(size=12))

    searcheventtype = ft.Dropdown(label="入室/退室")
    searcheventtype.options = [
        ft.DropdownOption("0", "入室"),
        ft.DropdownOption("1", "退室"),
    ]
        
    def get_datetime(date_picker, hour_dropdown, minute_dropdown,is_start=True):
        
        date = date_picker.value
        hour = hour_dropdown.value if hour_dropdown.value not in (None, "") else None
        minute = minute_dropdown.value if minute_dropdown.value not in (None, "") else None
        
        if date is None and (hour is not None or minute is not None):
            
            snack.content = ft.Text("日付を選択してください")
            page.open(snack)
            page.update()
            return None

        elif date is not None and hour is None and minute is not None:
            snack.content = ft.Text("時間を選択してください")
            page.open(snack)
            page.update()
            return None
        
        elif date is None:
            return None
        
        if hour is None and minute is None:
            hour = "00" if is_start else "23"
            minute = "00" if is_start else "59"
            second = "00" if is_start else "59"

        else:
            hour = hour if hour is not None else "00"
            minute = minute if minute is not None else "00"
            second = "00"
            
        datetime_str = f"{date.strftime('%Y-%m-%d')} {hour}:{minute}:{second}"
        return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")

    def search_logs(e):
        
        search_method = searchmethod.value.strip() if searchmethod.value else None
        search_cardname = searchcardname.value.strip() if searchcardname.value else None
        search_eventtype = int(searcheventtype.value.strip()) if searcheventtype.value else None

        
        start_dt = get_datetime(start_date, start_hour, start_minute,is_start=True)
        end_dt = get_datetime(end_date, end_hour, end_minute,is_start=False)

        if start_dt and end_dt and end_dt < start_dt:
            snack.content = ft.Text("終了日時は開始日時以降にしてください")
            page.open(snack)
            page.update()
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

    search_btn = ft.ElevatedButton("検索", on_click=search_logs)
    
    def show_all_logs(e):
        load_table()

    show_all_btn = ft.ElevatedButton("全件表示", on_click=show_all_logs)
    startdate_btn = ft.ElevatedButton(text = "開始日を選択", on_click=lambda e: open_datepicker(start_date))
    enddate_btn = ft.ElevatedButton(text = "終了日を選択", on_click=lambda e: open_datepicker(end_date))
    
    table = ft.DataTable(
        bgcolor=ft.Colors.LIGHT_BLUE_50,
        heading_row_color=ft.Colors.BLUE_100,
        column_spacing=100,
        border=ft.border.all(1, ft.Colors.GREY_400),
        border_radius=12,                          
        heading_row_height=50,
        columns=[
            ft.DataColumn(ft.Text("ログID", weight="bold", size=14)),
            ft.DataColumn(ft.Text("カード名", weight="bold", size=14)),
            ft.DataColumn(ft.Text("認証方式", weight="bold", size=14)),
            ft.DataColumn(ft.Text("入退室の日時", weight="bold", size=14)),
            ft.DataColumn(ft.Text("区分", weight="bold", size=14)),
        ],
        rows=[]
    )
     
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

    page.overlay.append(start_date)
    page.overlay.append(end_date)
    
     # 検索エリアの Column（非表示で初期化）
    search_area = ft.Container(
        content=ft.Column(
            [
                ft.Row([searchcardname, searchmethod, searcheventtype], spacing=20),
                ft.Row([ft.Text("開始日時:", width=80), startdate_btn, start_hour, start_minute], spacing=10),
                ft.Row([ft.Text("終了日時:", width=80), enddate_btn, end_hour, end_minute], spacing=10),
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
    
    card = ft.Card(
        content=ft.Container(
            padding=20,
            width=1000,
            alignment=ft.alignment.center,
            border_radius=12,

            content=ft.Column([
                ft.Text("入/退室ログ閲覧画面", size=24, weight="bold"),
                toggle_btn,
                search_area,
                table,
                ft.ElevatedButton("戻る", on_click=lambda e: page.go("/index")),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            )
        )
    )
   
    
    return ft.View(
        "/accesslogs",
        padding=20,
        bgcolor=ft.Colors.WHITE,
        vertical_alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=20,
       
        
        # 画面のコントロール
        # ここにコントロールを追加していく
         controls=[
            card,
        ]
    )
 