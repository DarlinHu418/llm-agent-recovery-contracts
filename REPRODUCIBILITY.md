# 运行环境和复现说明

## 离线复核原始实验

Python 3.10及以上即可，仅用标准库。不要先修改被冻结的原运行器和提示；`protocol.json`、`followup_protocol.json`及`retry_protocol.json`中的源码哈希用于检查既有证据。仓库目录关系应保留，后两个阶段导入相邻`live_experiment/`以复用CLI命令构建。

```bash
python scripts/verify.py
```

也可分别执行：

```bash
cd live_experiment
python test_experiment.py
python analyze.py
python audit_measurement.py
cd ../contract_recovery
python run.py check
python analyze.py
cd ../contract_boundaries
python run.py check
python analyze.py
```

分析脚本会重写相应汇总JSON/CSV，本地服务检查仅操作临时模拟状态，不访问外部业务工具。上述步骤没有LLM调用，不是重做在线实验。提交中的`SHA256SUMS.json`为发布文件快照，原证据包自己的清单另行保留。

Windows宿主有时会在临时状态的原子文件替换时出现短暂WinError 5。统一验证脚本仅在Windows下使用`scripts/offline_bootstrap.py`对该错误最多重试10次，每次50 ms，并在日志中报告重试次数；持续失败仍直接报错。此兼容层只作用于离线子进程，不改冻结源码、原始会话或在线运行器。其他系统直接执行原脚本。宿主文件权限问题不计作模型失败。

第一阶段读取24个`runs`和8个`followup_runs`；第二阶段读取18个`runs`；第三阶段先保留12个原始`runs`，再按独立协议对有效性不足的e04使用`replacement_runs/e04`，最终为12有效、13次尝试。不得把异常移除后仍称仅运行了12次。

## 图与文档工具

实验复核不需要安装文档、绘图库。需要重建图时，另建虚拟环境并安装可选依赖：

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\python.exe -m pip install -r requirements-authoring.txt
.\.venv\Scripts\python.exe authoring/figures.py
```

Linux/macOS使用`.venv/bin/python`。制图源使用Windows微软雅黑字体；其他系统需要自行安装可用中文字体并修改字体路径。相同字号与中文字体有助于保持历史图的布局，但无需据此修改冻结实验源码。历史制图脚本默认输出到`authoring/figures/`；根目录`figures/`现为作者提供的8张PNG，不应将历史重建图误认作当前版本。

`environment/packaging_environment.json`记录本轮离线整理时的Python及文档库版本；原在线实验配置则以每阶段协议和每个会话的`command.json`为准。`requirements-authoring.txt`固定的是可选制图/文档环境，不应声称原在线模型服务由这些Python包提供。

最终报告采用作者指定的24页PDF，按原字节保存于`report/final_report.pdf`，SHA256见`report/provenance.json`。`report/final_report.md`为该PDF逐页文字提取，不代替其中的图表、公式与分页。仓库当前图表为作者指定Fig目录的8张PNG，未经重绘；`authoring/`仅保留历史写作和制图源码，不能逐字重建最终PDF或新PNG。旧版Word和矢量图仍可在Git历史中查看。实验代码、原始结果及聊天记录保持原发布状态。

## 独立在线复跑

在线复跑需要自己已登录的Codex CLI及对应模型权限。历史模型别名为`gpt-5.6-sol`，精确权重快照、采样种子不可得；当前服务可能已变化。包内没有API密钥或认证文件。

原运行器的`BIN`使用原作者机器上的绝对CLI路径。不要直接修改既有冻结源码并继续把原协议当作新协议；使用下面的辅助脚本在**全新目录**建立副本：

```bash
python scripts/prepare_online.py --output ../new_recovery_run --codex "C:/your/path/to/codex.exe"
```

该脚本只复制必要代码，替换副本的CLI路径，不复制原协议、结果或会话。输出目录必须事先不存在。进入新目录的相应阶段，按原README先运行pilot，再运行main，阶段一随后运行followup.py。新运行会创建新协议；先检查新模型、提示和权限边界再消耗在线额度。第三阶段的`retry_infra.py`专为历史异常协议，不应不加检查地应用到新的任意异常。

原运行器在发现已有`run.json`时复用结果。重复执行分析或在原目录再次执行main，不代表获得新的在线样本。模拟器只写本地效果账本，example.invalid地址不发送真实通知。

## 证据与使用边界

公开轨迹过滤内部reasoning事件，保留工具动作和最终回答；用户与助手可见对话按导出索引完整保存。规则对照不是新增LLM样本，瞬时查询条件下预设的晚提交调度是合法风险见证，不能估计生产概率。确定性参考规则使用契约真值，未实现自然语言契约解析。

工程及文献假设、已知现象、本地复现、新增模型轨迹与未验证假设在最终报告中分别标明。当前结论不支持“重规划必然造成身份漂移”，也没有证明独立于合法重复要求的调用划分评分偏差。
