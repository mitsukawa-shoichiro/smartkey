"""
GUI(Flet)の各画面で共有する共通処理をまとめるモジュール(とりまエラー)

repository/service層は例外をraiseで投げっぱなしにする設計(層分けの原則)なので、
GUI層(view)側で必ずtry/exceptで受け止め、ユーザーに分かる形で表示する必要があります。
この受け止め方(エラーダイアログの出し方)を1箇所にまとめ、各画面から使い回してください。
"""
import flet as ft
from utils import japanese_text as jt

def show_error_dialog(page: ft.Page, message: str):
    """
    予期しないエラー(DBエラー等)が起きた時、ユーザーに分かる形で伝える共通ダイアログ。
    詳細な原因はlogger側に出す想定で、ここでは利用者向けの平易なメッセージのみ表示します。

    Args:
        page (ft.Page): 表示先のページ
        message (str): ユーザーに見せるメッセージ(内部エラーの詳細は含めない)
    """
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("エラー"),
        content=ft.Text(message),
        actions=[
            ft.TextButton("閉じる", autofocus=True, on_click=lambda e: page.close(dialog)),
        ],
    )
    page.open(dialog)



def build_user_option(user) -> ft.AutoCompleteOption:
    """User1件からAutoCompleteOptionを組み立てる(表示は漢字名(カナ名))"""
    return ft.AutoCompleteOption(key=str(user.id), text=f"{user.user_name}({user.user_kana})")


def filter_user_options(users, query: str):
    """
    ユーザー一覧をひら/カナ/ローマ字でも検索効くようにするフィルタ
    on_change等から呼び出して使ってください。
    Args:
        users (List[User]): ユーザーデータクラスのリスト
        query (str): 検索キーワード

    Returns:
        list[ft.AutoCompleteOption]: プルダウン形式のリスト
    """
    # 検索が空欄時
    if not query:
        return [build_user_option(u) for u in users]

    return [
        build_user_option(u) for u in users
        if jt.matches(query, u.user_name, u.user_kana)
    ]