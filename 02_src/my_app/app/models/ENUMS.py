from enum import Enum

class EntryStatus(Enum):
    ENTRY = "入室"
    EXIT = "退室"

class CardType(Enum):
    IC_CARD = "交通系ICカード"
    CREDIT_CARD = "クレジットカード"
    ELSE_CARD = "その他"

class Method(Enum):
    WIFI = "wifi"
    BLUE_TOOTH = "blue_tooth"


#status = EntryStatus("入室")
#EntryStatus.ENTRY.value = "入室"
