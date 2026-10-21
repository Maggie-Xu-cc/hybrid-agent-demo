# Hybrid Routing Agent

一个最小可用的**混合推理 Agent**：本地小模型处理简单请求，复杂请求自动升级到云端大模型，并把每次调用的 Token、延迟、成本都记下来。

> 课程 B 类（自命题型）工程实践：**proposal + 云上预演 demo + 未来算力需求设计**。
> 提案全文见 [PROPOSAL.md](PROPOSAL.md)。
> 核心不是"又一个聊天机器人"，而是回答一个问题：**在什么条件下，自建小模型 + 云端兜底比全部走 API 更划算？**

## 架构

```
                 ┌──────────────────────────────┐
   HTTP 请求 ──▶ │  FastAPI  (app/server.py)    │
                 └──────────────┬───────────────┘
                                ▼
                 ┌──────────────────────────────┐
                 │  路由 router.py              │
                 │  规则层 → 模型层 → 兜底层    │
                 └───────┬──────────────┬───────┘
                    easy │              │ hard
                         ▼              ▼
              ┌────────────────┐  ┌────────────────┐
              │ 本地 Qwen2.5-1.5B│  │ 云端大模型 API │
              │ transformers/ROCm│  │ OpenAI 兼容    │
              └───────┬────────┘  └───────┬────────┘
                      │  自检不通过 → 升级 │
                      └──────────┬────────┘
                                 ▼
                    ┌────────────────────────┐
                    │ 记账 store.py (SQLite) │
                    │ token / 延迟 / 成本     │
                    └────────────────────────┘
```

**设计要点**：本地推理服务与云端 API 都走 OpenAI 兼容协议，所以"路由"退化成一次 `base_url` 切换，不需要维护两套调用逻辑。平台镜像未提供 vLLM，本地服务由 transformers + 标准库 HTTP 自建（`deploy/local_server.py`，120 行），上层零改动。

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env          # 填入云端 API Key
python -m uvicorn app.server:app --host 0.0.0.0 --port 8080
```

`MOCK_MODE=1` 可以完全离线跑通（不需要 GPU、不需要 Key），用于先联调页面与记账逻辑。

打开 http://localhost:8080 即可对话。页面会实时显示本次请求走了哪条路、花了多少钱、比全云端省了多少。

本地模型的部署（AMD ROCm + transformers 自建 OpenAI 兼容服务）见 [docs/deploy.md](docs/deploy.md)。

## 云端实验：三条命令

```bash
python deploy/local_server.py  # 起 OpenAI 兼容本地服务（transformers，平台无 vLLM）
cp .env.example .env           # 改 LOCAL_MODEL / CLOUD_API_KEY / MOCK_MODE=0
python deploy/run_all.py       # 压测 + 三策略评测 + 算力重算 + 归档证据
```

`run_all.py` 会把所有产物写进 `docs/evidence/`，其中 `RESULTS.md` 是可直接抄进报告的汇总表。

## 算力需求测算

```bash
python tools/capacity_plan.py --gpu-tps 800 --easy-ratio 0.6 --price 4
```

输出三阶段（概念验证 / 试点 / 推广）的卡数、月度 GPU 成本、云端兜底成本与盈亏平衡点，可直接贴进报告的"未来算力需求设计"章节。

吞吐用实测值，别拍脑袋：

```bash
python tools/bench_throughput.py --concurrency 1,4,8 --num-prompts 16
# 最后一行 SUGGESTED_GPU_TPS=<n>，把它填进 capacity_plan.py 的 --gpu-tps
```

## 路由策略

三层，逐层降本：

| 层 | 触发条件 | 成本 | 覆盖场景 |
|---|---|---|---|
| 规则层 | 代码块 / 数学符号 / 超长文本 / 纯寒暄 | 0 | 实测 70.8% 请求 |
| 模型层 | 规则不确定时，本地模型输出 JSON 分类 | 约 30 token | 中间地带 |
| 兜底层 | 分类失败时按长度阈值 | 0 | 极少数 |

另有一层**质量自检**：本地答案过短或包含"不确定"类表述时，自动升级到云端重答，并单独计数。

## 实验结果

> 24 条自建测试集，云端全连通条件下实测（`python eval/run_eval_stdlib.py` 可复现），72 次调用零降级、零失败。

| 策略 | 平均延迟 | 总成本 | 相对全云端 | 路由准确率 | 升级次数 |
|---|---|---|---|---|---|
| 全本地 | 2858 ms | ¥0.0151 | 18.2% | — | 0 |
| 全云端 | 2067 ms | ¥0.0829 | 100% | — | 0 |
| 混合路由 | 2165 ms | ¥0.0714 | **86.1%** | **95.8%** | 3 |

## 成本模型

```
本地成本 = (输入+输出 token) / 1000 × 单价_local
云端成本 = 输入 / 1000 × 单价_in + 输出 / 1000 × 单价_out
基线成本 = 同样 token 全部按云端价计算
节省比例 = 1 - 实际成本 / 基线成本
```

本地单价不是 0：按"24GB 卡 ¥8/小时 ÷ 实测吞吐"折算，这样对比才诚实。参数见 `.env`。

## 算力说明

本地推理服务部署于 **AMD 云端 GPU**（ROCm + transformers 自建服务；vLLM 因平台镜像未提供，列为换卡后的迁移目标），部署命令、显存占用、压测数据见 [docs/deploy.md](docs/deploy.md)。

## 目录结构

```
app/
  config.py    环境变量
  clients.py   OpenAI 兼容客户端（本地/云端）+ 离线 mock
  router.py    三层难度路由
  agent.py     主流程 + 质量自检 + 记账
  store.py     SQLite 记录与统计
  server.py    FastAPI 服务
web/index.html 演示页面
eval/
  testset.jsonl  标注测试集
  run_eval.py    三策略对比
tools/
  capacity_plan.py   算力需求测算（三阶段预算）
  bench_throughput.py 并发压测（测单卡 tok/s）
deploy/
  start_vllm.sh  环境判定 + 下权重 + 起 vLLM（换独立显卡后的备用脚本）
  run_all.py     一键采集：压测 + 评测 + 算力重算 + 归档
docs/deploy.md   AMD ROCm 部署手册
docs/evidence/   云端实测证据（截图、压测、结果汇总）
PROPOSAL.md      提案（问题 / 路线 / 规划 / 算力设计）
```

## License

MIT
