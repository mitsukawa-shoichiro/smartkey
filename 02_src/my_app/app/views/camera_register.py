import flet as ft
import os
import cv2
import re
from my_app.camera.face_util.insightface_engine import InsightFaceEngine

#region config
import json
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

camera_config_path = os.path.join(BASE_DIR, "..", "..", "config", "camera_settings.json")
card_config_path = os.path.join(BASE_DIR, "..", "..", "config", "usb_settings.json")


with open(camera_config_path, "r", encoding="utf-8") as fc:
    camera_config = json.load(fc)
print(camera_config)


with open(card_config_path, "r", encoding="utf-8") as cc:
    card_config = json.load(cc)
print(card_config)


#endregion



#region face util functions
_face_engine = None

def get_face_engine():
    """
    顔検出モデルを最初の一回だけつくる
    """
    global _face_engine

    if _face_engine is None:
        _face_engine = InsightFaceEngine()

    return _face_engine

def detect(image_path: str, model="hog", out_path="detected.jpg") -> int:
    """
    画像から顔を検出して矩形を描画し、保存する。
    検出数を返す。
    """
    img_cv = cv2.imread(image_path)

    if img_cv is None:
        raise ValueError(
            f"画像を読み込めません: {image_path}"
        )

    faces = get_face_engine().detect_faces(img_cv)
    image_height, image_width = img_cv.shape[:2]

    for face in faces:
        x1, y1, x2, y2 = [
            int(round(float(value)))
            for value in face.bbox
        ]

        x1 = max(0, min(x1, image_width - 1))
        x2 = max(0, min(x2, image_width))
        y1 = max(0, min(y1, image_height - 1))
        y2 = max(0, min(y2, image_height))

        cv2.rectangle(
            img_cv,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2,
        )

    cv2.imwrite(out_path, img_cv)

    print(
        f"[OK] {len(faces)} 枚の顔を検出、"
        f"保存先: {out_path}"
    )

    return len(faces)

def Detect_face(camera_count=4) -> int:
    index = -1
    temp_files = []

    for i in range(camera_count):
        cap = cv2.VideoCapture(i)
        if not cap.isOpened():
            print(f"[WARN] カメラ {i} が開けません。")
            continue

        ret, frame = cap.read()
        cap.release()

        if not ret:
            print(f"[ERROR] カメラ {i} から映像を取得できません。")
            continue

        temp_path = f"temp_cam{i}.jpg"
        cv2.imwrite(temp_path, frame)
        temp_files.append(temp_path)

        # fd.detect はあなたの顔検出メソッド
        faces = detect(temp_path)
        if faces:  # 検出された場合
            print(f"[OK] カメラ {i} で顔を検出しました。")
            index = i
            break
        else:
            print(f"[INFO] カメラ {i} では顔が見つかりません。")

    # 一時ファイル削除
    for f in temp_files:
        if os.path.exists(f):
            os.remove(f)

    return index


from enum import Enum

class IndexEnum(Enum):
    入口 = "入口"
    出口 = "出口"
    テスト = "テスト"


def set_camera_config(camera_enum: IndexEnum, camera_index: int):
    camera_config["devices"][camera_enum.value]["index"] = camera_index

    with open(camera_config_path, "w", encoding="utf-8") as f:
        json.dump(camera_config, f, ensure_ascii=False, indent=2)

#endregion

#region card_util methods
from my_app.service.nfcutils.card_scan import scan_cardreader
def detect_cardreader() -> int:
    print("dectedreader")
    readerindex=int(scan_cardreader())

    return readerindex



def set_card_config(card_enum:IndexEnum,card_index:int):
    card_config["devices"][card_enum.value]["index"] = card_index

    with open(card_config_path, "w", encoding="utf-8") as f:
        json.dump(card_config, f, ensure_ascii=False, indent=2)

#endregion


