# 不同工具契约下 LLM Agent 非幂等操作失败恢复的决策边界研究

《海洋数据挖掘技术》课程研究的代码、真实模型实验记录、原创图表、AI协作对话和最终报告。研究链条为：先校准恢复方案的评价单位，再检验工具契约可见性下的恢复选择，最后用正确动作不同的匹配任务辨别简单重试规则与条件决策。

**[最终课程报告 PDF](report/final_report.pdf)** · [报告文本](report/final_report.md) · [完整可见AI协作对话](chat/完整AI协作聊天记录.md) · [复现说明](REPRODUCIBILITY.md)

## 五类交付材料

| 材料 | 位置与内容 |
|---|---|
| 完整实验代码 | `live_experiment/`、`contract_recovery/`、`contract_boundaries/`；含工具服务、运行器、提示、评分、冻结协议及离线分析 |
| 原始结果及图表 | 各阶段的 `runs/`、第一阶段 `followup_runs/`、第三阶段 `replacement_runs/`；`figures/`提供作者指定Fig目录中的8张PNG原图 |
| 环境和复现 | 本文件、`REPRODUCIBILITY.md`、`environment/`、`requirements*.txt`、`scripts/verify.py`与`scripts/prepare_online.py` |
| 完整AI协作聊天记录 | `chat/完整AI协作聊天记录.md`，从本聊天首次研究请求至导出截点逐条保存用户与助手可见发言；索引及范围见`chat/export_metadata.json` |
| 最终课程报告 | `report/final_report.pdf`是作者本次指定的24页PDF，字节级原样复制；Markdown为该PDF的逐页文字提取 |

## 实验与主要结果

原在线执行使用Codex CLI 0.154.0、模型别名`gpt-5.6-sol`、reasoning effort `low`。各阶段均为本地模拟通知服务，未发送真实邮件。模型精确后端快照与采样种子不可得，不能承诺未来在线复跑得到相同回答。

| 阶段 | 有效会话 | 回答的问题 | 本套件结果与边界 |
|---|---:|---|---|
| 一：评价有效性 | 24主实验+8探索性追加 | 评价单位会不会改变恢复方案选择？ | 内容评价与授权效果实例评价给出相反方案判断；全部分歧位于合法多份要求，未证明独立的调用划分测量偏差 |
| 二：契约可见性 | 18 | 模型能否依据明确契约恢复或停止？ | 18/18按可见信息处理，6个有证据完成、12个正确保留未决；可恢复条件共享原样重试，存在规则捷径 |
| 三：细粒度边界 | 12 | 不同缓存、期限与查询保证下是否改变动作？ | 12/12符合动作及最终状态边界；9完成、3必要未决。完整契约参考规则同样12/12 |

合计**62个有效会话、63次正式及补跑尝试**。第三阶段原始12次中11有效，另1次工具完成后响应流中断，原记录保留，按单独协议同条件补跑1次。`results.json`不覆盖原异常；最终统计同时读取`replacement_runs/e04`。pilot、连接调试、规则重放和隐藏世界结算不算新增模型样本，三个阶段也不汇总为同一个“总准确率”。

本研究新增的是这套本地实验设计与轨迹证据，未提出新幂等算法。正确选择依赖工具兑现契约；它不构成模型自身提供恰好一次效果保障、理解所有契约字段、优于完整确定性规则或适用于生产系统的证明。早期对话中的设想和暂定判断应与最终审计结论区分。

## 快速离线核验

Python 3.10+标准库即可核验三阶段实验，不需要登录或网络，也不产生新模型调用：

```bash
python scripts/verify.py
```

脚本核对文件清单、原协议源码哈希，运行第一阶段测试、重评分与测量审计，以及第二、三阶段的服务检查与独立分析。结果写入被Git忽略的`verification/latest.json`；本次发布前执行记录在`verification/offline_checks.json`。

原始会话中保存了`prompt.txt`、`command.json`、`run.json`、`state.json`、`answer.txt`（若产生）、`stderr.log`和排除内部推理事件的`public_events.jsonl`。异常会话没有最终回答文件属于原始事实，不补写模型回答。

## 图表与报告版本

`figures/1.png`至`8.png`为作者最新指定的Fig目录原文件，未经重绘或数值修正；文件编号、尺寸和SHA256见`report/figure_manifest.json`。本次仅提供8张独立PNG，最终PDF中图9未另提供独立文件。历史矢量图可从Git历史查看。

`report/provenance.json`记录最终PDF的SHA256与版本来源。`authoring/`仍保留作者修改前的报告写作与制图源文件，不能逐字重建最终PDF或这8张替换图。最终报告以`report/final_report.pdf`为准。23篇研究论文的固定版本、作者、时间、阅读范围及URL仍见`report/references_verified.json`。

## AI协作记录范围

对话Markdown保留本课题当前聊天中用户问题、助手进度和最终回答的原始顺序，包括后来被修正的判断、工具受阻及研究收敛过程，不以摘要冒充完整记录。仅去除机器环境包、系统/开发者指令、内部推理和工具协议，将本机用户目录及登录验证码替换为占位符。不导出其他聊天；截点之后的发言不在快照中。实验公开工具轨迹单独完整保存于各会话文件夹。

上游IdempotencyBench的固定代码与MIT许可保存在`live_experiment/third_party/idempotencybench/`，用途与出处见[第三方说明](THIRD_PARTY_NOTICES.md)。本仓库未包含论文全文、课程PPT、原本科毕设文稿或任何登录文件。
