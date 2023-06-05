### 计算机网络 课程项目 (2023/6)
用 Python 实现的简单的 LAN 文件传输器.

#### 原始需求
- The active ends of this utilities display the current user list which contains all the active users in LAN.
- An active user can share files and folders to another active user found in the current user list.

#### 环境要求
- Windows 系统
  
如果使用解释器运行，那么还需要
- Python 3.10+ 及安装 `tqdm`

#### 运行
有三种启动方式：
1. 在根目录下运行 `python main.py`. 请确保环境符合要求.
2. 运行 `start_*.bat`. 这实际上和第一种是同一种方式.
3. 运行二进制分发中的 `main.exe`.

#### 分发
1. 安装 pyinstaller
   
   `pip install pyinstaller`
2. 进行打包
   
   `pyinstaller -F main.py`

   可执行文件会生成在 `./dist` 下.

#### 注意事项
1. 广播能否正常工作取决于网络环境；可能需要禁用虚拟网卡。
2. 程序仅经过简单的测试，可能无法处理某些错误。