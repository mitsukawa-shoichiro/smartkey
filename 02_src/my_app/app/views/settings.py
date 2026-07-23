import asyncio
import copy
import json
import logging
import os
import shutil
import requests
from pathlib import Path

import flet as ft

from my_app.app.utils.front_camera_moduel import (
    CameraWorker_Front,
    request_camera_config_reload,
    request_camera_release,
    send_message,
)
from my_app.app.views.common import (
    Theme,
    app_view,
    card,
    primary_button,
    secondary_button,
    section_title,
    show_error_dialog,
    show_info_dialog,
)
from my_app.camera.camera_config import (
    CAMERA_CONFIG_PATH,
)
from my_app.service.utils.usb_connection import (
    probe_usb_readers,
)
from my_app.ui import theme as ui_theme


logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
USB_CONFIG_PATH = (
    BASE_DIR
    / "config"
    / "usb_settings.json"
)

BACKEND_CONFIG_DIR = (
    BASE_DIR / "config" / "backend"
)


def _probe_cloud_device(
    config_name,
    id_key,
    api_name,
):
    """SESAME APIを使って状態を取得する。施解錠は行わない。"""
    try:
        config_path = (
            BACKEND_CONFIG_DIR / config_name
        )
        config = json.loads(
            config_path.read_text(
                encoding="utf-8-sig"
            )
        )
        device = config["device"]

        response = requests.get(
            (
                "https://app.candyhouse.co/api/"
                f"{api_name}/{device[id_key]}"
            ),
            headers={
                "x-api-key": device["x_api_key"],
            },
            timeout=(3.05, 5.0),
        )

        if response.status_code != 200:
            return (
                "error",
                f"APIエラー HTTP {response.status_code}",
            )

        data = response.json()

        if not isinstance(data, dict):
            return "error", "API応答の形式が不正です"

        details = []

        state = (
            data.get("CHSesame2Status")
            or data.get("status")
            or data.get("openState")
        )

        if state is not None:
            state_labels = {
                "locked": "施錠",
                "unlocked": "解錠",
                "moved": "範囲外",
            }
            details.append(
                state_labels.get(
                    str(state).lower(),
                    str(state),
                )
            )

        battery = data.get("batteryPercentage")

        if battery is not None:
            details.append(f"電池 {battery}%")

        wm2_state = data.get("wm2State")

        if wm2_state is False:
            return (
                "error",
                "Wi-Fiモジュール未接続"
                + (
                    f" / {' / '.join(details)}"
                    if details
                    else ""
                ),
            )

        if wm2_state is True:
            status = "接続中"
            level = "ok"
        else:
            status = "API応答あり"
            level = "warning"

        if details:
            status += f" / {' / '.join(details)}"

        return level, status

    except requests.Timeout:
        return "error", "API応答がタイムアウトしました"

    except requests.ConnectionError:
        return "error", "ネットワークへ接続できません"

    except Exception as ex:
        return (
            "error",
            f"確認失敗 ({type(ex).__name__})",
        )


def _probe_smartkey_service():
    """Windowsサービスの起動状態を確認する。"""
    try:
        import win32service
        import win32serviceutil

        service_state = (
            win32serviceutil.QueryServiceStatus(
                "SmartKeyService"
            )[1]
        )

        if (
            service_state
            == win32service.SERVICE_RUNNING
        ):
            return "ok", "稼働中"

        if service_state in (
            win32service.SERVICE_START_PENDING,
            win32service.SERVICE_CONTINUE_PENDING,
        ):
            return "warning", "起動処理中"

        return "error", "停止中"

    except Exception as ex:
        return (
            "error",
            f"確認失敗 ({type(ex).__name__})",
        )


def _default_camera_config():
    return {
        "設置台数": 1,
        "devices": {
            "入口": {
                "index": 0,
            },
        },
    }


def _default_usb_config():
    return {
        "設置台数": 0,
        "devices": {},
    }


def _load_json(
    path: Path,
    default_factory,
):
    if not path.exists():
        return default_factory()

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(
            f"{path.name}の形式が正しくありません"
        )

    return data


