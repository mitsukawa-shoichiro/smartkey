from pathlib import Path
import dlib
import numpy as np
import cv2
import math

# # # # # # # # # #
# パス設定
# # # # # # # # # #

BASE_DIR = Path(__file__).resolve().parent                                  # face_core.py の場所
MODEL_DIR = BASE_DIR / "models"                                             # モデルファイルの場所
IMAGE_DIR = BASE_DIR / "images"                                             # 画像を置く場所
REGISTER_IMAGE_DIR = IMAGE_DIR / "register"                                 # 登録用の画像の場所
REGISTERED_FACE_PATH = BASE_DIR / "registered_face.npz"                     # 登録した画像の場所
LEGACY_REGISTERED_FACE_PATH = BASE_DIR / "registered_face.npy"                     # 登録した画像の場所

PREDICTOR_PATH = MODEL_DIR / "shape_predictor_5_face_landmarks.dat"         # モデル
FACE_MODEL_PATH = MODEL_DIR / "dlib_face_recognition_resnet_model_v1.dat"   # 数字変換用モデル



# # # # # # # # # #
# 認証設定
# # # # # # # # # #

DETECT_WIDTH = 320          # 検出用画像サイズ
UPSAMPLE = 0                # 大きくするか

AUTH_NUM_JITTERS = 1        # 認証時の顔特徴量(128点のやつ)の精度 大きいほど遅い

REGISTER_NUM_JITTERS = 5    # 登録時の顔特徴量の精度

FACE_THRESHOLD = 0.35       # 顔の閾値
AVG3_THRESHOLD = 0.38       # 上位3件の顔の閾値

IMAGE_EXTENSIONS = {        # 画像の拡張子
    ".jpg",
    ".jpeg",
    ".png"
}



# # # # # # # # # #
# dlibモデル読み込み
# # # # # # # # # #

def check_model_files():
    # 必要なモデルファイルの確認
    missing = []

    for path in [PREDICTOR_PATH, FACE_MODEL_PATH]:
        if not path.exists():
            missing.append(path)

    # なかったらエラー
    if missing:
        text = "\n".join(f"- {p}" for p in missing)
        raise FileNotFoundError(f"モデルファイルが見つからないよ:\n{text}")

# モデルファイル確認
check_model_files()

# 顔みつけるやつ
detector = dlib.get_frontal_face_detector()

# 顔の5点みつけるやつ
predictor = dlib.shape_predictor(str(PREDICTOR_PATH))

# 顔を128個の数字に変換するやつ
face_model = dlib.face_recognition_model_v1(str(FACE_MODEL_PATH))



# # # # # # # # # #
# 画像処理
# # # # # # # # # #

def read_bgr_image(image_path):
    image_path = Path(image_path)

    try:
        # 画像ファイルをよむ
        data = np.fromfile(str(image_path), dtype=np.uint8)
    except OSError:
        return None

    # ファイルなかったらNone
    if data.size == 0:
        return None

    # OpenCVで復元 -> BGR画像
    return cv2.imdecode(data, cv2.IMREAD_COLOR)

# 顔検出だけ小さい画像、特徴量計算は元画像！
def resize_for_detection(img):
    # 大きい辺をみつける
    h, w = img.shape[:2]
    max_side = max(h, w)

    # 設定より小さかったらそのまま
    if max_side <= DETECT_WIDTH:
        return img, 1.0

    # DETECT_WIDTH になるように縮小率計算
    scale = DETECT_WIDTH / max_side

    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))

    # 縮小
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    
    # 縮小画像、縮小率返す
    return resized, scale

