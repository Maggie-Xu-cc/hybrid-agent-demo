2026—2027 学年 第一学期 · 研究生课程

《人工智能技术科研应用实践》结课报告

面向中小规模AI应用的混合推理路由系统

＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿

学号：S202688173                   

姓名：徐牡姣

学院：计算机学院

专业：计算机技术

类型：实践                         

正文字数：3240

开源档位：工具级（系统级验证材料待补）

仓库链接：https://github.com/Maggie-Xu-cc/hybrid-agent-demo

提交日期：2026-11-30

指导教师评价

本页由学生填写信息区，评价区保持空白，由教师填写。

交前自检与自评

本页随报告一并提交（封面之后、正文之前）。提交前逐项打勾，并给自己的报告打个分。自评总分要与教师核定分比对：如实自评不吃亏，明显高估要扣分；判定规则见 8.4。

A　交前核对（12 项，全部打勾再交）

B　自评打分（勾出你走的那一轨，只填最后一列）

我走的是：□ 报告轨　☑ 实践轨（只勾一个；六项按所选这一轨的满分填）

我认为最可能被扣分的地方是：演示视频待补；外部使用者验证待补，当前 P5 按工具级上限自评。

自评总分：89

C　教师核定（学生不填）

问题与定位

1.1 研究环节与实际问题

本项目面向中小规模人工智能应用开发者，聚焦科研辅助系统从原型转为可用服务时的推理资源分配：短句翻译、格式转换与复杂代码分析混合到达，若全部调用强模型，简单任务也承担较高费用；若全部交给本地小模型，又可能损失专业任务的回答质量。项目与计算机技术专业的联系在于接口适配、服务编排、异常处理、实验评测和资源预算，而非训练新的基础模型。

本项目选择实践轨，沿用原“实践 B”自命题方向，交付 hybrid-agent-demo 端到端原型。核心问题是：在质量风险可追踪的前提下，规则与小模型路由能否降低调用估算费用，以及什么条件下值得自建推理服务。证据分为 P0 历史 GPU 实验与 P0.1 工程修订回归；二者分开记录，修订代码不回写历史实测指标。

1.2 需求与范围

系统处理单轮文本请求，提供规则优先、模型分类、长度兜底三级路由，本地作答后可升级云端，最后记录 token、延迟与估算成本。当前范围不包含多轮记忆、工具执行、检索增强或生产级服务承诺。虽然项目名含 Agent，实际实现是显式工作流编排；这一边界避免把普通路由组件描述为自主科研智能体。

如图 1 所示，系统由交互、编排、能力和数据四层组成。交付修订版的 Web、零依赖 HTTP 入口与统一评测脚本复用 app.agent.run，推理服务统一采用 OpenAI 兼容接口，SQLite 与 JSONL 分别保留状态和评测原始答案。历史旧评测脚本另行保留，不再作为新实验的主入口。

图 1 系统总体架构图 

现状与证据

2.1 文献与方案依据

FrugalGPT 将多模型级联用于成本控制[1]；RouteLLM 通过偏好数据学习模型选择[2]；Hybrid LLM 将预测难度与质量要求联合用于路由[3]。这些工作支持“按任务选模型”的技术方向[4][5]，却不能替代本项目在特定平台、价格和负载下的验证。本系统同时采用生成前路由与生成后升级，属于上述思想的轻量工程实现，不宣称提出新的路由理论。

推理服务侧，PagedAttention 与 SGLang 分别从显存管理和结构化程序执行优化服务效率[6][7]，行业报告也梳理了推理优化的工程实践[8]；Qwen2.5 与 Qwen2 技术报告提供模型能力与系列背景[9][10]。模型通用能力不等于本测试集的答案正确性。MT-Bench 与 Chatbot Arena 提醒评价应结合人类偏好并检查裁判偏差[11][12]，幻觉综述则说明流畅表达与事实可靠之间存在差距[13][14]。

AWQ 与 QLoRA 分别为量化推理及低成本微调提供候选路线[15][16]，偏好优化可作为后续收集人工反馈后的研究方向[17]；它们均未在本项目当前版本中实现。大模型综述用于界定训练、适配和推理部署的不同问题[18]，因此当前工作把资源投入可复现的推理链路，而非增加缺乏数据支持的训练环节。

2.2 实验材料与证据分层

原始材料包括 24 条测试集、AMD GPU 前向记录、最终混合策略逐请求 CSV 和全量三策略终端截图（见表 1）。表 1 区分各材料能支撑的结论，避免混用首次云端失败批次、最终连通批次与 MOCK 联调数据。最终 CSV 未保存完整答案和逐调用来源用量，不能据此补造质量评分或重建全部策略的逐条结果。

