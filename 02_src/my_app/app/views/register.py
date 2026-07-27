"""
カード登録画面GUI作成モジュール
登録処理に関してはView側の負担は最低限にすべく
バックとのやり取り、ロジックはcard_register_service、
状態管理はthread_state、
カード番号受け取り、保管はregister_listener
これらに責務を切り分けています。

未対処リスク

"""


import flet as ft
import asyncio
import logging

import my_app.db.repository as repo
from my_app.service.daemon_bridge import card_register_service as register_service
from my_app.service.daemon_bridge import register_listener
from my_app.models.ENUMS import CardType
from my_app.app.views.common import (
    show_error_dialog,
    build_user_autocomplete,
    Theme,
    app_view,
    card,
    section_title,
    primary_button,
    secondary_button,
    danger_button,
    invalidate_management_counts,
)
from my_app.ui import theme as ui_theme

logger = logging.getLogger(__name__)

async def update_registration_countdown(
    page,
    registration_token,
    countdown_text,
    countdown_bar,
    total_seconds=30,
):
    for remaining in range(total_seconds, -1, -1):
        if (
            getattr(page, "_app_closing", False)
            or page.route.split("?")[0] != "/register"
            or getattr(
                page,
                "_card_registration_token",
                None,
            ) is not registration_token
        ):
            return

        countdown_text.value = (
            f"残り時間: {remaining}秒"
        )
        countdown_bar.value = (
            remaining / max(total_seconds, 1)
        )

        if remaining <= 5:
            color = Theme.DANGER
        elif remaining <= 10:
            color = Theme.SUN
        else:
            color = Theme.SKY

        countdown_text.color = color
        countdown_bar.color = color
        page.update()

        if remaining > 0:
            await asyncio.sleep(1)

