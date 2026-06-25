# face_utils.py
# -*- coding: utf-8 -*-
import os
import glob
from typing import List, Dict

import numpy as np
import sys
import os
from typing import Tuple, Optional

import numpy as np
import face_recognition
import cv2


# === 対応する画像拡張子 ===
_IMAGE_PATTERNS = ["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp"]


#region CheckFaceNum
def check_face(img_path: str,model:str="hog") -> bool:
    """画像内の顔がちょうど1枚か確認"""
    result = __detect(img_path, model=model)
    return result == 1


def __detect(image_path: str, model="hog", out_path="detected.jpg") -> int:
    """
    画像から顔を検出して矩形を描画し、保存する。
    検出数を返す。
    """
    img = face_recognition.load_image_file(image_path)
    face_locations = face_recognition.face_locations(img, model=model)

    img_cv = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    for (top, right, bottom, left) in face_locations:
        cv2.rectangle(img_cv, (left, top), (right, bottom), (0, 255, 0), 2)

    cv2.imwrite(out_path, img_cv)
    print(f"[OK] {len(face_locations)} 枚の顔を検出、保存先: {out_path}")
    return len(face_locations)
#endregion

#region CheckFaceDatabase


# 認証通過の写真のローマ字を戻す
def match_against_db(
    query_img_path: str,
    db_dir: str,
    tolerance: float = 0.4,
    model:str="hog"
) -> str | None:
    """
    クエリ画像とDB内の画像を順に照合し、
    顔が一致した場合はファイル名（例: me_001.jpg）を返す。
    一致しない場合は None を返す。
    """
    for db_img_path in __read_imagedatabase(db_dir):
        name_roma = os.path.basename(db_img_path).split("_")[0]

        # print(f"[INFO] 照合中: {name_roma}")

        is_match, dist = __verify_face_similarity(
            db_img_path, query_img_path, tolerance
        )
        
        # if dist is not None:
        #     print(f"-> 距離: {dist:.4f}")
        #     print("[結果] " + ("OK: 顔が一致" if is_match else "NG: 不一致"))
        # else:
        #     print("[結果] NG: 顔検出失敗")

        if is_match:
            # print(f"[INFO] 一致したファイル: {name_roma}")
            return name_roma  # ✅ ファイル名を返す

    # 一致なし
    # print("[INFO] 一致する顔は見つかりませんでした。")
    return None

def __read_imagedatabase(path: str) -> List[str]:
    """指定ディレクトリ直下の画像パス一覧を返す"""
    paths: List[str] = []
    if not os.path.isdir(path):
        return paths
    for pat in _IMAGE_PATTERNS:
        paths.extend(glob.glob(os.path.join(path, pat)))
    return sorted(paths)

def __verify_face_similarity(
    train_image_path: str,
    target_image_path: str,
    tolerance: float ,
    model:str="hog"
) -> Tuple[bool, Optional[float]]:
    """
    2つの画像から顔特徴量を抽出して比較し、
    一致判定と距離を返す。
    """
    if not os.path.exists(train_image_path):
        print(f"[エラー] 登録画像が見つかりません: {train_image_path}")
        return False, None
    if not os.path.exists(target_image_path):
        print(f"[エラー] テスト画像が見つかりません: {target_image_path}")
        return False, None

    try:
        known_img = face_recognition.load_image_file(train_image_path)
        test_img = face_recognition.load_image_file(target_image_path)

        known_locs = face_recognition.face_locations(known_img, model=model)
        test_locs = face_recognition.face_locations(test_img, model=model)

        if len(known_locs) != 1:
            print(f"[エラー] 登録画像から1つの顔を検出できません (検出数={len(known_locs)})")
            return False, None
        if len(test_locs) != 1:
            print(f"[エラー] テスト画像から1つの顔を検出できません (検出数={len(test_locs)})")
            return False, None

        (known_enc,) = face_recognition.face_encodings(known_img, known_locs)
        (test_enc,) = face_recognition.face_encodings(test_img, test_locs)

        dists = face_recognition.face_distance([known_enc], test_enc)
        distance = dists[0]

        is_match = distance < tolerance
        print(is_match, distance)
        return is_match, distance

    except Exception as e:
        print(f"[致命的エラー] 顔認証処理で例外が発生: {e}")
        return False, None

#endregion

# if __name__ == "__main__":
#     print(read_imagedatabase(db_path))