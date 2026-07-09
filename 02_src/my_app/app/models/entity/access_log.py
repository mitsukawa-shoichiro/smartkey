from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from models.ENUMS import EventType

"""
access_log用データクラス(エンティティ)
変数詳細 : user_name(コピー)以外はテーブル定義を見てください、スマソ
"""

@dataclass
class AccessLog:
    id: Optional[int]
    timestamp: Optional[datetime]
    method: str
    event_type: EventType
    user_id: Optional[int]
    user_name: Optional[str] = None  # repositoryが埋める前提でNoneがデフォルト
    card_id: Optional[int] = None
    face_id: Optional[int] = None