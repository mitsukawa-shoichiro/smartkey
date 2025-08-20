
from service.utils.usb_card_readers import get_readers
from card_scan import load_config

def get_reader():
    config = load_config()
    reader_list = get_readers()
    
    if not reader_list:
        print("カードリーダーが見つかりませんでした")
        return None
    
    if len(reader_list) == 1:
        return reader_list[0]
    
    if len(reader_list) > 1:
        exit_id = config.get("出口")
        for r,s in reader_list:
            if exit_id in str(s):
                print(f"出口リーダーを使用: {r}")
                return r