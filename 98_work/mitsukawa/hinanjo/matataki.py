import cv2
import face_recognition as fr
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import msvcrt
import pickle


LEFT_EYE  = [362, 385, 387, 263, 373, 380]#左目の位置を指定
RIGHT_EYE = [33,  160, 158, 133, 153, 144]#右目の位置を指定

EAR_THRESHOLD = 0.15 #どこまで閉じたら瞬きとするかの閾値
BLINK_REQUIRED = 2 #必要な瞬き回数
BLINK_FRAMES = 3 #目を閉じている時間の指定

"""
openのところにもともと登録してある顔の特徴量(エンコーディング済み)を入れておいてください(パスとかも変えないと動かないと思います)
カメラから画像をとってきて瞬きを二回連続で検知してから登録してある顔と似てるか判別してコンソールに出します。
瞬きの回数もコンソールにリアルタイムで出ます
瞬きの時間が長すぎると判断された場合はリセットがかかります
"""

def calculate_ear(landmarks, eye_indices, img_w, img_h):
    points = [(int(landmarks[i].x * img_w), int(landmarks[i].y * img_h)) for i in eye_indices]
    v1 = np.linalg.norm(np.array(points[1]) - np.array(points[5]))
    v2 = np.linalg.norm(np.array(points[2]) - np.array(points[4]))
    h  = np.linalg.norm(np.array(points[0]) - np.array(points[3]))
    if h == 0:
        return 0
    return (v1 + v2) / (2.0 * h)

def get_frame(cap):
    ret, frame = cap.read()
    if not ret:
        print("カメラからフレームを取得できませんでした。")
        return None
    return frame

def recognize(frame, known_encoding):
    ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
    y, cr, cb = cv2.split(ycrcb)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    y = clahe.apply(y)
    ycrcb = cv2.merge([y, cr, cb])
    image = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
    rgb = np.ascontiguousarray(image[:, :, ::-1])

    small = cv2.resize(rgb, (0, 0), fx=0.25, fy=0.25)
    locations = fr.face_locations(small)

    for (top, right, bottom, left) in locations:
        top *= 4; right *= 4; bottom *= 4; left *= 4
        h, w, _ = rgb.shape
        top = max(0, top); right = min(w, right)
        bottom = min(h, bottom); left = max(0, left)

        face_area = (bottom - top) * (right - left)
        if face_area < 10000:
            return False

        encodings = fr.face_encodings(rgb, known_face_locations=[(top, right, bottom, left)], num_jitters=1)
        if not encodings:
            return False

        results = fr.compare_faces([known_encoding], encodings[0], tolerance=0.4)
        return results[0]

    return False

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("カメラを開けませんでした。")
        return

    with open("face_recognition/encoding.pkl", "rb") as f:#ここで登録された顔(エンコーディング済みのもの)を引っ張ってきてる
        known_encoding = pickle.load(f)

    base_options = python.BaseOptions(model_asset_path="face_landmarker.task")
    options = vision.FaceLandmarkerOptions(base_options=base_options, num_faces=1)
    landmarker = vision.FaceLandmarker.create_from_options(options)

    blink_count = 0
    blink_frame_count = 0
    frame_count = 0

    print("瞬きを2回してください。")

    while True:
        frame = get_frame(cap)
        if frame is None:
            break

        frame_count += 1

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = landmarker.detect(mp_image)

        if result.face_landmarks:
            landmarks = result.face_landmarks[0]
            h, w, _ = frame.shape
            left_ear  = calculate_ear(landmarks, LEFT_EYE, w, h)
            right_ear = calculate_ear(landmarks, RIGHT_EYE, w, h)
            ear = (left_ear + right_ear) / 2.0

            if ear < EAR_THRESHOLD:
                blink_frame_count += 1
            elif blink_frame_count > 0 and blink_frame_count <= BLINK_FRAMES:
                blink_count += 1
                print(f"瞬き検出: {blink_count}回")
                blink_frame_count = 0
            elif blink_frame_count > BLINK_FRAMES:
                print("長時間検出のためリセット")
                blink_frame_count = 0

            if blink_count >= BLINK_REQUIRED:
                print("瞬き確認。顔認証を行います...")
                if recognize(frame, known_encoding):
                    print("認証通過")
                else:
                    print("認証失敗")

                blink_count = 0
                blink_frame_count = 0
                print("瞬きを2回してください。")

        if msvcrt.kbhit():
            msvcrt.getch()
            break

    cap.release()
    landmarker.close()

if __name__ == "__main__":
    main()