def camera_register_view(page: ft.Page) -> ft.View:

    page.title = "設備設定"

    page.theme_mode = ft.ThemeMode.LIGHT
    #入口、出口にして
    card_indoor_text = ft.Text("現在:"+str(card_config["devices"][IndexEnum.テスト.value]["index"]), size=20)

    card_outdoor_text = ft.Text("現在:"+str(card_config["devices"][IndexEnum.テスト.value]["index"]), size=20)

    face_indoor_text = ft.Text("現在:" + str(camera_config["devices"][IndexEnum.入口.value]["index"]),size=20)

    face_outdoor_text = ft.Text("現在:" + str(camera_config["devices"][IndexEnum.出口.value]["index"]),size=20)


    #region face_util_method
    face_text = ft.Text("まだ検出していません。", size=20)


    def on_detect_click_face(e):
        print(face_text.value)
        face_text.value = "検出中..."
        page.update()
        try:
            cam_index = Detect_face(camera_count=4)
            if cam_index >= 0:
                face_text.value = f"顔を検出したカメラ番号: [{cam_index}]"
            else:
                face_text.value = "顔が検出されませんでした。"
        except Exception as ex:
            face_text.value = f"エラー: {ex}"
        page.update()


    def SetCameraIndex(camera_enum: IndexEnum):
        match = re.search(r"\[(\d+)\]", face_text.value)
        if match:
            cam_index = int(match.group(1))
            set_camera_config(camera_enum,cam_index)
            update_text_face()

    def update_text_face():
        with open(camera_config_path, "r", encoding="utf-8",) as fc:
            camera_config = json.load(fc)

        print(camera_config)

        face_indoor_text.value = ("現在:" + str(camera_config["devices"][IndexEnum.入口.value]["index"]))
        face_outdoor_text.value = ("現在:" + str(camera_config["devices"][IndexEnum.出口.value]["index"]))

    #endregion


    #region card_util method
    card_text = ft.Text("まだ検出していません。", size=20)


    def on_detect_click_card(e):
        card_text.value = "検出中..."
        page.update()
        try:
            cardreader_index = int(detect_cardreader())
            if cardreader_index >= 0:
                card_text.value = f"検出したカード番号: [{cardreader_index}]"
            else:
                card_text.value = "カードが検出されませんでした。"
        except Exception as ex:
            card_text.value = f"エラー: {ex}"
        page.update()

    def SetCardIndex(card_enum: IndexEnum):
        match = re.search(r"\[(\d+)\]", card_text.value)
        if match:
            cardreader_index = int(match.group(1))
            set_card_config(card_enum, cardreader_index)
            update_text_card()

    def update_text_card():
        with open(card_config_path, "r", encoding="utf-8") as fc:
            card_config = json.load(fc)
        print(card_config)
        card_indoor_text.value = "現在:"+str(card_config["devices"][IndexEnum.テスト.value]["index"])
        card_outdoor_text.value = "現在:"+str(card_config["devices"][IndexEnum.テスト.value]["index"])


    #endregion


    #region buttons
    #region face_button
    face_button = ft.ElevatedButton(text="顔を検出する", on_click=on_detect_click_face, width=200)

    set_face_indoor_button = ft.ElevatedButton(
        text="入口カメラに設定",
        on_click=lambda e: SetCameraIndex(IndexEnum.入口),
        width=200,
    )
    set_face_outdoor_button = ft.ElevatedButton(
        text="出口カメラに設定",
        on_click=lambda e: SetCameraIndex(IndexEnum.出口),
        width=200,
    )

    #endregion
    #region card_button
    card_button = ft.ElevatedButton(text="カードリーダーを検出する", on_click=on_detect_click_card, width=200)



    set_card_indoor_button = ft.ElevatedButton(
        text="入口カードリーダー設定",
        on_click=lambda e: SetCardIndex( IndexEnum.テスト),
        width=200,
    )
    set_card_outdoor_button = ft.ElevatedButton(
        text="出口カードリーダー設定",
        on_click=lambda e: SetCardIndex( IndexEnum.テスト),
        width=200,
    )

    #endregion
    #endregion


    #region face_register_view


    face_content = ft.Row(
        [ face_button,face_text],
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.CENTER
    )

    face_button = ft.Row(
        [set_face_indoor_button, set_face_outdoor_button],
        alignment=ft.MainAxisAlignment.SPACE_EVENLY,
        vertical_alignment=ft.CrossAxisAlignment.CENTER
    )

    face_text_area = ft.Row(
        [face_indoor_text, face_outdoor_text],
        alignment=ft.MainAxisAlignment.SPACE_EVENLY,
        vertical_alignment=ft.CrossAxisAlignment.CENTER
    )
    face_register_view = ft.Column(
        [face_content, face_button,face_text_area],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )


    #endregion

    #region card_register_view


    card_button = ft.ElevatedButton(text="カードを検出する", on_click=on_detect_click_card, width=200)

    card_content = ft.Row(
        [card_button,card_text],
        alignment=ft.MainAxisAlignment.CENTER,
    )

    card_button=ft.Row(
        [
        set_card_indoor_button,
        set_card_outdoor_button],
        alignment=ft.MainAxisAlignment.SPACE_EVENLY,
        vertical_alignment=ft.CrossAxisAlignment.CENTER

    )

    card_text_area=ft.Row(
        [
        card_indoor_text,
        card_outdoor_text],
        alignment=ft.MainAxisAlignment.SPACE_EVENLY,
        vertical_alignment=ft.CrossAxisAlignment.CENTER

    )

    card_register_view = ft.Column(
        [card_content, card_button,card_text_area],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    #endregion


    back_btn = ft.ElevatedButton(
                    "戻る",
                    icon=ft.Icons.ARROW_BACK,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=6),
                    ),
                    on_click=lambda e: page.go("/index"),
                )

    #region return
    return ft.View(
        route="/camera_register",
        controls=[
            ft.Column(
                [
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                face_register_view,
                                card_register_view,
                            ],
                            spacing=100,
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        expand=True,
                        alignment=ft.alignment.center,
                    ),
                    ft.Container(
                        content=back_btn,

                    ),
                ],
                expand=True,
            )
        ],
    )

    #endregion

def main(page: ft.Page):
    def route_change(e: ft.RouteChangeEvent):
        page.views.clear()
        if page.route in ("/", "/camera/register"):
            page.views.append(camera_register_view(page))
        page.update()

    page.on_route_change = route_change
    page.go("/camera/register")

