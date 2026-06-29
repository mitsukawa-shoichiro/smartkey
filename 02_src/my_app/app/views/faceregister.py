import socket
import flet as ft
import cv2
import os
import threading
import queue
from datetime import datetime
import tempfile, cv2, os
import service.db_manager as db
import random

from app.utils.front_camera_moduel import CameraWorker_Front, CaptureBuffer

#region util
import shutil
savedir="./db/FaceLib"

from pathlib import Path
import glob
import shutil
import os

savedir = "./db/FaceLib"


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
def SaveFaceDatas(src_paths,
                new_name,
                target_dir=savedir):
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

        dst_path = os.path.join(
            target_dir,
            f"{new_name}_{index:03d}{ext}"
        )

        shutil.copy2(src_path, dst_path)

        saved_files.append(dst_path)

        print(f"[OK] 保存: {dst_path}")

        index += 1

    return saved_files



def faceRegister_view(page: ft.Page) -> ft.View:
    page.title = "顔登録"
    page.padding = 20
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    CameraWorker_Front()


    status = ft.Text("カメラ未起動", size=16)

    def open_cam(_):
        CaptureBuffer.files.clear()
        #前回のバッファをクリアする
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

#撮影後にさらに撮影するかどうかを誘導
    def capture_one(_):
        CameraWorker_Front.instance.front_capture_photo()

        count = len(CaptureBuffer.files)

        capture_count.value = f"撮影枚数：{count}枚"

        if count > 0:
            status.value = "撮影しました。さらに撮影するか、『登録へ進む』を押してください。"
        else:
            status.value = "撮影に失敗しました。"

        page.update()
#登録画面に遷移するボタンの追加
    def go_register(_):

        if len(CaptureBuffer.files) == 0:

            status.value = "写真を1枚以上撮影してください。"
            status.update()
            return

        page.go("/faceRegister/input")

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
        "/faceRegister",
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
                                ft.ElevatedButton("撮影", icon=ft.Icons.CAMERA, on_click=capture_one),
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


# views/faceRegister.py 内の faceRegister_register
import flet as ft

