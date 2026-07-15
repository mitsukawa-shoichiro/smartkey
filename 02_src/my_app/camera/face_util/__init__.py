__all__ = [
    "run_face_back_system",
    "check_face",
    "match_against_db",
]


def __getattr__(name):
    """旧機能が要求されたときだけ読み込む"""

    if name == "run_face_back_system":
        from .face_back_system import run_face_back_system
        return run_face_back_system

    if name in ("check_face", "match_against_db"):
        from .face_utils import check_face, match_against_db

        functions = {
            "check_face": check_face,
            "match_against_db": match_against_db,
        }
        return functions[name]

    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}"
    )