"""
顔用データベースと顔写真の管理をまとめたモジュールです
例外はここでは上げるだけです、GUIで拾ってください
"""


from my_app.db import repository as repo
from my_app.service import face_storage
from my_app.service import face_embedding_storage
import logging

logger = logging.getLogger(__name__)

def register_face(user_id: int, image_bytes: bytes, embedding):
    """
    顔登録の際の画像フォルダ管理関数及びDB管理関数の呼び出しと例外時のロールバックを担当している関数

    Args:
        user_id (int): ユーザーID
        image_bytes (bytes): 顔写真

    Returns:
        (int): 顔ID
    """

    user = repo.get_user_by_id(user_id)

    if user is None:
        raise ValueError(
            f"ユーザーが存在しません: user_id={user_id}"
        )

    normalized_embedding = (
        face_embedding_storage.normalize_embedding(
            embedding
        )
    )

    #まずDBに登録、IDの取得
    face_id = repo.insert_face(user_id)

    #取得IDでファイル保存
    try:
        face_storage.save_face_image(
            face_id,
            image_bytes,
        )
        face_embedding_storage.save_embedding(
            face_id,
            normalized_embedding,
        )

    except Exception:
        #ロールバック
        logger.exception(
            "顔画像の保存に失敗しました、"
            "DB登録を取り消します: face_id=%s",
            face_id,
        )
        face_storage.delete_face_image(face_id)
        face_embedding_storage.delete_embedding(face_id)
        repo.delete_face(face_id)
        raise

    return face_id

def register_faces(user_id: int, samples):
    created_face_ids = []

    try:
        for image_bytes, embedding in samples:
            face_id = register_face(user_id, image_bytes, embedding)
            created_face_ids.append(face_id)

        return created_face_ids
    
    except Exception:
        for face_id in reversed(created_face_ids):
            try:
                remove_face(face_id)
            except Exception:
                logger.exception("顔認証取り消しできぬ face_id=%s", face_id)
        
        raise

def register_new_user_with_faces(user_name: str, user_name_romaji: str, samples):
    user_name = user_name.strip()
    user_name_romaji = user_name_romaji.strip()

    if not user_name:
        raise ValueError("ユーザー名を入力してください")

    if not user_name_romaji:
        raise ValueError("ローマ字名を入力してください")

    user_id = repo.insert_user(user_name, user_name_romaji)

    try:
        face_ids = register_faces(user_id, samples)

        return user_id, face_ids

    except Exception:
        try:
            repo.delete_user(user_id)
        except Exception:
            logger.exception("新規ユーザーのロールバックに失敗 user_id=%s", user_id)

        raise

def remove_face(face_id: int):
    """
    顔削除の際の画像フォルダ管理関数及びDB管理関数の呼び出しの関数
    Args:
        face_id(int): 顔ID
    """
    #画像を消す
    face_storage.delete_face_image(face_id)
    face_embedding_storage.delete_embedding(face_id)

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
    face_ids = repo.get_face_ids_by_user_id(user_id)

    #
    repo.delete_user(user_id)

    for face_id in face_ids:
        face_storage.delete_face_image(face_id)
        face_embedding_storage.delete_embedding(face_id)


def load_authentication_templates():
    templates = []

    for face in repo.get_all_faces_for_authentication():
        if not face_storage.face_image_exists(face.id):
            logger.warning("顔画像なし: face_id=%s", face.id)
            continue

        if not face_embedding_storage.embedding_exists(face.id):
            logger.warning("顔特徴量なし: face_id=%s", face.id)
            continue

        try:
            embedding = (face_embedding_storage.load_embedding(face.id))
        except (OSError, ValueError):
            logger.exception("顔特徴量読み込み失敗: face_id=%s",face.id)
            continue

        templates.append({
            "face_id": face.id,
            "user_id": face.user_id,
            "name": face.user_name,
            "embedding": embedding
        })

    return templates


def check_storage_consistency():
    database_ids = set(repo.get_all_face_ids())
    image_ids = face_storage.list_stored_face_ids()
    embedding_ids = (face_embedding_storage.list_stored_face_ids())

    return {
        "missing_images": sorted(database_ids - image_ids),
        "missing_embeddings": sorted(database_ids - embedding_ids),
        "orphan_images": sorted(image_ids - database_ids),
        "orphan_embeddings": sorted(embedding_ids - database_ids),
    }