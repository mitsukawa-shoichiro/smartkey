import smtplib
from email.mime.text import MIMEText
import os, sys
import logging
import json

#2階層上の絶対パスを取得してモジュール検索パスの先頭に追加する
LOGS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if LOGS_PATH not in sys.path:
    sys.path.insert(0, LOGS_PATH)
import my_app.logs.log_config_service

#設定パス（絶対パス）
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'backend', 'mail.json'))
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    mail_config = json.load(f)

mymail = mail_config['mailadress']
mypass = mail_config['password']
to_mail = mail_config['to_mail']
smtp_server = mail_config['smtp_server']
port = mail_config['port']

logger = logging.getLogger(__name__)  # logに書き込む用

# mail.json の絶対パスを指定
MAIL_CONFIG_PATH = r"C:\smartkey\02_src\my_app\config\backend\mail.json"


def send_mail(TITLE, TEXT):
    '''
    メールを送信するメソッド \n
    引数：\n
    TITLE (str): メールの件名,
    TEXT (str): メール本文 \n
    '''
    # mail.json を読み込む
    with open(MAIL_CONFIG_PATH, "r", encoding="utf-8") as f:
        mail_config = json.load(f)

    mymail = mail_config["mailadress"]
    mypass = mail_config["password"]
    to_mail = mail_config["to_mail"]
    smtp_server = mail_config["smtp_server"]
    port = mail_config["port"]
    # メール内容の設定
    msg = MIMEText(TEXT, 'plain', 'utf-8')
    msg['Subject'] = TITLE  # 件名
    msg['From'] = mymail  # 送信元
    msg['To'] = to_mail  # 宛先
    try:
        # 163メールのSMTPサーバーに接続してメールを送信
        with smtplib.SMTP_SSL(smtp_server, port) as server:
            server.login(mymail, mypass)
            server.send_message(msg)
            logger.info("メール送信成功")
    except Exception as e:
        logger.error(f"メール送信失敗: {e}")
    logger.info('メール送信完了')

if __name__ == "__main__":
    # テスト用のメール送信
    send_mail("テストメール", "これはテストメールです。")
    logger.info("テストメール送信完了")