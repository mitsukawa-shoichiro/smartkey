import datetime
import flet as ft

def main(page: ft.Page):
    # 日本語ロケール設定（省略可）
    page.locale_configuration = ft.LocaleConfiguration(
        supported_locales=[ft.Locale("ja", "JP"), ft.Locale("en", "US")],
        current_locale=ft.Locale("ja", "JP"),
    )

    # 表示用のテキスト
    selected_date_text = ft.Text("選択された日付がここに表示されます")

    def change_date(e):
        selected_date = date_picker.value
        date_button.text = f"{selected_date.strftime('%Y-%m-%d')}"
        page.update()  # ページを更新して表示を反映

    def date_picker_dismissed(e):
        print(f"Date picker dismissed: {date_picker.value}")

    today = datetime.date.today()

    # DatePicker を作成
    date_picker = ft.DatePicker(
        on_change=change_date,
        on_dismiss=date_picker_dismissed
    )

    # ボタンをクリックしたら DatePicker を開く
    date_button = ft.ElevatedButton(
        text="日付を選択",
        icon=ft.Icons.CALENDAR_MONTH,
        on_click=lambda e: page.open(date_picker),
    )

    # 画面に追加
    page.add(
        date_button,
        selected_date_text  # 選択結果を表示するテキスト
    )

ft.app(target=main)