表 1 实验材料与可核验范围

主体论证

3.1 技术选型与实现边界

四组候选方案的对比见表 2。P0 采用规则加小模型，不依赖路由器训练，适合有限标注和受限环境；学习型路由在质量偏好数据充分时更有潜力。推理服务先以 transformers 实现协议适配，再用目标环境压测决定是否迁移 vLLM。规则覆盖率只用于描述决策来源，不代替关闭规则后的受控消融。

表 2 技术候选与选择理由

历史版规则先检查寒暄、超过 300 字的长文本及代码、推理强特征，短句无强特征时判 easy；未决时以 48 token 上限分类，失败按 120 字阈值兜底。交付修订版新增 SQL review、SELECT/FROM 结构检测，并保留分类格式失败前已消耗的 token。本地与云端默认输出上限为 768、1024，温度 0.3；8 条 GPU 前向实验另用 greedy、96 token 上限，两组结果不可直接互换。

app/agent.py 协调路由、生成、自检、升级和记账。P0 的 SQLite 为 13 字段；P0.1 以幂等迁移新增 8 字段，记录降级、升级尝试、升级失败、错误及本地/云端分项用量。升级成功后才置 escalated；两端均失败也落库；连接在事务结束后显式关闭。强制基线跳过路由器，统一评测保存三策略全部答案与状态，从实现层减少基线污染和评测漂移。

如图 2 所示，规则、模型和兜底依次判定，本地答案自检未通过时尝试升级云端；该设计参考级联路由研究[19][20]，并非逐项复现。升级尝试、成功和失败分开计数。图下注明的 17/24 与 7/24 仅指历史批次的决策来源，不能解释为 easy 占比或修订版重测结果。

图 2 路由决策与升级流程 历史来源占比与执行分支分开标注

3.2 环境与复现方法

历史 GPU 环境为 AMD AUP Learning Cloud，Radeon 8060S，运行时可见内存 64 GB、20 CU；Python 3.12.3、torch 2.9.1+rocm7.13.0、HIP 7.13.99004、transformers 4.57.6。本地模型 Qwen2.5-1.5B-Instruct 以 fp16 运行，云端为 deepseek-chat。64 GB 是运行时报告的可见内存，不等于本进程可独占的显存配额。

复现提供两条路径：已有 Python 3.10+ 时，设置 MOCK_MODE=1 后执行 python tools/serve_stdlib.py --port 8081，无需第三方包即可验证页面、路由与记账；FastAPI 入口作为可选部署。真实 GPU 评测需关闭 MOCK、配置有效端点和密钥，使用 eval/run_eval_unified.py --real。零依赖演示可在本机跑通，不等于完成外部使用者三十分钟验收。

2026 年 11 月 9 日的修订验证：29 项回归全部通过，覆盖分类失效计费、升级状态、双端失败、旧库迁移、4 线程 20 请求记账隔离、鉴权及 HTTP 接口；独立进程演示完成三个输入和统计核对；统一脚本完成 24×3 策略的 MOCK 联调。上述为工程验证，不作为新增 GPU 性能或语义质量证据，原始结果随源包保存。

外部使用者验证记录：________________（待作者补充）。演示视频：docs/demo.mp4（2分33秒，未超过 3 分钟）。

如图 3 所示，环境预检识别到 Python 3.12.3、torch 2.9.1+rocm7.13.0 及 HIP 7.13.99004，同时显示 vLLM 未安装，支持本次采用 transformers 服务封装的选型。

图 3 AUP 环境核验关键字段 原始截图转录

如图 4 所示，真实请求返回本地模型回答，输入 33、输出 26、总计 59 token，服务端延迟 2578 ms；同屏 GPU 利用率为 49%。这些值对应截图中的单次请求，不替代 8 条前向实验和 24 条混合评测的汇总结果。

图 4 真实推理响应与 GPU 状态 单次历史记录转录

3.3 对照结果与费用口径

三策略在同一 24 条自建样例上串行各执行一遍，见表 3。没有多轮重复、随机顺序或人工答案评分，结果仅描述该次运行。全本地与全云端汇总取自终端截图，混合行由最终 CSV 复算；截图记录 72 次策略请求均无降级和失败。“72 次”不是底层模型调用数，因为分类和升级会产生额外调用。

表 3 三策略对照结果 历史实测

如图 5 所示，柱状图同时比较三策略的估算费用和平均延迟，蓝色为混合策略。混合费用 0.071379 元由最终 CSV 加总，与原始汇总的四舍五入值 0.0714 元一致。本图属于 P0 历史批次；修订版的 MOCK 输出仅供工程联调，不混入本图。

