# 1. ライブラリのインポート
from os import name
from smartcard.Exceptions import NoCardException
from smartcard.System import readers


def scan_card():
    # 2. カードリーダーを取得
    reader_list = readers()
    # カードリーダーに接続
    idm=0
    for reader in reader_list:
        try:
            conn = reader.createConnection()
            conn.connect()

            # カードを読み取り
            GET_IDM_APDU = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            response, sw1, sw2 = conn.transmit(GET_IDM_APDU)

            # 読み取り成功の場合
            if [sw1, sw2] == [0x90, 0x00]:
                idm = ''.join(format(byte, '02X') for byte in response)

                print(f"カードリーダーでカードを検出、IDm:"+str(idm))
                conn.disconnect()
            else:
                conn.disconnect()
        except NoCardException:

            continue
        except Exception as e:
            print(f"エラー: {e}")
            continue
    if(idm!=0):
        return idm
    else:
        return None

# ...existing code...
def scan_cardreader() -> int:
    """
    複数のカードリーダーを走査し、カードIDを取得できた
    リーダーのインデックスを返す。見つからなければ -1。
    """
    reader_list = readers()

    for idx, reader in enumerate(reader_list):
        print(idx)
        conn = None
        try:
            conn = reader.createConnection()
            conn.connect()

            GET_IDM_APDU = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            response, sw1, sw2 = conn.transmit(GET_IDM_APDU)

            if [sw1, sw2] == [0x90, 0x00] and response:
                idm = ''.join(format(byte, '02X') for byte in response)
                print(f"カードリーダーでカードを検出、IDm:{idm} / ReaderIndex:{idx}")
                return idx  # ← 検出できたリーダーのindexを返す

        except NoCardException:
            continue
        except Exception as e:
            print(f"エラー: {e}")
            continue
        finally:
            try:
                if conn:
                    conn.disconnect()
            except Exception:
                pass
    print("no card")
    return -1  # どのリーダーでも検出できなかった

if __name__ == "__main__":
    scan_card()
