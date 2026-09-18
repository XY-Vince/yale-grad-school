# 开发回归集 V1 历史基准记录

## 记录边界

- Gold：`cases_gold_v1.json`
- SHA-256：`902f3337d990ab81a639b5bac4a5866eabde2cbcedfe3a2874b39eece50392f9`
- 状态：`frozen_historical`
- 本文件保存的是 V1 当时的实测结果，不是用当前代码重新计算的结果。
- V1 不应被当前 V2 报告覆盖，也不纳入 V2 的当前发布结论。

## 历史结果

| 指标 | V1 历史值 |
|---|---:|
| 平均总分 | 97.96 / 100.0 |
| 硬性门槛全通率 | 80.0% (8/10) |
| 全集假合并数 | 0 |

未过全部门槛的用例：

- `jacqueline_mann`：86.25；未通过 claim precision、citation entailment、current status、pending review 门槛。
- `li_jiawen`：93.33；未通过 Gold claim recall 门槛。

## 版本变更

V2 经独立检查冻结语料后，为 `jacqueline_mann` 增加 `graduated_from: University of Michigan` 真值。该修订属于 Gold 真值纠错，不应回写 V1，也不应把 V1 的 80.0% 历史结果改写为当前代码下的结果。
