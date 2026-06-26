import time
import cv2
import numpy as np

from face_core import (
    REGISTERED_FACE_PATH,
    authenticate,
    calc_required_registered_matches,
    load_registered_faces,
)



# # # # # # # # # #
# カメラ設定
# # # # # # # # # #

CAMERA_INDEX = 0            # カメラ番号
CAMERA_WIDTH = 320          # カメラの横幅
CAMERA_HEIGHT = 240         # カメラの高さ

PROCESS_EVERY_N_FRAMES = 1  # 何フレームごとに顔認証するか
REQUIRED_MATCH_COUNT = 3    # 何回連続で認証成功したらOK
COOLDOWN_SECONDS = 0.1      # 一度認証成功した後、次の認証成功まで
SHOW_WINDOW = True          # カメラ画面表示

# カメラ開く
def open_camera():
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)

    # 開きなおし
    if not cap.isOpened():
        cap.release()
        cap = cv2.VideoCapture(CAMERA_INDEX)

    # 開けたらサイズ設定
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

        # バッファ設定 遅延がへる
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    return cap

# 認証成功
def on_authenticated(info):
    # 名前
    label = info["label"]

    # 一番近い顔
    best = info["best_distance"]

    # 近い顔3つの平均
    avg = info["avg_nearest_distance"]

    # 閾値以内だった数
    hits = info["registered_match_count"]

    print(f"AUTH OK user={label} best={best:.4f} avg={avg:.4f} hits={hits}")

# カメラのデバッグ用
def draw_debug(frame, info, match_count):
    best = info["best_distance"]
    avg = info["avg_nearest_distance"]
    hits = info["registered_match_count"]
    face = info["face"]
    label = info.get("label")
    required = info.get("required_registered_matches", 0)

    if best is None:
        text1 = "distance: -"
        text2 = f"match frames: {match_count}/{REQUIRED_MATCH_COUNT}"
    else:
        text1 = f"user: {label}  best: {best:.4f}  avg: {avg:.4f}  hits: {hits}/{required}"
        text2 = f"match frames: {match_count}/{REQUIRED_MATCH_COUNT}"

    cv2.putText(
        frame,
        text1,
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2,
    )

    cv2.putText(
        frame,
        text2,
        (20, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2,
    )

    if face is not None:
        cv2.rectangle(
            frame,
            (face.left(), face.top()),
            (face.right(), face.bottom()),
            (0, 255, 0),
            2,
        )



def main():
    registered_data = load_registered_faces(REGISTERED_FACE_PATH)

    # 登録データなかったらおわり
    if registered_data is None:
        print("先に顔登録してね: python register_face.py")
        return

    known_encodings, labels = registered_data

    # 登録画像枚数
    registered_count = len(known_encodings)

    print(f"登録枚数: {registered_count}枚")
    for label in sorted(set(labels)):
        count = int((labels == label).sum())
        required = calc_required_registered_matches(count)
        print(f"{label}: {count}枚 / 必要ヒット数: {required}")

    print("終了するときは q を押してね")

    # カメラ開く
    cap = open_camera()

    if not cap.isOpened():
        print("カメラ開けない；；")
        return

    frame_count = 0         # 読み込んだフレーム数
    match_count = 0         # 連続で合ってた回数
    last_auth_time = 0.0    # 最後に認証成功した時刻

    # 最後の認証結果
    last_info = {
        "best_distance": None,
        "avg_nearest_distance": None,
        "registered_match_count": 0,
        "required_registered_matches": 0,
        "label": None,
        "face": None,
    }

    try:
        while True:
            # カメラから1フレームとる
            ok, frame = cap.read()

            # 失敗したら少し待って次
            if not ok:
                time.sleep(0.01)
                continue

            frame_count += 1

            # PROCESS_EVERY_N_FRAMES 間隔で顔認証
            if frame_count % PROCESS_EVERY_N_FRAMES == 0:
                # 顔認証
                matched, last_info = authenticate(
                    known_encodings,
                    labels,
                    frame,
                )

                if matched:
                    match_count = min(match_count + 1, REQUIRED_MATCH_COUNT)
                else:
                    match_count = 0

                now = time.monotonic()

                # 連続成功数が必要回数以上、前回認証からクールダウン時間が過ぎているとき成功
                if (
                    match_count >= REQUIRED_MATCH_COUNT
                    and now - last_auth_time > COOLDOWN_SECONDS
                ):
                    on_authenticated(last_info)
                    last_auth_time = now
                    match_count = 0

            # カメラ
            if SHOW_WINDOW:
                # デバッグ用
                draw_debug(frame, last_info, match_count)

                # ウィンドウ表示
                cv2.imshow("face auth", frame)

                # qキーで終了
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    finally:
        # カメラ開放
        cap.release()

        # OpenCVのウィンドウ閉じる
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()