"""
MD5 Rainbow Table Builder - 精简示范版
只收录最常见的有规律密码，快速生成小型数据库
彩虹表原理：预计算常见密码的MD5哈希值并存储，用于快速反向查询明文密码
"""
# 导入必要的模块
import hashlib          # 用于计算MD5哈希值
import sqlite3          # 用于操作SQLite数据库
import itertools        # 用于生成密码组合（笛卡尔积）
import string           # 提供字符常量（数字、字母等）
import time             # 用于计算耗时
from pathlib import Path  # 用于获取文件大小

# 数据库文件保存路径
DB_PATH = "md5_rainbow.db"

def md5(s: str) -> str:
    """
    计算字符串的MD5哈希值（32位小写）
    :param s: 待计算的明文字符串
    :return: MD5哈希值字符串
    """
    return hashlib.md5(s.encode()).hexdigest()

def init_db(conn):
    """
    初始化数据库表结构
    :param conn: SQLite数据库连接对象
    """
    # 创建rainbow表，hash为主键（确保唯一），password存储明文密码
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rainbow (
            hash TEXT PRIMARY KEY,       -- MD5哈希值（主键，避免重复）
            password TEXT NOT NULL       -- 对应的明文密码
        )
    """)
    conn.commit()  # 提交表结构创建操作

def generate_passwords():
    """
    生成各类常见弱密码组合，涵盖数字、常用词汇、生日、姓名拼音等
    :return: 所有生成的密码列表
    """
    passwords = []  # 存储所有生成的密码

    # 1. 纯数字密码（4~6位）- 最常见的数字密码类型
    for length in range(4, 7):
        # 生成指定长度的数字组合（如4位：0000~9999）
        for combo in itertools.product(string.digits, repeat=length):
            passwords.append(''.join(combo))

    # 2. 常见弱密码词汇及变体 - 全网高频出现的弱密码
    base_words = [
        "password", "passwd", "pass", "admin", "root", "user", "login",
        "welcome", "hello", "world", "test", "guest", "master", "super",
        "qwerty", "asdf", "abc", "iloveyou", "monkey", "dragon", "letmein",
        "111111", "222222", "666666", "888888", "000000", "123123", "654321",
        "abc123", "abcdef", "aaaaaa", "password1", "admin123", "root123",
        "china", "beijing", "shanghai",
    ]
    # 常见后缀（弱密码常加的数字/符号）
    suffixes = ["", "1", "12", "123", "1234", "12345", "0", "!", "2024", "2025"]
    for word in base_words:
        for suf in suffixes:
            passwords.append(word + suf)          # 原词+后缀（如password123）
            if suf:
                passwords.append(word.capitalize() + suf)  # 首字母大写+后缀（如Password123）

    # 3. 年份密码（1970~2025）- 生日/纪念年份类密码
    for year in range(1970, 2026):
        for suf in ["", "0", "123", "!"]:
            passwords.append(str(year) + suf)  # 年份+后缀（如1990123、2000!）

    # 4. 生日格式密码 YYYYMMDD（1980~2005年 + 1~28日）- 避免2月29等特殊日期
    for year in range(1980, 2005):
        for month in range(1, 13):          # 1~12月
            for day in range(1, 29):        # 1~28日（兼容所有月份）
                passwords.append(f"{year}{month:02d}{day:02d}")  # 格式：YYYYMMDD（如19900101）

    # 5. 纯小写字母密码（3~4位）- 短字母组合弱密码
    for length in range(3, 5):
        # 生成指定长度的小写字母组合（如3位：aaa~zzz）
        for combo in itertools.product(string.ascii_lowercase, repeat=length):
            passwords.append(''.join(combo))

    # 6. 常见中国姓名拼音 + 数字 - 针对中文用户的弱密码
    names = ["zhang","wang","li","zhao","liu","chen","yang","huang",
             "zhou","wu","xu","sun","ma","zhu","hu","guo","lin","he"]  # 百家姓高频拼音
    for name in names:
        for suf in ["", "123", "1234", "12345", "2024", "2025", "0", "!"]:
            passwords.append(name + suf)  # 姓名拼音+后缀（如zhang123、li2024）

    return passwords

def build():
    """
    主构建函数：初始化数据库 → 生成密码 → 批量写入 → 建立索引 → 输出统计信息
    """
    print("[*] 初始化数据库...")
    # 连接（创建）SQLite数据库
    conn = sqlite3.connect(DB_PATH)
    # 优化SQLite写入性能（WAL模式、同步级别、缓存大小）
    conn.execute("PRAGMA journal_mode=WAL")        # 启用WAL模式，提升并发写入性能
    conn.execute("PRAGMA synchronous=NORMAL")      # 降低同步级别，加快写入速度
    conn.execute("PRAGMA cache_size=100000")       # 增大缓存，减少磁盘IO
    init_db(conn)  # 初始化表结构

    print("[*] 生成密码并写入...")
    t0 = time.time()  # 记录开始时间
    passwords = generate_passwords()  # 生成所有候选密码
    print(f"[*] 候选密码数量: {len(passwords):,}")  # 打印密码总数（千分位格式化）

    # 批量写入数据库（避免单条插入，提升效率）
    batch, total = [], 0  # batch：当前批次数据；total：已写入总数
    for pwd in passwords:
        # 存储（MD5哈希值，明文密码）元组
        batch.append((md5(pwd), pwd))
        # 每积累50000条批量写入一次
        if len(batch) >= 50000:
            # INSERT OR IGNORE：避免重复主键（哈希值）报错
            conn.executemany("INSERT OR IGNORE INTO rainbow VALUES (?,?)", batch)
            conn.commit()  # 提交事务
            total += len(batch)  # 更新已写入总数
            batch = []  # 清空批次
            # 实时打印进度（\r：回车不换行，覆盖当前行）
            print(f"    已写入 {total:,} 条...", end='\r')
    # 处理剩余不足50000条的批次
    if batch:
        conn.executemany("INSERT OR IGNORE INTO rainbow VALUES (?,?)", batch)
        conn.commit()
        total += len(batch)

    print(f"\n[*] 建立索引...")
    # 为hash字段建立索引，加速后续查询
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hash ON rainbow(hash)")
    conn.commit()
    conn.close()  # 关闭数据库连接

    # 计算数据库文件大小（MB）
    size_mb = Path(DB_PATH).stat().st_size / 1024 / 1024
    # 打印最终统计信息（耗时、数据量、数据库大小）
    print(f"[+] 完成！{total:,} 条，耗时 {time.time()-t0:.1f}s，数据库 {size_mb:.1f} MB")

# 程序入口
if __name__ == "__main__":
    build()  # 执行构建流程


