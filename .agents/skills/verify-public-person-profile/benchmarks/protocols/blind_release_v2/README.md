# Blind Release V2 执行手册

状态：协议工具已实现；隐藏候选池、Gold 与 WARC 尚待独立 Curator 构建。

## 1. 角色分离

- 实现团队冻结候选代码，只接收公开预注册文件及最终一次性评测结果。
- 至少两名不参与生产代码实现的 Curator 独立标注，之后由不参与实现的人员裁决分歧。
- Curator 持有候选池、人物名单、排除名册、选择种子、Gold、WARC 与 Query Index；运行前不向实现团队披露。
- DEV-001 至 DEV-010、`blind_release_v1` 及此前被 Codex/AG 用于规则设计的人物均进入隐藏排除名册。

## 2. 人物候选与分层

先建立至少 90 人、建议 120 人的隐藏候选池。年龄、学生身份或知名度不是排除条件；资格取决于是否能构成预注册的事实型或弃答型测试。

30 人的建议主分层如下，各人物只能属于一个主分层：

| 主分层 | 数量 | Gold 类型 | 选择条件 |
|---|---:|---|---|
| `homonym_hint_resolvable` | 8 | 事实型 | 至少存在一名强同名干扰者，预注册 Hint 可区分目标 |
| `unambiguous_academic_professional` | 6 | 事实型 | 姓名相对唯一，但网页结构与来源类型具有异质性 |
| `cross_language_alias` | 4 | 事实型 | 中英文名、拼音、昵称或顺序变体需要闭环 |
| `temporal_transition` | 4 | 事实型 | current/former、毕业、转岗或多阶段履历是主要难点 |
| `sparse_abstain` | 4 | 弃答型 | 公开证据不足，应输出 `insufficient_evidence` |
| `non_disambiguable` | 4 | 弃答型 | 同名证据无法安全区分，应输出 `ambiguous_identity` |

事实型候选原则上应有至少两个独立来源域、至少一项机构或权威来源，以及至少两条可逐字绑定的 Gold Claim。达不到该条件的候选只能进入弃答分层，不能靠推断补足。

## 3. 承诺与确定性抽样

1. Curator 先冻结候选池与排除名册。
2. 生成保密随机种子与独立 nonce。
3. 工具按 `SHA-256(seed, stratum, candidate_id)` 在每个分层内排序并无放回抽取。
4. 对种子、候选池、30 人选择清单、排除名册、Curator 声明及隐藏评测资产清单分别计算带 nonce 的承诺哈希。
5. 只公开 `BlindPreregistration`；不公开姓名、Hint、Gold、nonce 或种子。

导出公开 Schema：

```bash
python3 benchmarks/tools/blind_v2_protocol.py export-schema \
  --output /tmp/blind_release_v2_preregistration.schema.json
```

校验公开预注册：

```bash
python3 benchmarks/tools/blind_v2_protocol.py validate-public \
  --preregistration /path/to/blind_release_v2_preregistration.json
```

规范化生成某项隐藏资产的承诺值（nonce 从文件读取，不放入命令行参数）：

```bash
python3 benchmarks/tools/blind_v2_protocol.py build-commitment \
  --asset-type candidate_pool \
  --input /secure/candidate_pool.json \
  --nonce-file /secure/candidate_pool.nonce
```

## 4. 隐藏资产契约

隐藏资产目录必须恰好包含：

- `corpus.warc`
- `query_index.jsonl`
- `gold.json`
- `case_manifest.json`
- `capture_manifest.jsonl`
- `capture_failures.jsonl`

`gold.json` 必须通过 Gold Schema V2.2；全部 30 个案例的 `annotation_type` 必须为 `double_blind_adjudicated`，且 case ID、target name 与确定性选择清单一致。

## 5. 一次性揭示与消费

Curator 在冻结候选提交的独立干净 worktree 中运行：

```bash
python3 benchmarks/tools/blind_v2_protocol.py verify-reveal \
  --preregistration /secure/public_preregistration.json \
  --seed-file /secure/seed.txt --seed-nonce "$SEED_NONCE" \
  --candidate-pool /secure/candidate_pool.json --pool-nonce "$POOL_NONCE" \
  --selection-manifest /secure/selection_manifest.json --selection-nonce "$SELECTION_NONCE" \
  --exclusion-registry /secure/exclusions.json --exclusion-nonce "$EXCLUSION_NONCE" \
  --curator-attestation /secure/attestation.json --attestation-nonce "$ATTESTATION_NONCE" \
  --hidden-asset-manifest /secure/assets/asset_manifest.json \
  --hidden-assets-nonce "$ASSET_NONCE" --hidden-assets-dir /secure/assets \
  --repo-root /path/to/frozen/worktree \
  --evaluator-file /path/to/frozen/worktree/.agents/skills/verify-public-person-profile/benchmarks/tools/evaluator_v2_4.py \
  --gold-schema-file /path/to/frozen/worktree/.agents/skills/verify-public-person-profile/models/gold_schema_v2.py \
  --consume-ledger-dir /secure/one_shot_ledger
```

`--consume-ledger-dir` 通过原子 `O_EXCL` 创建消费凭证。同一 `suite_id` 再次运行会失败。该机制提供本地文件系统并发防重，不等同于远程不可篡改日志；正式执行时还应将凭证哈希发送至独立审计方或只追加存储。若发生环境或资产错误，应将该套件标记为无效并构建新版本，不得在看过结果后复用同一人物集调参。

## 6. 评测与决策

- G2：Hinted + TargetPrior OFF。
- G3：相同输入下 Hinted + TargetPrior ON。
- Evaluator 使用 `--evaluation-role blind_release`，并要求 G2/G3 上游输入一致。
- 门槛沿用公开预注册值：0 假合并、0 假拆分、0 未匹配释放，Macro Precision 不低于 0.95，Macro Recall 不低于 0.80，主体归属不低于 0.95，状态准确率不低于 0.90，弃答准确率为 1.0。
- 全部门槛通过只产生 `eligible_for_release_review`，仍需独立发布复核；失败则进入新的开发版本和全新的盲测集。
