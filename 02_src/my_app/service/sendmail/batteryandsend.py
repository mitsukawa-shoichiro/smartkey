import requests
import smtplib
from email.mime.text import MIMEText
import time

sesame_id = "11200413-0002-0611-3F00-9200FFFFFFFF"
x_api_key = "O3R8DiaBCR2CD8mi10ibR9yT5OMqZHByaDmSCmnT"
mymail = "lpj99199@163.com"
mypass = "lsq99199"
to_mail = "lsq99199@gmail.com"
# 一時間待機
sleep_time= 3600
# 30分ごとにバッテリーを確認し、条件を満たせばメールを作成
while True:
    # 処理前の時刻
    time1 = time.time()

    # バッテリー確認処理
    try:
        url = f"https://app.candyhouse.co/api/sesame2/{sesame_id}"
        headers = {"x-api-key": x_api_key}
        response = requests.get(url, headers=headers)
        # 取得したレスポンスを表示
        print(response)
        print(response.text)
        # JSONとしてパース

        #battery状態取得
        try:
            data = response.json()
            battery = data.get('batteryPercentage', '取得失敗')
        except Exception as e:
            battery = f"JSON解析失敗: {e}"
        # メール本文作成
        # 只有当电池电量小于等于20时才发送邮件
        # バッテリー残量が20以下の場合のみメールを送信する
        if isinstance(battery, int) and battery <= 20:
            mail_body = f"sesami状態は:\n{response.text}\n\n電池残量:\n{battery}"
            msg = MIMEText(mail_body, 'plain', 'utf-8')
            msg['Subject'] = 'セサミ状態通知'
            msg['From'] = mymail
            msg['To'] = to_mail
            # メール送信
            with smtplib.SMTP_SSL('smtp.163.com', 465) as server:
                server.login(mymail, mypass)
                server.send_message(msg)
            print('メール送信完了')
    except Exception as e:
        print("バッテリー確認中またはメール送信中にエラー:", e)

    # 最後に
    time2 = time.time()
    time.sleep(sleep_time)
