# Engineering Rigor, Terminology & Wording Standards (Antigravity 工作区规则)

Activation: Antigravity Workspace Rule

Use this rule for all tasks, documentation, artifacts, and communication in this workspace.

## 1. Zero Hyperbole & Banned Terms (禁用词表)

To maintain scientific integrity and candidate prototype positioning, the following terms are strictly forbidden in all reports, plans, walkthroughs, commit messages, and agent outputs:

| 严格禁用词 (Banned Terms) | 禁用原因 | 规范替代词 (Approved Standard Phrasing) |
| :--- | :--- | :--- |
| **彻底根治 / 彻底消除 / 彻底解决 / 根除** | 夸大工程效果，掩盖真实开放环境未知风险 | **所列测试均通过** / **在当前回归集内未复现** / **在当前用例中已修复/阻断** |
| **物理隔离 / 内核级防窥探** (在同 UID chmod 0o000 下) | 事实不符，同 UID 下所有者具备 chmod 权限 | **文件权限访问阻断 (chmod 0o000)** |
| **真实测试率 100% / 100% 解决** | 绝对化修辞，混淆测试集覆盖与开放世界真实率 | **所列反例测试均在前置通过结构校验的前提下完成业务分支验证** |
| **100% 客观规范 / 绝无漏洞** | 主观评价，违反可伪证性与学术规范 | **指标计算与文档表述遵循限定范围与规范** |
| **开放网络假合并率保证** / 未限定的 Clopper-Pearson | 统计外推谬误，合成基准不能推导开放世界 | **在本合成基准及二项独立假设下，Clopper-Pearson 单侧 95% 上限为 0.932%。不外推为真实开放网络上的总体假合并率保证。** |
| **虚构字段名** (`url_sha256`, `payload_sha256` 等) | 与代码实际实现漂移 | 必须引用代码真实字段：`mention_key = sha256(f"{source_id}:{start}:{end}".encode()).hexdigest()[:16]`, `Evidence.raw_payload_sha256 == SourceSnapshot.content_sha256` |

---

## 2. Status & Tense Synchronization (状态与时态一致性)

- **实施前**：方案文件可使用将来时（“拟整改”、“计划实施”）。
- **代码实现并验证后**：方案文件必须立即重命名或更新为**“实施记录”**（Implementation Record），全文统一转换为过去完成时态（“已实施”、“已完成”、“已修复”）。
- **严禁冲突**：严禁在总结报告中宣称“整改与验证完成”，但实施计划中仍保留“拟整改”字样。

---

## 3. Statistical Claims & Scope Qualification (统计断言与范围界定)

1. **试验单位真实性**：明确区分独立试验单位 $N$ 与衍生负例对数量，严禁将共享实体的成对负例重复计算为独立伯努利试验。
2. **假设与限定前提**：任何置信区间（如 Clopper-Pearson、Wilson、Bootstrap）必须明确标注前提假设（如“在本合成基准及二项独立假设下”）。
3. **禁止外推**：严禁将实验室合成语料（如 3,871 字节合成 HTML、参数化模板群组）的测试通过率宣称为“开放网络真实表现”或“达到全量商业发布标准”。

---

## 4. Prototype Positioning (候选原型统一口径)

在完成第三方独立盲测和动态异构网络验证前，系统定位必须严格保持为：
> **“自建回归集与合成基准通过的加固候选原型”；在完成第三方盲测和动态异构网络验证前，尚不具备发布结论。**