# 小さい画像で見つけた顔座標を元画像サイズにもどす
def scale_face_rect(face, scale, original_w, original_h):
    # 縮小してないならそのまま
    if scale == 1.0:
        return face

    # scale=0.5 なら座標を2倍
    inv = 1.0 / scale

    # 小さい画像の座標を元画像の座標に戻す
    left = int(round(face.left() * inv))
    top = int(round(face.top() * inv))
    right = int(round(face.right() * inv))
    bottom = int(round(face.bottom() * inv))

    # 画像の外にはみ出ないように
    left = max(0, min(original_w - 1, left))
    top = max(0, min(original_h - 1, top))
    right = max(0, min(original_w - 1, right))
    bottom = max(0, min(original_h - 1, bottom))

    # 横幅高さが0いかにならないように
    if right <= left:
        right = min(original_w - 1, left + 1)

    if bottom <= top:
        bottom = min(original_h - 1, top + 1)

    # dlib用の顔座標として返す
    return dlib.rectangle(left, top, right, bottom)
    
def get_largest_face(rgb):
    # 顔とる
    faces = detector(rgb, UPSAMPLE)

    if not faces:
        return None

    # 一番大きい顔をつかう
    return max(faces, key=lambda r: r.width() * r.height())

def encode_face(rgb, face, num_jitters):
    # 顔の5点とる
    shape = predictor(rgb, face)

    # 顔を128個の数字に
    desc = face_model.compute_face_descriptor(rgb, shape, num_jitters)

    # numpy配列変換
    return np.asarray(desc, dtype=np.float32)

# 画像から顔情報を作る
def get_face_encoding(image_path, num_jitters=REGISTER_NUM_JITTERS, verbose=True):
    img_bgr = read_bgr_image(image_path)

    if img_bgr is None:
        if verbose:
            print(f"画像なし: {image_path}")
        return None

    original_h, original_w = img_bgr.shape[:2]

    # dlib用にRGB変換
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    # 顔検出用で縮小 -> 一番大きい顔探す
    small_rgb, scale = resize_for_detection(img_rgb)
    small_face = get_largest_face(small_rgb)

    if small_face is None:
        if verbose:
            print(f"顔なし: {Path(image_path).name}")
        return None

    # もどす
    face = scale_face_rect(small_face, scale, original_w, original_h)

    # 元画像で顔特徴量を作って返す
    return encode_face(img_rgb, face, num_jitters)



# # # # # # # # # #
# 登録処理
# # # # # # # # # #

def collect_register_images(image_dir=REGISTER_IMAGE_DIR):
    # images/register/<人物名>/画像 を自動で集める
    image_dir = Path(image_dir)

    if not image_dir.exists():
        return []

    person_dirs = sorted(
        [p for p in image_dir.iterdir() if p.is_dir()],
        key=lambda p: p.name.lower()
    )

    labeled_files = []

    for person_dir in person_dirs:
        files = [
            p for p in person_dir.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        ]

        for file in sorted(files, key=lambda p: p.name.lower()):
            labeled_files.append((person_dir.name, file))

    return labeled_files

# registered_face.npyに保存
def register_faces(image_dir=REGISTER_IMAGE_DIR, output_path=REGISTERED_FACE_PATH):
    image_dir = Path(image_dir)
    output_path = Path(output_path)

    # 登録用の画像を取る
    image_files = collect_register_images(image_dir)

    if not image_files:
        print(f"登録画像がないよ: {image_dir}")
        return 0

    print(f"対象画像数: {len(image_files)}")

    encodings = []
    labels = []

    # 画像を顔情報に変換
    for label, file in image_files:
        enc = get_face_encoding(
            file,
            num_jitters=REGISTER_NUM_JITTERS,
            verbose=True
        )

        # 顔情報が作れたやつだけ登録
        if enc is not None:
            encodings.append(enc)
            labels.append(label)
            print(f"登録OK: {label}/{file.name}")
        else:
            print(f"登録スキップ: {label}/{file.name}")

    if not encodings:
        print("使える顔がなかったよ")
        return 0

    # 複数枚の顔情報を1つにまとめる
    encodings = np.vstack(encodings).astype(np.float32)
    labels = np.asarray(labels, dtype=str)

    # 保存
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(output_path, encodings=encodings, labels=labels)

    print(f"登録完了: {len(encodings)}枚")
    print(f"保存先: {output_path}")

    return len(encodings)