图 5 三策略成本与延迟对比

混合路由准确率为 23/24，即 95.8%，规则层覆盖 17/24，即 70.8%；Wilson 95% 区间约 79.8%—99.3%，显示小样本不确定性。混合延迟中位数 1850 ms，最近秩法 P95 为 4513 ms。P95 基于 24 条样例，不能视作生产 SLA。路由准确率衡量难度分类，不衡量最终答案正确率。

费用按历史配置价格估算：本地 0.0028 元/千 token，云端输入 0.005、输出 0.015 元/千 token。本地价格来自 8 元/小时、假设 800 tok/s 的示例折算，不是按 APU 实测 32.6 tok/s 推出的租赁成本。因此 13.9% 只表示该价格情景下，相对独立全云端估算费用的下降；不代表 APU 自建总成本已下降。CSV 同 token 云端牌价为 0.083465 元，按它计算的费用比为 85.5%、下降为 14.5%，分母与独立全云端不同。

三支路分别为纯本地 11 条、直接云端 10 条、升级 3 条，费用合计依次为 0.004088、0.064907、0.002384 元。三次升级的总费用不能当作升级“额外成本”，因为缺少未升级时的反事实答案。云端与本地答案长短不同也会影响费用，因而不能把全部价差解释为相同质量下的效率提升。

如图 6 所示，左图展示历史决策来源，右图展示执行支路单条均价。均价按各支路费用合计除以请求数，保留六位小数；不同支路承担的任务和答案长度不同，因此移除把价差解释为模型单价优势的倍数箭头。

图 6 路由决策来源分布与各支路单条成本

3.4 回归验证与失败分析

SQL review 样例被模型层判成 easy，人工标签为 hard。规则中缺少 SQL 特征是可检查的入口缺口，分类模型也未识别专业风险；单例不足以断言问题仅在规则。GPU 原始回答还将 vLLM 展开为错误英文名称，将语言模型的 KV Cache 泛化为普通键值缓存，并在进程池任务中输出 ThreadPoolExecutor。此类答案可能足够长且不含“不确定”，能够绕过当前升级条件，证明启发式自检不是语义质量保证。

初轮云端鉴权失败曾被本地降级掩盖，因此失败批次不进入主比较。交付修订版已通过回归验证：分类非法 JSON/标签不丢已知用量；升级失败不算成功；降级与双端失败可追溯；旧库迁移不覆盖记录；强制基线不消耗分类调用。修订后的 SQL 规则仅验证了明确结构，不据此宣称泛化准确率提升；完整语义质量与并发 GPU SLA 仍待受控重测。

后续质量验收采用至少 200 条脱敏请求、冻结留出集、相同提示词和输出限制、交错重复运行；两位评阅者盲评事实、遵循和完整性，代码题结合可执行用例。报告质量分、关键错误率、P95、费用和失败状态，不用路由准确率替代答案正确率。详细协议与空白评分表随源包提供，当前不填造质量结果。

3.5 未来算力需求设计

容量设计改用服务需求模型，避免把 32.6 输出 tok/s 当作输入输出总吞吐。设活跃窗口 h=8 小时、峰值系数 k=5，本地生成比例 r=0.6，需分类比例 q=0.3，分类服务时间假设 t=0.05 秒，本地生成服务时间 s 待目标环境压测。峰值到达率 λ=N×k/(3600h)，单请求本地服务需求 τ=r×s+q×t，卡数 G=ceil(λτ/0.7)，生产阶段另加 1 卡冗余。

预算同时计入本地升级比例：假设本地请求中 20% 升级，则云端比例为 (1-r)+0.2r=0.52。以历史 600 输入、300 输出及配置单价算每次云端 0.0075 元，月费=G×4×8×30+N×30×0.52×0.0075。表 4 以日请求 50000、不同 s 做敏感性分析；s=0.5/1/3 秒均是假设，不是新的 GPU 测量值。

表 4 服务时间敏感性分析 日请求 50000 含冗余与升级费用

如图 7 所示，同一模型下绘制 0.5、1、3 秒本地服务时间假设及全云端曲线，显式计入活跃窗口、分类开销、升级和生产冗余。三个阶段的业务量为 500、5000、50000 次/日，完整情景 JSON 可由 capacity_plan_service.py 一条命令复算。曲线用于识别敏感参数，不把验证环境外推为采购承诺。

图 7 含分类与升级开销的成本敏感性曲线 服务时间均为假设

