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


def next_index(target_dir: str, user_name: str, ext=".jpg"):
    """
    指定ユーザーの次の保存番号を取得する
    例)
        otomo_001.jpg
        otomo_002.jpg
    →
        3
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
    -------
    保存したファイルパス
    """

    if not os.path.exists(src_path):
        print(f"[ERROR] ファイルが存在しません: {src_path}")
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

    print(f"[OK] 保存: {dst_path}")

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

        print(f"[OK] 保存: {dst_path}")

        index += 1

    return saved_files



def face_register_view(page: ft.Page) -> ft.View:
    page.title = "顔登録"

    worker = CameraWorker_Front.get_instance()

    preview_active = False
    moving_to_input = False
    backend_session_active = False

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

    capture_count = ft.Text(
        "撮影枚数: 0枚",
        size=16,
        color=Theme.TEXT,
        weight=ft.FontWeight.W_700,
    )

    camera_label = ft.Text(
        "設定カメラを確認中",
        size=12,
        color=Theme.TEXT_MUTED,
    )

    def set_status(
        message,
        color,
        soft_color,
        icon,
    ):
        status_text.value = message
        status_text.color = color
        status_icon.name = icon
        status_icon.color = color
        status_panel.bgcolor = soft_color
        page.update()

    def delete_captured_files():
        for path in CaptureBuffer.files.copy():
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError as ex:
                print(
                    "[WARN] 一時画像を"
                    f"削除できません: {ex}"
                )

        CaptureBuffer.files.clear()

    def finish_backend_session():
        nonlocal backend_session_active

        if backend_session_active:
            send_message("finishRegistering")
            backend_session_active = False

    def stop_preview():
        nonlocal preview_active
        preview_active = False
        worker.stop_camera()

    def cancel_registration(_=None):
        stop_preview()
        delete_captured_files()
        finish_backend_session()
        page.go("/face")

    async def start_camera():
        nonlocal preview_active
        nonlocal backend_session_active

        await asyncio.sleep(0.15)
        delete_captured_files()

        try:
            camera_index = load_rgb_camera_index()
        except Exception as ex:
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

        if not released:
            set_status(
                message,
                Theme.DANGER,
                "#FCECEF",
                ft.Icons.ERROR_OUTLINE,
            )
            return

        backend_session_active = True

        worker.front_end_system(
            camera_index,
            show_window=False,
        )

        ready = await asyncio.to_thread(
            worker.wait_until_ready,
            4.0,
        )

        if not ready:
            message = (
                worker.get_camera_error()
                or "カメラを起動できませんでした"
            )
            set_status(
                message,
                Theme.DANGER,
                "#FCECEF",
                ft.Icons.ERROR_OUTLINE,
            )
            finish_backend_session()
            return

        preview_active = True
        capture_button.disabled = False

        set_status(
            "撮影できます",
            Theme.MINT,
            Theme.MINT_SOFT,
            ft.Icons.CHECK_CIRCLE_OUTLINE,
        )

        while preview_active:
            image_data = (
                worker.get_preview_base64()
            )

            if image_data:
                preview_image.src_base64 = image_data
                preview_image.visible = True
                placeholder.visible = False

                try:
                    preview_image.update()
                    placeholder.update()
                except Exception:
                    break

            await asyncio.sleep(0.12)

    async def capture_one(_):
        maximum_images = int(
            face_auth_config.get(
                "registration_max_images",
                5,
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

        capture_button.disabled = True
        page.update()

        try:
            path = await asyncio.to_thread(
                worker.front_capture_photo
            )

            if path is None:
                set_status(
                    "画像を取得できませんでした",
                    Theme.DANGER,
                    "#FCECEF",
                    ft.Icons.ERROR_OUTLINE,
                )
                return

            count = len(CaptureBuffer.files)
            capture_count.value = f"撮影枚数: {count}枚"

            minimum_images = int(
                face_auth_config.get(
                    "registration_min_images",
                    3,
                )
            )

            next_button.disabled = (
                count < minimum_images
            )

            set_status(
                "撮影しました",
                Theme.MINT,
                Theme.MINT_SOFT,
                ft.Icons.CHECK_CIRCLE_OUTLINE,
            )

        except Exception as ex:
            print(
                f"[ERROR] 顔画像の撮影に失敗しました: {ex}"
            )

            set_status(
                f"撮影エラー: {ex}",
                Theme.DANGER,
                "#FCECEF",
                ft.Icons.ERROR_OUTLINE,
            )

        finally:
            page.update()
            await asyncio.sleep(1.0)

            if preview_active:
                capture_button.disabled = False
                page.update()

    def clear_captures(_):
        delete_captured_files()
        capture_count.value = "撮影枚数: 0枚"
        next_button.disabled = True

        set_status(
            "撮影できます",
            Theme.MINT,
            Theme.MINT_SOFT,
            ft.Icons.CHECK_CIRCLE_OUTLINE,
        )

    def go_register(_):
        nonlocal moving_to_input

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
        stop_preview()
        page.go("/face_register/input")

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
            ],
        ),
    )

    controls_panel = ft.Container(
        width=250,
        content=ft.Column(
            controls=[
                status_panel,
                camera_label,
                ft.Container(height=6),
                capture_count,
                ft.Container(height=8),
                capture_button,
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
            capture_card,
        ],
        back_route="/face",
        on_back=cancel_registration,
    )

    page.run_task(start_camera)
    return view


# views/face_register.py 内の face_register_register
import flet as ft

def face_register_register(page: ft.Page) -> ft.View:
    page.title = "本人登録"
    page.padding = 20
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    add_confirm_dialog = ft.AlertDialog(modal=True)

    # --- 画像プレビュー（最後の1枚） ---→全画像に変更
    image_paths = CaptureBuffer.files.copy()
    print(f"[INFO] プレビュー画像: {image_paths}")

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
        engine = InsightFaceEngine()
        pad = PassivePad(threshold=face_auth_config["pad_threshold"])

        minimum_images = int(face_auth_config["registration_min_images"])
        maximum_images = int(face_auth_config["registration_max_images"])

        if len(image_paths) < minimum_images:
            raise ValueError(f"登録画像を{minimum_images}枚以上撮影して😡")

        if len(image_paths) > maximum_images:
            raise ValueError(f"登録画像は{maximum_images}枚以下にして😡")

        samples = []
        accepted_embeddings = []

        for image_number, path in enumerate(image_paths, start=1):
            image = cv2.imread(path)

            if image is None:
                raise ValueError(f"{image_number}枚目を読み込めない😡 {path}")

            faces = engine.extract_many(image)

            if len(faces) != 1:
                raise ValueError(f"{image_number}枚目には1人だけ写って😡 検出人数={len(faces)}")

            face_info = faces[0]
            embedding = face_info["embedding"]

            quality_ok, quality = (engine.check_registration_quality(image, face_info, face_auth_config))

            if not quality_ok:
                raise ValueError(f"{image_number}枚目の品質がたりない😡 {quality['reason']}")

            is_live, pad_information = pad.check(image, face_info["bbox"])

            if not is_live:
                raise ValueError(f"{image_number}枚目が写真かも❓🤔 PAD={pad_information['live_score']:.4f}")

            for old_embedding in accepted_embeddings:
                similarity = float(np.dot(embedding, old_embedding))

                if similarity >= float(face_auth_config["registration_duplicate_threshold"]):
                    raise ValueError(f"{image_number}枚目が以前の画像とかわらぬ😡 顔の向きや表情を少し変えてね😡")

            accepted_embeddings.append(embedding)

            encode_ok, encoded = cv2.imencode(".png", image)

            if not encode_ok:
                raise ValueError(f"{image_number}枚目をPNGへ変換できない😡")

            samples.append((encoded.tobytes(), embedding))

        return samples

    # --- 入力 ---
    registration_finished = False

    user_name = ft.TextField(
        label="ユーザー名",
        autofocus=True,
        width=320,
        border_radius=8,
        max_length=50,
        on_submit=lambda e: user_name_romaji.focus(),
    )

    user_name_romaji = ft.TextField(
        label="ユーザー名（ローマ字）",
        width=320,
        border_radius=8,
        max_length=50,
        on_submit=lambda e: open_add_confirm_dialog(e)
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
                print(f"[WARN] 一時画像を削除できません {path} : {e}")

        CaptureBuffer.files.clear()

    async def finish_register(_):
        page.close(add_confirm_dialog)
        await asyncio.sleep(0.1)
        page.go("/face")

    # --- 登録処理 ---
    async def execute_register(e):
        if e.control.disabled:
            return

        e.control.disabled = True
        page.update()

        try:
            samples = await asyncio.to_thread(
                prepare_face_samples
            )

            user_id, face_ids = await asyncio.to_thread(
                face_service.register_new_user_with_faces,
                user_name.value,
                user_name_romaji.value,
                samples,
            )

            remove_captured_files()
            finish_backend_registration()

            print(
                f"[本人登録] "
                f"user_id={user_id} "
                f"{user_name.value} "
                f"保存枚数={len(face_ids)}"
            )

            add_confirm_dialog.title = ft.Text("登録完了")
            add_confirm_dialog.content = ft.Text(
                "本人登録が完了しました。"
            )
            add_confirm_dialog.actions = [
                ft.TextButton(
                    "OK",
                    autofocus=True,
                    on_click=finish_register,
                )
            ]
            page.update()

        except Exception as ex:
            e.control.disabled = False

            print(
                f"[ERROR] 本人登録に失敗しました: {ex}"
            )

            add_confirm_dialog.title = ft.Text("登録エラー")
            add_confirm_dialog.content = ft.Text(
                f"本人登録に失敗しました。\n{ex}"
            )
            add_confirm_dialog.actions = [
                ft.TextButton(
                    "閉じる",
                    autofocus=True,
                    on_click=lambda event: page.close(
                        add_confirm_dialog
                    ),
                )
            ]
            page.update()

    # --- 確認ダイアログを開く ---
    def open_add_confirm_dialog(_):
        import re

        name = (user_name.value or "").strip()
        romaji = (user_name_romaji.value or "").strip()

        if not name:
            error_message = "ユーザー名を入力してください"

        elif not romaji:
            error_message = "ローマ字名を入力してください"

        elif not re.fullmatch(
            r"[A-Za-z][A-Za-z _'-]*",
            romaji,
        ):
            error_message = (
                "ローマ字名は半角英字で入力してください"
            )

        elif len(image_paths) == 0:
            error_message = "画像はありません"

        else:
            error_message = None

        if error_message is not None:
            add_confirm_dialog.title = ft.Text("エラー")
            add_confirm_dialog.content = ft.Text(
                error_message
            )
            add_confirm_dialog.actions = [
                ft.TextButton(
                    "OK",
                    on_click=lambda e: page.close(
                        add_confirm_dialog
                    ),
                )
            ]
            page.open(add_confirm_dialog)
            return

        add_confirm_dialog.title = ft.Text(
            "本人登録の確認"
        )
        add_confirm_dialog.content = ft.Text(
            f"ユーザー名: {name}\n"
            f"ローマ字名: {romaji}\n"
            "で登録しますか？"
        )
        add_confirm_dialog.actions = [
            ft.TextButton(
                "はい",
                on_click=execute_register,
            ),
            ft.TextButton(
                "いいえ",
                on_click=lambda e: page.close(
                    add_confirm_dialog
                ),
            ),
        ]
        page.open(add_confirm_dialog)

    async def cancel_register(_):
        remove_captured_files()
        finish_backend_registration()
        page.close(add_confirm_dialog)
        await asyncio.sleep(0.1)
        page.go("/face")

    # --- キャンセル ---
    def open_cancel_confirm_dialog(_):
        add_confirm_dialog.title = ft.Text("キャンセル確認")
        add_confirm_dialog.content = ft.Text("登録をキャンセルしますか？（一時画像は削除されます）")
        add_confirm_dialog.actions = [
            ft.TextButton("はい", on_click=cancel_register),
            ft.TextButton(
                "いいえ",
                on_click=lambda e: page.close(
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

    cancel_button = danger_button(
        "キャンセル",
        open_cancel_confirm_dialog,
        ft.Icons.CLOSE,
    )
    cancel_button.width = 200

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
        [registration_card],
        back_route="/face_register",
        on_back=open_cancel_confirm_dialog,
    )