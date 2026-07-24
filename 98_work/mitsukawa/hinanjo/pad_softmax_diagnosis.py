
"""
PAD (Silent-Face) の ONNX 出力が softmax 済みかどうかを診断するスクリプト。

目的:
  現状の PassivePad.check は session.run() の生出力をそのまま合算して
  live_score = prediction[0][1] を確率とみなし、>= 0.80 で判定している。
  もし ONNX が softmax 前のロジットを返しているなら、この閾値は無意味。
  それをここで白黒つける。

使い方:
  1. 本物の顔画像(実際に人がカメラに写ったフレーム)と、
     なりすまし画像(顔写真をカメラで撮ったもの・スマホ画面リプレイ)を用意
  2. 下の REAL_IMAGES / SPOOF_IMAGES にパスを列挙
  3. python pad_softmax_diagnosis.py

見るべきポイント:
  - raw 行が [0,1] に収まって合計≈1.0 なら softmax 済み
  - raw の値が負や >1、合計が 1 から大きくずれるなら softmax 前(ロジット)
    → PassivePad 側に自前 softmax が必要
  - softmax 適用後、本物は live 列(index=1)が高く、なりすましは低く出るのが正常
"""

import sys
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

SCRIPT_DIR = Path(__file__).resolve().parent   # camera/
IMAGES_DIR = SCRIPT_DIR / "images"

# ==== 環境に合わせて書き換える ====
# face_auth 側と同じ vendor パスを指す
APP_ROOT = Path(__file__).resolve().parent.parent   # camera の一つ上 = my_app
PAD_REPOSITORY = APP_ROOT / "vendor" / "Silent-Face-Anti-Spoofing"
PAD_MODEL_DIRECTORY = PAD_REPOSITORY / "resources" / "anti_spoof_models"

def load_images_from(folder):
    """フォルダ内の画像を全部拾う。bbox は None(=画像全体)"""
    exts = {".png", ".jpg", ".jpeg", ".bmp"}
    items = []
    if not folder.is_dir():
        print(f"⚠️ フォルダがない: {folder}")
        return items
    for path in sorted(folder.iterdir()):
        if path.suffix.lower() in exts:
            items.append((str(path), None))
    return items



REAL_IMAGES = load_images_from(IMAGES_DIR / "real")
SPOOF_IMAGES = load_images_from(IMAGES_DIR / "spoof")
# =================================


def softmax(x, axis=1):
    x = x - np.max(x, axis=axis, keepdims=True)
    e = np.exp(x)
    return e / np.sum(e, axis=axis, keepdims=True)


def load_models():
    if not PAD_MODEL_DIRECTORY.is_dir():
        raise FileNotFoundError(f"PADモデルディレクトリがない: {PAD_MODEL_DIRECTORY}")

    repo = str(PAD_REPOSITORY)
    if repo not in sys.path:
        sys.path.insert(0, repo)

    from src.generate_patches import CropImage
    from src.utility import parse_model_name

    cropper = CropImage()
    model_paths = sorted(PAD_MODEL_DIRECTORY.glob("*.onnx"))
    if not model_paths:
        raise FileNotFoundError(f"ONNXモデルがない: {PAD_MODEL_DIRECTORY}")

    models = []
    for model_path in model_paths:
        pth_name = model_path.with_suffix(".pth").name
        h, w, _, scale = parse_model_name(pth_name)
        session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        models.append({
            "path": model_path,
            "session": session,
            "input_name": session.get_inputs()[0].name,
            "output_name": session.get_outputs()[0].name,
            "input_height": h,
            "input_width": w,
            "scale": scale,
        })
    return cropper, models


