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
import my_app.app.views.card as card
import my_app.app.views.access_logs as access_logs
import my_app.app.views.register as register
import my_app.app.views.user as user
import my_app.app.views.face_register as face_register
import my_app.app.views.face as face
import my_app.app.views.camera_register as camera_register

# モジュール経由で参照する。
# from ... import thread_handle だと値のコピーになり、
# global thread_handle で書き換えてもthread_state側には反映されない。
import my_app.service.daemon_bridge.thread_state as thread_state

from my_app.app.views.common import Theme, show_error_dialog

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
        "/card": lambda p: card.cardView(p),
        "/access_logs": lambda p: access_logs.access_logs(p),
        "/register": _start_registering,
        "/register/input": lambda p: register.register_input(p),
        "/face": lambda p: face.faceView(p),
        "/face_register": lambda p: face_register.face_register_view(p),
        "/face_register/input": lambda p: face_register.face_register_register(p),
        "/user": lambda p: user.user_view(p),
        "/camera_register": lambda p: camera_register.camera_register_view(p),
    }

    def page_route_change(e):
        # クエリ文字列(?error=...)は使わない方針。ルート部分だけで判定する。
        route_path = e.route.split("?")[0]

        page.title = "ドア開閉システム"
        page.views.clear()
        logger.info("%sに遷移しました", route_path)

        builder = _ROUTES.get(route_path)
        if builder is None:
            logger.warning("未定義のルートです: %s", e.route)
            page.views.append(_fallback_view(route_path))
            show_error_dialog(page, "指定された画面が見つかりませんでした",
                                go_home=route_path != HOME_ROUTE)
            page.update()
            return

        try:
            page.views.append(builder(page))
        except Exception:
            # 画面が組み立てられなかった場合、必ずViewを積む。
            # (Viewを積まないと画面が描画されず、エラーダイアログも表示されない)
            logger.exception("画面の表示中にエラーが発生しました: %s", route_path)
            page.views.append(_fallback_view(route_path))
            # ホーム自体が失敗している場合にgo_homeすると遷移が堂々巡りになるため、
            # その時だけは留まらせる
            show_error_dialog(page, "画面の表示中にエラーが発生しました",
                                go_home=route_path != HOME_ROUTE)

        page.update()

    page.on_route_change = page_route_change


def _fallback_view(route_path: str) -> ft.View:
    """画面の組み立てに失敗した時に積む、空のView"""
    return ft.View(route_path, controls=[], bgcolor=Theme.BG)