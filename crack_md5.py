"""
MD5 Cracker - 通过彩虹表数据库查找MD5对应的明文密码
用法:
    python crack_md5.py <md5hash>  # 命令行模式，传入一个或多个MD5哈希值
    python crack_md5.py            # 交互模式，手动输入MD5哈希值查询
"""
# 导入所需模块
import sqlite3  # 用于操作SQLite数据库
import sys      # 用于获取命令行参数和系统相关操作
import hashlib  # 用于MD5哈希验证
import time     # 用于计算查询耗时
from pathlib import Path  # 用于检查文件/数据库是否存在

# 定义彩虹表数据库文件路径
DB_PATH = "md5_rainbow.db"

def lookup(hash_val: str) -> str | None:
    """
    根据MD5哈希值查询对应的明文密码
    :param hash_val: 待查询的MD5哈希字符串
    :return: 找到则返回明文密码，未找到/无效则返回None
    """
    # 去除首尾空格并转为小写（统一哈希值格式，避免大小写/空格问题）
    hash_val = hash_val.strip().lower()
    # 校验MD5哈希格式：必须是32位十六进制字符串
    if len(hash_val) != 32:
        print("[-] 无效的MD5哈希（应为32位十六进制字符串）")
        return None

    # 检查数据库文件是否存在
    if not Path(DB_PATH).exists():
        print(f"[-] 数据库 {DB_PATH} 不存在，请先运行 build_db.py")
        return None

    # 连接SQLite数据库
    conn = sqlite3.connect(DB_PATH)
    # 设置数据库为只读模式，防止误操作修改数据
    conn.execute("PRAGMA query_only=1")
    # 记录查询开始时间（用于计算耗时）
    t0 = time.time()
    # 执行SQL查询：根据哈希值查找对应的明文密码
    row = conn.execute(
        "SELECT password FROM rainbow WHERE hash = ?", (hash_val,)
    ).fetchone()  # fetchone()获取第一条匹配结果，无结果则返回None
    # 关闭数据库连接（释放资源）
    conn.close()
    # 计算查询耗时（毫秒）
    elapsed = (time.time() - t0) * 1000

    # 判断是否查询到结果
    if row:
        print(f"[+] 破解成功！({elapsed:.2f}ms)")
        print(f"    MD5   : {hash_val}")
        print(f"    密码  : {row[0]}")
        return row[0]  # 返回明文密码
    else:
        print(f"[-] 未找到（{elapsed:.2f}ms）- 该密码不在彩虹表中")
        return None

def verify(password: str, hash_val: str) -> bool:
    """
    验证明文密码的MD5哈希是否与目标哈希值匹配
    :param password: 待验证的明文密码
    :param hash_val: 目标MD5哈希值
    :return: 匹配返回True，不匹配返回False
    """
    # 计算明文密码的MD5哈希（encode()转为字节串，hexdigest()转为十六进制字符串）
    # 转为小写后与目标哈希值比较（统一格式）
    return hashlib.md5(password.encode()).hexdigest() == hash_val.lower()

def db_stats():
    """
    输出彩虹表数据库的统计信息（记录数、文件大小）
    """
    # 检查数据库文件是否存在
    if not Path(DB_PATH).exists():
        print(f"[-] 数据库不存在")
        return
    # 连接数据库
    conn = sqlite3.connect(DB_PATH)
    # 查询数据库中的总记录数
    count = conn.execute("SELECT COUNT(*) FROM rainbow").fetchone()[0]
    # 关闭数据库连接
    conn.close()
    # 计算数据库文件大小（转换为MB）
    size_mb = Path(DB_PATH).stat().st_size / 1024 / 1024
    # 输出统计信息（格式化数字，增加可读性）
    print(f"[*] 数据库统计: {count:,} 条记录，{size_mb:.1f} MB")

# 主程序入口
if __name__ == "__main__":
    # 先输出数据库统计信息
    db_stats()
    print()  # 空行分隔，提升输出可读性

    # 判断运行模式：命令行模式 / 交互模式
    if len(sys.argv) > 1:
        # 命令行模式：遍历传入的所有MD5哈希参数，逐个查询
        for h in sys.argv[1:]:
            lookup(h)
    else:
        # 交互模式：提示用户输入，支持退出指令
        print("输入MD5哈希值进行查找（输入 q 退出）")
        while True:
            # 获取用户输入的MD5哈希值（去除首尾空格）
            h = input("\nMD5> ").strip()
            # 判断是否输入退出指令（q/quit/exit，不区分大小写）
            if h.lower() in ('q', 'quit', 'exit'):
                break
            # 输入非空时执行查询
            if h:
                lookup(h)


