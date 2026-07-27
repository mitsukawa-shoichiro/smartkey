import socket
import time

HOST = '127.0.0.1'  # 本地回环地址

PORT = 10000        


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
msg="registering"
sock.sendto(msg.encode('utf-8'), (HOST, PORT))
