import socket, tkinter as tk

HOST, PORT = '127.0.0.1', 12345
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def toggle_state():
    sock.sendto("toggle".encode(), (HOST, PORT))

root = tk.Tk()
tk.Button(root, text="change state", command=toggle_state).pack(padx=20, pady=20)
root.mainloop()