def faceRegister_register(page: ft.Page) -> ft.View:
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
                color=ft.Colors.RED
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
        preview_area = ft.Row(
            controls=preview_controls,
            wrap=True,
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
        )
    hint = ft.Text(f"直近の撮影: {image_paths}", size=12, color=ft.Colors.BLUE_GREY_600)
    
    preview = ft.Text("画像がありません", size=16, color=ft.Colors.RED)
    hint = ft.Text(
        f"撮影画像：{len(image_paths)}枚",
        size=12,
        color=ft.Colors.BLUE_GREY_600,
    )

    # --- 入力 ---
    user_name = ft.TextField(
        label="ユーザー名",
        autofocus=True,
        width=320,
        border_radius=8,
        max_length=50,
    )
    # --- 入力 ---
    user_name_romaji = ft.TextField(
        label="ユーザー名（ローマ字）",
        autofocus=True,
        width=320,
        border_radius=8,
        max_length=50,
    )
    # --- 登録処理 ---
    def execute_register(e):

        #region 保存処理

        # TODO: ここで正式保存（DB 登録 / 画像の本保存先へ移動 など）

        # イメージセーブ
        saved_files = SaveFaceDatas(
            image_paths,
            user_name_romaji.value
        )

        # DB登録
        db.insert_facedata(user_name.value, user_name_romaji.value)
        for path in image_paths:
            if os.path.exists(path):
                os.remove(path)    #一時画像ファイルの削除
        CaptureBuffer.files.clear() #一時画像の消去
        print(
            f"[本人登録] "
            f"{user_name.value} "
            f"保存枚数={len(saved_files)}"
        )

        # 完了ダイアログ
        page.close(add_confirm_dialog)
        add_confirm_dialog.title = ft.Text("登録完了")
        add_confirm_dialog.content = ft.Text("本人登録が完了しました。")
        add_confirm_dialog.actions = [
            ft.TextButton("OK", autofocus=True, on_click=lambda e: page.go("/faceRegister")),
        ]
        page.open(add_confirm_dialog)



    # --- 確認ダイアログを開く ---
    def open_add_confirm_dialog(e):
        # region 入力チェック
        if not user_name.value:
            add_confirm_dialog.title = ft.Text("エラー")
            add_confirm_dialog.content = ft.Text("ユーザー名を入力してください")
            add_confirm_dialog.actions = [
                ft.TextButton("OK", on_click=lambda e: page.close(add_confirm_dialog))
            ]
            page.open(add_confirm_dialog)
            return

        # region 入力チェック
        if not user_name_romaji.value:
            add_confirm_dialog.title = ft.Text("エラー")
            add_confirm_dialog.content = ft.Text("ローマ字を入力してください")
            add_confirm_dialog.actions = [
                ft.TextButton("OK", on_click=lambda e: page.close(add_confirm_dialog))
            ]
            page.open(add_confirm_dialog)
            return
        import re
        def is_romaji(s):
            return bool(re.fullmatch(r"[A-Za-z_]+", s))

        if not is_romaji(user_name_romaji.value):
            add_confirm_dialog.title = ft.Text("エラー")
            add_confirm_dialog.content = ft.Text(
                "ローマ字のみで入力してください（A–Z / a–z、_可）"
            )
            add_confirm_dialog.actions = [
                ft.TextButton("OK", on_click=lambda e: page.close(add_confirm_dialog))
            ]
            page.open(add_confirm_dialog)
            return


        # 画像がない場合の警告（任意）
        if len(image_paths) == 0:
            add_confirm_dialog.title = ft.Text("エラー")
            add_confirm_dialog.content = ft.Text("画像はありません")
            add_confirm_dialog.actions = [
                ft.TextButton("OK", on_click=lambda e: page.close(add_confirm_dialog))
            ]
            page.open(add_confirm_dialog)
            return
        # endregion


        add_confirm_dialog.title = ft.Text("本人登録の確認")
        add_confirm_dialog.content = ft.Text(
            f"ユーザー名: {user_name.value}\ローマ字: {user_name_romaji.value}\nで登録しますか？"
        )
        add_confirm_dialog.actions = [
            ft.TextButton("はい", on_click=execute_register),
            ft.TextButton("いいえ", on_click=lambda e: page.close(add_confirm_dialog)),
        ]
        page.open(add_confirm_dialog)

        #endregion
    def cancel_register(e):
        CaptureBuffer.files.clear()
        page.close(add_confirm_dialog)
        page.go("/faceRegister")

    # --- キャンセル ---
    def open_cancel_confirm_dialog(e):
        add_confirm_dialog.title = ft.Text("キャンセル確認")
        add_confirm_dialog.content = ft.Text("登録をキャンセルしますか？（一時画像は削除されます）")
        add_confirm_dialog.actions = [
            ft.TextButton("はい", on_click=cancel_register),
            ft.TextButton("いいえ", on_click=lambda e: page.close(add_confirm_dialog)),
        ]
        page.open(add_confirm_dialog)


    title_and_preview_area = ft.Column(
        controls=[
            ft.Text("本人登録", size=28, weight=ft.FontWeight.BOLD),
            # 外部で定義された preview と hint を使用
            preview_area,          # ← 画像を表示するft.Imageコントロール
            hint,             # ← 画像に関するヒントテキスト
            user_name,        # ← ユーザー名入力欄（ft.TextFieldなどを想定）
            user_name_romaji, # ← ユーザー名（ローマ字）入力欄
            ft.Container(height=20),
        ],
        spacing=16,
        alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    #region UIElements



    # 2. ボタンエリアのコンポーネント
    button_area = ft.Column(
        controls=[
            ft.ElevatedButton(
                "登録",
                icon=ft.Icons.CHECK,
                width=200,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
                on_click=open_add_confirm_dialog, # 外部で定義された関数
            ),
            ft.ElevatedButton(
                "キャンセル",
                icon=ft.Icons.ARROW_BACK,
                width=200,
                color=ft.Colors.RED,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
                on_click=open_cancel_confirm_dialog, # 外部で定義された関数
            ),
        ],
        spacing=20,
        alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # 3. メインコンテンツ（中央揃えのコンテナ）
    main_content = ft.Container(
        content=ft.Column(
            controls=[
                title_and_preview_area,  # 1. タイトル＆プレビュー

                button_area,             # 2. ボタンエリア
            ],
            spacing=0, # title_and_preview_area と button_area の間のスペースは既に内部で調整済み
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        margin=ft.margin.only(top=80),
        width=420,
    )

    # --- 画面 (ft.View) への統合 ---
    # ft.Viewのcontrolsは、画面全体の中央揃えを実現するためにft.Rowで囲みます
    return ft.View(
        "/faceRegister/input",
        controls=[
            ft.Row(
                controls=[
                    main_content, # 3. メインコンテンツ
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                expand=True,
            )
        ]
    )
    #endregion