def infer_raw(cropper, models, bgr, bbox):
    """各モデルの生出力(raw)とsoftmax後を、モデル単位でも合算でも返す"""
    x1, y1, x2, y2 = [int(v) for v in bbox]
    face_bbox = [x1, y1, max(1, x2 - x1), max(1, y2 - y1)]

    per_model = []
    raw_sum = np.zeros((1, 3), dtype=np.float32)
    softmax_sum = np.zeros((1, 3), dtype=np.float32)

    for model in models:
        crop = cropper.crop(
            org_img=bgr,
            bbox=face_bbox,
            scale=model["scale"],
            out_w=model["input_width"],
            out_h=model["input_height"],
            crop=model["scale"] is not None,
        )
        tensor = np.ascontiguousarray(
            crop.transpose(2, 0, 1)[None, ...], dtype=np.float32
        )
        raw = model["session"].run(
            [model["output_name"]], {model["input_name"]: tensor}
        )[0]

        sm = softmax(raw, axis=1)
        per_model.append((model["path"].name, raw.copy(), sm.copy()))
        raw_sum += raw
        softmax_sum += sm

    n = len(models)
    return per_model, raw_sum / n, softmax_sum / n


def describe_raw(raw_sum):
    """生出力が確率っぽいか(softmax済みか)を判定"""
    row = raw_sum[0]
    total = float(np.sum(row))
    in_range = bool(np.all(row >= -1e-4) and np.all(row <= 1.0 + 1e-4))
    looks_like_prob = in_range and abs(total - 1.0) < 0.05
    return looks_like_prob, total, row


def run_batch(label, items, cropper, models):
    print(f"\n{'='*60}\n{label} ({len(items)}枚)\n{'='*60}")
    for path, bbox in items:
        img = cv2.imread(path)
        if img is None:
            print(f"  [読込失敗] {path}")
            continue
        if bbox is None:
            h, w = img.shape[:2]
            bbox = [0, 0, w, h]

        per_model, raw_avg, sm_avg = infer_raw(cropper, models, img, bbox)
        looks_prob, total, raw_row = describe_raw(raw_avg)

        # 現状コードの判定(生出力をそのまま確率扱い)
        current_label = int(np.argmax(raw_avg, axis=1)[0])
        current_live_score = float(raw_avg[0][1])

        # softmaxを噛ませた場合の判定
        fixed_label = int(np.argmax(sm_avg, axis=1)[0])
        fixed_live_score = float(sm_avg[0][1])

        print(f"\n  {Path(path).name}")
        print(f"    生出力合算(平均): {raw_row}  合計={total:.4f}  "
              f"softmax済みに見える={looks_prob}")
        print(f"    [現状コード] label={current_label} "
              f"live_score={current_live_score:.4f} "
              f"(>=0.80 → {'live' if current_live_score >= 0.80 else 'spoof'})")
        print(f"    [softmax後 ] label={fixed_label} "
              f"live_score={fixed_live_score:.4f} "
              f"(>=0.80 → {'live' if fixed_live_score >= 0.80 else 'spoof'})")


def main():
    cropper, models = load_models()
    print(f"モデル数: {len(models)}")
    for m in models:
        print(f"  - {m['path'].name} (in={m['input_width']}x{m['input_height']}, scale={m['scale']})")

    if not REAL_IMAGES and not SPOOF_IMAGES:
        print("\n⚠️ REAL_IMAGES / SPOOF_IMAGES が空です。検証画像を設定してください。")
        return

    run_batch("本物 (REAL)", REAL_IMAGES, cropper, models)
    run_batch("なりすまし (SPOOF)", SPOOF_IMAGES, cropper, models)

    print(f"\n{'='*60}\n判定の読み方\n{'='*60}")
    print("・生出力合計が≈1.0で[0,1]内 → softmax済み。現状コードでOK")
    print("・生出力が負や>1、合計が1から外れる → softmax前(ロジット)")
    print("  → PassivePad.check に softmax を追加する必要あり")
    print("・softmax後の列で、本物のlive_scoreが高く/なりすましが低く分離")
    print("  していれば、閾値0.80が妥当かどうかも同時に見える")


if __name__ == "__main__":
    main()