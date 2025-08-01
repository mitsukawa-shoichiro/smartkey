import socket
import logging

# Windowsサービス起動時

HOST = '127.0.0.1'
PORT = 33333

try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        msg = "AUTHENTICATING"
        sock.sendall(msg.encode('utf-8'))
        logging.info(f"Sent message: {msg}")
except Exception as e:
    logging.error(f"通信エラー: {e}")


# cardSys.py

HOST = '127.0.0.1'
PORT = 33333

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((HOST, PORT))
sock.listen()

# receive_card()
conn, addr = sock.accept()
with conn:
    data = conn.recv(1024).decode()

    if data == "AUTHENTICATING":
        logging.info("解錠リクエスト")
        # unlock()

    elif data != "REGISTERING":
        logging.error("間違った値")


# flet register.py

HOST = '127.0.0.1'
PORT = 33333

# 状態変更
try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        msg = "REGISTERING"
        sock.sendall(msg.encode('utf-8'))
        logging.info(f"Sent message: {msg}")
except Exception as e:
    logging.error(f"通信エラー: {e}")
