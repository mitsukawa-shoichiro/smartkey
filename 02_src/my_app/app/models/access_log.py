from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from ENUMS import EventType

"""
access_log用データクラス(エンティティ)
引数が多く、後でリポジトリが値を埋める(user_nameのコピー)事情があったので
access_logのみデータクラスの実装済みです。
変数詳細 : user_name_jpn(コピー)以外はテーブル定義を見てください、スマソ
"""

@dataclass
class AccessLog:
    id: Optional[int]
    timestamp: Optional[datetime]
    method: str
    event_type: EventType
    user_id: Optional[int]
    user_name_jpn: Optional[str] = None  # repositoryが埋める前提でNoneがデフォルト
    card_id: Optional[int] = None
    face_id: Optional[int] = None