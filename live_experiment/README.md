# 授权效果评价与 Agent 恢复方案选择

本数据包记录真实在线 gpt-5.6-sol 经 Codex CLI 0.154.0 选择 MCP 工具的会话。通知服务为本地持久化模拟器，所有收件地址使用 example.invalid，不发送真实通知。24 个正式会话与 8 个追加故障恢复会话分别统计；pilot、连接测试和环境调试均不混入正式结果。

## 先看哪些文件

- `实验结果报告.md`：结果及解释，与另行交付的 Word 增补报告对应。
- `analysis.json`：独立离线重评分、分任务结果、匹配任务的评价偏好。
- `results.csv` / `results.json`：24 个主实验会话。
- `followup_results.json`：8 个探索性追加会话。
- `evaluator_disagreements.csv`：E0 与 E1 判断不同的逐条记录。
- `protocol.json` / `followup_protocol.json`：各阶段运行前本地冻结时间和源码 SHA256。并非第三方外部预注册。
- `runs/` / `followup_runs/`：每个会话的批准清单、持久效果账本、工具事件、模型最终回答与运行元数据。`public_events.jsonl` 保留公开工具动作和用量，排除 reasoning 类型事件。
- `third_party/idempotencybench/`：用于核对原内容匹配评价概念的固定公开代码及 MIT 许可；不是复现其已发表分数。

## 离线复核

Python 3.10 及以上，标准库即可。不需要模型权限或网络：

```powershell
python test_experiment.py
python analyze.py
```

`analyze.py` 不调用实验运行器的评分函数，而是从账本重新实现核心计数，并核对 CLI 公开工具调用与服务事件一一对应、冻结源码哈希、正式运行有效性以及结果文件。它支持原始 events.jsonl 和本包 public_events.jsonl。SHA256SUMS.json 对应打包时的静态快照；再次运行分析后同内容输出的排版或写入格式可能改变。

E0 要求每种批准内容至少出现一份且内容重复数为零；E0 加自报状态还要求 finish=completed；E1 要求每个必需批准效果实例恰好一次、授权及内容绑定正确、finish=completed。所有批准实例在本实验中均明确要求一次，不是可选额度。两种内容完全相同但合法要求两次的效果应当算两项。

正式准入规则是本套件内所有有效会话均通过所选评价。该规则预先写入协议，不是生产可靠性认证。六个结构任务各重复两次，不能据此估计生产发生率或跨模型显著性。

## 在线复跑

需自行具有可用 Codex CLI 登录和 `gpt-5.6-sol` 模型权限。包中不含认证文件。`experiment.py` 中的 BIN 是本机 CLI 的绝对位置，复跑者应在副本中改为自己的路径；`sys.executable` 自动用于本地服务。原协议用于核对原始结果，修改后的实验必须建立新的协议并保留改动记录。

将源码复制到新的空实验目录，不复制 runs、followup_runs、protocol.json、followup_protocol.json，先运行：

```powershell
python experiment.py pilot
python experiment.py main
python followup.py
python analyze.py
```

运行器会复用已有 run.json；不会自动覆盖已有完整会话或重复消耗额度。两个阶段依次运行，各自并发上限 2。工具写入仅在指定本地 MCP 服务中启用；模型内置 shell、浏览器、其他插件和多智能体功能关闭。其余配置及确切命令保存在每个会话 command.json。

模型精确后端快照、采样种子不可得；输入用量包括大量缓存命中。CLI 启动的模型别名不是可永久固定的模型版本。用量不是收费金额。

## 结论边界

这是合法重复要求下评价迁移有效性的先导案例。内容回执方案的错误由内容归并契约直接决定，不证明 LLM 自主重规划造成了身份漂移。真实模型轨迹能证明模型实际选择了批次、查询、重试或缩小剩余集合。脚本故障器只在提交后丢失回执，不替模型写出恢复动作。该数据尚未覆盖并发提交、迟到提交、真实供应商 API、动态新增或撤回授权、上下文压缩或多智能体交接。
