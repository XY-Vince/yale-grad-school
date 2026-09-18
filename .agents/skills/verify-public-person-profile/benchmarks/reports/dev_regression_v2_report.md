# 开发回归集端到端基准评测报告 (Dev Regression Benchmark Report)

- **评测用例总数**: 10 (收录 6 个真实人物 + 4 个历史失败去标识化夹具)
- **Gold 真值文件版本**: `cases_gold_v2.json`
- **Gold SHA-256**: `3a49b56f9564757e77490b5338722a93423c4a9d2b5cf1f7c7c632d2c593225a`
- **DAC 权限哨兵检查 (chmod 0o000)**: ✅ 已验证生效 (PermissionError 拦截)
- **DAC 哨兵门禁 (DAC Sentinel Gate)**: ✅ 通过 (同 UID 权限拦截)
- **盲测隔离性质说明**: 本地主机同 UID 运行仅构成 DAC 哨兵检查，不构成跨进程/命名空间盲测隔离证明；受限沙箱因无权限修改操作直接 Fail-Closed 判定 FAIL。
- **平均总分 (100分制)**: 100.0 / 100.0
- **硬性门槛全通率 (All Gates Pass Rate)**: 100.0%
- **全集假合并错误数 (Total False Merges)**: 0
- **Bundle 只读不可变性核验 (Immutability)**: ✅ 全部一致

## 用例明细评测表
| 用例编号 (Case ID) | 目标人名 | 结构校验通过 | 得分 (Score) | 门槛通过 (Gates Passed) | B³ F1 | 假合并数 | 不可变性 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `vaishali_panwar` | Vaishali Panwar | ✅ 是 | 100.0 | ✅ 通过 | 1.000 | 0 | ✅ 是 |
| `jacqueline_mann` | Jacqueline Mann | ✅ 是 | 100.0 | ✅ 通过 | 1.000 | 0 | ✅ 是 |
| `xin_zhou` | Xin Zhou | ✅ 是 | 100.0 | ✅ 通过 | 1.000 | 0 | ✅ 是 |
| `yang_qirong` | 杨启荣 | ✅ 是 | 100.0 | ✅ 通过 | 1.000 | 0 | ✅ 是 |
| `donna_cheng` | Donna Cheng | ✅ 是 | 100.0 | ✅ 通过 | 1.000 | 0 | ✅ 是 |
| `li_jiawen` | 李嘉文 | ✅ 是 | 100.0 | ✅ 通过 | 1.000 | 0 | ✅ 是 |
| `fixture_01_dnl_ldn` | David N. Liam | ✅ 是 | 100.0 | ✅ 通过 | 1.000 | 0 | ✅ 是 |
| `fixture_02_sparse_liam` | Liam | ✅ 是 | 100.0 | ✅ 通过 | 1.000 | 0 | ✅ 是 |
| `fixture_03_roster_duplication_sina` | Sina Ovali | ✅ 是 | 100.0 | ✅ 通过 | 1.000 | 0 | ✅ 是 |
| `fixture_04_snippet_attribution_katniss` | Katniss Ni | ✅ 是 | 100.0 | ✅ 通过 | 1.000 | 0 | ✅ 是 |