import smtplib
from email.mime.text import MIMEText
import os,sys
import logging
LOGS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if LOGS_PATH not in sys.path:
    sys.path.insert(0, LOGS_PATH)
import logs.log_config_service

#  修正するとき、smtplib.SMTP_SSLの部分を修正してください
mymail = "mymail"
mypass = "mypass"
to_mail = "to_mail"
def send_mail(TITLE,TEXT):
    '''
    メールを送信するメソッド \n
    引数：\n
    TITLE (str): メールの件名,
    TEXT (str): メール本文 \n
    '''
    # メール内容の設定
    msg = MIMEText(TEXT, 'plain', 'utf-8')
    msg['Subject'] = TITLE  # 件名
    msg['From'] = mymail  # 送信元
    msg['To'] = to_mail  # 宛先
    try:
    # 163メールのSMTPサーバーに接続してメールを送信
        with smtplib.SMTP_SSL('？', port) as server:
            server.login(mymail, mypass)
            server.send_message(msg)
            print("メール送信成功")
    except Exception as e:
        print("メール送信失敗:", e)
        logging.error(f"メール送信失敗: {e}")
    print('メール送信完了')
