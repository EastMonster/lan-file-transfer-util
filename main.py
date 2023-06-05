from cfg import *
from enum import IntEnum
import os
import socket
import signal
from tkinter import filedialog, Tk
from os import system
from service import TcpReceiver, TcpSender
from util import *


class ServiceMode(IntEnum):
    UNDEFINED = 0,
    SENDER = 1,
    RECEIVER = 2


def choose_service_mode() -> ServiceMode:
    while True:
        try:
            system("cls")
            print("[LAN 收发器] 选择你的服务模式: ")
            print("  1. 发送端")
            print("  2. 接收端")
            res = int(input("(1/2) "))

            if res != 1 and res != 2:
                wprint("请输入选项范围内的数字.", end="", pause=True)
                continue

            return ServiceMode(res)

        except ValueError:
            wprint("请输入数字.", end="", pause=True)
            continue


def sender_mode():
    system("title LAN 收发器 - 发送端")

    root = Tk()
    root.withdraw()
    root.wm_attributes("-topmost", 1)

    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)

    while True:
        system("cls")

        print("[LAN 收发器 - 发送端]")
        print(f"你的 IP 地址是 {ip_address}")
        while True:
            try:
                print("选择你的发送内容: ")
                print("  1. 文件")
                print("  2. 文件夹")
                res = int(input("(1/2) "))

                if res != 1 and res != 2:
                    wprint("请输入选项范围内的数字.", end="", pause=True)
                    continue
                break
            except ValueError:
                wprint("请输入数字.", end="", pause=True)
                continue

        path = ""
        match res:
            case 1:
                print("准备发送文件: ", end="")
                path = filedialog.askopenfilename(title="选择你要发送的文件")
            case 2:
                print("准备发送文件夹: ", end="")
                path = filedialog.askdirectory(title="选择你要发送的文件夹")
            case _:
                eprint("未知错误.", pause=True, exit=True)

        if not path:
            eprint("未选择路径，程序即将退出.", pause=True, exit=True)

        print(os.path.basename(path))

        sender = TcpSender(path)
        if sender.start():
            continue
        else:
            break


def receiver_mode():
    system("title LAN 收发器 - 接收端")
    system("cls")
    print("[LAN 收发器 - 接收端]")

    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    print("你的 IP 地址是 {}".format(ip_address))

    if not os.path.exists(FOLDER_PATH):
        os.makedirs(FOLDER_PATH)

    receiver = TcpReceiver()
    receiver.start()

service_mode = ServiceMode.UNDEFINED

if __name__ == "__main__":
    signal.signal(signal.SIGINT, ignore_signal)

    argv = sys.argv
    if len(argv) > 1:
        if argv[1] == "-s":
            sender_mode()
        elif argv[1] == "-r":
            receiver_mode()
    else:
        system("title LAN 收发器")
        service_mode = choose_service_mode()
        match service_mode:
            case ServiceMode.UNDEFINED:
                eprint("未知错误, 程序即将退出.", pause=True, exit=True)
            case ServiceMode.SENDER:
                sender_mode()
            case ServiceMode.RECEIVER:
                receiver_mode()