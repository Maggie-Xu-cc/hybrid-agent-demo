# Hybrid Routing Agent

一个最小可用但完整闭环的**混合推理 Agent**：本地小模型处理简单请求，复杂请求自动升级到云端大模型，并把每次调用的 Token、延迟与成本逐条记账，回答"**在什么条件下，自建小模型 + 云端兜底比全部走 API 更划算？**"

## 这是什么

面向中小规模 AI 应用（内部工具、科研辅助系统、低-中流量在线服务）的**成本感知推理网关**。真实业务的请求分布高度偏斜：大量请求是"翻译一句话""格式转换""解释名词"这类简单任务，只有少部分需要多步推理，但两类请求按同样的单价计费。本项目把"按难度分配算力"做成一个可运行、可复现、可开源的端到端原型。

**功能特性**：

- 三层难度路由：规则层（零成本）→ 模型分类层（约 30 token）→ 长度兜底层（零成本），逐层降本
- 质量自检与升级：本地答案过短或含"不确定"类表述时，自动升级云端重答并单独计数
- Token 级记账：每次调用记录输入/输出 token、延迟、实际成本、反事实基线成本与节省比例，逐条落 SQLite
- 反事实成本基线：节省比例不是拍出来的，由逐条记录按同一公式累加复算，可审计
- 双链路对照：全本地 / 全云端 / 混合路由三策略在同一测试集上可比
- Web 演示页面：实时显示本次请求走了哪条路、花了多少钱、比全云端省了多少

> 课程工程实践（自命题）交付：proposal + AMD 云端 GPU 部署预演 + 未来算力需求设计。提案全文见 [PROPOSAL.md](PROPOSAL.md)。

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
              │ 本地 Qwen2.5    │  │ 云端大模型 API │
              │ transformers/ROCm│  │ OpenAI 兼容    │
              └───────┬────────┘  └───────┬───────┘
                      │  自检不通过 → 升级 │
                      └──────────┬────────┘
                                 ▼
                    ┌────────────────────────┐
                    │ 记账 store.py (SQLite) │
                    │ token / 延迟 / 成本     │
                    └────────────────────────┘
```

**设计要点**：本地推理服务与云端 API 都走 OpenAI 兼容协议，所以"路由"退化成一次 `base_url` 切换，不需要维护两套调用逻辑。AMD 平台镜像未提供 vLLM，本地服务由 transformers + 标准库 HTTP 自建（`deploy/local_server.py`，120 行），上层零改动。

## 怎么装

环境要求：Python 3.10+；本地推理需要 ROCm/HIP 栈的 AMD GPU（云端实验环境：Radeon 8060S，ROCm 7.13，torch 2.9.1+rocm）；离线联调不需要 GPU。

```bash
pip install -r requirements.txt
cp .env.example .env          # 填入云端 API Key
```

`.env` 关键配置项：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `MOCK_MODE` | `0` | 置 `1` 完全离线跑通（不需要 GPU、不需要 Key），用于联调页面与记账 |
| `LOCAL_MODEL` | `Qwen2.5-7B-AWQ` | 本地模型；云端实验用 `.env` 指定实际加载的模型 |
| `CLOUD_BASE_URL` | `https://api.deepseek.com/v1` | 云端 OpenAI 兼容地址 |
| `CLOUD_MODEL` | `deepseek-chat` | 云端模型名 |
| `CLOUD_API_KEY` | 空 | 云端密钥，必填（MOCK_MODE 下可不填） |
| `PRICE_CLOUD_IN_PER_1K` | `0.005` | 云端输入单价（元/千 token），对齐 DeepSeek 牌价 |
| `PRICE_CLOUD_OUT_PER_1K` | `0.015` | 云端输出单价（元/千 token） |

## 怎么跑

**① 起服务（含离线模式）**

```bash
# 离线联调：不需要 GPU 和 Key
MOCK_MODE=1 python -m uvicorn app.server:app --host 0.0.0.0 --port 8080

# 真实模式：本地模型 + 云端兜底
python -m uvicorn app.server:app --host 0.0.0.0 --port 8080
```

打开 http://localhost:8080 即可对话。HTTP 接口：

| 接口 | 方法 | 说明 |
|---|---|---|
| `/api/chat` | POST | 主对话接口，返回答案 + 路由来源 + 成本明细 |
| `/api/stats` | GET | 累计记账统计（调用数、节省比例、各支路分布） |
| `/api/clear` | POST | 清空会话 |
| `/healthz` | GET | 健康检查 |

**② 本地模型部署（AMD ROCm）**

```bash
python deploy/local_server.py    # 起 OpenAI 兼容本地服务（transformers 自建）
python tools/preflight_stdlib.py # 环境预检：Python/torch/HIP 版本与 GPU 识别
```

完整部署手册（权重下载、显存占用、常见报错）见 [docs/deploy.md](docs/deploy.md)。

**③ 云端实验一键采集**

```bash
cp .env.example .env             # 改 LOCAL_MODEL / CLOUD_API_KEY / MOCK_MODE=0
python deploy/run_all.py         # 压测 + 三策略评测 + 算力重算 + 归档证据
```

`run_all.py` 把所有产物写进 `docs/evidence/`，其中 `RESULTS.md` 是可直接引用的汇总表。评测复现（三策略各跑一遍 24 条测试集）：

```bash
python eval/run_eval_stdlib.py
```