# # # # # # # # # #
# 認証処理
# # # # # # # # # #

def load_registered_faces(path=REGISTERED_FACE_PATH):
    path = Path(path)

    if path.exists():
        # 登録済顔情報を読み込む
        data = np.load(path)
        known_encodings = data["encodings"].astype(np.float32)
        labels = data["labels"].astype(str)

    elif LEGACY_REGISTERED_FACE_PATH.exists():
        # 古い登録済顔情報を読み込む
        known_encodings = np.load(LEGACY_REGISTERED_FACE_PATH).astype(np.float32)
        known_encodings = np.atleast_2d(known_encodings)
        labels = np.full(len(known_encodings), "default", dtype=str)

    else:
        return None

    # 2次元配列にする
    known_encodings = np.atleast_2d(known_encodings)

    # 形確認
    if known_encodings.ndim != 2 or known_encodings.shape[1] != 128:
        raise ValueError(f"登録データの形がおかしいよ: {known_encodings.shape}")

    if len(labels) != len(known_encodings):
        raise ValueError(f"登録データの数がおかしいよ: {len(labels)} != {len(known_encodings)}")

    return known_encodings, labels

# 登録画像のうち、何枚に近ければいいか決める
def calc_required_registered_matches(total):
    if total <= 0:
        raise ValueError("登録枚数が0枚だよ")

    if total == 1:
        return 1

    # 登録枚数の30%に近ければいける
    # 最低2枚、最大3枚
    #
    # 5枚 -> 2枚以上
    # 10枚 -> 3枚以上
    # 20枚 -> 3枚以上
    return min(3, max(2, math.ceil(total * 0.3)))

def authenticate(known_encodings, labels, frame_bgr):
    # 認証結果の情報
    info = {
        "best_distance": None,
        "avg_nearest_distance": None,
        "registered_match_count": 0,
        "required_registered_matches": 0,
        "label": None,
        "face": None,
    }

    if frame_bgr is None:
        return False, info

    labels = np.asarray(labels).astype(str)

    original_h, original_w = frame_bgr.shape[:2]
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    small_rgb, scale = resize_for_detection(frame_rgb)
    small_face = get_largest_face(small_rgb)

    if small_face is None:
        return False, info

    face = scale_face_rect(small_face, scale, original_w, original_h)
    target = encode_face(frame_rgb, face, AUTH_NUM_JITTERS)

    # 登録済みの顔情報全てと距離を計算
    distances = np.linalg.norm(known_encodings - target, axis=1)

    best_info = None
    matched_info = None

    for label in sorted(set(labels)):
        person_distances = distances[labels == label]
        required_registered_matches = calc_required_registered_matches(len(person_distances))

        # 一番近いやつ
        best_distance = float(np.min(person_distances))

        # 上位3件とる
        k = min(3, len(person_distances))
        nearest = np.partition(person_distances, k - 1)[:k]

        # 上位3件の平均
        avg_nearest_distance = float(np.mean(nearest))

        # いけた顔の枚数
        registered_match_count = int(np.sum(person_distances < FACE_THRESHOLD))

        current_info = {
            "best_distance": best_distance,
            "avg_nearest_distance": avg_nearest_distance,
            "registered_match_count": registered_match_count,
            "required_registered_matches": required_registered_matches,
            "label": label,
            "face": face,
        }

        if best_info is None or best_distance < best_info["best_distance"]:
            best_info = current_info

        matched = (
            best_distance < FACE_THRESHOLD
            and avg_nearest_distance < AVG3_THRESHOLD
            and registered_match_count >= required_registered_matches
        )

        if matched and (
            matched_info is None
            or best_distance < matched_info["best_distance"]
        ):
            matched_info = current_info

    return matched_info is not None, matched_info or best_info or info