在日请求 50000 的情景中，只有 s=0.5 秒的假设出现 5.3% 估算节省；s=1 秒即高于全云端，说明收益取决于目标服务效率与升级比例。此前 7111 次/日的单卡回本点未同时满足容量约束，已不再作为结论。下一步应以目标硬件的服务时间分布、并发排队与 P95 校准该模型，并纳入运维和长期空闲费用。

反思与迁移

4.1 从跑通链路到验证边界

此前把“小模型更便宜”和“混合架构更省钱”联系得过于直接。原以为本地模型参数更少就应更快，现在依据同批次结果，本地 2858 ms 慢于云端 2067 ms；模型规模不能单独决定端到端延迟。以课程中的“端侧约束”理解这一变化，更需要同时检查共享内存、解码实现和排队方式，而不是把原因归结为某个品牌硬件。此前的单卡回本点同样需要接受容量约束，不能用一个漂亮数字代替资源设计。

4.2 AI 失效与工程失效的区别

实践记录中，huggingface_hub 下载失败而网络探活正常，最后改用 curl 获取权重；accelerate 缺失则通过显式迁移到 GPU 解决。这体现“环节分解”的必要性：分别检查网络、下载库、权重、加载和服务接口，才能定位失败。云端 401 被本地降级掩盖，则说明“有答案”不等于“按预定策略执行”，评测必须把模型来源、失败和升级结果单独保存。

更严重的边界来自原始 GPU 回答：小模型会以确定语气解释错误概念。按“评价不可形式化”的课程概念，答案长度与关键词只能检查形式，不能完整表达正确性、完整性和专业适用性。本项目优先选择可观测自检便于实现，但由此得到的质量承诺必须收缩。涉及代码与数学的输出，应增加可执行检查和人工核验；无法自动核验的回答，应保留原文和审核记录。

4.3 与文献对话及迁移动作

我同意幻觉综述[13]关于事实可靠性需要独立检测与评估的判断，原始回答为这一局限提供了直接案例。但这并不意味着所有请求都应走强模型：RouteLLM[2]与 RouteNLP[21]等模型路由研究表明路由值得研究，关键是把降本与质量一起验证。本项目暂时只有难度标签，尚不能复用文献中质量保持的结论；也不应让同一个生成模型独自担任裁判。MT-Bench 对裁判偏差的讨论[11]支持加入盲评和人工复核。

本次修订已补齐可追踪性与故障回归，后续计划为：11 月 22 日前扩充至少 200 条脱敏请求并双人标注；11 月 26 日前在目标独显完成 1、4、8 并发及同输出限制的重复对照；11 月 29 日前由一位未参与开发者独立运行并录制不超过三分钟的视频。实际提交时按执行记录更新状态。迁移到其他科研辅助系统时重新标定任务风险、质量标准和服务时间，保留协议与逐调用追踪，不直接复制当前阈值。

结论与后续

第一，项目已在 AMD GPU 完成真实模型推理与混合工作流预演，接口适配、路由、升级和费用记录构成可运行原型。第二，最终 24 条样例中路由准确率为 95.8%，相对独立全云端的估算费用约下降 13.9%，这一结果受小样本、输出长度和历史价格约束，尚不证明质量等价。第三，APU 实测可支持概念验证，生产选型必须依据目标环境的并发压测，当前不能确认整体盈亏平衡点。

交付包已补强异常可追踪、统一评测、零依赖演示和资源敏感性分析。当前按工具级材料自评，外部验证记录与视频链接留空，待作者真实补充；完成后按系统级完整清单重新核定。后续质量结论须建立在独立复用和受控评测上，不将计划作为已完成证据。

参考文献

[1] CHEN L, ZAHARIA M, ZOU J. FrugalGPT: how to use large language models while reducing cost and improving performance[J]. Transactions on Machine Learning Research, 2024.

[2] ONG I, ALMAHAIRI A, WU V, et al. RouteLLM: learning to route LLMs with preference data[C]//The Thirteenth International Conference on Learning Representations (ICLR). 2025.

[3] DING D, MALLICK A, WANG C, et al. Hybrid LLM: cost-efficient and quality-aware query routing[C]//The Twelfth International Conference on Learning Representations (ICLR). 2024.

[4] VARANGOT-REILLE C, BOUVARD C, CIANCONE M, et al. Doing more with less: a survey on routing strategies for resource optimisation in large language model-based systems[J]. Journal of Artificial Intelligence Research, 2026, 86. DOI: 10.1613/jair.1.19801.

[5] BEHERA A P, CHAMPATI J P, MORABITO R, et al. Towards efficient multi-LLM inference: characterization and analysis of LLM routing and hierarchical techniques[J]. arXiv preprint arXiv:2506.06579, 2025.

