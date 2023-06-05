import datetime
import ipaddress
import os
import socket
import sys
from cfg import *

RED = "\033[31m"
YELLOW = "\033[33m"
L_BLUE = "\033[94m"
RESET = "\033[0m"
LINK_BEGIN = "\033]8;;"  # 链接后需要加 \a
LINK_END = "\033]8;;\a"


def ignore_signal(signum, frame):
    pass

def log(msg, end="\n", r=False):
    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    if not r:
        print(f"[{now_str}] {msg}", end=end)
    else:
        print(f"\r[{now_str}] {msg}", end="")
    sys.stdout.flush()


def log_bcst(ip: str, hostname: str):
    log(f"收到来自 {ip} ({L_BLUE}{hostname}{RESET}) 的广播.")


def log_connection(ip: str, hostname: str):
    log(f"与 {ip} ({L_BLUE}{hostname}{RESET}) 建立连接.")


def log_host_and_file(hostname: str, name: str, size: int, is_folder=False):
    if not is_folder:
        log(f"准备接收来自 {L_BLUE}{hostname}{RESET} 的文件 {YELLOW}{name}{RESET}, 大小 {convert_size(size)}.")
    else:
        log(f"准备接收来自 {L_BLUE}{hostname}{RESET} 的文件夹 {YELLOW}{name}{RESET}, 大小共 {convert_size(size)}.")


def log_recv_finish(hostname: str, count: int):
    log(f"来自 {L_BLUE}{hostname}{RESET} 的 {count} 个文件接收完毕. \
点击{YELLOW}{LINK_BEGIN}{os.getcwd()}\\{FOLDER_PATH[2:]}\a这里{LINK_END}{RESET}查看文件.")


def wprint(msg, end="\n", pause=False):
    print(f"{YELLOW}警告{RESET}: {msg}", end=end)
    if pause is True:
        input(" 按任意键继续.")


def eprint(msg, end="\n", pause=False, exit=False):
    print(f"{RED}错误{RESET}: {msg}", end=end)
    if exit is True:
        sys.exit(-1)
    if pause is True:
        input(" 按任意键继续.")


def is_folder(path: str) -> bool:
    if os.path.isfile(path):
        return False
    elif os.path.isdir(path):
        return True
    return False


def convert_size(size: int) -> str:
    if size < 1024:
        return f"{size} 字节"
    elif size >= 1024 and size < 1048576:
        return f"{round(size / 1024, 3)} KB"
    elif size >= 1048576 and size < 1073741824:
        return f"{round(size / 1048576, 3)} MB"
    else:
        return f"{round(size / 1073741824, 3)} GB"


def get_target_ip(user_list: list[tuple[str, str, bool]]) -> str:
    while True:
        try:
            for i, (ip, hostname, stat) in enumerate(user_list):
                if stat is True:
                    print(f"   {i + 1}. {L_BLUE}{hostname}{RESET} ({ip}) {YELLOW}(正在忙){RESET}")  # 这里没有测试
                else:
                    print(f"   {i + 1}. {L_BLUE}{hostname}{RESET} ({ip})")
            print("   0. 自定义")
            print("   -1. 重新探测")
            print("选择一个接收方: ")
            length = len(user_list)
            res = int(input(f"(-1~{length}) "))

            if res < -1 or res > length:
                wprint("请输入选项范围内的数字.", end="", pause=True)
                continue

            if res == 0:
                return get_custom_ip()
            elif res == -1:
                return REMAKE
            elif user_list[res - 1][2] is True:
                eprint("该主机正在接收文件.")
                return REMAKE
            else:
                return user_list[res - 1][0]
        except ValueError:
            wprint("请输入数字.", end="", pause=True)
            continue
        except Exception as e:
            eprint(f"未知错误: {e}", end="", pause=True, exit=True)


def get_custom_ip() -> str:
    ip = ""
    while True:
        ip = input("请输入接收方 IP 地址: ")
        if ip.strip() == "":
            ip = "127.0.0.1"
            return ip
        if not is_valid_ip(ip):
            wprint("请输入合法 IP.", end="", pause=True)
            continue
        elif not is_port_open(ip, RECV_PORT):
            eprint("连接超时，请重试.", end="", pause=True)
            continue
        else:
            return ip


def get_dir_structure(path: str) -> tuple[list[str], list[str]]:
    """返回值: (目录结构, 文件结构)"""
    dirs = []
    files = []
    if not is_folder(path):
        return dirs, [path]

    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                files.append(os.path.join(dirpath, filename))
            for dirname in dirnames:
                dirs.append(os.path.join(dirpath, dirname))
    except Exception as e:
        eprint(f"错误: {e}", pause=True, exit=True)
    return dirs, files


def is_valid_ip(ip: str) -> bool:
    try:
        _ = ipaddress.ip_address(ip)
        return True
    except Exception:
        return False


def is_port_open(ip: str, port: int):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        sock.connect((ip, port))
        return True
    except Exception:
        return False
    finally:
        sock.close()


def request_continue() -> bool:
    print("发送完毕. 是否继续发送？ (y/n) ", end="")
    res = input()
    if res.lower() == "y":
        return True
    else:
        print("程序即将退出.")
        return False