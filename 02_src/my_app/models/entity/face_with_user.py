from dataclasses import dataclass
from typing import Optional

"""
face_user結合用データクラス(エンティティ)
変数詳細 : テーブル定義から見てください
"""

@dataclass
class FaceWithUser:
    id: Optional[int]
    register_date: Optional[str]
    user_id: int
    user_name: str