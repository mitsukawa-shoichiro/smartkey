# 1. ライブラリのインポート
from os import name
from smartcard.Exceptions import NoCardException
from smartcard.System import readers


def scan_card():
    # 2. カードリーダーを取得
    reader = readers()
    print("利用可能なカードリーダー:", reader)

    # 3. カードリーダーの選択と接続
    connection = reader[0].createConnection()
    connection.connect()

    # 4. IDm の取得（FeliCa Polling の簡易版）
    GET_IDM_APDU = [0xFF, 0xCA, 0x00, 0x00, 0x00]
    response, sw1, sw2 = connection.transmit(GET_IDM_APDU)

    # 5. IDm を表示
    if sw1 == 0x90 and sw2 == 0x00:
        idm = response
        idm_hex = ''.join(format(byte, '02X') for byte in idm)
        print("カードのIDm:", idm_hex)
        return idm_hex
    else:
        print("カードのIDmを取得できませんでした")
        return None
if __name__ == "__main__":
    scan_card()