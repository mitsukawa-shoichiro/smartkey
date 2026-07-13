from dataclasses import dataclass
from typing import Optional

"""
card用データクラス(エンティティ)
変数詳細 : テーブル定義から見てください
"""

@dataclass
class Card:
    id: Optional[int]
    card_type: str
    card_number: str
    register_date: Optional[str]
    user_id: int