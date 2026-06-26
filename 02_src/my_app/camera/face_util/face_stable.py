import math
import os
import glob
import numpy as np
import face_recognition
from pathlib import Path

# 画像拡張子
_IMAGE_PATTERNS = [
    "*.jpg",
    "*.jpeg",
    "*.png",
    "*.bmp",
]

# 顔DBの特徴量キャッシュ
_face_db_cache = {
    "signature": None,
    "encodings": None,
    "labels": None
}

FACE_THRESHOLD = 0.35   # 1番近い登録画像との閾値
AVG_THRESHOLD = 0.38    # 上位3件の平均閾値



def _read_image_database(db_dir):
    # DBディレクトリ内の画像をとる
    paths = []
    for pat in _IMAGE_PATTERNS:
        paths.extend(glob.glob(os.path.join(str(db_dir), pat)))
    
    return sorted(paths)

def _db_signature(paths):
    # DB画像が変更されたか判定する情報つくる
    return tuple(
        (path, os.path.getmtime(path), os.path.getsize(path))
        for path in paths
    )

def _label_from_path(path):
    # ファイル名の頭を名前にする
    # otomo_001.jpg -> otomo
    return Path(path).stem.split("_")[0]

def _encode_image(path, model="hog"):
    # 顔特徴量つくる
    img = face_recognition.load_image_file(path)
    locations = face_recognition.face_locations(img, model=model)

    # 登録画像は顔が1つだけのものをつかう！
    if len(locations) != 1:
        print(f"登録画像の顔が1つじゃないよ: {path}, count={len(locations)}")
        return None
    
    encodings = face_recognition.face_encodings(img, locations)
    if not encodings:
        print(f"登録画像の特徴量がないよー: {path}")
        return None

    return np.asarray(encodings[0], dtype=np.float32)

def load_face_database(db_dir, model="hog"):
    global _face_db_cache

    # 顔のDB内の画像を取得
    paths = _read_image_database(db_dir)

    # 画像の更新有無確認署名
    signature = _db_signature(paths)

    # 前回読み込み時からDB画像が変わってなかったらキャッシュつかう
    if _face_db_cache["signature"] == signature:
        return _face_db_cache["encodings"], _face_db_cache["labels"]
    
    encodings = []
    labels = []

    # 登録画像を全て顔特徴量に変換！
    for path in paths:
        enc = _encode_image(path, model=model)
        if enc is None:
            continue

        encodings.append(enc)
        labels.append(_label_from_path(path))

    # numpyで距離計算しやすい形に変換
    if encodings:
        encodings = np.vstack(encodings).astype(np.float32)
        labels = np.asarray(labels, dtype=str)
    else:
        encodings = np.empty((0, 128), dtype=np.float32)
        labels = np.asarray([], dtype=str)
    
    # キャッシュぱく
    _face_db_cache = {
        "signature": signature,
        "encodings": encodings,
        "labels": labels
    }

    print(f"顔DBよみこんだよ: {len(labels)}枚")
    return encodings, labels

def calc_required_registered_matches(total):
    # 登録画像なかったらおわり
    if total <= 0:
        return 0
    
    # 登録画像が1枚のとき
    if total == 1:
        return 1
    
    # 登録画像の30%、最低2枚、最大3枚が閾値以内なら
    return min(3, max(2, math.ceil(total * 0.3)))

def recognize_image_average(image_path, db_dir, face_threshold=FACE_THRESHOLD, avg3_threshold=AVG_THRESHOLD, model="hog"):
    # 認証結果の情報
    info = {
        "label": None,
        "best_distance": None,
        "avg_nearest_distance": None,
        "registered_match_count": 0,
        "required_registered_matches": 0,
        "reason": None
    }

    # 登録済の顔特徴量をとる
    known_encodings, labels = load_face_database(db_dir, model=model)

    if len(known_encodings) == 0:
        info["reason"] = "顔DBないよ；；"
        return None, info
    
    # ターゲット画像をとる
    img = face_recognition.load_image_file(image_path)
    locations = face_recognition.face_locations(img, model=model)

    # ターゲット画像の顔が1つだけならはんてい
    if len(locations) != 1:
        info["reason"] = f"顔あった！: {len(locations)}"
        return None, info
    
    encodings = face_recognition.face_encodings(img, locations)
    if not encodings:
        info["reason"] = "画像変換できぬ"
        return None, info
    
    target = np.asarray(encodings[0], dtype=np.float32)

    # ターゲットの顔と、登録済の顔を計算
    distances = face_recognition.face_distance(known_encodings, target)

    best_info = None
    matched_info = None

    # 人ごとにまとめて判定
    for label in sorted(set(labels)):
        person_distances = distances[labels == label]

        # その人の登録画像のうち、何枚近ければOKか決める
        required = calc_required_registered_matches(len(person_distances))

        # その人の登録画像の中で一番近いやつ
        best_distance = float(np.min(person_distances))

        # 近い上位3件の平均
        k = min(3, len(person_distances))
        nearest = np.partition(person_distances, k - 1)[:k]
        avg_nearest_distance = float(np.mean(nearest))

        # しきい値以内だった登録画像数
        registered_match_count = int(np.sum(person_distances < face_threshold))

        current_info = {
            "label": label,
            "best_distance": best_distance,
            "avg_nearest_distance": avg_nearest_distance,
            "registered_match_count": registered_match_count,
            "required_registered_matches": required,
            "reason": None,
        }

        # 認証失敗時のデバッグ用に、一番近かった人物も保持する
        if best_info is None or best_distance < best_info["best_distance"]:
            best_info = current_info

        # 1枚だけでなく、近い画像の平均と一致枚数も使って判定するよ
        matched = (
            best_distance < face_threshold
            and avg_nearest_distance < avg3_threshold
            and registered_match_count >= required
        )

        if matched and (
            matched_info is None
            or best_distance < matched_info["best_distance"]
        ):
            matched_info = current_info

    # 認証できなかった場合、一番近かった人物情報だけ返すよ
    if matched_info is None:
        return None, best_info or info

    # 認証できた人物名と詳細情報を返す
    return matched_info["label"], matched_info