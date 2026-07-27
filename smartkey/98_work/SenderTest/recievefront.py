import socket, threading, tkinter as tk

HOST, PORT = '127.0.0.1', 12345
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))

current_state = False

def ChangeState():
    while True:
        data, _ = sock.recvfrom(100)
        global current_state
        current_state = not current_state
        root.after(0, update_label, current_state)


def update_label(state):
    state_var.set(f"state: {state}")


root = tk.Tk()
state_var = tk.StringVar(value=f"state: {current_state}")
tk.Label(root, textvariable=state_var, font=('Arial', 16)).pack(padx=20, pady=20)

threading.Thread(target=ChangeState, daemon=True).start()
root.mainloop()