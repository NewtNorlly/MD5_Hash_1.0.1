# 导入系统相关模块
import os
import sqlite3
import time
from pathlib import Path
# 导入Flask Web框架相关模块
from flask import Flask, request, jsonify, render_template
# 导入Anthropic AI客户端模块
import anthropic

# 初始化Flask应用实例
app = Flask(__name__)
# 定义SQLite数据库文件路径，位于当前脚本同级目录下的md5_rainbow.db
DB_PATH = Path(__file__).parent / "md5_rainbow.db"

# 初始化Anthropic AI客户端
# API Key 优先从环境变量读取，环境变量不存在时使用指定的默认值
AI_CLIENT = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY", "sk-66cabcc54db44e5e98245c5f214532c5")
)


def query_db(hash_val: str):
    """
    从彩虹表数据库中查询MD5哈希对应的明文密码
    :param hash_val: 待查询的MD5哈希值（字符串类型）
    :return: 元组(明文密码/None, 查询耗时(毫秒))
             - 找到返回对应的明文密码，未找到返回None
             - 耗时为从连接数据库到查询完成的时间，单位毫秒
    """
    # 建立与SQLite数据库的连接
    conn = sqlite3.connect(DB_PATH)
    # 记录查询开始时间
    t0 = time.time()
    # 执行SQL查询，查找对应哈希值的密码（哈希值统一转小写避免大小写问题）
    row = conn.execute(
        "SELECT password FROM rainbow WHERE hash = ?", (hash_val.lower(),)
    ).fetchone()
    # 关闭数据库连接，释放资源
    conn.close()
    # 计算查询耗时（毫秒），返回密码（如果有）和耗时
    return row[0] if row else None, (time.time() - t0) * 1000


def query_ai(hash_val: str):
    """
    调用Anthropic AI生成常见弱密码候选列表，逐一计算MD5验证是否匹配目标哈希
    AI 无法直接破解MD5，仅通过生成常见弱密码进行碰撞尝试
    :param hash_val: 待破解的MD5哈希值（字符串类型）
    :return: 元组(匹配的明文密码/None, 总耗时(毫秒))
             - 碰撞成功返回对应的明文密码，失败返回None
             - 耗时为从调用AI到碰撞完成的总时间，单位毫秒
    """
    # 导入MD5哈希计算模块（局部导入减少初始加载开销）
    import hashlib
    # 记录AI查询开始时间
    t0 = time.time()
    try:
        # 调用Anthropic AI接口生成常见弱密码列表
        resp = AI_CLIENT.messages.create(
            model="claude-sonnet-4-6",  # 指定使用的AI模型
            max_tokens=512,             # 生成内容的最大token数
            messages=[{
                "role": "user",         # 消息角色为用户
                "content": (            # 提示词：要求生成100个常见弱密码
                    "请列出100个最常见的弱密码，要求：\n"
                    "1. 包含常见单词+数字+符号组合，如 Admin@123、P@ssw0rd、Welcome1\n"
                    "2. 包含大小写混合变体，如 Password1、Passw0rd、Admin123\n"
                    "3. 包含常见符号变体，如 admin@123、root@2024、test!123\n"
                    "4. 每行只输出一个密码，不要编号，不要任何解释"
                )
            }]
        )
        # 解析AI返回的密码列表，按行分割并去除首尾空白
        candidates = resp.content[0].text.strip().splitlines()
        # 遍历候选密码列表，逐一进行MD5碰撞验证
        for pwd in candidates:
            pwd = pwd.strip()  # 去除单个密码的首尾空白
            if not pwd:        # 跳过空行
                continue
            # 计算当前候选密码的MD5哈希值，与目标哈希对比
            if hashlib.md5(pwd.encode()).hexdigest() == hash_val:
                # 碰撞成功，计算总耗时并返回密码和耗时
                ms = (time.time() - t0) * 1000
                return pwd, ms
        # 遍历完所有候选密码未匹配，返回None和耗时
        ms = (time.time() - t0) * 1000
        return None, ms
    except Exception:
        # 捕获调用AI过程中的异常，返回None和耗时
        return None, (time.time() - t0) * 1000


@app.get("/")
def index():
    """
    处理根路径GET请求，渲染并返回主页HTML模板
    :return: 渲染后的index.html页面
    """
    return render_template("index.html")


@app.post("/crack")
def crack():
    """
    处理/crack路径POST请求，执行MD5哈希破解逻辑
    步骤：1. 验证输入合法性 2. 查询彩虹表 3. AI碰撞兜底 4. 返回结果
    :return: JSON格式的破解结果，包含是否找到、密码、来源、耗时等信息
    """
    # 获取请求的JSON数据，静默模式下解析失败返回空字典
    data = request.get_json(silent=True) or {}
    # 提取并清洗输入的MD5哈希值（转小写、去首尾空白）
    h = (data.get("hash") or "").strip().lower()
    # 验证MD5哈希格式：必须是32位十六进制字符
    if len(h) != 32 or not all(c in "0123456789abcdef" for c in h):
        # 格式无效返回400错误和提示信息
        return jsonify({"error": "无效的MD5（需32位十六进制）"}), 400

    # 第一步：查询彩虹表数据库
    password, ms = query_db(h)
    if password:
        # 数据库中找到密码，返回成功结果（来源为database）
        return jsonify({"found": True, "source": "database", "password": password, "time_ms": round(ms, 2)})

    # 第二步：数据库未找到，调用AI进行碰撞兜底
    ai_password, ai_ms = query_ai(h)
    if ai_password:
        # AI碰撞成功，返回成功结果（来源为ai），总耗时为数据库查询+AI碰撞
        return jsonify({"found": True, "source": "ai", "password": ai_password, "time_ms": round(ms + ai_ms, 2)})

    # 数据库和AI都未找到密码，返回失败结果和总耗时
    return jsonify({"found": False, "time_ms": round(ms + ai_ms, 2)})


@app.get("/stats")
def stats():
    """
    处理/stats路径GET请求，返回彩虹表数据库的统计信息
    :return: JSON格式的统计数据（记录数、数据库文件大小）
    """
    # 检查数据库文件是否存在
    if not DB_PATH.exists():
        return jsonify({"error": "数据库不存在"}), 404
    # 连接数据库查询记录总数
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute("SELECT COUNT(*) FROM rainbow").fetchone()[0]
    conn.close()
    # 计算数据库文件大小（转换为MB，保留1位小数）
    size_mb = round(DB_PATH.stat().st_size / 1024 / 1024, 1)
    # 返回统计信息
    return jsonify({"count": count, "size_mb": size_mb})


# 程序主入口
if __name__ == "__main__":
    # 启动Flask开发服务器，开启调试模式，监听5000端口
    app.run(debug=True, port=5000)


