# MD5 彩虹表破解系统

基于 Python + Flask + SQLite 的 MD5 哈希值查找工具，内置 AI 兜底查询功能。

---

## 项目结构

```
今晚上机/
├── app.py              # Flask 后端服务
├── build_db.py         # 彩虹表数据库构建脚本
├── crack_md5.py        # 命令行破解工具
├── md5_rainbow.db      # SQLite 彩虹表数据库（约 592 万条记录）
└── templates/
    └── index.html      # 前端页面
```

---

## 环境要求

- Python 3.10+
- 依赖库：Flask、anthropic

安装依赖：

```bash
py -3 -m pip install flask anthropic
```

---

## 快速开始

### 第一步：构建数据库（只需执行一次）

```bash
py -3 build_db.py
```

执行完成后生成 `md5_rainbow.db`，约需 2 分钟，数据库大小约 795 MB。

### 第二步：启动服务

```bash
py -3 app.py
```

终端显示以下内容即表示启动成功：

```
* Running on http://127.0.0.1:5000
```

### 第三步：访问页面

打开浏览器，访问：

```
http://127.0.0.1:5000
```

在输入框中粘贴 32 位 MD5 哈希值，点击「查找」即可。

---

## 模块说明

### build_db.py — 数据库构建

按规律批量生成候选密码，计算 MD5 后写入 SQLite 数据库。

**密码生成规则：**

| 类型 | 示例 | 数量 |
|------|------|------|
| 纯数字 4~6 位 | `1234`、`654321` | 约 111 万 |
| 纯小写字母 3~4 位 | `abc`、`qwer` | 约 47 万 |
| 常见弱密码及变体 | `admin123`、`Password1` | 约 700 |
| 年份变体 1970~2025 | `2024`、`2024!` | 约 224 |
| 生日格式 YYYYMMDD | `19901201`、`01011990` | 约 8.7 万 |
| 中国姓名拼音变体 | `zhang123`、`Wang2024` | 约 144 |

**数据流：**

```
候选密码生成
    ↓
hashlib.md5(password.encode()).hexdigest()
    ↓
INSERT OR IGNORE INTO rainbow(hash, password)
    ↓
CREATE INDEX idx_hash ON rainbow(hash)
```

---

### app.py — 后端服务

基于 Flask 构建，提供 3 个 HTTP 接口。API Key 优先从环境变量 `ANTHROPIC_API_KEY` 读取。

**接口列表：**

| 路由 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 返回前端页面 |
| `/crack` | POST | 接收 MD5 哈希，查询并返回明文 |
| `/stats` | GET | 返回数据库记录数和文件大小 |

**`/crack` 接口说明：**

请求体（JSON）：

```json
{ "hash": "e10adc3949ba59abbe56e057f20f883e" }
```

响应体（JSON）：

```json
// 数据库命中
{ "found": true, "source": "database", "password": "123456", "time_ms": 7.2 }

// AI 碰撞命中
{ "found": true, "source": "ai", "password": "Admin@123", "time_ms": 3150.0 }

// 未找到
{ "found": false, "time_ms": 3200.0 }
```

**查询逻辑（两阶段）：**

```
第一阶段：查彩虹表
    SELECT password FROM rainbow WHERE hash = ?
    命中 → 立即返回（< 10ms）
    未命中 ↓

第二阶段：AI 兜底
    调用 Claude API 生成 100 个常见弱密码候选列表
    （含单词+数字+符号组合、大小写变体、常见符号变体）
    逐一计算 MD5 与目标哈希碰撞验证
    命中 → 返回（约 3s）
    未命中 → 返回 found: false
```

---

### index.html — 前端页面

纯原生 HTML + CSS + JavaScript，无外部依赖。

**交互流程：**

```
用户输入 32 位 MD5 哈希值
    ↓
fetch POST /crack（JSON 请求体）
    ↓
等待响应（显示加载状态）
    ↓
渲染结果：
  - 数据库命中 → 绿色，显示「数据库」标签
  - AI 推测命中 → 蓝色，显示「AI 推测」标签
  - 未找到 → 红色提示
```

页面加载时自动请求 `/stats`，在底部显示数据库记录数和文件大小。

---

### crack_md5.py — 命令行工具

不启动 Web 服务时，直接在终端查询 MD5。

**用法：**

```bash
# 单个哈希
py -3 crack_md5.py e10adc3949ba59abbe56e057f20f883e

# 多个哈希
py -3 crack_md5.py <hash1> <hash2> <hash3>

# 交互模式
py -3 crack_md5.py
```

---

## 测试用例

以下 MD5 值均可在数据库中查到：

| MD5 哈希值 | 明文密码 |
|---|---|
| `e10adc3949ba59abbe56e057f20f883e` | 123456 |
| `21232f297a57a5a743894a0e4a801fc3` | admin |
| `5f4dcc3b5aa765d61d8327deb882cf99` | password |
| `63a9f0ea7bb98050796b649e85481845` | root |
| `d8578edf8458ce06fbc5bb76a58c5ca4` | qwerty |
| `e99a18c428cb38d5f260853678922e03` | abc123 |
| `0192023a7bbd73250516f069df18b500` | admin123 |
| `482c811da5d5b4bc6d497ffa98491e38` | password123 |
| `c82c1cd77fbd144003b1e476718f66ce` | 19900101 |
| `195d91be1e3ba6f1c857d46f24c5a454` | zhang123 |

---

## 数据库规格

| 项目 | 数值 |
|------|------|
| 记录总数 | 约 592 万条 |
| 文件大小 | 约 795 MB |
| 存储引擎 | SQLite 3 |
| 索引字段 | `hash`（PRIMARY KEY） |
| 单次查询耗时 | < 10ms |

---

## 注意事项

- `md5_rainbow.db` 体积较大，首次构建需要约 2 分钟
- Web 服务运行期间请保持终端窗口开启，关闭终端即停止服务
- AI 兜底查询依赖网络，响应时间约 3 秒
- 本项目仅用于学习和教学演示，请勿用于非法用途


