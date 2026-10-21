# 用 PyCharm 跑这个项目

完全不需要 VSCode。项目是纯 Python，任何 IDE 都能跑，PyCharm 反而更省事（解释器管理、运行配置都是图形化的）。

---

## 1. 打开项目

`File` → `Open` → 选**文件夹** `hybrid-agent-demo` → `OK`

> 一定要选文件夹，不要选单个 .py 文件。选错了目录树里就只有一两个文件，后面 import 会全红。

---

## 2. 配解释器（关键一步）

`File` → `Settings` → `Project: hybrid-agent-demo` → `Python Interpreter` → 右上角 `Add Interpreter`

### 路线 A：直接用这台机器上现成的（最快，依赖已装好）

`Add Interpreter` → `Existing` → 选：

```
C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe
```

选完直接能跑，不用装任何包。

### 路线 B：自己建一个干净的虚拟环境（推荐，可迁移）

`Add Interpreter` → `Virtualenv Environment` → `New`：

- Location: `<项目目录>\.venv`
- Base interpreter: `D:\Python\python 3.14\python.exe`
- 勾选 `Inherit global site-packages`（可选，不勾也行）

创建完成后，打开底部 `Terminal`（`Alt+F12`），执行：

```bash
pip install -r requirements.txt
```

> 如果装某个包时报"没有可用的 wheel"，说明 Python 3.14 太新，换成 3.13 再建环境。

---

## 3. 启动服务

在目录树里右键 `run_server.py` → `Run 'run_server'`（或 `Shift+F10`）

控制台出现：

```
服务地址： http://127.0.0.1:8080
INFO:     Uvicorn running on http://127.0.0.1:8080
```

点控制台里的蓝色链接，或浏览器手动输入 `http://127.0.0.1:8080`。

> 第一次跑时如果没有 `.env`，会自动进 MOCK 模式（回答是假的，但页面和记账都是真的），方便先看效果。

**停服务**：点控制台左侧的红色方块按钮。

---

## 4. 跑评测（产出报告要的表）

右键 `eval/run_eval.py` → `Modify Run Configuration...` → 把 `Working directory` 设为项目根目录 → `Run`

控制台会打印三策略对比表，并生成 `eval/result.csv`。

> 为什么必须设 Working directory：脚本用相对路径找测试集和数据库，工作目录错了就找不到文件。

---

## 5. 跑算力测算

右键 `tools/capacity_plan.py` → `Modify Run Configuration...`：

- `Working directory`: 项目根目录
- `Parameters`: `--gpu-tps 800`（换成你的实测值）

`Run` 之后控制台输出三阶段预算表。

---

## 6. 改配置（`.env`）

1. 目录树里右键 `.env.example` → `Copy` → 再 `Paste` → 重命名为 `.env`
2. 双击打开，改这几行：

```ini
CLOUD_BASE_URL=https://api.deepseek.com/v1
CLOUD_MODEL=deepseek-chat
CLOUD_API_KEY=sk-你的key
```

`.env` 会被 `python-dotenv` 自动读取，**不用**在运行配置里重复设置。

临时想用 MOCK 模式：Run Configuration → `Environment variables` 里加 `MOCK_MODE=1`。

---

## 7. 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| `import app.xxx` 标红，但能跑 | PyCharm 没把根目录当源码根 | 右键项目根 → `Mark Directory as` → `Sources Root` |
| `ModuleNotFoundError: fastapi` | 解释器选错了 | Settings 里确认 Interpreter 是你装了依赖的那个 |
| 页面打不开，控制台没报错 | 服务没启动或已停 | 看控制台是否还有 `Uvicorn running` |
| 端口 8080 被占用 | 上次的服务没关 | 控制台点红方块停掉，或改 `run_server.py` 里的端口 |
| 运行很慢、卡在 installing | 首次装包 | 等 1–2 分钟，正常 |

---

## 8. 提交代码前

`Settings` → `Version Control` 里确认 `.idea/` 已被忽略（项目自带 `.gitignore` 已包含）。
PyCharm 生成的 `.idea` 是本地配置，**不要**提交到 GitHub——老师看到一堆 IDE 配置会显得不专业。