# ===================================================
# カード登録待機画面
# ===================================================
def registering(page: ft.Page):
    registration_token = object()
    page._card_registration_token = (
        registration_token
    )

    def stop_loop(_=None):
        if (
            getattr(
                page,
                "_card_registration_token",
                None,
            ) is not registration_token
        ):
            return

        page._card_registration_token = None
        register_service.cancel_registration_session()
        page.go("/card")

    try:
        register_service.start_registration_session()

        loading_text = ft.Text(
            "カード登録を待機しています",
            size=22,
            color=Theme.TEXT,
            weight=ui_theme.FONT_WEIGHT,
            font_family=ui_theme.FONT_FAMILY,
            text_align=ft.TextAlign.CENTER,
        )

        loading_spinner = ft.CupertinoActivityIndicator(
            radius=32,
            color=Theme.SKY,
            animating=True,
        )

        reader_image = ft.Image(
            src="img/card_reader.JPG",
            width=220,
            height=130,
            fit=ft.ImageFit.CONTAIN,
            border_radius=8,
        )

        reader_hint = ft.Text(
            "登録するカードをカードリーダーにかざしてください",
            size=12,
            color=Theme.TEXT_MUTED,
            font_family=ui_theme.FONT_FAMILY,
            text_align=ft.TextAlign.CENTER,
        )

        countdown_bar = ft.ProgressBar(
            value=1,
            width=280,
            height=6,
            color=Theme.SKY,
            bgcolor=Theme.SKY_SOFT,
            border_radius=3,
        )

        countdown_text = ft.Text(
            "残り時間: 30秒",
            size=13,
            color=Theme.SKY,
            font_family=ui_theme.FONT_FAMILY,
        )

        cancel_button = danger_button(
            "キャンセル",
            stop_loop,
            ft.Icons.CLOSE,
        )
        cancel_button.width = 200

        waiting_card = card(
            ft.Column(
                controls=[
                    loading_text,
                    ft.Container(height=8),
                    reader_image,
                    reader_hint,
                    loading_spinner,
                    countdown_bar,
                    countdown_text,
                    ft.Container(height=8),
                    cancel_button,
                ],
                spacing=16,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            accent=Theme.SKY,
            padding=32,
        )

        page.run_task(
            update_registration_countdown,
            page,
            registration_token,
            countdown_text,
            countdown_bar,
        )

        return app_view(
            "/register",
            page,
            [waiting_card],
            back_route="/card",
            on_back=stop_loop,
        )

    except Exception as ex:
        page._card_registration_token = None
        register_service.cancel_registration_session()
        logger.exception(
            "カード登録画面の表示中にエラーが発生しました: %s",
            ex,
        )

        error_card = card(
            ft.Column(
                controls=[
                    ft.Icon(
                        ft.Icons.ERROR_OUTLINE,
                        size=42,
                        color=Theme.DANGER,
                    ),
                    ft.Text(
                        "カード登録を開始できませんでした",
                        color=Theme.DANGER,
                        weight=ui_theme.FONT_WEIGHT,
                        font_family=ui_theme.FONT_FAMILY,
                    ),
                ],
                spacing=14,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            accent=Theme.DANGER,
        )

        return app_view(
            "/register",
            page,
            [error_card],
            back_route="/card",
        )


# ===================================================
# カード番号ポーリングループ待機
# ===================================================

async def delayed_transition(page: ft.Page):

    """
    登録受信待機スレッドを立ち上げ、読み取り結果を受け取る関数
    細かい動きはregister_serviceに任せています。
    """
    registration_token = getattr(
        page,
        "_card_registration_token",
        None,
    )

    # 30秒間読み取り結果を待機
    result = await register_service.wait_for_new_card(
        timeout_total_s=30
    )

    if (
        page.route.split("?")[0] != "/register"
        or getattr(
            page,
            "_card_registration_token",
            None,
        ) is not registration_token
    ):
        return

    page._card_registration_token = None

    # ダイアログ定義
    dialog = ft.AlertDialog(modal=True)

    # キャンセル時
    if result.status == register_service.STATUS_CANCELLED:
        return

    # 二重登録時
    if result.status == register_service.STATUS_DUPLICATE:
        def close_duplicate_dialog(_):
            register_listener.clear_card_number()
            page.close(dialog)
            page.go("/card")

        dialog.title = ft.Text(
            "登録済みのカードです",
            font_family=ui_theme.FONT_FAMILY,
        )
        dialog.content = ft.Column(
            controls=[
                ft.Container(
                    width=58,
                    height=58,
                    bgcolor=Theme.SUN_SOFT,
                    border_radius=29,
                    alignment=ft.alignment.center,
                    content=ft.Icon(
                        ft.Icons.CREDIT_CARD,
                        size=30,
                        color=Theme.SUN,
                    ),
                ),
                ft.Text(
                    "このカードはすでに登録されています",
                    size=15,
                    color=Theme.TEXT,
                    weight=ui_theme.FONT_WEIGHT,
                    font_family=ui_theme.FONT_FAMILY,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "カード管理画面から登録内容を確認してください",
                    size=12,
                    color=Theme.TEXT_MUTED,
                    font_family=ui_theme.FONT_FAMILY,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            spacing=12,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        dialog.actions = [
            ft.TextButton(
                "カード管理へ",
                autofocus=True,
                on_click=close_duplicate_dialog,
            )
        ]
        page.open(dialog)
        return


    # 登録成功時
    if result.status == register_service.STATUS_SUCCESS:
        page.go("/register/input")
        return

    # タイムアウト時
    if result.status == register_service.STATUS_TIMEOUT:
        dialog.title = ft.Text(
            "読み取り時間を超えました",
            font_family=ui_theme.FONT_FAMILY,
        )
        dialog.content = ft.Column(
            controls=[
                ft.Container(
                    width=58,
                    height=58,
                    bgcolor=Theme.SUN_SOFT,
                    border_radius=29,
                    alignment=ft.alignment.center,
                    content=ft.Icon(
                        ft.Icons.TIMER_OFF_OUTLINED,
                        size=30,
                        color=Theme.SUN,
                    ),
                ),
                ft.Text(
                    "30秒以内にカードを確認できませんでした",
                    size=15,
                    color=Theme.TEXT,
                    weight=ui_theme.FONT_WEIGHT,
                    font_family=ui_theme.FONT_FAMILY,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "もう一度読み取りを開始できます",
                    size=12,
                    color=Theme.TEXT_MUTED,
                    font_family=ui_theme.FONT_FAMILY,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            spacing=12,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def retry(e):
        if e.control.disabled:
            return

        e.control.disabled = True
        page.close(dialog)
        page._card_registration_token = None

        retry_number = (
            getattr(
                page,
                "_card_registration_retry_number",
                0,
            )
            + 1
        )
        page._card_registration_retry_number = (
            retry_number
        )

        page.go(
            f"/register?retry={retry_number}"
        )

    def close_timeout(_):
        page._card_registration_token = None
        page.close(dialog)
        page.go("/card")

    dialog.actions = [
        ft.TextButton(
            "もう一度読み取る",
            autofocus=True,
            on_click=retry,
        ),
        ft.TextButton(
            "カード管理へ戻る",
            on_click=close_timeout,
        ),
    ]
    page.open(dialog)

# ===================================================
# カード情報入力画面
# ===================================================

def register_input(page: ft.Page):
    """検知済みのIDmに対して、所有者(user)とカード種別を選んで登録する画面"""
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    selected_user_id = None
    registration_busy = False
    # 読み取り結果を取得
    card_number = register_listener.get_card_number()

    dialog = ft.AlertDialog(modal=True)

    if not card_number:
        def retry_card_scan(_):
            page.go("/register")

        retry_button = primary_button(
            "もう一度読み取る",
            retry_card_scan,
            ft.Icons.REFRESH,
        )
        retry_button.width = 220

        missing_card_card = card(
            ft.Column(
                controls=[
                    ft.Icon(
                        ft.Icons.CREDIT_CARD_OFF,
                        size=48,
                        color=Theme.DANGER,
                    ),
                    ft.Text(
                        "カード情報を確認できませんでした",
                        size=18,
                        color=Theme.TEXT,
                        weight=ui_theme.FONT_WEIGHT,
                        font_family=ui_theme.FONT_FAMILY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "もう一度カードを読み取ってください",
                        size=13,
                        color=Theme.TEXT_MUTED,
                        font_family=ui_theme.FONT_FAMILY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=6),
                    retry_button,
                ],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            accent=Theme.DANGER,
            padding=30,
        )

        return app_view(
            "/register/input",
            page,
            [missing_card_card],
            back_route="/card",
        )

    # ユーザー選択用Autocomplete(face_view.pyと同じパターン)
    users = repo.get_all_users()

    if not users:
        def go_to_face_register(_):
            register_listener.clear_card_number()
            page.go("/face_register")

        def return_to_card_management(_):
            register_listener.clear_card_number()
            page.go("/card")

        face_register_button = primary_button(
            "顔登録へ進む",
            go_to_face_register,
            ft.Icons.PERSON_ADD,
        )
        face_register_button.width = 220

        no_user_card = card(
            ft.Column(
                controls=[
                    ft.Icon(
                        ft.Icons.PERSON_ADD,
                        size=48,
                        color=Theme.SUN,
                    ),
                    ft.Text(
                        "登録できるユーザーがいません",
                        size=18,
                        color=Theme.TEXT,
                        weight=ui_theme.FONT_WEIGHT,
                        font_family=ui_theme.FONT_FAMILY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "先に顔登録から新しいユーザーを登録してください",
                        size=13,
                        color=Theme.TEXT_MUTED,
                        font_family=ui_theme.FONT_FAMILY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=6),
                    face_register_button,
                ],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            accent=Theme.SUN,
            padding=30,
        )

        return app_view(
            "/register/input",
            page,
            [no_user_card],
            back_route="/card",
            on_back=return_to_card_management,
        )

    registration_hint_icon = ft.Icon(
        ft.Icons.PERSON_SEARCH,
        size=20,
        color=Theme.SKY,
    )

    registration_hint_text = ft.Text(
        "カードの所有者を選択してください",
        size=13,
        color=Theme.SKY,
        weight=ui_theme.FONT_WEIGHT,
        font_family=ui_theme.FONT_FAMILY,
    )

    registration_hint = ft.Container(
        width=340,
        padding=ft.padding.symmetric(
            horizontal=14,
            vertical=11,
        ),
        bgcolor=Theme.SKY_SOFT,
        border=ft.border.all(1, Theme.SKY),
        border_radius=10,
        content=ft.Row(
            controls=[
                registration_hint_icon,
                registration_hint_text,
            ],
            spacing=10,
        ),
    )

    def refresh_registration_state(update_page=True):
        is_ready = (
            selected_user_id is not None
            and bool(card_type_dropdown.value)
        )

        register_button.disabled = (
            registration_busy or not is_ready
        )

        if selected_user_id is None:
            values = (
                ft.Icons.PERSON_SEARCH,
                "カードの所有者を選択してください",
                Theme.SKY,
                Theme.SKY_SOFT,
            )
        elif not card_type_dropdown.value:
            values = (
                ft.Icons.CREDIT_CARD,
                "カードの種類を選択してください",
                Theme.SUN,
                Theme.SUN_SOFT,
            )
        else:
            values = (
                ft.Icons.CHECK_CIRCLE_OUTLINE,
                "登録内容を確認できます",
                Theme.MINT,
                Theme.MINT_SOFT,
            )

        icon, message, color, background = values
        registration_hint_icon.name = icon
        registration_hint_icon.color = color
        registration_hint_text.value = message
        registration_hint_text.color = color
        registration_hint.bgcolor = background
        registration_hint.border = ft.border.all(1, color)

        if update_page:
            page.update()

    # ユーザーID保存
    def on_user_selected(user_id: int):
        nonlocal selected_user_id
        selected_user_id = user_id
        refresh_registration_state()

    # プルダウン定義
    user_field = build_user_autocomplete(
        users,
        on_user_selected,
    )

    # カード種類プルダウン定義
    card_type_dropdown = ft.Dropdown(
        label="カードの種類",
        width=320,
        options=[
            ft.dropdown.Option(
                key=ct.value,
                text=ct.value,
            )
            for ct in CardType
        ],
        on_change=lambda _: refresh_registration_state(),
    )

    # 登録確認関数
    def open_add_confirm_dialog(e):
        if registration_busy:
            return
        if selected_user_id is None or not card_type_dropdown.value:
            dialog.title = ft.Text("エラー")
            dialog.content = ft.Text("入力漏れがあります")
            dialog.actions = [
                ft.TextButton("OK", autofocus=True, on_click=lambda e: page.close(dialog)),
            ]
            page.open(dialog)
            return

        selected_user = next(
            (
                user
                for user in users
                if user.id == selected_user_id
            ),
            None,
        )

        if selected_user is None:
            selected_user_name = (
                f"ユーザーID: {selected_user_id}"
            )
        else:
            selected_user_name = (
                f"{selected_user.user_name}"
                f"（{selected_user.user_kana}）"
            )

        dialog.title = ft.Text(
            "カード登録の確認",
            font_family=ui_theme.FONT_FAMILY,
        )
        dialog.content = ft.Column(
            controls=[
                ft.Text(
                    "次の内容でカードを登録します",
                    color=Theme.TEXT_MUTED,
                    font_family=ui_theme.FONT_FAMILY,
                ),
                ft.Container(
                    padding=14,
                    bgcolor=Theme.SKY_SOFT,
                    border_radius=10,
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(
                                        ft.Icons.PERSON_SEARCH,
                                        color=Theme.SKY,
                                        size=20,
                                    ),
                                    ft.Text(
                                        "所有者",
                                        width=70,
                                        color=Theme.TEXT_MUTED,
                                        font_family=ui_theme.FONT_FAMILY,
                                    ),
                                    ft.Text(
                                        selected_user_name,
                                        color=Theme.TEXT,
                                        weight=ui_theme.FONT_WEIGHT,
                                        font_family=ui_theme.FONT_FAMILY,
                                    ),
                                ],
                                spacing=8,
                            ),
                            ft.Row(
                                controls=[
                                    ft.Icon(
                                        ft.Icons.CREDIT_CARD,
                                        color=Theme.SKY,
                                        size=20,
                                    ),
                                    ft.Text(
                                        "カード種類",
                                        width=70,
                                        color=Theme.TEXT_MUTED,
                                        font_family=ui_theme.FONT_FAMILY,
                                    ),
                                    ft.Text(
                                        card_type_dropdown.value,
                                        color=Theme.TEXT,
                                        weight=ui_theme.FONT_WEIGHT,
                                        font_family=ui_theme.FONT_FAMILY,
                                    ),
                                ],
                                spacing=8,
                            ),
                        ],
                        spacing=12,
                        tight=True,
                    ),
                ),
            ],
            spacing=14,
            tight=True,
        )

        dialog.actions = [
            ft.TextButton(
                "登録する",
                on_click=execute_register,
            ),
            ft.TextButton(
                "戻る",
                autofocus=True,
                on_click=lambda event: page.close(dialog),
            ),
        ]

        page.open(dialog)

    # キャンセル確認関数
    def open_cancel_confirm_dialog(e):
        if registration_busy:
            return

        dialog.title = ft.Text(
            "カード登録を中止しますか？",
            font_family=ui_theme.FONT_FAMILY,
        )
        dialog.content = ft.Text(
            "読み取ったカード情報は破棄されます",
            color=Theme.TEXT_MUTED,
            font_family=ui_theme.FONT_FAMILY,
        )
        dialog.actions = [
            ft.TextButton(
                "中止して戻る",
                on_click=complete_cancel_confirm_dialog,
                style=ft.ButtonStyle(
                    color=Theme.DANGER,
                ),
            ),
            ft.TextButton(
                "登録を続ける",
                autofocus=True,
                on_click=lambda event: page.close(
                    dialog
                ),
            ),
        ]
        page.open(dialog)

    # キャンセル完了関数
    def complete_cancel_confirm_dialog(e):
        if registration_busy:
            return

        register_listener.clear_card_number()
        page.close(dialog)
        page.go("/card")


    # カード登録関数
    async def execute_register(e):
        nonlocal registration_busy

        if registration_busy:
            return

        if not card_number:
            logger.critical(
                "カード番号を取得できませんでした"
            )
            page.close(dialog)
            dialog.title = ft.Text("エラー")
            dialog.content = ft.Text(
                "カード番号を取得できませんでした"
            )
            dialog.actions = [
                ft.TextButton(
                    "OK",
                    autofocus=True,
                    on_click=lambda event: page.go(
                        "/card"
                    ),
                )
            ]
            page.open(dialog)
            return

        registration_busy = True
        registration_succeeded = False

        register_button.disabled = True
        cancel_button.disabled = True
        user_field.disabled = True
        card_type_dropdown.disabled = True

        dialog.title = ft.Text("登録しています")
        dialog.content = ft.Row(
            controls=[
                ft.ProgressRing(
                    width=22,
                    height=22,
                    stroke_width=2.5,
                    color=Theme.SKY,
                ),
                ft.Text("カード情報を保存しています"),
            ],
            spacing=12,
            alignment=ft.MainAxisAlignment.CENTER,
        )
        dialog.actions = []
        page.update()

        try:
            card_type = CardType(
                card_type_dropdown.value
            )

            await asyncio.to_thread(
                register_service.register_card,
                card_number,
                card_type,
                selected_user_id,
            )

            invalidate_management_counts(page)
            registration_succeeded = True

            dialog.title = ft.Text(
                "登録完了",
                font_family=ui_theme.FONT_FAMILY,
            )
            dialog.content = ft.Column(
                controls=[
                    ft.Container(
                        width=58,
                        height=58,
                        bgcolor=Theme.MINT_SOFT,
                        border_radius=29,
                        alignment=ft.alignment.center,
                        content=ft.Icon(
                            ft.Icons.CHECK,
                            size=30,
                            color=Theme.MINT,
                        ),
                    ),
                    ft.Text(
                        "カードの登録が完了しました",
                        size=16,
                        color=Theme.TEXT,
                        weight=ui_theme.FONT_WEIGHT,
                        font_family=ui_theme.FONT_FAMILY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "カード管理画面で登録内容を確認できます",
                        size=12,
                        color=Theme.TEXT_MUTED,
                        font_family=ui_theme.FONT_FAMILY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                spacing=12,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
            dialog.actions = [
                ft.TextButton(
                    "カード管理へ",
                    autofocus=True,
                    on_click=lambda event: page.go(
                        "/card"
                    ),
                )
            ]

        except Exception:
            logger.exception(
                "カード登録に失敗しました: "
                "card_number=%s, user_id=%s",
                card_number,
                selected_user_id,
            )

            dialog.title = ft.Text(
                "登録できませんでした",
                font_family=ui_theme.FONT_FAMILY,
            )
            dialog.content = ft.Column(
                controls=[
                    ft.Container(
                        width=58,
                        height=58,
                        bgcolor=ui_theme.DANGER_BG,
                        border_radius=29,
                        alignment=ft.alignment.center,
                        content=ft.Icon(
                            ft.Icons.ERROR_OUTLINE,
                            size=30,
                            color=Theme.DANGER,
                        ),
                    ),
                    ft.Text(
                        "カード情報の保存に失敗しました",
                        size=16,
                        color=Theme.TEXT,
                        weight=ui_theme.FONT_WEIGHT,
                        font_family=ui_theme.FONT_FAMILY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "入力内容は保持されています。しばらく待ってからもう一度お試しください",
                        size=12,
                        color=Theme.TEXT_MUTED,
                        font_family=ui_theme.FONT_FAMILY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                spacing=12,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
            dialog.actions = [
                ft.TextButton(
                    "もう一度試す",
                    autofocus=True,
                    on_click=lambda event: page.close(
                        dialog
                    ),
                )
            ]

        finally:
            registration_busy = False

            if not registration_succeeded:
                cancel_button.disabled = False
                user_field.disabled = False
                card_type_dropdown.disabled = False
                refresh_registration_state(
                    update_page=False
                )

            page.update()

    register_button = primary_button(
        "登録",
        open_add_confirm_dialog,
        ft.Icons.CHECK,
    )
    register_button.width = 200
    register_button.disabled = True

    cancel_button = danger_button(
        "キャンセル",
        open_cancel_confirm_dialog,
        ft.Icons.CLOSE,
    )
    cancel_button.width = 200

    form_content = ft.Column(
        controls=[
            section_title(
                "登録内容",
                accent=Theme.SKY,
            ),
            ft.Container(height=8),
            ft.Text(
                "ユーザー",
                size=13,
                color=Theme.TEXT_MUTED,
                weight=ui_theme.FONT_WEIGHT,
                font_family=ui_theme.FONT_FAMILY,
            ),
            ft.Container(
                width=340,
                content=user_field,
            ),
            card_type_dropdown,
            registration_hint,
            ft.Container(height=12),
            ft.Row(
                controls=[
                    register_button,
                    cancel_button,
                ],
                spacing=14,
                wrap=True,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        ],
        spacing=14,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    form_card = card(
        form_content,
        accent=Theme.SKY,
        padding=30,
    )

    return app_view(
        "/register/input",
        page,
        [form_card],
        back_route="/card",
        on_back=open_cancel_confirm_dialog,
    )