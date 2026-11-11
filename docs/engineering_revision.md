# 工程修订与证据边界

日期：2026-11-09。本次修订在交付源包副本中完成，尚未替作者推送远程仓库，未改动D盘原项目。

## 已修复

1. 模型分类返回非法JSON或非法标签时，保留该次已知输入输出token，再按长度兜底。
2. 升级状态分为attempted、succeeded（escalated）、failed。云端升级失败时保留本地答案，不计为升级成功。
3. SQLite新增8个字段至21字段，保存降级、升级尝试/失败、错误和本地/云端分项用量；旧库可幂等迁移，不覆盖旧记录。
4. SQLite连接以contextmanager保证提交/回滚后关闭，修复Windows文件句柄占用。
5. 强制全本地/全云端基线跳过路由器，避免基线被分类调用污染。
6. 对SQL review与SELECT/FROM等结构加保守规则；普通“什么是SQL”不因SQL词本身强制升级。
7. 客户端支持标准库HTTP回退，统一评测脚本复用app.agent，不再复制一套编排实现。
8. 增加标准库本机HTTP演示服务，无需安装FastAPI/OpenAI SDK即可在MOCK模式跑通。

## 本次验证

`python tests/test_regression.py`执行29项：非法分类计费、升级成功/失败、双提供方失败落库、旧库迁移、4线程20请求独立记账、鉴权头和HTTP接口等。结果见docs/evidence/revision/regression_summary.json。

`python tools/smoke_demo.py`启动独立服务进程，经回环HTTP完成3个输入及统计核对。耗时仅代表当前已具备Python环境的自检，不等于陌生使用者安装，不等于真实GPU延迟。

`python eval/run_eval_unified.py --mock`验证24条×3策略的统一链路。所有答案与失败状态均写入JSONL。MOCK路由分类并非真实模型能力，不能将其准确率、费用或延迟写成新GPU实验结果。

## 历史与修订指标不得混写

历史GPU批次仍为23/24路由准确、混合估算费用0.071379元；本次修订没有重跑GPU或付费云端，不回写历史数据，不声称语义质量已提高。

`eval/run_eval_stdlib.py`、`eval/run_eval.py`保留用于追溯历史实现。新对照实验使用`eval/run_eval_unified.py --real`，运行前确认授权密钥、预算和MOCK关闭。分类/升级占用资源、云端与本地出错后的未知用量仍需与供应商账单核对。

外部使用者验证记录：李晓慧（未参与开发者），2026-11-10，Windows 11 / Python 3.12，main@5b41886；29 项回归 OK、MOCK 下简单/复杂请求路由正确、统计落库正常，全程约 20 分钟，仅验证工程链路。
演示视频：`docs/demo.mp4`（2分33秒）
