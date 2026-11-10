# AUP Learning Cloud · GPU 推理实测记录

- 采集时间：2026-10-20 04:09:57
- 模型：`/home/jovyan/models/qwen2.5-1.5b`（fp16，device_map=cuda）
- torch：2.9.1+rocm7.13.0　HIP：7.13.99004-3309c6114a
- GPU：Radeon 8060S Graphics　显存 64.0 GB　CU 20
- 权重加载耗时：1.4s　峰值显存：**2.99 GB**
- 单请求最大生成 96 token，greedy 解码

## 逐条结果

| # | 标注 | 输入tok | 输出tok | 延迟(ms) | tok/s | 回答（截断） |
|---|---|---|---|---|---|---|
| 1 | easy | 33 | 56 | 5366 | 10.4 | 您好！我是阿里云开发的一款超大规模语言模型，我叫通义千问。我可以回答各种问题、创 |
| 2 | easy | 38 | 8 | 226 | 35.4 | "Today's weather is nice." |
| 3 | easy | 38 | 96 | 2672 | 35.9 | REST（Representational State Transfer）API |
| 4 | easy | 33 | 96 | 2660 | 36.1 | KV Cache 是一种基于键值对的缓存技术，它将数据存储在内存中，并通过哈希函 |
| 5 | hard | 54 | 96 | 2682 | 35.8 | 在Python中，`queue.Queue` 是一个线程安全的任务队列，而 `c |
| 6 | hard | 63 | 96 | 2677 | 35.9 | 在处理大数据集时，SQL查询的性能可能会受到多种因素的影响。对于你的特定查询 ` |
| 7 | hard | 48 | 96 | 2673 | 35.9 | VLLM（Virtual Language Learning Machine）和 |
| 8 | hard | 61 | 96 | 2686 | 35.7 | 要证明在 \( n \) 个元素的数组上，任何基于比较的排序算法最坏情况至少需要 |

## 汇总

- 平均吞吐：**32.6 tok/s**
- 平均延迟：**2705 ms**
- 峰值显存：**2.99 GB**

## 结论口径（直接写进报告）

> P0 预演已在 AUP Learning Cloud 的 AMD GPU（ROCm）上完成模型前向推理实测：模型 `/home/jovyan/models/qwen2.5-1.5b`，峰值显存 2.99 GB，平均吞吐 32.6 tok/s，平均延迟 2705 ms。
> 生产形态的 vLLM 服务化部署与并发压测因平台单次会话时长限制未完成，列为 P1 任务。

## 附：原始 JSON

