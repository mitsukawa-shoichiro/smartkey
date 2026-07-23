import logging
import flet as ft

import my_app.app.views.user as user_screen
import my_app.app.views.card as card_screen
import my_app.app.views.face as face_screen

from my_app.app.views.common import (
    Theme,
    MANAGEMENT_ROUTES,
    app_view,
    management_tabs,
    route_page_title,
)

logger = logging.getLogger(__name__)

_MANAGEMENT_TITLES = {
    "/user": "ユーザー管理",
    "/card": "カード管理",
    "/face": "顔管理",
}


def management_view(
    page: ft.Page,
    initial_route=None,
    view_route="/management",
):
    active_route = (
        initial_route
        or page.session.get("management_last_route")
        or "/user"
    )

    if active_route not in MANAGEMENT_ROUTES:
        active_route = "/user"

    page.session.set("management_last_route", active_route)

    builders = {
        "/user": user_screen.user_view,
        "/card": card_screen.cardView,
        "/face": face_screen.faceView,
    }

    def build_body(route):
        old_mode = getattr(page, "_management_embed_mode", False)
        page._management_embed_mode = True

        try:
            body = builders[route](page)
        except Exception:
            logger.exception("管理画面の本文を表示できませんでした: %s", route)
            body = ft.Container(
                padding=40,
                alignment=ft.alignment.center,
                content=ft.Column(
                    controls=[
                        ft.Icon(
                            ft.Icons.ERROR_OUTLINE,
                            size=36,
                            color=Theme.DANGER,
                        ),
                        ft.Text(
                            "画面の表示中にエラーが発生しました",
                            color=Theme.DANGER,
                        ),
                    ],
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
        finally:
            page._management_embed_mode = old_mode

        host = ft.Container(
            key=f"management-body-{route.removeprefix('/')}",
            width=1040,
            content=body,
        )
        body_cache[route] = host
        return host

    tabs_host = ft.Container(width=1040)

    title_host = ft.Container(
        width=1040,
        content=route_page_title(active_route),
    )

    body_switcher = ft.AnimatedSwitcher(
        content=build_body(active_route),
        duration=160,
        reverse_duration=130,
        switch_in_curve=ft.AnimationCurve.EASE_OUT_CUBIC,
        switch_out_curve=ft.AnimationCurve.EASE_IN_CUBIC,
        transition=ft.AnimatedSwitcherTransition.FADE,
        width=1040,
    )

    def select_tab(route):
        nonlocal active_route

        if route == active_route:
            return

        # 180ms以内の連打だけを無視する
        now = time.monotonic()
        if now - last_switch_at < 0.18:
            return

        last_switch_at = now

        next_body = build_body(route)
        active_route = route

        title_host.content = route_page_title(active_route)

        page.session.set(
            "management_last_route",
            route,
        )

        tabs_host.content = management_tabs(
            page,
            active_route,
            on_change=select_tab,
        )

        body_switcher.content = next_body
        page.title = _MANAGEMENT_TITLES[active_route]
        page.update()

    tabs_host.content = management_tabs(
        page,
        active_route,
        on_change=select_tab,
    )

    page.title = _MANAGEMENT_TITLES[active_route]

    view = app_view(
        "/management",
        page,
        [
            tabs_host,
            body_switcher,
        ],
        back_route="/index",
        page_title_control=title_host,
    )
    view.route = view_route
    return view