[6] KWON W, LI Z, ZHUANG S, et al. Efficient memory management for large language model serving with PagedAttention[C]//Proceedings of the 29th ACM Symposium on Operating Systems Principles (SOSP). 2023: 611-626.

[7] ZHENG L, YIN L, XIE Z, et al. SGLang: efficient execution of structured language model programs[C]//Advances in Neural Information Processing Systems 37 (NeurIPS). 2024: 62557-62583.

[8] 中国信息通信研究院. 大模型推理优化关键技术及应用实践研究报告（2026年）[R/OL]. 北京: 中国信息通信研究院, 2026[2026-10-21]. https://www.caict.ac.cn/kxyj/qwfb/ztbg/202604/t20260415_719838.htm.

[9] QWEN TEAM. Qwen2.5 Technical Report[EB/OL]. 2024. https://arxiv.org/abs/2412.15115.

[10] YANG A, YANG B, HUI B, et al. Qwen2 Technical Report[EB/OL]. 2024. https://arxiv.org/abs/2407.10671.

[11] ZHENG L, CHIANG W L, SHENG Y, et al. Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena[EB/OL]. 2023. https://arxiv.org/abs/2306.05685.

[12] CHIANG W L, ZHENG L, SHENG Y, et al. Chatbot Arena: An Open Platform for Evaluating LLMs by Human Preference[EB/OL]. 2024. https://arxiv.org/abs/2403.04132.

[13] HUANG L, YU W, MA W, et al. A Survey on Hallucination in Large Language Models: Principles, Taxonomy, Challenges, and Open Questions[EB/OL]. 2023. https://arxiv.org/abs/2311.05232.

[14] ZHANG Y, LI Y, CUI L, et al. Siren's Song in the AI Ocean: A Survey on Hallucination in Large Language Models[EB/OL]. 2023. https://arxiv.org/abs/2309.01219.

[15] LIN J, TANG J, TANG H, et al. AWQ: Activation-aware Weight Quantization for LLM Compression and Acceleration[EB/OL]. 2023. https://arxiv.org/abs/2306.00978.

[16] DETTMERS T, PAGNONI A, HOLTZMAN A, et al. QLoRA: Efficient Finetuning of Quantized LLMs[EB/OL]. 2023. https://arxiv.org/abs/2305.14314.

[17] RAFAILOV R, SHARMA A, MITCHELL E, et al. Direct Preference Optimization: Your Language Model is Secretly a Reward Model[EB/OL]. 2023. https://arxiv.org/abs/2305.18290.

[18] ZHAO W X, ZHOU K, LI J, et al. A Survey of Large Language Models[EB/OL]. 2023. https://arxiv.org/abs/2303.18223.

[19] MOSLEM Y, KACMAJOR M, NEDUMPOZHIMANA V, et al. Cluster, route, escalate: cascaded framework for cost-aware LLM serving[J]. arXiv preprint arXiv:2606.27457, 2026.

[20] KOTTE V. UCCI: calibrated uncertainty for cost-optimal LLM cascade routing[J]. arXiv preprint arXiv:2605.18796, 2026.

[21] GUO D, WU J, YIU S M. RouteNLP: closed-loop LLM routing with conformal cascading and distillation co-optimization[C]//Proceedings of the 64th Annual Meeting of the Association for Computational Linguistics (ACL), Industry Track. 2026.

附录 AI 使用声明

本次整理使用的 AI 工具包括 Codex、ChatGPT、DeepSeek 与 WorkBuddy。以下为涉及的 AI 辅助环节登记，正式提交时须与独立声明表保持一致。

表 5 AI 使用登记表

AI 生成内容占全文比例估计：约 50 %（沿用作者上一版估计；本次新增图形、代码和容量分析须经作者复核后更新比例。历史实测数据保留原始记录，不由 AI 改写。）

使用 AI 生成图表：□否    ☑是（注明：图 1、2、5、6、7 以带文本节点的 SVG 重绘；图 3、4 将历史截图关键字段绘成可复制文字的记录图，不是新实验。PDF 直接绘制文字与线条，原始 PNG 和 SVG 源文件随包保留。AI 还辅助代码修订、回归测试、容量情景计算和文字整理；历史 GPU 数据未改写，新增工程结果与历史实测分开登记。）

开源档位自评：□ 复现级  ☑ 工具级  □ 系统级  □ 不适用（外部验证与视频待作者补充，完成后重新核定）。

诚信声明：本报告的分析、结论与对策均由本人独立完成，所有引用真实可查；如有不实，愿承担学术不端责任。签名：徐牡姣    日期：2026-11-30