```json
{
  "env": {
    "torch": "2.9.1+rocm7.13.0",
    "hip": "7.13.99004-3309c6114a",
    "gpu_available": true,
    "gpu_name": "Radeon 8060S Graphics",
    "gpu_mem_gb": 64.0,
    "gpu_cu": 20,
    "transformers": "4.57.6"
  },
  "load_s": 1.38,
  "peak_gb": 2.99,
  "avg_tps": 32.6,
  "avg_latency_ms": 2705,
  "rows": [
    {
      "q": "你好，请介绍一下你自己",
      "gold": "easy",
      "answer": "您好！我是阿里云开发的一款超大规模语言模型，我叫通义千问。我可以回答各种问题、创作文字和代码、撰写报告等，并且还能进行多轮对话。如果您有任何问题或需要帮助，请随时告诉我，我会尽力提供支持。",
      "latency_ms": 5366,
      "in_tokens": 33,
      "out_tokens": 56,
      "tok_per_s": 10.4
    },
    {
      "q": "把「今天天气不错」翻译成英文",
      "gold": "easy",
      "answer": "\"Today's weather is nice.\"",
      "latency_ms": 226,
      "in_tokens": 38,
      "out_tokens": 8,
      "tok_per_s": 35.4
    },
    {
      "q": "REST API 和 RPC 最核心的区别是什么？",
      "gold": "easy",
      "answer": "REST（Representational State Transfer）API和RPC（Remote Procedure Call）都是用于远程调用的协议，它们在设计上有一些关键区别：\n\n1. **数据传输方式**：\n   - REST API 使用HTTP请求进行数据传输。它通过URL来标识资源，并使用标准的HTTP方法（如GET、POST、PUT等）来进行操作。\n   - RPC则通常使用二进制格式的数据传输，例如JSON-RPC或gRPC。\n\n2",
      "latency_ms": 2672,
      "in_tokens": 38,
      "out_tokens": 96,
      "tok_per_s": 35.9
    },
    {
      "q": "什么是 KV Cache？",
      "gold": "easy",
      "answer": "KV Cache 是一种基于键值对的缓存技术，它将数据存储在内存中，并通过哈希函数进行快速查找和更新。这种设计使得 KV Cache 可以提供高并发、低延迟的数据访问性能。\n\nKV Cache 的主要特点包括：\n\n1. 高效性：KV Cache 通常使用高效的哈希算法来实现，可以快速地找到所需的键值对。\n\n2. 快速响应：由于数据都在内存中",
      "latency_ms": 2660,
      "in_tokens": 33,
      "out_tokens": 96,
      "tok_per_s": 36.1
    },
    {
      "q": "用 Python 写一个带超时控制的进程池，并解释任务队列为什么用 deque 而不是 list",
      "gold": "hard",
      "answer": "在Python中，`queue.Queue` 是一个线程安全的任务队列，而 `collections.deque` 是一个双端队列。当使用 `Queue` 作为任务队列时，如果需要处理大量数据并且希望避免阻塞，则可以设置超时时间来限制任务执行的时间。\n\n下面是一个带有超时控制的进程池的例子：\n\n```python\nfrom concurrent.futures import ThreadPoolExecutor, as_completed\nimport time\n\ndef task(n):",
      "latency_ms": 2682,
      "in_tokens": 54,
      "out_tokens": 96,
      "tok_per_s": 35.8
    },
    {
      "q": "分析下面这段 SQL 在大表上很慢的原因：SELECT * FROM orders WHERE DATE(created_at) = '2024-01-01'",
      "gold": "hard",
      "answer": "在处理大数据集时，SQL查询的性能可能会受到多种因素的影响。对于你的特定查询 `SELECT * FROM orders WHERE DATE(created_at) = '2024-01-01'`，以下是一些可能影响其性能的因素和原因：\n\n### 1. 数据库索引\n- **问题**：如果 `created_at` 列没有适当的索引，数据库将不得不扫描整个表来查找符合条件的行。\n- **",
      "latency_ms": 2677,
      "in_tokens": 63,
      "out_tokens": 96,
      "tok_per_s": 35.9
    },
    {
      "q": "对比 vLLM 与 Ollama 在吞吐和显存管理上的设计差异",
      "gold": "hard",
      "answer": "VLLM（Virtual Language Learning Machine）和Ollama都是大型语言模型，它们在吞吐量和显存管理上有一些不同的设计差异。以下是一些主要的比较：\n\n1. **吞吐量**：\n   - VLLM的设计目标是提供高吞吐量，以支持实时交互和大规模并发请求。它可能采用多线程或并行计算技术来提高处理速度。\n   - Ollama则更注重性能",
      "latency_ms": 2673,
      "in_tokens": 48,
      "out_tokens": 96,
      "tok_per_s": 35.9
    },
    {
      "q": "证明：在 n 个元素的数组上，任何基于比较的排序算法最坏情况至少需要 Ω(n log n) 次比较",
      "gold": "hard",
      "answer": "要证明在 \\( n \\) 个元素的数组上，任何基于比较的排序算法最坏情况至少需要 \\( \\Omega(n \\log n) \\) 次比较，我们可以使用拉格朗日插值定理和信息论中的熵来分析。\n\n### 方法一：拉格朗日插值定理\n\n1. **定义**：\n   - 设 \\( f(x) \\) 是一个单调递增或递减的函数",
      "latency_ms": 2686,
      "in_tokens": 61,
      "out_tokens": 96,
      "tok_per_s": 35.7
    }
  ]
}
```