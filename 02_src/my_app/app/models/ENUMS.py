from enum import Enum, IntEnum

class EntryStatus(Enum):
    ENTRY = "入室"
    EXIT = "退室"

class CardType(Enum):
    IC_CARD = "交通系ICカード"
    CREDIT_CARD = "クレジットカード"
    ELSE_CARD = "その他"

class Method(Enum):
    FACE = "face"
    CARD = "card"

class EventType(IntEnum):#カードリーダーのID(Configにて設定)からの入退室イベントタイプを定義
    ENTRY = 1
    EXIT = 0


#status = EntryStatus("入室")
#EntryStatus.ENTRY.value = "入室"
