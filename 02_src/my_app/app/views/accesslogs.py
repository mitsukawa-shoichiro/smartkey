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
    
    start_hour = ft.Dropdown(label="何時", options=[ft.DropdownOption(h, h) for h in hours],width=100)
    start_minute = ft.Dropdown(label="何分", options=[ft.DropdownOption(m, m) for m in minutes],width=100)

    end_hour = ft.Dropdown(label="何時", options=[ft.DropdownOption(h, h) for h in hours],width=100)
    end_minute = ft.Dropdown(label="何分", options=[ft.DropdownOption(m, m) for m in minutes],width=100)

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

    startdate_btn = ft.ElevatedButton(text = "開始日を選択", on_click=lambda e: open_datepicker(start_date))
    enddate_btn = ft.ElevatedButton(text = "終了日を選択", on_click=lambda e: open_datepicker(end_date))
    
    table = ft.DataTable(
        # width=1500,
        # bgcolor=ft.Colors.LIGHT_BLUE_50,
        # border=ft.border.all(2, ft.Colors.BLACK),
        # border_radius=10,
        # vertical_lines=ft.border.BorderSide(3, ft.Colors.BLACK),
        # horizontal_lines=ft.border.BorderSide(1, ft.Colors.BLACK),
        # sort_column_index=0,
        # sort_ascending=True,
        # heading_row_height=100,
        # data_row_color={ft.ControlState.HOVERED: "0x30FF0000"},
        # show_checkbox_column=True,
        # divider_thickness=0,
        # column_spacing=200,
        
        columns=[
            
            ft.DataColumn(ft.Text("ログID")),
            ft.DataColumn(ft.Text("カード名")),
            ft.DataColumn(ft.Text("認証方式")),
            ft.DataColumn(ft.Text("入室/退室の日時")),
            ft.DataColumn(ft.Text("")),
        ],
        rows=[],
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

    return ft.View(
            "/accesslogs",
            [
                ft.Column([
                    searchcardname,
                    ft.Row([
                    startdate_btn,
                    start_date,
                    start_hour,
                    start_minute,
                ], spacing=10),
                
                ft.Row([
                    enddate_btn,
                    end_date,
                    end_hour,
                    end_minute,
                ], spacing=10),
                ft.Row([
                    searchmethod,
                    searcheventtype,
                ], spacing=10),
                search_btn,
                table,
                ]),
                ft.ElevatedButton("戻る", on_click=lambda e: page.go("/index")),
                
            ],
        )
 