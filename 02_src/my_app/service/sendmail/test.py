import os, smtplib, ssl
from email.message import EmailMessage

HOST = "smtp.office365.com"
PORT = 587                      # STARTTLS
USER = "ml-smartkey@try-ltd.co.jp"
PWD  = os.getenv("SMTP_APP_PWD")  # 建议改用 App Password

msg = EmailMessage()
msg["Subject"] = "テスト"
msg["From"]    = USER
msg["To"]      = "dest@example.com"
msg.set_content("SMTP AUTH テスト")

context = ssl.create_default_context()

try:
    with smtplib.SMTP(HOST, PORT, timeout=10) as srv:
        srv.ehlo()
        srv.starttls(context=context)
        srv.ehlo()
        srv.login(USER, PWD)          # 若此处抛 535，请返回步骤②③
        srv.send_message(msg)
except smtplib.SMTPAuthenticationError as e:
    print("認証失敗:", e)              # 仅在失败时输出
else:
    print("メール送信完了")             # 成功时才输出
