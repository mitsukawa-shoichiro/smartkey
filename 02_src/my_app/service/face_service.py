"""
顔用データベースと顔写真の管理をまとめたモジュールです
例外はここでは上げるだけです、GUIで拾ってください
"""


from my_app.db import repository as repo
from my_app.app.storage import face_storage
import logging

logger = logging.getLogger(__name__)

def register_face(user_id: int, image_bytes: bytes):
    """
    顔登録の際の画像フォルダ管理関数及びDB管理関数の呼び出しと例外時のロールバックを担当している関数

    Args:
        user_id (int): ユーザーID
        image_bytes (bytes): 顔写真

    Returns:
        (int): 顔ID
    """

    #まずDBに登録、IDの取得
    face_id = repo.insert_face(user_id)

    #取得IDでファイル保存
    try:
        face_storage.save_face_image(face_id, image_bytes)

    except OSError:
        #ロールバック
        logger.exception("顔画像の保存に失敗しました、DB登録を取り消します: face_id=%s", face_id)
        repo.delete_face(face_id)
        raise

    return face_id



def remove_face(face_id: int):
    """
    顔削除の際の画像フォルダ管理関数及びDB管理関数の呼び出しの関数
    Args:
        face_id(int): 顔ID
    """
    #画像を消す
    face_storage.delete_face_image(face_id)

    #DBから該当行を削除
    repo.delete_face(face_id)



def delete_user_with_cleanup(user_id: int):
    """
    ユーザー削除時のラッパー関数、少々構造と責務的には気持ち悪いが顔画像がDBと紐づいてないので許してほしい。
    ユーザー削除前に紐づく顔IDを取得し削除する関数を呼び、ユーザー削除(CASCADEでDBは一括削除)

    Args:
        user_id (int): ユーザーID
    """

    #
    faces = repo.get_faces_by_user_id(user_id)

    #
    repo.delete_user(user_id)

    for face in faces:
        face_storage.delete_face_image(face["id"])