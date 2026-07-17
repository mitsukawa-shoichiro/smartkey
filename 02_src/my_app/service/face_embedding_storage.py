import os
from pathlib import Path
from uuid import uuid4

import numpy as np


APP_DIR = Path(__file__).resolve().parent.parent
EMBEDDINGS_DIR = APP_DIR / "storage" / "face_embeddings"
EMBEDDING_DIM = 512


def _ensure_directory():
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)


def get_embedding_path(face_id: int) -> Path:
    return EMBEDDINGS_DIR / f"{int(face_id)}.npy"


def normalize_embedding(embedding) -> np.ndarray:
    vector = np.asarray(embedding, dtype=np.float32)

    if vector.ndim != 1:
        raise ValueError(f"顔特徴量が1次元じゃない；； {vector.shape}")

    if vector.size != EMBEDDING_DIM:
        raise ValueError(f"顔特徴量は{EMBEDDING_DIM}次元にしてね {vector.size}")

    if not np.isfinite(vector).all():
        raise ValueError("顔があかんわ")

    norm = float(np.linalg.norm(vector))

    if norm <= 0:
        raise ValueError("顔特徴量のノルム０")

    return np.ascontiguousarray(vector / norm, dtype=np.float32)


def save_embedding(face_id: int, embedding) -> Path:
    _ensure_directory()

    vector = normalize_embedding(embedding)
    destination = get_embedding_path(face_id)
    temporary = EMBEDDINGS_DIR / (
        f".{int(face_id)}.{uuid4().hex}.tmp"
    )

    try:
        with temporary.open("wb") as file:
            np.save(file, vector, allow_pickle=False)
            file.flush()
            os.fsync(file.fileno())

        os.replace(temporary, destination)
        return destination

    finally:
        if temporary.exists():
            temporary.unlink()


def load_embedding(face_id: int) -> np.ndarray:
    path = get_embedding_path(face_id)

    with path.open("rb") as file:
        vector = np.load(file, allow_pickle=False)

    return normalize_embedding(vector)


def delete_embedding(face_id: int) -> None:
    try:
        get_embedding_path(face_id).unlink()
    except FileNotFoundError:
        pass


def embedding_exists(face_id: int) -> bool:
    return get_embedding_path(face_id).is_file()


def list_stored_face_ids() -> set[int]:
    if not EMBEDDINGS_DIR.is_dir():
        return set()

    return {
        int(path.stem)
        for path in EMBEDDINGS_DIR.glob("*.npy")
        if path.stem.isdigit()
    }