def _save_json(
    path: Path,
    data: dict,
):
    """
    保存前に.json.bakを作成し、
    一時ファイルから原子的に置き換える。
    """
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    serialized = (
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )

    temporary_path = path.with_suffix(
        path.suffix + ".tmp"
    )

    backup_path = path.with_suffix(
        path.suffix + ".bak"
    )

    if path.exists():
        current_text = path.read_text(
            encoding="utf-8"
        )

        if current_text != serialized:
            shutil.copy2(
                path,
                backup_path,
            )

    try:
        temporary_path.write_text(
            serialized,
            encoding="utf-8",
        )

        os.replace(
            temporary_path,
            path,
        )

    finally:
        temporary_path.unlink(
            missing_ok=True
        )


def _get_camera_index(config: dict):
    try:
        return str(
            int(
                config[
                    "devices"
                ][
                    "入口"
                ][
                    "index"
                ]
            )
        )
    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return "0"


def _camera_index_field(
    value,
    on_change,
):
    return ft.TextField(
        label="入口カメラ index",
        value=value,
        keyboard_type=(
            ft.KeyboardType.NUMBER
        ),
        prefix_icon=(
            ft.Icons.VIDEOCAM_OUTLINED
        ),
        filled=True,
        fill_color=Theme.SURFACE,
        border_color=Theme.BORDER,
        focused_border_color=(
            Theme.EQUIPMENT_GREEN
        ),
        border_radius=8,
        on_change=on_change,
        text_style=ft.TextStyle(
            font_family=(
                ui_theme.FONT_FAMILY
            ),
            weight=(
                ui_theme.FONT_WEIGHT
            ),
            color=Theme.TEXT,
        ),
        label_style=ft.TextStyle(
            font_family=(
                ui_theme.FONT_FAMILY
            ),
            weight=(
                ui_theme.FONT_WEIGHT
            ),
            color=Theme.TEXT_MUTED,
        ),
    )


def _reader_item(
    location,
    device,
    probe_result=None,
):
    if not isinstance(device, dict):
        device = {}

    name = (
        device.get("name")
        or "未設定"
    )
    vid = device.get("vid") or "-"
    pid = device.get("pid") or "-"
    serial = (
        device.get("serial")
        or "-"
    )

    if serial == "-":
        status = "未設定"
        status_color = Theme.TEXT_MUTED
        status_background = "#F2F5F6"
        detail = (
            "カードリーダー設定がありません"
        )

    elif probe_result is None:
        status = "未確認"
        status_color = Theme.TEXT_MUTED
        status_background = "#F2F5F6"
        detail = (
            "接続確認を実行してください"
        )

    elif probe_result.get("connected"):
        status = "接続中"
        status_color = Theme.MINT
        status_background = (
            Theme.MINT_SOFT
        )
        detail = (
            "USB・PC/SCともに認識済み"
        )

    elif probe_result.get(
        "pnp_connected"
    ):
        status = "PC/SC未認識"
        status_color = Theme.SUN
        status_background = (
            Theme.SUN_SOFT
        )
        detail = (
            "USBは認識されていますが、"
            "PC/SCで認識されていません"
        )

    else:
        status = "未接続"
        status_color = Theme.DANGER
        status_background = "#FCECEF"
        detail = (
            "USBデバイスが見つかりません"
        )

    return ft.Container(
        col={
            "sm": 12,
            "md": 6,
        },
        padding=ft.padding.symmetric(
            horizontal=16,
            vertical=14,
        ),
        bgcolor="#FAFCFC",
        border=ft.border.all(
            1,
            Theme.BORDER,
        ),
        border_radius=8,
        content=ft.Row(
            controls=[
                ft.Container(
                    width=42,
                    height=42,
                    bgcolor=(
                        status_background
                    ),
                    border_radius=21,
                    alignment=(
                        ft.alignment.center
                    ),
                    content=ft.Icon(
                        ft.Icons.USB,
                        size=21,
                        color=status_color,
                    ),
                ),
                ft.Column(
                    controls=[
                        ft.Text(
                            location,
                            size=15,
                            color=Theme.TEXT,
                            weight=(
                                ui_theme
                                .FONT_WEIGHT
                            ),
                            font_family=(
                                ui_theme
                                .FONT_FAMILY
                            ),
                        ),
                        ft.Text(
                            name,
                            size=12,
                            color=(
                                Theme.TEXT_MUTED
                            ),
                            font_family=(
                                ui_theme
                                .FONT_FAMILY
                            ),
                            max_lines=1,
                            overflow=(
                                ft.TextOverflow
                                .ELLIPSIS
                            ),
                        ),
                        ft.Text(
                            (
                                f"VID: {vid}  "
                                f"PID: {pid}  "
                                f"serial: {serial}"
                            ),
                            size=11,
                            color=(
                                Theme.TEXT_MUTED
                            ),
                            font_family=(
                                ui_theme
                                .FONT_FAMILY
                            ),
                            max_lines=1,
                            overflow=(
                                ft.TextOverflow
                                .ELLIPSIS
                            ),
                        ),
                        ft.Text(
                            detail,
                            size=11,
                            color=status_color,
                            font_family=(
                                ui_theme
                                .FONT_FAMILY
                            ),
                        ),
                    ],
                    spacing=3,
                    expand=True,
                ),
                ft.Container(
                    padding=(
                        ft.padding.symmetric(
                            horizontal=10,
                            vertical=6,
                        )
                    ),
                    bgcolor=(
                        status_background
                    ),
                    border_radius=8,
                    content=ft.Text(
                        status,
                        size=11,
                        color=status_color,
                        weight=(
                            ui_theme.FONT_WEIGHT
                        ),
                        font_family=(
                            ui_theme.FONT_FAMILY
                        ),
                    ),
                ),
            ],
            spacing=12,
            vertical_alignment=(
                ft.CrossAxisAlignment
                .CENTER
            ),
        ),
    )


