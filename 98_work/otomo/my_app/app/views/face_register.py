import socket
import flet as ft
import cv2
import os
import threading
import queue
from datetime import datetime
import tempfile, cv2, os
import my_app.models.db_manager as db
import random

from my_app.app.utils.front_camera_module import CameraWorker_Front, CaptureBuffer

#region util
import shutil
savedir="./db/FaceLib"
def SaveFaceData(src_path: str, new_name: str,target_dir=savedir) :
    if not os.path.exists(src_path):
        print(f"[ERROR] ファイルが存在しません: {src_path}")
        return None

    # 保存先ディレクトリ
    if target_dir is None:
        target_dir = os.path.dirname(src_path)
    os.makedirs(target_dir, exist_ok=True)

    _, ext = os.path.splitext(src_path)
    if not ext:
        ext = ".jpg"

    # 連番で空き名を探す
    counter = 1
    while True:
        new_filename = f"{new_name}_{counter:03d}{ext}"
        dst_path = os.path.join(target_dir, new_filename)
        if not os.path.exists(dst_path):
            shutil.copy2(src_path, dst_path)  # ← コピー
            print(f"[OK] 画像を保存しました: {dst_path}")
            return dst_path
        counter += 1

#endregion



def face_register_view(page: ft.Page) -> ft.View:
    page.title = "顔登録"
    page.padding = 20
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    CameraWorker_Front()


    status = ft.Text("カメラ未起動", size=16)

    def open_cam(_):
        CameraWorker_Front.instance.close_camera = False
        CameraWorker_Front.instance.front_end_system(camera_index_input_area.value)

        status.value = "カメラ起動中（別ウィンドウにプレビュー表示）"
        status.update()

    def close_cam(_):
        CameraWorker_Front.instance.close_camera = True
        status.value = "カメラ停止コマンドを送信しました"
        status.update()

    def __cleanup(_=None):

        CameraWorker_Front.instance.close_camera = True

    def capture_one(_):
        CameraWorker_Front.instance.front_capture_photo()
        if len(CaptureBuffer.files) > 0:
            path = CaptureBuffer.get_newest_shot()  # 最新の1枚
            print(f"[OK] 撮影成功: {path}")
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

    # --- 画像プレビュー（最後の1枚） ---
    last_img_path = CaptureBuffer.files[-1]
    print(f"[INFO] プレビュー画像: {last_img_path}")
    if last_img_path and os.path.exists(last_img_path):
        preview = ft.Image(
            src=last_img_path,        # デスクトップアプリならローカルパスでOK
            width=320, height=240,
            fit=ft.ImageFit.CONTAIN,
        )
        hint = ft.Text(f"直近の撮影: {last_img_path}", size=12, color=ft.Colors.BLUE_GREY_600)
    else:
        preview = ft.Text("画像がありません", size=16, color=ft.Colors.RED)
        hint = ft.Text("", size=12)

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
        SaveFaceData(CaptureBuffer.files[-1], user_name_romaji.value)

        # DB登録
        db.insert_facedata(user_name.value, user_name_romaji.value)

        print(f"[本人登録] ユーザー名={user_name.value}  画像={CaptureBuffer.files[-1]}")

        # 完了ダイアログ
        page.close(add_confirm_dialog)
        add_confirm_dialog.title = ft.Text("登録完了")
        add_confirm_dialog.content = ft.Text("本人登録が完了しました。")
        add_confirm_dialog.actions = [
            ft.TextButton("OK", autofocus=True, on_click=lambda e: page.go("/face_register")),
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
        if not CaptureBuffer.files[-1]:
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


    # --- キャンセル ---
    def open_cancel_confirm_dialog(e):
        add_confirm_dialog.title = ft.Text("キャンセル確認")
        add_confirm_dialog.content = ft.Text("登録をキャンセルしますか？（一時画像は残ります）")
        add_confirm_dialog.actions = [
            ft.TextButton("はい", on_click=lambda e: page.go("/face_register")),
            ft.TextButton("いいえ", on_click=lambda e: page.close(add_confirm_dialog)),
        ]
        page.open(add_confirm_dialog)


    title_and_preview_area = ft.Column(
        controls=[
            ft.Text("本人登録", size=28, weight=ft.FontWeight.BOLD),
            # 外部で定義された preview と hint を使用
            preview,          # ← 画像を表示するft.Imageコントロール
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
        "/face_register/input",
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