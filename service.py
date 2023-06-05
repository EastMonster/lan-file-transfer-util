import math
import os.path
import socket
import struct
import threading
from tqdm import tqdm
from cfg import *
from util import *


class TcpSender:

    def __init__(self, path: str):
        self.path: str = path
        self.active_users: list[tuple[str, str, bool]] = []

        try:
            self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp.bind(("0.0.0.0", SND_LSTN_PORT))

            # 启用广播
            self.udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except socket.error as msg:
            eprint(msg)

    # 发送广播
    def boardcast(self):
        self.active_users.clear()
        hostname = os.getlogin()
        self.udp.sendto(struct.pack(SND_BCST_FMT, hostname.encode()),
                        ("<broadcast>", RECV_LSTN_PORT))
        print("正在探测子网中的接收端...")
        self.udp.settimeout(BCST_TIMEOUT)
        while True:
            try:
                bcpack_size = struct.calcsize(RECV_BCST_FMT)
                data, addr = self.udp.recvfrom(bcpack_size)

                r_hostname, is_working = struct.unpack(RECV_BCST_FMT, data)
                self.active_users.append(
                    (addr[0], r_hostname.decode(), is_working))
            except socket.timeout:
                print("探测结束.")
                break

    def start(self) -> bool:
        while True:
            listening = threading.Thread(target=self.boardcast)
            listening.start()
            listening.join()
            self.ip = get_target_ip(self.active_users)
            if self.ip != REMAKE:
                break
        return self.send()

    # 返回是否继续发送
    def send(self) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.ip, RECV_PORT))
        except socket.error as msg:
            eprint(msg)

        # 文件总览信息发一个包
        folder_flag = is_folder(self.path)
        dirs, files = get_dir_structure(self.path)
        dir_count = len(dirs)
        file_count = len(files)
        file_sizes = [os.path.getsize(x) for x in files]
        file_size_sum = sum(file_sizes)
        file_summary = struct.pack(FILE_SUM_FMT, os.getlogin().encode(),folder_flag,
                                   dir_count, file_count, file_size_sum,
                                   os.path.basename(self.path).encode())

        sock.send(file_summary)

        # 发送目录结构，让接收端先建好目录
        # 八个一组分块并用问号分隔 (因为问号不可能出现在路径中)
        if folder_flag:
            print("正在发送目录信息...")
            for i in range(dir_count):
                dirs[i] = os.path.relpath(dirs[i], self.path)
            dirs_chunks = [
                '?'.join(map(str, chunk))
                for chunk in [dirs[i:i + 8] for i in range(0, dir_count, 8)]
            ]
            for dirs_chunk in dirs_chunks:
                dirs_info = struct.pack(DIR_INFO_FMT, dirs_chunk.encode())
                sock.send(dirs_info)

        # 开始发送文件
        with tqdm(total=file_size_sum, unit='B', unit_scale=True, unit_divisor=1024) as pbar:
            for i, file in enumerate(files):
                # 每个文件发一个包
                relpath = os.path.relpath(file, self.path) if folder_flag else os.path.basename(self.path)
                file_info = struct.pack(FILE_INFO_FMT, file_sizes[i],
                                        relpath.encode())
                sock.send(file_info)
                pbar.set_description(f"({i + 1}/{file_count}) 正在发送")
                with open(file, "rb") as f:
                    try:
                        while True:
                            data = f.read(1024)
                            if not data:
                                break
                            sock.send(data)
                            pbar.update(len(data))
                    except socket.error as msg:
                        eprint(msg)

        self.udp.close()
        sock.close()

        return request_continue()


class TcpReceiver:

    def __init__(self, path=""):
        self.path: str = path
        self.busy: bool = False
        threading.Thread(target=self.listening).start()

    # 监听广播
    def listening(self):
        try:
            udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            udp.bind(("0.0.0.0", RECV_LSTN_PORT))

            # 启用广播
            udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except socket.error as msg:
            eprint(msg, pause=True, exit=True)

        bcpack_size = struct.calcsize(SND_BCST_FMT)
        hostname = os.getlogin()
        while True:
            data, addr = udp.recvfrom(bcpack_size)
            s_hostname = struct.unpack(SND_BCST_FMT, data)[0].decode()
            udp.sendto(struct.pack(RECV_BCST_FMT, hostname.encode(), self.busy), addr)
            log_bcst(addr[0], s_hostname)

    def start(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(("0.0.0.0", RECV_PORT))
            sock.listen(5)
        except socket.error as msg:
            eprint(msg, pause=True, exit=True)

        while True:
            conn, addr = sock.accept()
            self.busy = True
            t = threading.Thread(target=self.receive, args=(conn, addr[0]))
            t.start()
            t.join()
            self.busy = False

    def receive(self, conn: socket.socket, ip: str):
        while True:
            file_summary_size = struct.calcsize(FILE_SUM_FMT)
            file_info_size = struct.calcsize(FILE_INFO_FMT)
            dir_info_size = struct.calcsize(DIR_INFO_FMT)
            buf = conn.recv(file_summary_size)
            if buf:
                # 发送端用户名，是否为文件夹, 文件夹数，文件数，总大小，顶层文件/文件夹名
                hostname, isdir, dcount, fcount, tsize, tname = struct.unpack(FILE_SUM_FMT, buf)
                tname: str = tname.strip(b'\00').decode()
                hostname: str = hostname.strip(b'\00').decode()
                full_path = os.path.join(FOLDER_PATH, tname)

                log_connection(ip, hostname)
                log_host_and_file(hostname, tname, tsize, is_folder=isdir)

                if isdir and not os.path.exists(full_path):
                    os.mkdir(full_path)

                dir_chunk_count = math.ceil(dcount / 8)  # 需要接收的总目录信息包数
                recvd_dir_info = 0  # 已接收的总目录信息包数
                recvd_file = 0  # 已接收的总文件数
                recvd_size = 0  # 单个文件已接收的大小

                # 接收目录信息
                if isdir:
                    log("正在建立目录结构...")
                    while recvd_dir_info != dir_chunk_count:
                        dirinfo = conn.recv(dir_info_size)
                        dirs = struct.unpack(DIR_INFO_FMT, dirinfo)
                        dirs = dirs[0].strip(b'\00').decode().split('?')
                        for dir in dirs:
                            os.makedirs(os.path.join(FOLDER_PATH, tname, dir),
                                        exist_ok=True)
                        recvd_dir_info += 1

                # 接收文件
                with tqdm(total=tsize, unit='B', unit_scale=True, unit_divisor=1024) as pbar:
                    while recvd_file != fcount:
                        fileinfo = conn.recv(file_info_size)
                        fsize, name = struct.unpack(FILE_INFO_FMT, fileinfo)
                        name: str = name.strip(b'\00').decode()
                        file_path = os.path.join(FOLDER_PATH, tname, name) if isdir else os.path.join(FOLDER_PATH, name)
                        pbar.set_description(f"({recvd_file + 1}/{fcount}) 正在接收")
                        recvd_size = 0
                        with open(file_path, "wb") as f:
                            try:
                                while recvd_size < fsize:
                                    data = conn.recv(min(fsize - recvd_size, 1024))
                                    if not data:
                                        break
                                    data_size = len(data)
                                    recvd_size += data_size
                                    pbar.update(data_size)
                                    f.write(data)
                                recvd_file += 1
                            except socket.error as msg:
                                eprint(msg)
                log_recv_finish(hostname, fcount)
            conn.close()
            break
