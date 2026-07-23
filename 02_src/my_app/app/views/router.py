"""
画面遷移(ルーティング)

各View関数は例外をそのまま投げてよい。画面構築中に起きた例外は、この
router が一括で受け止めて、エラーダイアログを出しつつホームへ戻す。
(SpringでいうControllerAdviceの位置づけ)

ただし、routerが拾えるのは「画面を組み立てる時」の例外だけ。
ボタンクリックから呼ばれる処理(load_table等)の例外は、Fletのイベント
ループが直接呼ぶためここには届かない。それらは各画面側でtry/exceptする。
"""
import threading
import logging

import flet as ft

import my_app.app.views.login as login
import my_app.app.views.index as index
import my_app.app.views.access_logs as access_logs
import my_app.app.views.register as register
import my_app.app.views.face_register as face_register
import my_app.app.views.settings as settings
import my_app.app.views.management as management

from my_app.app.views.common import (
    Theme,
    show_error_dialog,
)

# モジュール経由で参照する。
# from ... import thread_handle だと値のコピーになり、
# global thread_handle で書き換えてもthread_state側には反映されない。
import my_app.service.daemon_bridge.thread_state as thread_state

logger = logging.getLogger(__name__)

HOME_ROUTE = "/index"


def route(page: ft.Page):

    def _start_registering(page: ft.Page):
        """
        カード登録の待機画面を出し、IDm受信のポーリングを別スレッドで開始する。
        スレッドの実体は thread_state に持たせて、他の場所からも参照できるようにする。
        """
        thread_state.stop_event.clear()
        view = register.registering(page)

        thread_state.thread_handle = threading.Thread(
            target=lambda: register.run_async_delayed_transition(page),
            daemon=True,
        )
        thread_state.thread_handle.start()
        return view

    # ルート -> Viewを組み立てる関数 の対応表
    # 画面を増やす時はここに1行足す。
    _ROUTES = {
        "/": lambda p: login.login(p),
        "/index": lambda p: index.index_view(p),

        "/management": lambda p: management.management_view(p),
        "/user": lambda p: management.management_view(
            p, initial_route="/user", view_route="/user"
        ),
        "/card": lambda p: management.management_view(
            p, initial_route="/card", view_route="/card"
        ),
        "/face": lambda p: management.management_view(
            p, initial_route="/face", view_route="/face"
        ),

        "/access_logs": lambda p: access_logs.access_logs(p),
        "/register": _start_registering,
        "/register/input": lambda p: register.register_input(p),
        "/face_register": lambda p: face_register.face_register_view(p),
        "/face_register/input": lambda p: face_register.face_register_register(p),
        "/settings": lambda p: settings.settings_view(p),
    }

    def page_route_change(e):
        route_path = e.route.split("?")[0]

        page.title = "ドア開閉システム"
        logger.info("%sに遷移しました", route_path)

        builder = _ROUTES.get(route_path)
        error_message = None

        if builder is None:
            logger.warning("未定義のルートです: %s", e.route)
            next_view = _fallback_view(route_path)
            error_message = "指定された画面が見つかりませんでした"
        else:
            try:
                # 次画面を完成させてから現在の画面と交換する
                next_view = builder(page)
            except Exception:
                logger.exception(
                    "画面の表示中にエラーが発生しました: %s",
                    route_path,
                )
                next_view = _fallback_view(route_path)
                error_message = "画面の表示中にエラーが発生しました"

        page.views.clear()
        page.views.append(next_view)
        page.update()

        if error_message is not None:
            show_error_dialog(
                page,
                error_message,
                go_home=route_path != HOME_ROUTE,
            )

    page.on_route_change = page_route_change


def _fallback_view(route_path: str) -> ft.View:
    """画面の組み立てに失敗した時に積む、空のView"""
    return ft.View(route_path, controls=[], bgcolor=Theme.BG)