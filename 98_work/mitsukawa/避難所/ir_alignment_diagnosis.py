"""
IRアライメント現状把握スクリプト。

目的:
  現在の rgb_to_ir_homography_normalized(単位行列のまま?)で、
  RGBで検出した顔が IR画像上のどこにマッピングされているかを目視確認する。
  同時に、その IR顔領域の輝度(face_mean など)を実測し、
  「スマホ画面リプレイが IR で本当に真っ黒に映るか」を数値で確認する。

これで確かめたいこと:
  1. IRの顔矩形が、実際の顔の位置と合っているか(ズレていないか)
  2. 本物の顔 vs スマホ画面で、IR顔領域の輝度に差が出るか
     → 出るなら IR で画面リプレイを弾ける。前任者「大丈夫」が正しい
     → 出ない/ズレてるなら キャリブレーションが必要

操作:
  実行するとRGB+IRを連続キャプチャする。
  SPACE キー: 現在のフレームを1組(RGB/IR/合成)保存
  Q キー    : 終了
  本物の顔・スマホ画面リプレイ、それぞれで SPACE を押して撮り比べる。

保存先: ./ir_diag_out/ に連番で保存される。
"""

import sys
import time
from pathlib import Path

import cv2
import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

# ==== 実運用のモジュールを流用するためのパス設定 ====
# このスクリプトは camera/ に置く想定。my_app をimport可能にする。
SCRIPT_DIR = Path(__file__).resolve().parent          # camera/
MY_APP_DIR = SCRIPT_DIR.parent                         # my_app/
SRC_DIR = MY_APP_DIR.parent                            # 02_src/
for p in (str(SRC_DIR), str(MY_APP_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import json

from my_app.camera.face_util.insightface_engine import InsightFaceEngine
from my_app.camera.media_foundation_ir import MediaFoundationIRCamera

# face_auth.json を読む(実運用と同じ設定)
FACE_AUTH_CONFIG_PATH = MY_APP_DIR / "config" / "face_auth.json"
with FACE_AUTH_CONFIG_PATH.open("r", encoding="utf-8") as f:
    CONFIG = json.load(f)

RGB_CAMERA_INDEX = int(CONFIG["rgb_camera_index"])
IR_DEVICE_ID_CONTAINS = str(CONFIG["ir_device_id_contains"])
IR_STARTUP_TIMEOUT_SEC = float(CONFIG.get("ir_startup_timeout_sec", 5.0))
DET_SIZE = tuple(CONFIG.get("insightface_det_size", [256, 256]))

# 現在のホモグラフィ(単位行列のはず)を読む
homography = CONFIG.get("rgb_to_ir_homography_normalized")
if homography is None:
    homography = np.eye(3, dtype=np.float32)
HOMOGRAPHY = np.asarray(homography, dtype=np.float32)

# IRしきい値(参考表示用)
IR_MIN_FACE_MEAN = float(CONFIG.get("ir_min_face_mean", 8))
IR_MIN_FACE_STD = float(CONFIG.get("ir_min_face_std", 5.0))
IR_MIN_ABS_CONTRAST = float(CONFIG.get("ir_min_abs_contrast", 2.0))

OUT_DIR = SCRIPT_DIR / "ir_diag_out"
OUT_DIR.mkdir(exist_ok=True)


def map_bbox_to_ir(bbox, rgb_shape, ir_shape):
    """LivenessGate._map_bbox と同じロジックで RGB bbox を IR 座標へ変換"""
    rgb_h, rgb_w = rgb_shape[:2]
    ir_h, ir_w = ir_shape[:2]
    x1, y1, x2, y2 = map(float, bbox)

    points = np.asarray([
        [x1 / rgb_w, y1 / rgb_h],
        [x2 / rgb_w, y1 / rgb_h],
        [x2 / rgb_w, y2 / rgb_h],
        [x1 / rgb_w, y2 / rgb_h],
    ], dtype=np.float32).reshape(1, 4, 2)

    mapped = cv2.perspectiveTransform(points, HOMOGRAPHY)[0]
    mapped[:, 0] *= ir_w
    mapped[:, 1] *= ir_h

    ix1 = max(0, min(int(np.floor(mapped[:, 0].min())), ir_w - 1))
    iy1 = max(0, min(int(np.floor(mapped[:, 1].min())), ir_h - 1))
    ix2 = max(0, min(int(np.ceil(mapped[:, 0].max())), ir_w))
    iy2 = max(0, min(int(np.ceil(mapped[:, 1].max())), ir_h))
    return ix1, iy1, ix2, iy2


def measure_ir(gray, ir_bbox):
    """IR顔領域の輝度統計を測る"""
    x1, y1, x2, y2 = ir_bbox
    if x2 <= x1 or y2 <= y1:
        return None
    roi = gray[y1:y2, x1:x2]
    if roi.size == 0:
        return None
    return {
        "frame_mean": float(np.mean(gray)),
        "face_mean": float(np.mean(roi)),
        "face_std": float(np.std(roi)),
    }


def make_side_by_side(rgb_vis, ir_vis):
    """RGBとIRを同じ高さに揃えて横並び合成"""
    h = 480
    def resize_h(img):
        scale = h / img.shape[0]
        return cv2.resize(img, (int(img.shape[1] * scale), h))
    left = resize_h(rgb_vis)
    right = resize_h(ir_vis)
    return np.hstack([left, right])


def main():
    print("InsightFace初期化中...")
    engine = InsightFaceEngine(det_size=DET_SIZE)

    print("IRカメラ起動中...")
    ir_cam = MediaFoundationIRCamera(
        device_id_contains=IR_DEVICE_ID_CONTAINS,
        startup_timeout=IR_STARTUP_TIMEOUT_SEC,
        max_age_ms=1000.0,  # 診断中は緩め
    )
    if not ir_cam.isOpened():
        print(f"IRカメラひらけん: {ir_cam.last_error}")
        return

    print("RGBカメラ起動中...")
    rgb_cap = cv2.VideoCapture(RGB_CAMERA_INDEX, cv2.CAP_DSHOW)
    if not rgb_cap.isOpened():
        rgb_cap = cv2.VideoCapture(RGB_CAMERA_INDEX, cv2.CAP_MSMF)
    if not rgb_cap.isOpened():
        print("RGBカメラひらけん")
        ir_cam.release()
        return

    is_identity = np.allclose(HOMOGRAPHY, np.eye(3))
    print(f"\nホモグラフィ = {'単位行列(未キャリブレーション)' if is_identity else 'キャリブレーション済み'}")
    print("SPACE=保存, Q=終了\n")

    save_count = 0
    try:
        while True:
            rgb_ok, rgb_frame = rgb_cap.read()
            ir_ok, ir_frame = ir_cam.read()
            if not rgb_ok or rgb_frame is None:
                time.sleep(0.05)
                continue
            if not ir_ok or ir_frame is None:
                # IRが取れないときもRGBだけは見せる
                cv2.imshow("RGB(left) | IR(right)", rgb_frame)
                if (cv2.waitKey(1) & 0xFF) == ord("q"):
                    break
                continue

            if ir_frame.ndim == 3:
                ir_gray = cv2.cvtColor(ir_frame, cv2.COLOR_BGR2GRAY)
            else:
                ir_gray = ir_frame

            rgb_vis = rgb_frame.copy()
            ir_vis = cv2.cvtColor(ir_gray, cv2.COLOR_GRAY2BGR)

            faces = engine.extract_many(rgb_frame)
            info_lines = []

            for face in faces:
                bbox = face["bbox"]
                x1, y1, x2, y2 = [int(v) for v in bbox]
                cv2.rectangle(rgb_vis, (x1, y1), (x2, y2), (0, 255, 0), 2)

                ir_bbox = map_bbox_to_ir(bbox, rgb_frame.shape, ir_gray.shape)
                ix1, iy1, ix2, iy2 = ir_bbox
                cv2.rectangle(ir_vis, (ix1, iy1), (ix2, iy2), (0, 255, 0), 2)

                stats = measure_ir(ir_gray, ir_bbox)
                if stats is None:
                    info_lines.append("IR顔領域が無効(bboxズレの疑い)")
                    continue

                mean_ok = stats["face_mean"] >= IR_MIN_FACE_MEAN
                std_ok = stats["face_std"] >= IR_MIN_FACE_STD
                verdict = "本物っぽい" if (mean_ok and std_ok) else "偽物判定される"
                line = (f"face_mean={stats['face_mean']:.1f}(>={IR_MIN_FACE_MEAN}) "
                        f"std={stats['face_std']:.1f}(>={IR_MIN_FACE_STD}) "
                        f"frame_mean={stats['frame_mean']:.1f} -> {verdict}")
                info_lines.append(line)

                color = (0, 255, 0) if (mean_ok and std_ok) else (0, 0, 255)
                cv2.putText(ir_vis, verdict, (ix1, max(20, iy1 - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            combined = make_side_by_side(rgb_vis, ir_vis)

            y = 24
            for line in info_lines[:4]:
                cv2.putText(combined, line, (10, y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                y += 22
            if not faces:
                cv2.putText(combined, "顔なし", (10, y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)

            cv2.imshow("RGB(left) | IR(right)", combined)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord(" "):
                save_count += 1
                stamp = time.strftime("%H%M%S")
                cv2.imwrite(str(OUT_DIR / f"{save_count:02d}_{stamp}_rgb.png"), rgb_vis)
                cv2.imwrite(str(OUT_DIR / f"{save_count:02d}_{stamp}_ir.png"), ir_vis)
                cv2.imwrite(str(OUT_DIR / f"{save_count:02d}_{stamp}_combined.png"), combined)
                print(f"[保存] {save_count:02d}_{stamp}  " +
                      (info_lines[0] if info_lines else "顔なし"))

    finally:
        rgb_cap.release()
        ir_cam.release()
        cv2.destroyAllWindows()
        print(f"\n終了。{save_count}組を {OUT_DIR} に保存しました。")


if __name__ == "__main__":
    main()