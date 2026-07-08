from dataclasses import dataclass
from typing import Optional

"""
face用データクラス(エンティティ)
変数詳細 : テーブル定義から見てください
"""

@dataclass
class Face:
    id: Optional[int]
    register_date: Optional[str]
    user_id: int