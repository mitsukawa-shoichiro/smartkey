import requests
import time
from sendmail import send_mail

sesame_id = "11200413-0002-0611-3F00-9200FFFFFFFF"
x_api_key = "O3R8DiaBCR2CD8mi10ibR9yT5OMqZHByaDmSCmnT"

url = "http://127.0.0.1:5000/api/check_alive"
sleep_time = 3600

def check_sesame_battery():
    '''
    # sesameのバッテリー残量を確認し、20%以下ならメールを送信する
    '''
    try:
        sesame_url = f"https://app.candyhouse.co/api/sesame2/{sesame_id}"
        headers = {"x-api-key": x_api_key}
        response = requests.get(sesame_url, headers=headers)
        print(response.text)
        try:
            data = response.json()
            battery = data.get('batteryPercentage', '取得失敗')
        except Exception as e:
            battery = f"JSON解析失敗: {e}"
        print("バッテリー残量:", battery)
        try:
            if float(battery) <= 20:
                mail_body = f"sesami状態は:\n{response.text}\n\n電池残量:\n{battery}"
                send_mail('セサミ状態通知', mail_body)
                print('メール送信完了')
        except Exception as e:
            print("バッテリー値の変換またはメール送信中にエラー:", e)
    except Exception as e:
        print("バッテリー確認中またはメール送信中にエラー:", e)

def check_api_alive():
    '''
    # サーバーAPIが生きているか確認し、アクセスできない場合はメールを送信する
    '''
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get("alive") == "true":
            print("✅ サーバーは正常に稼働しています")
            return True
        else:
            print("🚨 サーバーが異常な応答を返しました")
            send_mail('サーバー異常通知', 'サーバーが応答していません。確認してください。')
            return False
    except Exception as e:
        print("🚨 サーバーにアクセスできません！例外情報:", e)
        send_mail('サーバー異常通知', f'サーバーが応答していません。例外情報:\n{e}')
        return False

if __name__ == "__main__":
    '''
    # メインループ。1時間ごとにsesameのバッテリーとサーバー状態を確認する
    '''
    while True:
        print("⏱️ sesameのバッテリーとサーバー状態を確認中...")
        check_sesame_battery()
        check_api_alive()
        time.sleep(sleep_time)