def settings_view(
    page: ft.Page,
) -> ft.View:
    page.title = "設定"

    camera_load_ok = True
    camera_load_error = None

    try:
        camera_config = _load_json(
            CAMERA_CONFIG_PATH,
            _default_camera_config,
        )
    except Exception as ex:
        logger.exception(
            "カメラ設定の読み込みに失敗しました"
        )
        camera_config = (
            _default_camera_config()
        )
        camera_load_ok = False
        camera_load_error = str(ex)

    try:
        usb_config = _load_json(
            USB_CONFIG_PATH,
            _default_usb_config,
        )
        usb_load_error = None
    except Exception as ex:
        logger.exception(
            "USB設定の読み込みに失敗しました"
        )
        usb_config = (
            _default_usb_config()
        )
        usb_load_error = str(ex)

    worker = (
        CameraWorker_Front
        .get_instance()
    )

    dirty = False
    preview_active = False
    backend_paused = False
    last_tested_index = None
    reader_probe_results = {}

    camera_status_icon = ft.Icon(
        ft.Icons.INFO_OUTLINE,
        size=18,
        color=Theme.TEXT_MUTED,
    )

    camera_status_text = ft.Text(
        (
            camera_load_error
            or (
                "現在の設定: "
                f"index "
                f"{_get_camera_index(camera_config)}"
            )
        ),
        size=12,
        color=(
            Theme.DANGER
            if camera_load_error
            else Theme.TEXT_MUTED
        ),
        font_family=(
            ui_theme.FONT_FAMILY
        ),
    )

    camera_status_panel = ft.Container(
        padding=ft.padding.symmetric(
            horizontal=14,
            vertical=10,
        ),
        bgcolor=(
            "#FCECEF"
            if camera_load_error
            else "#F5F8F9"
        ),
        border_radius=8,
        content=ft.Row(
            controls=[
                camera_status_icon,
                camera_status_text,
            ],
            spacing=8,
        ),
    )

    reader_status_text = ft.Text(
        (
            usb_load_error
            or "USB接続は未確認です"
        ),
        size=12,
        color=(
            Theme.DANGER
            if usb_load_error
            else Theme.TEXT_MUTED
        ),
        font_family=(
            ui_theme.FONT_FAMILY
        ),
    )

    def new_device_status_text():
        return ft.Text(
            "未確認",
            size=12,
            color=Theme.TEXT_MUTED,
            font_family=ui_theme.FONT_FAMILY,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

    sesame_status_text = new_device_status_text()
    open_sensor_status_text = (
        new_device_status_text()
    )
    service_status_text = new_device_status_text()

    preview_image = ft.Image(
        fit=ft.ImageFit.CONTAIN,
        gapless_playback=True,
        visible=False,
        expand=True,
    )

    preview_placeholder = ft.Column(
        controls=[
            ft.Icon(
                ft.Icons.VIDEOCAM_OUTLINED,
                size=44,
                color=Theme.TEXT_MUTED,
            ),
            ft.Text(
                "カメラテスト",
                color=Theme.TEXT_MUTED,
                font_family=(
                    ui_theme.FONT_FAMILY
                ),
            ),
        ],
        spacing=10,
        alignment=(
            ft.MainAxisAlignment.CENTER
        ),
        horizontal_alignment=(
            ft.CrossAxisAlignment.CENTER
        ),
    )

    preview_panel = ft.Container(
        height=300,
        bgcolor="#F7FAFB",
        border=ft.border.all(
            1,
            Theme.BORDER,
        ),
        border_radius=8,
        clip_behavior=(
            ft.ClipBehavior.ANTI_ALIAS
        ),
        content=ft.Stack(
            controls=[
                ft.Container(
                    left=0,
                    right=0,
                    top=0,
                    bottom=0,
                    alignment=(
                        ft.alignment.center
                    ),
                    content=preview_image,
                ),
                ft.Container(
                    left=0,
                    right=0,
                    top=0,
                    bottom=0,
                    alignment=(
                        ft.alignment.center
                    ),
                    content=(
                        preview_placeholder
                    ),
                ),
            ],
            expand=True,
        ),
    )

    def set_camera_status(
        message,
        color=Theme.TEXT_MUTED,
        background="#F5F8F9",
    ):
        camera_status_text.value = message
        camera_status_text.color = color
        camera_status_icon.color = color
        camera_status_panel.bgcolor = (
            background
        )
        page.update()

    def parse_camera_index():
        value = (
            entrance_index.value
            or ""
        ).strip()

        try:
            camera_index = int(value)
        except ValueError as ex:
            raise ValueError(
                "カメラindexは整数で"
                "入力してください"
            ) from ex

        if (
            camera_index < 0
            or camera_index > 99
        ):
            raise ValueError(
                "カメラindexは0から99で"
                "入力してください"
            )

        return camera_index

    def mark_dirty(_):
        nonlocal dirty
        nonlocal last_tested_index

        dirty = True
        last_tested_index = None

        save_button.disabled = (
            not camera_load_ok
        )

        set_camera_status(
            "設定が変更されています",
            Theme.SUN,
            Theme.SUN_SOFT,
        )

    entrance_index = (
        _camera_index_field(
            _get_camera_index(
                camera_config
            ),
            mark_dirty,
        )
    )

    reader_list = ft.ResponsiveRow(
        controls=[],
        columns=12,
        spacing=14,
        run_spacing=14,
    )

    def rebuild_reader_list():
        devices = usb_config.get(
            "devices",
            {},
        )

        if not isinstance(
            devices,
            dict,
        ):
            devices = {}

        reader_list.controls = [
            _reader_item(
                location,
                devices.get(
                    location,
                    {},
                ),
                reader_probe_results.get(
                    location
                ),
            )
            for location
            in ("入口", "出口")
        ]

    rebuild_reader_list()

    async def stop_camera_test_session(
        message=None,
    ):
        nonlocal preview_active
        nonlocal backend_paused

        preview_active = False

        await asyncio.to_thread(
            worker.stop_camera
        )

        if backend_paused:
            send_message(
                "finishRegistering"
            )
            backend_paused = False
            await asyncio.sleep(0.5)

        entrance_index.disabled = False
        test_button.disabled = (
            not camera_load_ok
        )
        stop_test_button.visible = False

        preview_image.visible = False
        preview_image.src_base64 = None
        preview_placeholder.visible = True

        save_button.disabled = (
            not dirty
            or not camera_load_ok
        )

        if message:
            set_camera_status(message)
        else:
            page.update()

    async def start_camera_test(_):
        nonlocal preview_active
        nonlocal backend_paused
        nonlocal last_tested_index

        if preview_active:
            return

        try:
            camera_index = (
                parse_camera_index()
            )
        except ValueError as ex:
            show_error_dialog(
                page,
                str(ex),
            )
            return

        test_button.disabled = True
        save_button.disabled = True
        entrance_index.disabled = True

        set_camera_status(
            "認証カメラを一時停止しています",
            Theme.SUN,
            Theme.SUN_SOFT,
        )

        released, message = await asyncio.to_thread(
            request_camera_release,
            5.0,
        )

        if not released:
            entrance_index.disabled = False
            test_button.disabled = False

            save_button.disabled = (
                not dirty
                or not camera_load_ok
            )

            set_camera_status(
                message,
                Theme.DANGER,
                "#FCECEF",
            )
            return

        backend_paused = True

        worker.front_end_system(
            camera_index,
            show_window=False,
        )

        ready = await asyncio.to_thread(
            worker.wait_until_ready,
            4.0,
        )

        if not ready:
            error_message = (
                worker.get_camera_error()
                or (
                    f"カメラindex "
                    f"{camera_index}を"
                    "開けませんでした"
                )
            )

            await stop_camera_test_session()

            set_camera_status(
                error_message,
                Theme.DANGER,
                "#FCECEF",
            )
            return

        preview_active = True
        last_tested_index = (
            camera_index
        )

        stop_test_button.visible = True
        preview_placeholder.visible = False
        preview_image.visible = True

        set_camera_status(
            (
                f"カメラindex "
                f"{camera_index}を"
                "テスト中です"
            ),
            Theme.MINT,
            Theme.MINT_SOFT,
        )

        try:
            while preview_active:
                image_data = (
                    worker
                    .get_preview_base64()
                )

                if image_data:
                    preview_image.src_base64 = (
                        image_data
                    )

                    try:
                        preview_image.update()
                    except Exception:
                        break

                await asyncio.sleep(0.12)

        finally:
            if preview_active:
                await (
                    stop_camera_test_session()
                )

    async def stop_camera_test(_):
        await stop_camera_test_session(
            "カメラテストを停止しました"
        )

    async def save_camera_settings(_):
        nonlocal camera_config
        nonlocal dirty

        try:
            camera_index = (
                parse_camera_index()
            )
        except ValueError as ex:
            show_error_dialog(
                page,
                str(ex),
            )
            return

        if preview_active or backend_paused:
            await stop_camera_test_session()

        save_button.disabled = True
        reload_button.disabled = True
        test_button.disabled = True
        page.update()

        try:
            updated_config = (
                copy.deepcopy(
                    camera_config
                )
            )

            old_entrance = (
                updated_config
                .get("devices", {})
                .get("入口", {})
            )

            if not isinstance(
                old_entrance,
                dict,
            ):
                old_entrance = {}

            entrance_device = (
                old_entrance.copy()
            )
            entrance_device["index"] = (
                camera_index
            )

            updated_config[
                "設置台数"
            ] = 1

            updated_config[
                "devices"
            ] = {
                "入口": entrance_device,
            }

            await asyncio.to_thread(
                _save_json,
                CAMERA_CONFIG_PATH,
                updated_config,
            )

            camera_config = (
                updated_config
            )

            success, message = (
                await asyncio.to_thread(
                    request_camera_config_reload,
                    10.0,
                )
            )

            if success:
                dirty = False

                set_camera_status(
                    message,
                    Theme.MINT,
                    Theme.MINT_SOFT,
                )

                extra_message = ""

                if (
                    last_tested_index
                    != camera_index
                ):
                    extra_message = (
                        "\nカメラテストは"
                        "実行されていません。"
                    )

                show_info_dialog(
                    page,
                    (
                        "カメラ設定を保存し、"
                        "認証サービスへ"
                        "反映しました。"
                        f"{extra_message}"
                    ),
                    title="保存完了",
                )

            else:
                dirty = True

                set_camera_status(
                    (
                        "設定は保存しましたが、"
                        f"即時反映に失敗しました: "
                        f"{message}"
                    ),
                    Theme.DANGER,
                    "#FCECEF",
                )

                show_error_dialog(
                    page,
                    (
                        "設定ファイルは"
                        "保存されましたが、"
                        "認証サービスへ"
                        "反映できませんでした。\n"
                        f"{message}"
                    ),
                )

        except Exception:
            dirty = True

            logger.exception(
                "カメラ設定の保存に失敗しました"
            )

            show_error_dialog(
                page,
                "カメラ設定を保存できませんでした。",
            )

        finally:
            save_button.disabled = (
                not dirty
                or not camera_load_ok
            )
            reload_button.disabled = False
            test_button.disabled = (
                not camera_load_ok
            )
            page.update()

    async def reload_settings(_):
        nonlocal camera_config
        nonlocal usb_config
        nonlocal camera_load_ok
        nonlocal dirty
        nonlocal last_tested_index
        nonlocal reader_probe_results

        if preview_active or backend_paused:
            await stop_camera_test_session()

        reload_button.disabled = True
        page.update()

        try:
            camera_config = _load_json(
                CAMERA_CONFIG_PATH,
                _default_camera_config,
            )

            camera_load_ok = True
            dirty = False
            last_tested_index = None

            entrance_index.value = (
                _get_camera_index(
                    camera_config
                )
            )

            try:
                usb_config = _load_json(
                    USB_CONFIG_PATH,
                    _default_usb_config,
                )
                reader_status_text.value = (
                    "USB接続は未確認です"
                )
                reader_status_text.color = (
                    Theme.TEXT_MUTED
                )
            except Exception as ex:
                logger.exception(
                    "USB設定の再読み込みに失敗しました"
                )
                usb_config = (
                    _default_usb_config()
                )
                reader_status_text.value = (
                    str(ex)
                )
                reader_status_text.color = (
                    Theme.DANGER
                )

            reader_probe_results = {}
            rebuild_reader_list()

            save_button.disabled = True
            test_button.disabled = False

            set_camera_status(
                "設定を再読み込みしました",
                Theme.MINT,
                Theme.MINT_SOFT,
            )

        except Exception as ex:
            camera_load_ok = False
            save_button.disabled = True
            test_button.disabled = True

            logger.exception(
                "カメラ設定の再読み込みに失敗しました"
            )

            show_error_dialog(
                page,
                str(ex),
            )

        finally:
            reload_button.disabled = False
            page.update()

    async def check_device_connections(_):
        controls = (
            reader_status_text,
            sesame_status_text,
            open_sensor_status_text,
            service_status_text,
        )

        reader_check_button.disabled = True

        for control in controls:
            control.value = "確認中..."
            control.color = Theme.SUN

        page.update()

        try:
            (
                usb_probe,
                sesame_probe,
                sensor_probe,
                service_probe,
            ) = await asyncio.gather(
                asyncio.to_thread(
                    probe_usb_readers,
                    usb_config,
                ),
                asyncio.to_thread(
                    _probe_cloud_device,
                    "sesame_config.json",
                    "sesame_id",
                    "sesame2",
                ),
                asyncio.to_thread(
                    _probe_cloud_device,
                    "open_sensor_config.json",
                    "open_sensor_id",
                    "open_sensor",
                ),
                asyncio.to_thread(
                    _probe_smartkey_service
                ),
                return_exceptions=True,
            )

            if isinstance(usb_probe, Exception):
                reader_result = (
                    "error",
                    "USB確認に失敗しました",
                )
            else:
                reader_states = []
                reader_levels = []

                for location in ("入口", "出口"):
                    result = usb_probe.get(
                        location,
                        {},
                    )

                    if not result.get("configured"):
                        state = "未設定"
                        level = "warning"
                    elif not result.get("probe_available"):
                        state = "確認不可"
                        level = "warning"
                    elif result.get("connected"):
                        state = "接続中"
                        level = "ok"
                    elif result.get("pnp_connected"):
                        state = "PC/SC未認識"
                        level = "warning"
                    elif result.get("pcsc_connected"):
                        state = "USB情報を照合できません"
                        level = "warning"
                    else:
                        state = "未接続"
                        level = "error"

                    reader_states.append(
                        f"{location}: {state}"
                    )
                    reader_levels.append(level)

                if "error" in reader_levels:
                    reader_level = "error"
                elif "warning" in reader_levels:
                    reader_level = "warning"
                else:
                    reader_level = "ok"

                reader_result = (
                    reader_level,
                    " / ".join(reader_states),
                )

            def apply_result(control, result):
                if isinstance(result, Exception):
                    result = (
                        "error",
                        "確認処理に失敗しました",
                    )

                level, message = result

                colors = {
                    "ok": Theme.MINT,
                    "warning": Theme.SUN,
                    "error": Theme.DANGER,
                }

                control.value = message
                control.color = colors.get(
                    level,
                    Theme.TEXT_MUTED,
                )

            apply_result(
                reader_status_text,
                reader_result,
            )
            apply_result(
                sesame_status_text,
                sesame_probe,
            )
            apply_result(
                open_sensor_status_text,
                sensor_probe,
            )
            apply_result(
                service_status_text,
                service_probe,
            )

        finally:
            reader_check_button.disabled = False
            page.update()

    async def leave_settings(_):
        if preview_active or backend_paused:
            await stop_camera_test_session()

        page.go("/index")

    save_button = primary_button(
        "保存",
        save_camera_settings,
        ft.Icons.SAVE,
    )
    save_button.bgcolor = (
        Theme.EQUIPMENT_GREEN
    )
    save_button.disabled = True

    reload_button = secondary_button(
        "再読み込み",
        reload_settings,
        ft.Icons.REFRESH,
    )

    test_button = secondary_button(
        "カメラテスト",
        start_camera_test,
        ft.Icons.VIDEOCAM,
    )
    test_button.disabled = (
        not camera_load_ok
    )

    stop_test_button = secondary_button(
        "テスト停止",
        stop_camera_test,
        ft.Icons.STOP_CIRCLE_OUTLINED,
    )
    stop_test_button.visible = False

    reader_check_button = secondary_button(
        "すべて確認",
        check_device_connections,
        ft.Icons.REFRESH,
    )

    camera_controls = ft.Column(
        controls=[
            entrance_index,
            camera_status_panel,

            # カメラ設定の操作ボタン
            ft.Row(
                controls=[
                    save_button,
                    reload_button,
                    test_button,
                    stop_test_button,
                ],
                spacing=10,
                run_spacing=10,
                wrap=True,
                alignment=(
                    ft.MainAxisAlignment.START
                ),
            ),
        ],
        spacing=14,
        horizontal_alignment=(
            ft.CrossAxisAlignment.STRETCH
        ),
    )

    camera_card = card(
        ft.Column(
            controls=[
                section_title(
                    "カメラ",
                    accent=(
                        Theme
                        .EQUIPMENT_GREEN
                    ),
                ),
                ft.Container(height=4),
                ft.ResponsiveRow(
                    controls=[
                        ft.Container(
                            content=(
                                preview_panel
                            ),
                            col={
                                "sm": 12,
                                "md": 7,
                            },
                        ),
                        ft.Container(
                            content=(
                                camera_controls
                            ),
                            col={
                                "sm": 12,
                                "md": 5,
                            },
                        ),
                    ],
                    columns=12,
                    spacing=18,
                    run_spacing=18,
                ),
            ],
            spacing=14,
        ),
        accent=(
            Theme.EQUIPMENT_GREEN
        ),
        padding=26,
    )

    def device_tile(
        title,
        icon,
        color,
        status_control,
    ):
        return ft.Container(
            bgcolor="#FAFCFC",
            border=ft.border.all(
                1,
                Theme.BORDER,
            ),
            border_radius=8,
            content=ft.ListTile(
                leading=ft.Icon(
                    icon,
                    color=color,
                ),
                title=ft.Text(
                    title,
                    size=14,
                    color=Theme.TEXT,
                    weight=ui_theme.FONT_WEIGHT,
                    font_family=ui_theme.FONT_FAMILY,
                ),
                subtitle=status_control,
                dense=True,
            ),
        )

    equipment_card = card(
        ft.Column(
            controls=[
                section_title(
                    "機器接続状況",
                    accent=Theme.MINT,
                ),
                ft.Row(
                    controls=[
                        reader_check_button,
                    ],
                    alignment=(
                        ft.MainAxisAlignment.END
                    ),
                ),
                device_tile(
                    "カードリーダー",
                    ft.Icons.CREDIT_CARD,
                    Theme.SKY,
                    reader_status_text,
                ),
                device_tile(
                    "SESAME",
                    ft.Icons.LOCK_OUTLINE,
                    Theme.LAVENDER,
                    sesame_status_text,
                ),
                device_tile(
                    "開閉センサー",
                    ft.Icons.SENSOR_DOOR,
                    Theme.SUN,
                    open_sensor_status_text,
                ),
                device_tile(
                    "認証サービス",
                    ft.Icons.SETTINGS,
                    Theme.MINT,
                    service_status_text,
                ),
            ],
            spacing=10,
        ),
        accent=Theme.MINT,
        padding=22,
    )

    return app_view(
        "/settings",
        page,
        [
            camera_card,
            ft.Container(height=8),
            equipment_card,
        ],
        back_route="/index",
        on_back=leave_settings,
    )