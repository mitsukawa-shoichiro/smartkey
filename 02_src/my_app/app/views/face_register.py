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

from my_app.app.utils.front_camera_moduel import CameraWorker_Front, CaptureBuffer, send_message

from my_app.app.views.common import build_user_autocomplete
from my_app.camera.face_util.insightface_engine import InsightFaceEngine
from my_app.service import face_service

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
    page.padding = 20
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    CameraWorker_Front()


    status = ft.Text("カメラ未起動", size=16)

    async def open_cam(_):
        CaptureBuffer.files.clear()
        #前回のバッファをクリアする

        send_message("startRegistering")
        await asyncio.sleep(0.5)

        CameraWorker_Front.instance.close_camera = False
        CameraWorker_Front.instance.front_end_system(camera_index_input_area.value)

        status.value = "カメラ起動中（別ウィンドウにプレビュー表示）"
        status.update()

    #撮影枚数を提示
    capture_count = ft.Text(
        "撮影枚数：0枚",
        size=16,
        color=ft.Colors.BLUE,
    )

    def close_cam(_):
        CameraWorker_Front.instance.close_camera = True
        status.value = "カメラ停止コマンドを送信しました"
        status.update()

    def __cleanup(_=None):

        CameraWorker_Front.instance.close_camera = True
        CaptureBuffer.files.clear()

# 拍摄后引导用户选择是否继续拍摄
    async def capture_one(e):
        maximum_images = int(
            face_auth_config["registration_max_images"])

        if len(CaptureBuffer.files) >= maximum_images:
            status.value = (f"撮影できる画像は {maximum_images}枚まで！")
            page.update()
            return

        # 为防止连续点击, 在开始拍摄的同时立即禁用按钮
        e.control.disabled = True
        status.value = "撮影中..."
        page.update()

        before_count = len(CaptureBuffer.files)

        try:
            await asyncio.to_thread(CameraWorker_Front.instance.front_capture_photo)

            count = len(CaptureBuffer.files)
            capture_count.value = f"撮影枚数: {count}枚"

            if count > before_count:
                status.value = "1秒まって～"
            else:
                status.value = "しっぱい；；"

            page.update()

            # 1秒間のクールタイム
            await asyncio.sleep(1.0)

        finally:
            e.control.disabled = False
            status.value = "撮影可能"
            page.update()

    capture_button = ft.ElevatedButton("撮影", icon = ft.Icons.CAMERA, on_click = capture_one)


# 登録画面に遷移するボタンの追加
    def go_register(_):

        minimum_images = int(face_auth_config["registration_min_images"])

        if len(CaptureBuffer.files) < minimum_images:
            status.value = f"写真を{minimum_images}枚以上撮影してください。"
            status.update()
            return

        page.go("/face_register/input")

    #region face_register_view
    camera_index_input_area = ft.TextField(
        label="Camera Index",
        hint_text="0、1、2 …",
        value="",
        width=220,
        prefix_text="",
        keyboard_type=ft.KeyboardType.NUMBER,
        autofocus=True,
    )


    v = ft.View(
        "/face_register",
        controls=[
            ft.Container(
                expand=True,
                content=ft.Column(
                    [
                        ft.Text("顔登録", size=24, weight=ft.FontWeight.BOLD),
                        status,
                        capture_count,
                        camera_index_input_area,
                        ft.Row(
                            [
                                ft.ElevatedButton("カメラを起動", icon=ft.Icons.VIDEOCAM, on_click=open_cam),
                                capture_button,
                                ft.ElevatedButton("カメラを終了", icon=ft.Icons.VIDEOCAM_OFF, on_click=close_cam),
                            ], ft.MainAxisAlignment.CENTER
                        ),
                        ft.Text(
                            "説明：『カメラを起動』で別ウィンドウにプレビュー、"
                            "『撮影』で ./db/FaceLib に保存、"
                            "『カメラを終了』で閉じます。",
                            size=12,
                            color=ft.Colors.BLUE_GREY_600,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "写真は真正面一枚でお願いします。  ",
                            size=12,
                            color=ft.Colors.BLUE_GREY_600,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "または、本人登録画面で『キャンセル』を押してやり直すこともできます。",
                            size=12,
                            color=ft.Colors.BLUE_GREY_600,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.ElevatedButton(
                            "登録へ",
                            on_click=go_register
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=12,
                    expand=True,  # 占满垂直空间
                ),
            ),
            # ✅ 左下角固定的戻る按钮
            ft.Container(
                alignment=ft.alignment.bottom_left,
                padding=20,
                content=ft.ElevatedButton(
                    "戻る",
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: (__cleanup(), page.go("/index")),
                ),
            ),
        ],
    )


    v.on_dispose = __cleanup
    return v
    #endregion


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
        page.go("/face_register")

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
        page.go("/face_register")

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
    main_content = ft.Column(
        controls=[
            ft.Text(
                "本人登録",
                size=28,
                weight=ft.FontWeight.BOLD,
            ),
            preview_area,
            hint,
            user_name,
            user_name_romaji,
            ft.ElevatedButton(
                "登録",
                icon=ft.Icons.CHECK,
                width=200,
                on_click=open_add_confirm_dialog,
            ),
            ft.ElevatedButton(
                "キャンセル",
                icon=ft.Icons.ARROW_BACK,
                width=200,
                color=ft.Colors.RED,
                on_click=open_cancel_confirm_dialog,
            ),
        ],
        spacing=16,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    view = ft.View(
        "/face_register/input",
        controls=[
            ft.Container(
                content=main_content,
                width=440,
                expand=True,
                alignment=ft.alignment.top_center,
                padding=ft.padding.only(top=30, bottom=30),
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO,
    )

    view.on_dispose = finish_backend_registration
    return view
    #endregion