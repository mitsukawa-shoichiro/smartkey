import socket
import flet as ft
import os
import threading
import queue
import numpy as np
from datetime import datetime
import tempfile, cv2, os
import my_app.db.repository as repo
import random
import asyncio
import logging
import time

from my_app.app.utils.front_camera_moduel import (
    CameraWorker_Front,
    CaptureBuffer,
    request_camera_release,
    send_message,
)
from my_app.camera.camera_config import load_rgb_camera_index

from my_app.app.views.common import (
    Theme,
    app_view,
    card,
    section_title,
    primary_button,
    secondary_button,
    danger_button,
    invalidate_management_counts,
)
from my_app.camera.face_util.insightface_engine import InsightFaceEngine
from my_app.service import face_service
from my_app.ui import theme as ui_theme

#region util
import shutil
savedir="./db/FaceLib"

from pathlib import Path
import glob
import shutil
import os

savedir = "./db/FaceLib"


import json
from my_app.camera.passive_pad import PassivePad

FACE_AUTH_CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "config"
    / "face_auth.json"
)


with FACE_AUTH_CONFIG_PATH.open("r", encoding="utf-8") as file:
    face_auth_config = json.load(file)


logger = logging.getLogger(__name__)


def face_registration_steps(active_step: int):
    def step(number, label, icon):
        active = number == active_step
        completed = number < active_step
        accent = Theme.MINT if completed else Theme.LAVENDER
        soft_color = (
            Theme.MINT_SOFT
            if completed
            else Theme.LAVENDER_SOFT
        )

        return ft.Container(
            width=180,
            height=38,
            bgcolor=(
                soft_color
                if active or completed
                else Theme.SURFACE
            ),
            border=ft.border.all(
                1,
                accent
                if active or completed
                else Theme.BORDER,
            ),
            border_radius=8,
            alignment=ft.alignment.center,
            content=ft.Row(
                controls=[
                    ft.Container(
                        width=23,
                        height=23,
                        border_radius=12,
                        bgcolor=(
                            accent
                            if active or completed
                            else Theme.BG
                        ),
                        alignment=ft.alignment.center,
                        content=ft.Icon(
                            ft.Icons.CHECK if completed else icon,
                            size=14,
                            color=(
                                "#FFFFFF"
                                if active or completed
                                else Theme.TEXT_MUTED
                            ),
                        ),
                    ),
                    ft.Text(
                        label,
                        size=13,
                        color=(
                            Theme.TEXT
                            if active or completed
                            else Theme.TEXT_MUTED
                        ),
                        weight=ft.FontWeight.W_700,
                        font_family=ui_theme.FONT_FAMILY,
                    ),
                ],
                spacing=8,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        )

    return ft.Container(
        alignment=ft.alignment.center,
        content=ft.Row(
            controls=[
                step(
                    1,
                    "顔を撮影",
                    ft.Icons.CAMERA_ALT,
                ),
                ft.Container(
                    width=36,
                    height=2,
                    bgcolor=(
                        Theme.MINT
                        if active_step > 1
                        else Theme.BORDER
                    ),
                ),
                step(
                    2,
                    "本人情報",
                    ft.Icons.PERSON_OUTLINE,
                ),
            ],
            spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

def next_index(target_dir: str, user_name: str, ext=".jpg"):
    """
    指定ユーザーの次の保存番号を取得する
    例)
        otomo_001.jpg
        otomo_002.jpg
    """

    pattern = os.path.join(target_dir, f"{user_name}_*")

    max_index = 0

    for path in glob.glob(pattern):
        stem = Path(path).stem

        try:
            idx = int(stem.split("_")[-1])
            max_index = max(max_index, idx)
        except Exception:
            pass

    return max_index + 1

#1枚だけ保存する場合
def SaveFaceData(src_path: str,
                new_name: str,
                target_dir=savedir):
    """
    画像1枚を保存する

    Returns
    ----------
    保存したファイルパス
    """

    if not os.path.exists(src_path):
        logger.error("顔画像ファイルが存在しません: %s", src_path)
        return None

    os.makedirs(target_dir, exist_ok=True)

    _, ext = os.path.splitext(src_path)
    if ext == "":
        ext = ".jpg"

    index = next_index(target_dir, new_name)

    dst_path = os.path.join(
        target_dir,
        f"{new_name}_{index:03d}{ext}"
    )

    shutil.copy2(src_path, dst_path)

    logger.info("顔画像を保存しました: %s", dst_path)

    return dst_path
    # 現在の最大番号＋１枚の形で画像を管理
    #endregion
    #画像を複数枚保存する場合
def SaveFaceDatas(src_paths, new_name, target_dir=savedir):
    """
    複数画像をまとめて保存する

    Parameters
    ----------
    src_paths : list[str]
    """

    if len(src_paths) == 0:
        return []

    os.makedirs(target_dir, exist_ok=True)

    saved_files = []

    index = next_index(target_dir, new_name)

    for src_path in src_paths:

        if not os.path.exists(src_path):
            continue

        _, ext = os.path.splitext(src_path)

        if ext == "":
            ext = ".jpg"

        dst_path = os.path.join(target_dir, f"{new_name}_{index:03d}{ext}")

        shutil.copy2(src_path, dst_path)

        saved_files.append(dst_path)

        logger.warning("一時画像を撮影できません: %s", path, exc_info=True)

        index += 1

    return saved_files



def face_register_view(page: ft.Page) -> ft.View:
    page.title = "顔登録"

    worker = CameraWorker_Front.get_instance()

    preview_active = False
    moving_to_input = False
    backend_session_active = False
    capture_busy = False
    live_engine = getattr(
        page,
        "_face_registration_engine",
        None,
    )
    registration_pad = getattr(
        page,
        "_face_registration_pad",
        None,
    )
    accepted_embeddings = []
    face_analysis_lock = asyncio.Lock()
    live_capture_ready = False
    live_ready_streak = 0
    cooldown_active = False
    camera_stop_lock = asyncio.Lock()
    live_analysis_generation = 0

    view_token = object()
    page._face_register_view_token = view_token

    def view_is_active():
        return (
            page.route == "/face_register"
            and getattr(page, "_face_register_view_token", None) is view_token
        )

    preview_image = ft.Image(
        width=560,
        height=350,
        fit=ft.ImageFit.CONTAIN,
        gapless_playback=True,
        visible=False,
    )

    placeholder = ft.Column(
        controls=[
            ft.Icon(
                ft.Icons.VIDEOCAM_OUTLINED,
                size=46,
                color=Theme.TEXT_MUTED,
            ),
            ft.Text(
                "カメラを準備しています",
                color=Theme.TEXT_MUTED,
            ),
        ],
        spacing=12,
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=(
            ft.CrossAxisAlignment.CENTER
        ),
    )

    status_icon = ft.Icon(
        ft.Icons.HOURGLASS_TOP,
        size=18,
        color=Theme.LAVENDER,
    )

    status_text = ft.Text(
        "設定を確認しています",
        color=Theme.TEXT,
        size=13,
    )

    status_panel = ft.Container(
        bgcolor=Theme.LAVENDER_SOFT,
        border_radius=8,
        padding=ft.padding.symmetric(
            horizontal=14,
            vertical=10,
        ),
        content=ft.Row(
            controls=[
                status_icon,
                status_text,
            ],
            spacing=8,
        ),
    )

    required_capture_count = max(
        1,
        int(face_auth_config.get("registration_min_images", 3)),
    )
    maximum_capture_count = max(
        required_capture_count,
        int(face_auth_config.get("registration_max_images", 5)),
    )

    capture_count = ft.Text(
        f"撮影 0 / {required_capture_count}枚",
        size=14,
        color=Theme.TEXT,
        weight=ft.FontWeight.W_700,
        font_family=ui_theme.FONT_FAMILY,
    )

    capture_progress_dots = [
        ft.Container(
            width=25,
            height=25,
            border_radius=13,
            bgcolor=Theme.SURFACE,
            border=ft.border.all(1, Theme.BORDER),
            alignment=ft.alignment.center,
            content=ft.Text(
                str(index + 1),
                size=11,
                color=Theme.TEXT_MUTED,
            ),
        )
        for index in range(required_capture_count)
    ]

    capture_hint_icon = ft.Icon(
        ft.Icons.FACE_RETOUCHING_NATURAL,
        size=17,
        color=Theme.LAVENDER,
    )
    capture_hint_text = ft.Text(
        "正面を向いてください",
        size=12,
        color=Theme.TEXT_MUTED,
        font_family=ui_theme.FONT_FAMILY,
        expand=True,
    )

    capture_progress_panel = ft.Container(
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        bgcolor="#FAFCFC",
        border=ft.border.all(1, Theme.BORDER),
        border_radius=8,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        capture_count,
                        ft.Row(
                            controls=capture_progress_dots,
                            spacing=6,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    controls=[
                        capture_hint_icon,
                        capture_hint_text,
                    ],
                    spacing=7,
                ),
            ],
            spacing=8,
        ),
    )

    def update_capture_progress():
        count = len(CaptureBuffer.files)

        capture_count.value = (
            f"撮影 {count} / {required_capture_count}枚"
            if count <= required_capture_count
            else f"撮影 {count}枚（完了）"
        )

        for index, dot in enumerate(capture_progress_dots):
            completed = index < count
            dot.bgcolor = (
                Theme.MINT_SOFT if completed else Theme.SURFACE
            )
            dot.border = ft.border.all(
                1,
                Theme.MINT if completed else Theme.BORDER,
            )
            dot.content = (
                ft.Icon(
                    ft.Icons.CHECK,
                    size=14,
                    color=Theme.MINT,
                )
                if completed
                else ft.Text(
                    str(index + 1),
                    size=11,
                    color=Theme.TEXT_MUTED,
                )
            )

        pose_hints = (
            "正面を向いてください",
            "顔を少し左へ向けてください",
            "顔を少し右へ向けてください",
        )
        completed = count >= required_capture_count

        if count >= maximum_capture_count:
            hint = "撮影完了です。本人情報へ進んでください"
        elif completed:
            hint = "必要枚数を撮影できました。本人情報へ進めます"
        else:
            hint = pose_hints[
                min(count, len(pose_hints) - 1)
            ]

        capture_hint_icon.name = (
            ft.Icons.CHECK_CIRCLE_OUTLINE
            if completed
            else ft.Icons.FACE_RETOUCHING_NATURAL
        )
        capture_hint_icon.color = (
            Theme.MINT if completed else Theme.LAVENDER
        )
        capture_hint_text.value = hint
        capture_hint_text.color = (
            Theme.MINT if completed else Theme.TEXT_MUTED
        )

    camera_label = ft.Text(
        "設定カメラを確認中",
        size=12,
        color=Theme.TEXT_MUTED,
    )

    live_status_icon = ft.Icon(
        ft.Icons.FACE_OUTLINED,
        size=18,
        color=Theme.LAVENDER,
    )

    live_status_text = ft.Text(
        "顔判定を準備しています",
        size=13,
        color=Theme.TEXT,
    )

    distance_text = ft.Text(
        "距離: 判定待ち",
        size=11,
        color=Theme.TEXT_MUTED,
    )

    live_status_panel = ft.Container(
        padding=ft.padding.symmetric(
            horizontal=14,
            vertical=10,
        ),
        bgcolor=Theme.LAVENDER_SOFT,
        border_radius=8,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        live_status_icon,
                        live_status_text,
                    ],
                    spacing=8,
                ),
                distance_text,
            ],
            spacing=4,
        ),
    )

    cooldown_text = ft.Text(
        "",
        size=12,
        color=Theme.LAVENDER,
        text_align=ft.TextAlign.CENTER,
    )

    cooldown_bar = ft.ProgressBar(
        value=0,
        width=220,
        height=5,
        color=Theme.LAVENDER,
        bgcolor=Theme.LAVENDER_SOFT,
        border_radius=3,
    )

    cooldown_panel = ft.Column(
        controls=[
            cooldown_bar,
            cooldown_text,
        ],
        spacing=6,
        visible=False,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    face_guide_outline = ft.Container(
        width=210, height=260,
        border=ft.border.all(3, Theme.LAVENDER),
        border_radius=105,
        animate=ft.Animation(160, ft.AnimationCurve.EASE_OUT),
    )
    face_guide_overlay = ft.Container(
        left=0, right=0, top=0, bottom=0,
        alignment=ft.alignment.center,
        visible=False,
        content=face_guide_outline,
    )
    face_guide_icon = ft.Icon(
        ft.Icons.CENTER_FOCUS_STRONG,
        size=16,
        color=Theme.LAVENDER,
    )
    face_guide_text = ft.Text(
        "顔を枠の中央に合わせてください",
        size=12,
        color=Theme.TEXT,
        weight=ft.FontWeight.W_700,
        font_family=ui_theme.FONT_FAMILY,
    )
    face_guide_badge = ft.Container(
        left=0, right=0, bottom=14,
        alignment=ft.alignment.center,
        visible=False,
        content=ft.Container(
            padding=ft.padding.symmetric(horizontal=13, vertical=8),
            bgcolor=Theme.LAVENDER_SOFT,
            border_radius=8,
            content=ft.Row(
                [face_guide_icon, face_guide_text],
                spacing=7,
                tight=True,
            ),
        ),
    )

    def update_face_guide(ok, information):
        reason = str(information.get("reason", "顔を確認できません"))
        face_count = int(information.get("face_count", 0) or 0)

        if ok:
            message = (
                "撮影できます" if live_capture_ready
                else "その位置で少し静止してください"
            )
            color, soft_color = Theme.MINT, Theme.MINT_SOFT
            icon = (
                ft.Icons.CHECK_CIRCLE_OUTLINE if live_capture_ready
                else ft.Icons.HOURGLASS_TOP
            )
        elif face_count > 1 or "実物" in reason:
            message = (
                "1人だけ枠内に入ってください"
                if face_count > 1 else reason
            )
            color, soft_color = Theme.DANGER, "#FCECEF"
            icon = ft.Icons.ERROR_OUTLINE
        else:
            message = (
                "顔を枠の中央に合わせてください"
                if face_count == 0 else reason
            )
            needs_adjustment = any(
                word in reason
                for word in ("近づけ", "離して", "暗", "明る", "ぼや")
            )
            color, soft_color = (
                (Theme.SUN, Theme.SUN_SOFT)
                if needs_adjustment
                else (Theme.LAVENDER, Theme.LAVENDER_SOFT)
            )
            icon = ft.Icons.CENTER_FOCUS_STRONG

        face_guide_outline.border = ft.border.all(3, color)
        face_guide_icon.name = icon
        face_guide_icon.color = color
        face_guide_text.value = message
        face_guide_badge.content.bgcolor = soft_color
        face_guide_overlay.visible = preview_active
        face_guide_badge.visible = preview_active

    def set_status(
        message,
        color,
        soft_color,
        icon,
    ):
        if not view_is_active():
            return
        status_text.value = message
        status_text.color = color
        status_icon.name = icon
        status_icon.color = color
        status_panel.bgcolor = soft_color
        page.update()

    def refresh_capture_button():
        maximum_images = int(
            face_auth_config.get(
                "registration_max_images",
                5,
            )
        )

        capture_button.disabled = not (
            preview_active
            and live_capture_ready
            and not capture_busy
            and not cooldown_active
            and len(CaptureBuffer.files)
            < maximum_images
        )

    def apply_live_result(ok, information):
        nonlocal live_capture_ready
        nonlocal live_ready_streak

        if not view_is_active():
            return

        face_ratio = information.get("face_ratio")
        minimum_ratio = float(
            face_auth_config[
                "registration_min_face_ratio"
            ]
        )
        maximum_ratio = float(
            face_auth_config[
                "registration_max_face_ratio"
            ]
        )

        if face_ratio is None:
            distance_text.value = "距離: 判定できません"
        elif face_ratio < minimum_ratio:
            distance_text.value = "距離: 遠い"
        elif face_ratio > maximum_ratio:
            distance_text.value = "距離: 近い"
        else:
            distance_text.value = "距離: 適正"

        if ok:
            live_ready_streak += 1
            required = int(
                face_auth_config.get(
                    "registration_ready_streak",
                    2,
                )
            )
            live_capture_ready = (
                live_ready_streak >= required
            )

            if live_capture_ready:
                live_status_text.value = "撮影できます"
                live_status_icon.name = (
                    ft.Icons.CHECK_CIRCLE_OUTLINE
                )
                live_status_icon.color = Theme.MINT
                live_status_panel.bgcolor = (
                    Theme.MINT_SOFT
                )
            else:
                live_status_text.value = (
                    "その位置で少し静止してください"
                )
        else:
            live_ready_streak = 0
            live_capture_ready = False
            live_status_text.value = information.get(
                "reason",
                "顔を確認できません",
            )
            live_status_icon.name = (
                ft.Icons.FACE_OUTLINED
            )
            live_status_icon.color = Theme.LAVENDER
            live_status_panel.bgcolor = (
                Theme.LAVENDER_SOFT
            )

        update_face_guide(ok, information)
        refresh_capture_button()
        page.update()

    async def ensure_live_engine():
        """InsightFaceとPADを準備する"""
        nonlocal live_engine
        nonlocal registration_pad

        if live_engine is None:
            detection_size = tuple(
                face_auth_config.get(
                    "insightface_det_size",
                    (256, 256),
                )
            )

            live_engine = await asyncio.to_thread(
                InsightFaceEngine,
                "buffalo_l",
                detection_size,
            )
            page._face_registration_engine = (
                live_engine
            )

        if registration_pad is None:
            registration_pad = await asyncio.to_thread(
                PassivePad,
                threshold=float(
                    face_auth_config[
                        "pad_threshold"
                    ]
                ),
            )
            page._face_registration_pad = (
                registration_pad
            )

    async def live_analysis_loop(generation):
        """プレビューとは別周期で撮影可能状態を判定する"""
        error_logged = False
        interval = max(
            0.2,
            float(
                face_auth_config.get(
                    "registration_live_check_interval_sec",
                    0.45,
                )
            ),
        )

        while (
            preview_active
            and view_is_active()
            and generation == live_analysis_generation
        ):
            frame = worker.get_latest_frame(
                max_age_sec=1.0,
            )

            if generation != live_analysis_generation:
                return

            if frame is None:
                apply_live_result(
                    False,
                    {
                        "reason": "カメラ画像を待っています",
                        "face_count": 0,
                    },
                )
                await asyncio.sleep(interval)
                continue

            try:
                async with face_analysis_lock:
                    ok, information = await asyncio.to_thread(
                        live_engine.check_registration_frame,
                        frame,
                        face_auth_config,
                    )
                error_logged = False

            except Exception:
                if not error_logged:
                    logger.exception(
                        "リアルタイム顔判定に失敗しました"
                    )
                    error_logged = True

                ok = False
                information = {
                    "reason": "顔判定を一時的に実行できません",
                    "face_count": 0,
                }

            if (
                not preview_active
                or not view_is_active()
                or generation != live_analysis_generation
            ):
                return

            apply_live_result(
                ok,
                information,
            )
            await asyncio.sleep(interval)

    def delete_captured_files():
        for path in CaptureBuffer.files.copy():
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                logger.warning(
                    "一時画像を削除できません: %s",
                    path,
                    exc_info=True,
                )

        CaptureBuffer.files.clear()

    def discard_captured_path(path):
        try:
            CaptureBuffer.files.remove(path)
        except ValueError:
            pass

        try:
            if path and os.path.exists(path):
                os.remove(path)
        except OSError:
            logger.warning(
                "不合格画像を削除できませんでした: %s",
                path,
                exc_info=True,
            )

    def validate_captured_path(
        path,
        previous_embeddings,
    ):
        image = cv2.imread(path)

        if image is None:
            return (
                False,
                "撮影画像を読み込めませんでした",
                None,
            )

        ok, information = (
            live_engine.check_registration_frame(
                image,
                face_auth_config,
            )
        )

        if not ok:
            return (
                False,
                information.get(
                    "reason",
                    "顔画像を確認できませんでした",
                ),
                None,
            )

        face_info = information["face_info"]
        is_live, pad_information = (
            registration_pad.check(
                image,
                face_info["bbox"],
            )
        )

        if not is_live:
            logger.warning(
                "撮影画像のPAD判定失敗: score=%.4f",
                float(
                    pad_information.get(
                        "live_score",
                        0.0,
                    )
                ),
            )
            return (
                False,
                "実物の顔を確認できませんでした",
                None,
            )

        embedding = face_info["embedding"]
        duplicate_threshold = float(
            face_auth_config[
                "registration_duplicate_threshold"
            ]
        )

        for old_embedding in previous_embeddings:
            similarity = float(
                np.dot(
                    embedding,
                    old_embedding,
                )
            )

            if similarity >= duplicate_threshold:
                return (
                    False,
                    "前の画像とよく似ています。顔の向きや表情を少し変えてください",
                    None,
                )

        return True, "ok", embedding

    def finish_backend_session():
        nonlocal backend_session_active

        if backend_session_active:
            send_message("finishRegistering")
            backend_session_active = False

    async def stop_camera_safely():
        async with camera_stop_lock:
            try:
                await asyncio.to_thread(
                    worker.stop_camera
                )
            except Exception as ex:
                logger.warning("カメラ停止処理に失敗しました", exc_info=True)

    async def stop_preview():
        nonlocal preview_active

        preview_active = False
        await stop_camera_safely()

    def show_camera_retry():
        face_guide_overlay.visible = False
        face_guide_badge.visible = False
        capture_button.disabled = True
        clear_button.disabled = (
            len(CaptureBuffer.files) == 0
        )
        retry_button.disabled = False
        retry_button.visible = True

    async def cancel_registration(_=None):
        if not view_is_active():
            return

        capture_button.disabled = True
        retry_button.disabled = True
        clear_button.disabled = True
        next_button.disabled = True

        set_status(
            "カメラを終了しています",
            Theme.LAVENDER,
            Theme.LAVENDER_SOFT,
            ft.Icons.SYNC,
        )

        page._face_register_view_token = None
        await stop_preview()
        delete_captured_files()
        finish_backend_session()
        page.go("/face")

    async def start_camera(
        clear_existing_captures=True,
    ):
        nonlocal live_engine
        nonlocal live_capture_ready
        nonlocal live_ready_streak
        nonlocal live_analysis_generation
        nonlocal preview_active
        nonlocal backend_session_active

        await asyncio.sleep(0.15)
        if not view_is_active():
            return

        if clear_existing_captures:
            delete_captured_files()

        try:
            camera_index = load_rgb_camera_index()
        except Exception as ex:
            show_camera_retry()
            set_status(
                str(ex),
                Theme.DANGER,
                "#FCECEF",
                ft.Icons.ERROR_OUTLINE,
            )
            return

        camera_label.value = (
            f"使用カメラ: 入口 / "
            f"index {camera_index}"
        )

        set_status(
            "認証処理を一時停止しています",
            Theme.LAVENDER,
            Theme.LAVENDER_SOFT,
            ft.Icons.SYNC,
        )

        released, message = await asyncio.to_thread(
            request_camera_release,
            5.0,
        )

        if not view_is_active():
            send_message("finishRegistering")
            return

        if not released:
            show_camera_retry()
            set_status(
                message,
                Theme.DANGER,
                "#FCECEF",
                ft.Icons.ERROR_OUTLINE,
            )
            return

        backend_session_active = True

        try:
            await asyncio.to_thread(
                worker.front_end_system,
                camera_index,
                False,
            )

            if not view_is_active():
                await stop_camera_safely()
                finish_backend_session()
                return

            ready = await asyncio.to_thread(
                worker.wait_until_ready,
                4.0,
            )

        except Exception as ex:
            try:
                await stop_camera_safely()
            except Exception as stop_ex:
                logger.warning("カメラ停止処理に失敗しました", exc_info=True)

            finish_backend_session()
            show_camera_retry()

            set_status(
                f"カメラ起動エラー: {ex}",
                Theme.DANGER,
                "#FCECEF",
                ft.Icons.ERROR_OUTLINE,
            )
            return

        if not view_is_active():
            await stop_camera_safely()
            finish_backend_session()
            return

        if not ready:
            message = (
                worker.get_camera_error()
                or "カメラを起動できませんでした"
            )

            await stop_camera_safely()
            finish_backend_session()
            show_camera_retry()

            set_status(
                message,
                Theme.DANGER,
                "#FCECEF",
                ft.Icons.ERROR_OUTLINE,
            )
            return

        set_status(
            "顔判定モデルを準備しています",
            Theme.LAVENDER,
            Theme.LAVENDER_SOFT,
            ft.Icons.SYNC,
        )

        try:
            await ensure_live_engine()
        except Exception:
            logger.exception(
                "登録用顔判定モデルを準備できませんでした"
            )
            await stop_camera_safely()
            finish_backend_session()
            show_camera_retry()
            set_status(
                "顔判定モデルを起動できませんでした",
                Theme.DANGER,
                "#FCECEF",
                ft.Icons.ERROR_OUTLINE,
            )
            return

        retry_button.visible = False
        retry_button.disabled = True

        live_analysis_generation += 1
        current_analysis_generation = (
            live_analysis_generation
        )

        preview_active = True
        live_capture_ready = False
        live_ready_streak = 0

        clear_button.disabled = (
            len(CaptureBuffer.files) == 0
        )
        capture_button.disabled = True

        set_status(
            "カメラ接続済み",
            Theme.MINT,
            Theme.MINT_SOFT,
            ft.Icons.VIDEOCAM_OUTLINED,
        )

        apply_live_result(
            False,
            {
                "reason": "顔をカメラに映してください",
                "face_count": 0,
            },
        )
        page.run_task(
            live_analysis_loop,
            current_analysis_generation,
        )

        try:
            while preview_active and view_is_active():
                image_data = worker.get_preview_base64()

                if image_data is None:
                    if not worker.is_camera_open():
                        raise RuntimeError(
                            worker.get_camera_error()
                            or "カメラとの接続が切れました"
                        )

                    await asyncio.sleep(0.12)
                    continue

                preview_image.src_base64 = image_data
                preview_image.visible = True
                placeholder.visible = False

                preview_image.update()
                placeholder.update()

                await asyncio.sleep(0.12)

        except Exception as ex:
            preview_active = False
            capture_button.disabled = True

            if view_is_active():
                set_status(
                    f"プレビューエラー: {ex}",
                    Theme.DANGER,
                    "#FCECEF",
                    ft.Icons.ERROR_OUTLINE,
                )

        finally:
            preview_active = False
            await stop_camera_safely()

            if not moving_to_input:
                finish_backend_session()

        if (
            view_is_active()
            and not moving_to_input
        ):
            show_camera_retry()
            page.update()

    async def retry_camera(_):
        if (
            not view_is_active()
            or preview_active
        ):
            return

        retry_button.visible = False
        retry_button.disabled = True
        capture_button.disabled = True
        preview_image.visible = False
        placeholder.visible = True

        set_status(
            "カメラを再接続しています",
            Theme.LAVENDER,
            Theme.LAVENDER_SOFT,
            ft.Icons.SYNC,
        )

        await start_camera(
            clear_existing_captures=False,
        )

    async def run_capture_cooldown(
        maximum_images,
    ):
        nonlocal cooldown_active

        cooldown_active = True
        cooldown_panel.visible = True
        refresh_capture_button()

        for tick in range(10, -1, -1):
            if (
                not preview_active
                or not view_is_active()
            ):
                break

            cooldown_text.value = (
                f"次の撮影まで {tick / 10:.1f}秒"
            )
            cooldown_bar.value = (
                10 - tick
            ) / 10
            page.update()

            if tick > 0:
                await asyncio.sleep(0.1)

        cooldown_active = False
        cooldown_panel.visible = False
        cooldown_bar.value = 0

        if view_is_active():
            refresh_capture_button()

            if (
                len(CaptureBuffer.files)
                >= maximum_images
            ):
                set_status(
                    f"{maximum_images}枚の撮影が完了しました",
                    Theme.MINT,
                    Theme.MINT_SOFT,
                    ft.Icons.CHECK_CIRCLE_OUTLINE,
                )
            else:
                page.update()


    async def capture_one(_):
        nonlocal capture_busy

        if (
            capture_busy
            or cooldown_active
            or not live_capture_ready
            or not view_is_active()
        ):
            return

        maximum_images = int(
            face_auth_config.get(
                "registration_max_images",
                5,
            )
        )
        minimum_images = int(
            face_auth_config.get(
                "registration_min_images",
                3,
            )
        )

        if len(CaptureBuffer.files) >= maximum_images:
            set_status(
                f"撮影できる画像は{maximum_images}枚までです",
                Theme.DANGER,
                "#FCECEF",
                ft.Icons.INFO_OUTLINE,
            )
            return

        capture_busy = True
        capture_succeeded = False
        capture_button.disabled = True
        clear_button.disabled = True
        next_button.disabled = True
        page.update()

        path = None

        try:
            path = await asyncio.to_thread(
                worker.front_capture_photo
            )

            if not view_is_active():
                if path is not None:
                    discard_captured_path(path)
                return

            if path is None:
                set_status(
                    "撮影できませんでした。少し待ってもう一度お試しください",
                    Theme.DANGER,
                    "#FCECEF",
                    ft.Icons.ERROR_OUTLINE,
                )
                return

            async with face_analysis_lock:
                (
                    image_ok,
                    failure_reason,
                    embedding,
                ) = await asyncio.to_thread(
                    validate_captured_path,
                    path,
                    tuple(accepted_embeddings),
                )

            if not view_is_active():
                discard_captured_path(path)
                return

            if not image_ok:
                discard_captured_path(path)

                apply_live_result(
                    False,
                    {
                        "reason": failure_reason,
                        "face_count": 1,
                    },
                )
                set_status(
                    f"撮り直してください: "
                    f"{failure_reason}",
                    Theme.DANGER,
                    "#FCECEF",
                    ft.Icons.REPLAY,
                )
                return

            accepted_embeddings.append(
                embedding
            )
            capture_succeeded = True

            count = len(CaptureBuffer.files)
            update_capture_progress()

            logger.info(
                "顔登録画像を受理しました: "
                "count=%s, path=%s",
                count,
                path,
            )

            set_status(
                "顔を確認して撮影しました",
                Theme.MINT,
                Theme.MINT_SOFT,
                ft.Icons.CHECK_CIRCLE_OUTLINE,
            )

        except Exception:
            if (
                path is not None
                and not capture_succeeded
            ):
                discard_captured_path(path)

            logger.exception(
                "顔画像の撮影・検査に失敗しました"
            )

            set_status(
                "撮影画像を確認できませんでした。もう一度お試しください",
                Theme.DANGER,
                "#FCECEF",
                ft.Icons.ERROR_OUTLINE,
            )

        finally:
            if (
                capture_succeeded
                and view_is_active()
            ):
                await run_capture_cooldown(
                    maximum_images
                )

            capture_busy = False

            if view_is_active():
                refresh_capture_button()
                clear_button.disabled = (
                    len(CaptureBuffer.files) == 0
                )
                next_button.disabled = (
                    len(CaptureBuffer.files)
                    < minimum_images
                )
                page.update()

    def clear_captures(_):
        if (
            capture_busy
            or not view_is_active()
        ):
            return

        delete_captured_files()
        accepted_embeddings.clear()
        update_capture_progress()
        clear_button.disabled = True
        next_button.disabled = True

        if (
            preview_active
            and worker.is_camera_open()
        ):
            refresh_capture_button()

            set_status(
                "撮影画像を消去しました",
                Theme.MINT,
                Theme.MINT_SOFT,
                ft.Icons.DELETE_SWEEP_OUTLINED,
            )
        else:
            show_camera_retry()

            set_status(
                "カメラが接続されていません。再接続してください",
                Theme.DANGER,
                "#FCECEF",
                ft.Icons.ERROR_OUTLINE,
            )

    async def go_register(_):
        nonlocal moving_to_input

        if (
            moving_to_input
            or not view_is_active()
        ):
            return

        minimum_images = int(
            face_auth_config[
                "registration_min_images"
            ]
        )

        if len(CaptureBuffer.files) < minimum_images:
            set_status(
                f"写真を{minimum_images}枚以上"
                "撮影してください",
                Theme.DANGER,
                "#FCECEF",
                ft.Icons.INFO_OUTLINE,
            )
            return

        moving_to_input = True
        capture_button.disabled = True
        retry_button.disabled = True
        clear_button.disabled = True
        next_button.disabled = True

        set_status(
            "本人情報画面を準備しています",
            Theme.LAVENDER,
            Theme.LAVENDER_SOFT,
            ft.Icons.SYNC,
        )

        page._face_register_view_token = None
        await stop_preview()
        page.go("/face_register/input")

    retry_button = secondary_button(
        "カメラ再接続",
        retry_camera,
        ft.Icons.REFRESH,
    )
    retry_button.width = 220
    retry_button.visible = False

    capture_button = primary_button(
        "撮影",
        capture_one,
        ft.Icons.CAMERA_ALT,
    )

    capture_button.width = 220
    capture_button.disabled = True

    clear_button = secondary_button(
        "撮り直す",
        clear_captures,
        ft.Icons.REFRESH,
    )
    clear_button.width = 220
    clear_button.disabled = True

    next_button = primary_button(
        "本人情報へ",
        go_register,
        ft.Icons.ARROW_FORWARD,
    )
    next_button.width = 220
    next_button.disabled = True

    preview_panel = ft.Container(
        width=560,
        height=350,
        bgcolor="#F7FAFB",
        border=ft.border.all(
            1,
            Theme.BORDER,
        ),
        border_radius=8,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        alignment=ft.alignment.center,
        content=ft.Stack(
            controls=[
                ft.Container(
                    left=0,
                    right=0,
                    top=0,
                    bottom=0,
                    alignment=ft.alignment.center,
                    content=preview_image,
                ),
                ft.Container(
                    left=0,
                    right=0,
                    top=0,
                    bottom=0,
                    alignment=ft.alignment.center,
                    content=placeholder,
                ),
                face_guide_overlay,
                face_guide_badge,
            ],
        ),
    )

    controls_panel = ft.Container(
        width=250,
        content=ft.Column(
            controls=[
                status_panel,
                camera_label,
                live_status_panel,
                ft.Container(height=6),
                capture_progress_panel,
                cooldown_panel,
                ft.Container(height=8),
                capture_button,
                retry_button,
                clear_button,
                next_button,
            ],
            spacing=12,
            horizontal_alignment=(
                ft.CrossAxisAlignment.STRETCH
            ),
        ),
    )

    capture_card = card(
        ft.Row(
            controls=[
                preview_panel,
                controls_panel,
            ],
            spacing=24,
            run_spacing=20,
            wrap=True,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=(
                ft.CrossAxisAlignment.CENTER
            ),
        ),
        accent=Theme.LAVENDER,
        padding=24,
    )

    view = app_view(
        "/face_register",
        page,
        [
            face_registration_steps(1),
            capture_card,
        ],
        back_route="/face",
        on_back=cancel_registration,
    )

    page.run_task(start_camera)
    return view


# views/face_register.py 内の face_register_register
def face_register_register(page: ft.Page) -> ft.View:
    page.title = "本人登録"
    page.padding = 20
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    add_confirm_dialog = ft.AlertDialog(modal=True)

    input_view_token = object()
    page._face_register_input_view_token = input_view_token

    def input_view_is_active():
        return (
            page.route == "/face_register/input"
            and getattr(
                page,
                "_face_register_input_view_token",
                None,
            ) is input_view_token
        )

    registration_engine = getattr(
        page,
        "_face_registration_engine",
        None,
    )
    registration_pad = getattr(
        page,
        "_face_registration_pad",
        None,
    )

    def get_registration_models():
        nonlocal registration_engine
        nonlocal registration_pad

        if registration_engine is None:
            detection_size = tuple(
                face_auth_config.get(
                    "insightface_det_size",
                    (256, 256),
                )
            )
            registration_engine = InsightFaceEngine(
                "buffalo_l",
                detection_size,
            )
            page._face_registration_engine = (
                registration_engine
            )

        if registration_pad is None:
            registration_pad = PassivePad(
                threshold=float(
                    face_auth_config[
                        "pad_threshold"
                    ]
                )
            )
            page._face_registration_pad = (
                registration_pad
            )

        return (
            registration_engine,
            registration_pad,
        )

    # --- 画像プレビュー（最後の1枚） ---→全画像に変更
    image_paths = CaptureBuffer.files.copy()
    logger.debug(
        "顔登録プレビュー画像: %s",
        image_paths,
    )

    preview_controls = []

    if len(image_paths) == 0:
        preview_controls.append(
            ft.Text(
                "画像がありません",
                color=ft.Colors.RED,
            )
        )
    else:
        for path in image_paths:
            if not os.path.exists(path):
                continue

            preview_controls.append(
                ft.Container(
                    content=ft.Image(
                        src=path,
                        width=140,
                        height=100,
                        fit=ft.ImageFit.CONTAIN,
                    ),
                    padding=5,
                )
            )

    # 高さを固定し、画像が増えた場合はこの中をスクロールする
    preview_area = ft.GridView(
        controls=preview_controls,
        max_extent=150,
        spacing=10,
        run_spacing=10,
        child_aspect_ratio=1.4,
        width=420,
        height=230,
    )
    hint = ft.Text(f"直近の撮影: {image_paths}", size=12, color=ft.Colors.BLUE_GREY_600)

    preview = ft.Text("画像がありません", size=16, color=ft.Colors.RED)
    hint = ft.Text(
        f"撮影画像：{len(image_paths)}枚",
        size=12,
        color=ft.Colors.BLUE_GREY_600,
    )

    def prepare_face_samples():
        engine, pad = get_registration_models()

        minimum_images = int(
            face_auth_config["registration_min_images"]
        )
        maximum_images = int(
            face_auth_config["registration_max_images"]
        )

        if len(image_paths) < minimum_images:
            raise ValueError(f"登録画像を{minimum_images}枚以上撮影してください")

        if len(image_paths) > maximum_images:
            raise ValueError(f"登録画像は{maximum_images}枚以下にしてください")

        samples = []
        accepted_embeddings = []

        for image_number, path in enumerate(
            image_paths,
            start=1,
        ):
            image = cv2.imread(path)

            if image is None:
                raise ValueError(f"{image_number}枚目の画像を読み込めませんでした")

            quality_ok, quality = (
                engine.check_registration_frame(
                    image,
                    face_auth_config,
                )
            )

            if not quality_ok:
                reason = str(
                    quality.get(
                        "reason",
                        "顔画像の品質を確認できませんでした",
                    )
                ).strip()

                raise ValueError(f"{image_number}枚目を撮り直してください。{reason}")

            face_info = quality["face_info"]
            embedding = face_info["embedding"]

            is_live, pad_information = pad.check(
                image,
                face_info["bbox"],
            )

            if not is_live:
                live_score = float(
                    pad_information.get(
                        "live_score",
                        0.0,
                    )
                )
                logger.warning(
                    "登録画像のPAD判定失敗: image=%s score=%.4f",
                    image_number,
                    live_score,
                )

                raise ValueError(f"{image_number}枚目で実物の顔を確認できませんでした。カメラの正面で撮り直してください")

            for old_embedding in accepted_embeddings:
                similarity = float(
                    np.dot(
                        embedding,
                        old_embedding,
                    )
                )

                if similarity >= float(
                    face_auth_config[
                        "registration_duplicate_threshold"
                    ]
                ):
                    raise ValueError(f"{image_number}枚目が前の画像とよく似ています。顔の向きや表情を少し変えて撮り直してください"
                    )

            accepted_embeddings.append(embedding)

            encode_ok, encoded = cv2.imencode(
                ".png",
                image,
            )

            if not encode_ok:
                raise ValueError(f"{image_number}枚目の画像を変換できませんでした")

            samples.append(
                (
                    encoded.tobytes(),
                    embedding,
                )
            )

        return samples

    # --- 入力 ---
    registration_finished = False
    registration_busy = False

    input_status_icon = ft.Icon(
        ft.Icons.EDIT_OUTLINED,
        size=17,
        color=Theme.LAVENDER,
    )
    input_status_text = ft.Text(
        "ユーザー名とローマ字名を入力してください",
        size=12,
        color=Theme.TEXT_MUTED,
        font_family=ui_theme.FONT_FAMILY,
        expand=True,
    )
    input_status_panel = ft.Container(
        width=320,
        padding=ft.padding.symmetric(
            horizontal=12,
            vertical=10,
        ),
        bgcolor=Theme.LAVENDER_SOFT,
        border_radius=8,
        content=ft.Row(
            controls=[
                input_status_icon,
                input_status_text,
            ],
            spacing=8,
        ),
    )

    def validate_input_state(_=None):
        import re

        name = (user_name.value or "").strip()
        romaji = " ".join(
            (user_name_romaji.value or "").split()
        )
        romaji_ok = bool(
            re.fullmatch(
                r"[A-Za-z][A-Za-z _'-]*",
                romaji,
            )
        )
        images_ok = (
            len(image_paths)
            >= int(
                face_auth_config.get(
                    "registration_min_images",
                    3,
                )
            )
            and len(image_paths)
            <= int(
                face_auth_config.get(
                    "registration_max_images",
                    5,
                )
            )
            and all(
                os.path.isfile(path)
                for path in image_paths
            )
        )

        if not name:
            message = "ユーザー名を入力してください"
        elif not romaji:
            message = "ローマ字名を入力してください"
        elif not romaji_ok:
            message = (
                "ローマ字名は半角英字で入力してください"
            )
        elif not images_ok:
            message = (
                "撮影画像を確認できません。撮影画面へ戻ってください"
            )
        else:
            message = "入力内容を確認できます"

        valid = bool(
            name
            and romaji_ok
            and images_ok
        )

        input_status_icon.name = (
            ft.Icons.CHECK_CIRCLE_OUTLINE
            if valid
            else ft.Icons.EDIT_OUTLINED
        )
        input_status_icon.color = (
            Theme.MINT if valid else Theme.LAVENDER
        )
        input_status_text.value = message
        input_status_text.color = (
            Theme.MINT if valid else Theme.TEXT_MUTED
        )
        input_status_panel.bgcolor = (
            Theme.MINT_SOFT
            if valid
            else Theme.LAVENDER_SOFT
        )
        user_name_romaji.border_color = (
            Theme.DANGER
            if romaji and not romaji_ok
            else Theme.BORDER
        )
        register_button.disabled = (
            not valid or registration_busy
        )

        if (
            _ is not None
            and input_view_is_active()
        ):
            page.update()

        return valid

    def submit_user_info(event):
        if validate_input_state():
            open_add_confirm_dialog(event)
        else:
            page.update()

    user_name = ft.TextField(
        label="ユーザー名",
        autofocus=True,
        width=320,
        border_radius=8,
        max_length=50,
        on_change=validate_input_state,
        on_submit=lambda e: user_name_romaji.focus(),
    )

    user_name_romaji = ft.TextField(
        label="ユーザー名（ローマ字）",
        width=320,
        border_radius=8,
        max_length=50,
        on_change=validate_input_state,
        on_submit=submit_user_info,
    )

    def finish_backend_registration(_=None):
        nonlocal registration_finished

        if registration_finished:
            return

        send_message("finishRegistering")
        registration_finished = True

    def remove_captured_files():
        for path in image_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError as e:
                logger.warning("一時画像を削除できません: %s", path, exc_info=True)

        CaptureBuffer.files.clear()

    async def finish_register(_):
        if not input_view_is_active():
            return

        page._face_register_input_view_token = None
        page.close(add_confirm_dialog)
        await asyncio.sleep(0.1)
        page.go("/face")

    async def retry_face_capture(_):
        if not input_view_is_active():
            return

        page._face_register_input_view_token = None
        remove_captured_files()
        finish_backend_registration()
        page.close(add_confirm_dialog)

        await asyncio.sleep(0.1)
        page.go("/face_register")


    # --- 登録処理 ---
    async def execute_register(e):
        nonlocal registration_busy

        if (
            registration_busy
            or not input_view_is_active()
        ):
            return

        registration_busy = True
        registration_succeeded = False

        user_name.disabled = True
        user_name_romaji.disabled = True
        register_button.disabled = True
        cancel_button.disabled = True

        add_confirm_dialog.title = ft.Text("登録しています")
        add_confirm_dialog.content = ft.Row(
            controls=[
                ft.ProgressRing(
                    width=22,
                    height=22,
                    stroke_width=2.5,
                    color=Theme.LAVENDER,
                ),
                ft.Text("顔情報を確認しています"),
            ],
            spacing=12,
            alignment=ft.MainAxisAlignment.CENTER,
        )
        add_confirm_dialog.actions = []
        page.update()

        try:
            samples = await asyncio.to_thread(
                prepare_face_samples
            )

            if not input_view_is_active():
                remove_captured_files()
                finish_backend_registration()
                return

            user_id, face_ids = await asyncio.to_thread(
                face_service.register_new_user_with_faces,
                user_name.value,
                user_name_romaji.value,
                samples,
            )

            invalidate_management_counts(page)
            registration_succeeded = True

            remove_captured_files()
            finish_backend_registration()

            if not input_view_is_active():
                return

            logger.info("本人登録完了: user_id=%s name=%s 保存枚数=%s", user_id, user_name.value, len(face_ids))

            add_confirm_dialog.title = ft.Text(
                "登録完了",
                font_family=ui_theme.FONT_FAMILY,
            )
            add_confirm_dialog.content = ft.Column(
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
                        "本人登録が完了しました",
                        size=16,
                        color=Theme.TEXT,
                        weight=ui_theme.FONT_WEIGHT,
                        font_family=ui_theme.FONT_FAMILY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "顔管理画面で登録内容を確認できます",
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
            add_confirm_dialog.actions = [
                ft.TextButton(
                    "顔管理へ",
                    autofocus=True,
                    on_click=finish_register,
                )
            ]

        except Exception as ex:
            can_retake = isinstance(ex, ValueError)

            if can_retake:
                logger.warning(
                    "顔登録の入力・品質チェックに失敗: %s",
                    ex,
                )
                user_message = str(ex)
            else:
                logger.exception(
                    "本人登録処理でエラーが発生しました"
                )
                user_message = (
                    "顔情報を登録できませんでした。時間を置いてもう一度お試しください"
                )

            if not input_view_is_active():
                remove_captured_files()
                finish_backend_registration()
                return

            if can_retake:
                error_title = "撮影画像を確認してください"
                error_icon = ft.Icons.CAMERA_ALT_OUTLINED
                error_color = Theme.SUN
                error_background = Theme.SUN_SOFT
                support_message = (
                    "撮影画面へ戻って、顔画像を撮り直してください"
                )
            else:
                error_title = "登録できませんでした"
                error_icon = ft.Icons.ERROR_OUTLINE
                error_color = Theme.DANGER
                error_background = ui_theme.DANGER_BG
                support_message = (
                    "入力内容は保持されています。しばらく待ってからもう一度お試しください"
                )

            add_confirm_dialog.title = ft.Text(
                error_title,
                font_family=ui_theme.FONT_FAMILY,
            )
            add_confirm_dialog.content = ft.Column(
                controls=[
                    ft.Container(
                        width=58,
                        height=58,
                        bgcolor=error_background,
                        border_radius=29,
                        alignment=ft.alignment.center,
                        content=ft.Icon(
                            error_icon,
                            size=30,
                            color=error_color,
                        ),
                    ),
                    ft.Text(
                        user_message,
                        size=14,
                        color=Theme.TEXT,
                        weight=ui_theme.FONT_WEIGHT,
                        font_family=ui_theme.FONT_FAMILY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        support_message,
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

            if can_retake:
                add_confirm_dialog.actions = [
                    ft.TextButton(
                        "撮り直す",
                        autofocus=True,
                        on_click=retry_face_capture,
                    )
                ]
            else:
                add_confirm_dialog.actions = [
                    ft.TextButton(
                        "入力画面に戻る",
                        autofocus=True,
                        on_click=lambda event: page.close(
                            add_confirm_dialog
                        ),
                    )
                ]

        finally:
            registration_busy = False

            if input_view_is_active():
                if not registration_succeeded:
                    user_name.disabled = False
                    user_name_romaji.disabled = False
                    register_button.disabled = False
                    cancel_button.disabled = False

                page.update()

    # --- 確認ダイアログを開く ---
    def open_add_confirm_dialog(_):
        if (
            registration_busy
            or not input_view_is_active()
        ):
            return

        import re

        name = (user_name.value or "").strip()
        romaji = " ".join(
            (user_name_romaji.value or "").split()
        )

        minimum_images = int(
            face_auth_config.get(
                "registration_min_images",
                3,
            )
        )
        maximum_images = int(
            face_auth_config.get(
                "registration_max_images",
                5,
            )
        )

        missing_images = [
            path
            for path in image_paths
            if not os.path.isfile(path)
        ]

        if not name:
            error_message = (
                "ユーザー名を入力してください"
            )

        elif not romaji:
            error_message = (
                "ローマ字名を入力してください"
            )

        elif not re.fullmatch(
            r"[A-Za-z][A-Za-z _'-]*",
            romaji,
        ):
            error_message = (
                "ローマ字名は半角英字で入力してください"
            )

        elif missing_images:
            error_message = (
                "撮影画像を確認できませんでした。撮影画面へ戻って撮り直してください"
            )

        elif len(image_paths) < minimum_images:
            error_message = (
                f"顔画像を{minimum_images}枚以上"
                "撮影してください"
            )

        elif len(image_paths) > maximum_images:
            error_message = (
                f"顔画像は{maximum_images}枚以下に"
                "してください"
            )

        else:
            error_message = None

        if error_message is not None:
            add_confirm_dialog.title = ft.Text(
                "入力を確認してください"
            )
            add_confirm_dialog.content = ft.Text(
                error_message
            )
            add_confirm_dialog.actions = [
                ft.TextButton(
                    "OK",
                    autofocus=True,
                    on_click=lambda e: page.close(
                        add_confirm_dialog
                    ),
                )
            ]
            page.open(add_confirm_dialog)
            return

        user_name.value = name
        user_name_romaji.value = romaji

        add_confirm_dialog.title = ft.Text(
            "本人登録の確認",
            font_family=ui_theme.FONT_FAMILY,
        )
        add_confirm_dialog.content = ft.Column(
            controls=[
                ft.Text(
                    "次の内容で本人情報を登録します",
                    color=Theme.TEXT_MUTED,
                    font_family=ui_theme.FONT_FAMILY,
                ),
                ft.Container(
                    padding=14,
                    bgcolor=Theme.LAVENDER_SOFT,
                    border_radius=10,
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(
                                        ft.Icons.PERSON_OUTLINE,
                                        size=20,
                                        color=Theme.LAVENDER,
                                    ),
                                    ft.Column(
                                        controls=[
                                            ft.Text(
                                                "ユーザー名",
                                                size=11,
                                                color=Theme.TEXT_MUTED,
                                                font_family=ui_theme.FONT_FAMILY,
                                            ),
                                            ft.Text(
                                                name,
                                                color=Theme.TEXT,
                                                weight=ui_theme.FONT_WEIGHT,
                                                font_family=ui_theme.FONT_FAMILY,
                                            ),
                                        ],
                                        spacing=2,
                                        tight=True,
                                    ),
                                ],
                                spacing=10,
                            ),
                            ft.Row(
                                controls=[
                                    ft.Icon(
                                        ft.Icons.LANGUAGE,
                                        size=20,
                                        color=Theme.LAVENDER,
                                    ),
                                    ft.Column(
                                        controls=[
                                            ft.Text(
                                                "ローマ字名",
                                                size=11,
                                                color=Theme.TEXT_MUTED,
                                                font_family=ui_theme.FONT_FAMILY,
                                            ),
                                            ft.Text(
                                                romaji,
                                                color=Theme.TEXT,
                                                weight=ui_theme.FONT_WEIGHT,
                                                font_family=ui_theme.FONT_FAMILY,
                                            ),
                                        ],
                                        spacing=2,
                                        tight=True,
                                    ),
                                ],
                                spacing=10,
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
        add_confirm_dialog.actions = [
            ft.TextButton(
                "登録する",
                on_click=execute_register,
            ),
            ft.TextButton(
                "入力に戻る",
                autofocus=True,
                on_click=lambda event: page.close(
                    add_confirm_dialog
                ),
            ),
        ]

        page.open(add_confirm_dialog)

    async def cancel_register(_):
        if (
            registration_busy
            or not input_view_is_active()
        ):
            return

        page._face_register_input_view_token = None
        remove_captured_files()
        finish_backend_registration()
        page.close(add_confirm_dialog)
        await asyncio.sleep(0.1)
        page.go("/face")

    # --- キャンセル ---
    def open_cancel_confirm_dialog(_):
        if (
            registration_busy
            or not input_view_is_active()
        ):
            return

        add_confirm_dialog.title = ft.Text(
            "顔登録を中止しますか？",
            font_family=ui_theme.FONT_FAMILY,
        )
        add_confirm_dialog.content = ft.Column(
            controls=[
                ft.Container(
                    width=58,
                    height=58,
                    bgcolor=ui_theme.DANGER_BG,
                    border_radius=29,
                    alignment=ft.alignment.center,
                    content=ft.Icon(
                        ft.Icons.DELETE_OUTLINE,
                        size=30,
                        color=Theme.DANGER,
                    ),
                ),
                ft.Text(
                    "撮影した顔画像と入力内容は破棄されます",
                    size=14,
                    color=Theme.TEXT,
                    weight=ui_theme.FONT_WEIGHT,
                    font_family=ui_theme.FONT_FAMILY,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "この操作は元に戻せません",
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
        add_confirm_dialog.actions = [
            ft.TextButton(
                "中止して戻る",
                on_click=cancel_register,
                style=ft.ButtonStyle(
                    color=Theme.DANGER,
                ),
            ),
            ft.TextButton(
                "登録を続ける",
                autofocus=True,
                on_click=lambda event: page.close(
                    add_confirm_dialog
                ),
            ),
        ]
        page.open(add_confirm_dialog)

    #region UIElements
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

    validate_input_state()

    preview_panel = ft.Container(
        width=440,
        content=ft.Column(
            controls=[
                section_title(
                    "撮影画像",
                    accent=Theme.LAVENDER,
                ),
                ft.Container(height=8),
                preview_area,
                hint,
            ],
            spacing=10,
        ),
    )

    input_panel = ft.Container(
        width=360,
        content=ft.Column(
            controls=[
                section_title(
                    "本人情報",
                    accent=Theme.LAVENDER,
                ),
                ft.Container(height=8),
                input_status_panel,
                user_name,
                user_name_romaji,
                ft.Container(height=12),
                register_button,
                cancel_button,
            ],
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    registration_card = card(
        ft.Row(
            controls=[
                preview_panel,
                input_panel,
            ],
            spacing=28,
            run_spacing=24,
            wrap=True,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        accent=Theme.LAVENDER,
        padding=28,
    )

    return app_view(
        "/face_register/input",
        page,
        [
            face_registration_steps(2),
            registration_card,
        ],
        back_route="/face_register",
        on_back=open_cancel_confirm_dialog,
    )