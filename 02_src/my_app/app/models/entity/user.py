from dataclasses import dataclass
from typing import Optional

"""
user用データクラス(エンティティ)
変数詳細 : テーブル定義から見てください
"""

@dataclass
class User:
    id: Optional[int]
    user_name: str
    user_kana: str