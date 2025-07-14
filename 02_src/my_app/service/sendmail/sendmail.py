import smtplib
from email.mime.text import MIMEText

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
    # 163メールのSMTPサーバーに接続してメールを送信
    with smtplib.SMTP_SSL('？', port) as server:
        server.login(mymail, mypass)
        server.send_message(msg)

    print('メール送信完了')