**④ 算力需求测算**

```bash
# 先实测单卡吞吐，别拍脑袋
python tools/bench_throughput.py --concurrency 1,4,8 --num-prompts 16
# 最后一行 SUGGESTED_GPU_TPS=<n>，填进下面的 --gpu-tps

python tools/capacity_plan.py --gpu-tps 800 --easy-ratio 0.6 --price 4
```

输出三阶段（概念验证 / 试点 / 推广）的卡数、月度 GPU 成本、云端兜底成本与盈亏平衡点。

## 效果如何

24 条自建测试集（`eval/testset.jsonl`），云端全连通条件下实测，72 次调用零降级、零失败：

| 策略 | 平均延迟 | 总成本 | 相对全云端 | 路由准确率 | 升级次数 |
|---|---|---|---|---|---|
| 全本地 | 2858 ms | ¥0.0151 | 18.2% | — | 0 |
| 全云端（基线） | 2067 ms | ¥0.0829 | 100% | — | 0 |
| **混合路由** | 2165 ms | ¥0.0714 | **86.1%** | **95.8%**（23/24） | 3 |

**指标定义**：

- **路由准确率**：与人工标注的 easy/hard 标签一致的请求比例。n=24，Wilson 95% 区间约 79%–99%，小样本下仅供方向判断
- **相对全云端**：混合策略总成本 ÷ 全云端总成本，费用按配置单价估算
- **规则层覆盖率**：实测 70.8%（17/24）请求被零成本规则层直接处理；三支路分布为纯本地 11 条、直接云端 10 条、升级 3 条

**成本模型**（与记账逐条对应，可由 `/api/stats` 复算）：

```
本地成本 = (输入+输出 token) / 1000 × 单价_local
云端成本 = 输入 / 1000 × 单价_in + 输出 / 1000 × 单价_out
基线成本 = 同样 token 全部按云端价计算
节省比例 = 1 - 实际成本 / 基线成本
```

本地单价不是 0：按"24GB 卡 ¥8/小时 ÷ 实测吞吐"折算为 0.0028 元/千 token（输入输出同价），这样对比才诚实。参数见 `.env`。

单条真实请求实测样例：输入 33 / 输出 26 token，服务端延迟 2578 ms，GPU 利用率截图见 `docs/evidence/`。

## 部署说明

本地推理服务部署于 **AMD 云端 GPU**（Radeon 8060S，ROCm 7.13）：

1. `tools/preflight_stdlib.py` 预检运行时（Python 3.12 / torch 2.9.1+rocm / HIP 版本与 GPU 识别）
2. `deploy/local_server.py` 用 transformers 自建 OpenAI 兼容服务（平台镜像无 vLLM；换独立显卡后可用 `deploy/start_vllm.sh` 迁移 vLLM + AWQ 4bit）
3. `deploy/run_all.py` 一键压测、评测、算力重算并归档证据到 `docs/evidence/`

## 已知问题与局限

如实列出，按影响排序：

1. **规则层特征缺口**：SQL review 样例被模型层判成 easy（人工标注 hard），规则中缺少 SQL 特征；这是可检查的入口缺口，修复已列入后续计划
2. **分类失败漏记账**：模型分类失败走兜底的场景，路由来源与升级状态字段记录不完整，待修复
3. **鉴权回落污染汇总**：初轮云端鉴权失败曾回落本地，让"全云端"汇总看似完整；最终批次在修复鉴权后重跑，初轮结果不进入主比较，但当前代码对回落场景的提示仍不够醒目
4. **吞吐受限**：transformers 朴素解码相对 vLLM 连续批处理有 3–5 倍差距，是平台镜像约束而非模型上限；换卡后应迁移 vLLM + AWQ 4bit
5. **容量脚本是情景计算不是采购结论**：`capacity_plan.py` 顶层会额外加一张冗余卡（复核后应为 70 卡而非此前误记的 71 卡），且 800 tok/s 是目标环境假设值，正式容量决策必须用目标环境压测值重算
6. **评测规模小**：24 条自建样例、单轮、无多轮重复与人工答案评分，结果仅描述该次运行，不外推

## 外部使用者验证记录

> 系统级开源档位要求至少 1 位外部使用者独立跑通并反馈。记录模板如下，跑通后填写：

| 日期 | 使用者（姓名/标识） | 环境 | 跑通的命令 | 反馈摘要 |
|---|---|---|---|---|
| 待填 | 待填 | 待填 | 待填 | 待填 |

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
  testset.jsonl       标注测试集（24 条）
  run_eval.py         三策略对比
  run_eval_stdlib.py  标准库版评测（云端实测用）
tools/
  preflight.py         环境预检
  preflight_stdlib.py  标准库版环境预检
  bench_throughput.py  并发压测（测单卡 tok/s）
  bench_stdlib.py      标准库版压测
  capacity_plan.py     算力需求测算（三阶段预算）
deploy/
  local_server.py  transformers 自建 OpenAI 兼容服务
  start_vllm.sh    环境判定 + 下权重 + 起 vLLM（换独立显卡后的备用脚本）
  run_all.py       一键采集：压测 + 评测 + 算力重算 + 归档
docs/deploy.md     AMD ROCm 部署手册
docs/evidence/     云端实测证据（截图、压测、结果汇总）
PROPOSAL.md        提案（问题 / 路线 / 规划 / 算力设计）
```

## License

MIT
