"""
GUI(Flet)の各画面で共有する共通処理をまとめるモジュール。

repository/service層は例外をraiseで投げっぱなしにする設計(層分けの原則)なので、
GUI層(view)側で必ずtry/exceptで受け止め、ユーザーに分かる形で表示する必要がある。
この受け止め方(エラーダイアログの出し方)を1箇所にまとめ、各画面から使い回す。
"""
import flet as ft
from app.utils import japanese_text as jt

# =====================================================================
# デザイン定義
# =====================================================================

class Theme:
    """テーマ、属性"""
    # 背景色
    BG = "#F4F6FA"
    SURFACE = "#FFFFFF"
    # アクセントポイント(強調色)
    PRIMARY = "#3B5BDB"
    PRIMARY_DARK = "#2F49AE"
    # テキスト
    TEXT = "#1F2933"
    TEXT_MUTED = "#7B8794"
    # 状態色
    DANGER = "#E03131"
    # テーブル
    HEADING_BG = "#EEF2F8"
    ROW_HOVER = "#F7F9FC"
    BORDER = "#E5E9F0"
    # 形状
    RADIUS = 16 # カード等大きめのものの角丸
    RADIUS_SM = 8 # ボタン等小さめのものの角丸

def card_shadow():
    """カードに乗せる用の影"""
    return ft.BoxShadow(
        spread_radius=0,
        blur_radius=0,
        color="#1F000000",# 駄目だったらcolor="#1F000000"に
        offset=ft.Offset(0, 6),
    )



# =====================================================================
# 共通部品
# =====================================================================

def card(content, col=None, padding: int = 24):
    """
    かっこいいカード共通部品！
    Args:
        content (_type_): カードの中身
        col (_type_, optional): ResponsiveRowで使う列幅. デフォルトは幅いっぱいまで
        padding (int, optional): カード内側に空ける余白. Defaults to 24.
    """
    return ft.Container(
        content=content,
        padding=padding,
        bgcolor=Theme.SURFACE,
        border_radius=Theme.RADIUS,
        shadow=card_shadow(),
        col=col,
    )


def section_title(text: str, subtitle: str = None):
    """
    見出し、タイトル + サブタイトル(説明)
    左端にアクセントカラーバー
    """
    title_row = ft.Row(
        controls=[
            ft.Container(width=4, height=22, bgcolor=Theme.PRIMARY, border_radius=2),
            ft.Text(text, size=20, weight=ft.FontWeight.BOLD, color=Theme.TEXT),
        ],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    if not subtitle:
        return title_row
    return ft.Column(
        controls=[
            title_row,
            ft.Text(subtitle, size=13, color=Theme.TEXT_MUTED),
        ],
        spacing=4,
    )


def responsive_cards(cards_with_cols):
    """
    複数カードをウィンドウ幅に合わせて並べるレスポンシブグリッド。
    Args:
        cards_with_cols (_type_): [(content, col_dict), ...]のリスト

    Returns:
        ft.ResponsiveRow
    """
    return ft.ResponsiveRow(
        controls=[card(content, col=col) for content, col in cards_with_cols],
        run_spacing=16,
        spacing=16,
    )


def primary_button(text: str, on_click, icon=None):
    """アクセントカラーのメインボタン(登録等を想定)"""
    return ft.ElevatedButton(
        text=text,
        icon=icon,
        on_click=on_click,
        bgcolor="#FFFFFF",
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=Theme.RADIUS_SM),
            padding=ft.padding.symmetric(horizontal=20, vertical=16),
        ),
    )

_CARD_TYPE_COLORS = {
    "クレジットカード": ("#E7F0FF", "#2F49AE"),
    "交通系ICカード": ("#E6F7EE", "#1B7F4B"),
    "その他": ("#E7F0FF", "#5A6675"),
}

def card_type_badge(card_type_value: str):


def show_error_dialog(page: ft.Page, message: str, go_home: bool = False):
    """
    予期しないエラー(DBエラー等)が起きた時、ユーザーに分かる形で伝える共通ダイアログ。
    詳細な原因はlogger側に出す想定で、ここでは利用者向けの平易なメッセージのみ表示する。

    Args:
        page (ft.Page): 表示先のページ
        message (str): ユーザーに見せるメッセージ(内部エラーの詳細は含めない)
        go_home (bool): Trueなら「閉じる」を押した後にホーム(/index)へ遷移する。
                        Falseならダイアログを閉じるだけで、その画面に留まる(デフォルト)。
    """
    def on_close(e):
        page.close(dialog)
        if go_home:
            page.go("/index")

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("エラー"),
        content=ft.Text(message),
        actions=[
            ft.TextButton("閉じる", autofocus=True, on_click=on_close),
        ],
    )
    page.open(dialog)


def build_user_option(user) -> ft.AutoCompleteSuggestion:
    """
    User1件からAutoCompleteSuggestionを組み立てる。

    重要: Flet の AutoComplete は「key」に対してユーザー入力をマッチング
    (部分一致・大文字小文字無視)する。「value」は選択後に入力欄へ表示される
    だけで、絞り込み対象ではない。そのため:

    key:   検索対象にしたい文字列を全部入れる。漢字・カタカナ・ひらがな・ローマ字を
        連結し、さらに末尾に "#<user_id>" を付けて、選択時にuser_idを復元できるようにする。
        例: "山田太郎 ヤマダタロウ やまだたろう yamadatarou #1"
        (これで「やまだ」「ヤマダ」「yamada」「山田」いずれの入力でもヒットする)
    value: 入力欄に表示される名前。人が見て分かる表示用。
        例: "山田太郎(ヤマダタロウ)"
    """
    romaji = jt.katakana_to_romaji(user.user_kana)
    hiragana = jt.katakana_to_hiragana(user.user_kana)
    key = f"{user.user_name} {user.user_kana} {hiragana} {romaji} #{user.id}"
    value = f"{user.user_name}({user.user_kana})"
    return ft.AutoCompleteSuggestion(key=key, value=value)


def extract_user_id_from_key(key: str) -> int:
    """
    build_user_option が作った key の末尾 "#<user_id>" から user_id を取り出す。
    """
    return int(key.rsplit("#", 1)[1])


def build_user_autocomplete(users, on_selected):
    """
    ユーザー検索用のAutocompleteを組み立てて返す共通部品。
    各画面はこれを呼ぶだけで、同じ検索UIを使える(Thymeleafのフラグメント的な使い方)。

    絞り込みはFletのAutoComplete標準機能(keyに対する部分一致)に任せる。
    keyに漢字・カナ・ローマ字を含めてあるので、表記ゆれに対応できる。
    選択されたら、keyの末尾に埋め込んだuser_idを取り出してon_selectedに渡す。

    Args:
        users: 全ユーザー一覧(repo.get_all_users()の結果)
        on_selected: 選択時に呼ばれるコールバック。引数として user_id(int) を受け取る。

    Returns:
        ft.AutoComplete
    """
    def handle_select(e: ft.ControlEvent):
        on_selected(extract_user_id_from_key(e.selection.key))

    return ft.Container(
        width=300,
        content=ft.AutoComplete(
            suggestions=[build_user_option(u) for u in users],
            on_select=handle_select,
        )
    )

def build_card(content, col=None):
    return ft.Container(
        content=content,
        padding=20,
        margin=ft.margin.only(bottom=16),
        bgcolor=ft.colors.WHITE,
        border_radius=16,
        shadow=ft.BoxShadow(
            blur_radius=15,
            color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK),
            offset=ft.offset(0, 4),
        ),
        col=col,
    )