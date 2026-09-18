# 方案 A 实施记录

日期：2026-09-10
状态：内部加固闭环完成；仍定位为自建回归候选原型

## 1. 范围

本轮覆盖机构抽取、Profile 字段、中文学校、Benchmark 2 严格 5D 门槛，以及端到端 Gold V1/V2 版本隔离。未扩大到开放网络准确率或生产发布保证。

## 2. TDD 记录

先增加或收紧以下回归约束：

1. 禁止 `of Biostatistics` 与 `of ...` 介词残片，同时要求完整机构头词。
2. mHealth Profile 必须识别 Yale School of Medicine 与 Internal Medicine，且不得继承上一段的时态。
3. `毕业于北京一零一中` 必须精确抽取；`北京中` 不得因裸 `中` 后缀形成学校 claim。
4. 严格 5D 的 precision、recall、F1 必须分别过门槛，单独 F1 通过不够。
5. 未版本化 Gold 输入必须被拒绝；V1/V2 哈希与唯一变更必须受测试约束。

红灯阶段实测：Profile 时态断言失败；Benchmark/Gold 新治理接口在测试收集时不存在。实现后相关测试转绿。

## 3. 实现增量

- 抽取器在每个 clause 内先独立计算 polarity 与 temporal status；无显式历史/否定标记的 Profile Position/Role 字段按 current 处理。
- Profile 机构发现继续统一走 `extract_organizations()`，保留完整 Department/Section/School 头词并过滤 `of ...` 残片。
- 中文毕业学校使用 `毕业于/就读于` 上下文与明确学校模式；不启用裸 `中` 后缀。
- Benchmark 2 的严格 object 只接受标准化精确值或显式 equivalence set；subject 使用完整姓名边界或代词，不再以任意姓名 token 子串命中。
- Benchmark 2 新增 joint 5D precision、recall、F1 独立门槛与聚合 `strict_5d_release_gate`；命令行在硬门槛失败时返回非零状态。
- 端到端 evaluator 默认读取 V2，校验 manifest SHA-256，拒绝 `cases_gold.json`，并按 Gold 版本生成独立报告。
- V1 的 97.96/100 与 80.0% 历史结果被单独冻结；V2 只增加 Jacqueline Mann 的 University of Michigan 母校关系。冻结 WARC 第 25 行原文明确陈述其 PhD 来自该校。

## 4. 验证结果

| 检查 | 结果 |
|---|---|
| Pytest 全量 | 54 passed |
| Benchmark 2 | strict joint 5D P/R/F1 = 1.0000；release gate = pass |
| Benchmark 4 V2 | 10 cases；mean 100.0；all-gates pass 100%；false merges 0 |
| Bundle 不可变性 | 10/10 通过 |
| Gold V2 SHA-256 | `3a49b56f9564757e77490b5338722a93423c4a9d2b5cf1f7c7c632d2c593225a` |
| Skill quick validation | pass |

## 5. 边界

- V1 与 V2 的结果基于不同 Gold，不应作为纯代码改进幅度直接相减。
- `chmod 0o000` 仅为同机文件权限阻断，不提供进程级或主机级隔离；版本哈希、环境变量清理、评测目录分离和 bundle 哈希共同降低污染风险。
- 100% 仅描述当前 10 个 V2 自建回归用例，不外推为开放网络表现或普遍准确率。
