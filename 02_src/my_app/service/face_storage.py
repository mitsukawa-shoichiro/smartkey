"""
顔画像ファイル(.png)の保存削除をまとめたモジュール

DBで保存するのは少し困難としたため、画像ファイルで直に保存させていただきます。

のぞき見防止の為、暗号化いたします。
暗号化関連はface_key_managerに任せます。

"""

import os
import logging
#from cryptgraphy.fernet import Fernet
#from my_app.service import face_key_manager
from uuid import uuid4


logger = logging.getLogger(__name__)

# _fernet = Fernet(face_key_manager.load_key())

#
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = APP_DIR / "storage"
FACES_DIR = STORAGE_DIR / "faces"
EMBEDDINGS_DIR = STORAGE_DIR / "face_embeddings"

def _ensure_faces_dir():
    """
    facesフォルダがなければ作る関数
    """
    os.makedirs(FACES_DIR, exist_ok=True)



def get_face_image_path(face_id: int):
    """
    face_idから画像ファイルの絶対パスを返す関数

    Args:
        face_id (int): 顔ID

    Returns:
        str: 指定の顔の絶対パス
    """

    return os.path.join(FACES_DIR, f"{face_id}.png")



def save_face_image(face_id: int, image_bytes: bytes):
    """
    顔画像をfacesフォルダにPNGで保存する。

    Args:
        face_id (int):
        image_bytes (bytes): 画像のバイナリデータ

    Returns:
        str: 保存した画像の絶対パス
    """

    _ensure_faces_dir()
    path = get_face_image_path(face_id)
    try:
        #encrypted = _fernet.encrypt(image_bytes)
        with open(path, "wb") as f:
            f.write(image_bytes)
        return path
    except OSError:
        logger.exception("顔画像の保存に失敗しました: face_id=%s, path=%s", face_id, path)
        raise



def load_face_image(face_id: int):
    """
    顔画像を読み込む関数

    Args:
        face_id (int): 顔ID

    Return:
        bytes: 顔画像のバイナリデータ(.png)
    """

    path = get_face_image_path(face_id)
    try:
        with open(path, "rb") as f:
            data = f.read()
        return data
    except FileNotFoundError:
        logger.warning("読み込み対象の顔画像が見つかりません: face_id=%s, path=%s", face_id, path)
        raise
    except OSError:
        logger.exception("顔画像の読み込みに失敗しました: face_id=%s, path=%s", face_id, path)
        raise


def delete_face_image(face_id: int) -> None:
    """
    顔画像ファイルを削除する関数
    ファイルが元から無い場合はエラーにせず、警告ログのみ出す

    Args:
        face_id (int): 顔情報のID
    """
    path = get_face_image_path(face_id)
    try:
        os.remove(path)
    except FileNotFoundError:
        logger.warning("削除対象の顔画像が見つかりません: face_id=%s, path=%s", face_id, path)
    except OSError:
        logger.exception("顔画像の削除に失敗しました: face_id=%s, path=%s", face_id, path)
        raise


def face_image_exists(face_id: int) -> bool:
    """
    顔画像ファイルが存在するかどうかを確認する。

    Args:
        face_id (int): 顔情報のID

    Returns:
        bool: 存在すればTrue
    """
    return os.path.isfile(get_face_image_path(face_id))


def list_stored_face_ids() -> set[int]:
    if not FACES_DIR.is_dir():
        return set()

    return {
        int(path.stem)
        for path in FACES_DIR.glob("*.png")
        if path.stem.isdigit()
    }