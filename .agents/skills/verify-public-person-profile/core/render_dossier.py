"""
Dossier Markdown Renderer (V4.4.1).
Renders machine-readable Dossier and Claims into a structured, human-readable Markdown dossier.
Supports primary candidate profile rendering and side-by-side ambiguous candidate presentation.
Ensures every sentence is explicitly backed by [claim_id] provenance citations.
"""

from typing import Dict, List, Optional
from models.schemas import AdjudicationStatus, CandidateEntity, Claim, Dossier, RunOutcome


def render_dossier_markdown(
    dossier: Dossier,
    claims: List[Claim],
    person_name: str,
    candidates: Optional[List[CandidateEntity]] = None,
    run_outcome: Optional[RunOutcome] = None,
    is_offline_replay: bool = False,
) -> str:
    claim_map: Dict[str, Claim] = {c.claim_id: c for c in claims}

    lines = []
    lines.append(f"# 个人全景档案: {person_name}")
    lines.append("")
    lines.append(f"> **生成时间**: {dossier.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    if run_outcome == RunOutcome.INSUFFICIENT_EVIDENCE or (
        dossier.candidate_entity_id is None and run_outcome != RunOutcome.AMBIGUOUS_IDENTITY and not dossier.ambiguous_candidates
    ):
        lines.append("> **状态提示**: `[INSUFFICIENT_EVIDENCE] 公开证据不足或置信度不达标，合规弃答`")
        lines.append("")
        lines.append("### 调查弃答简报 (Abstention Notice)")
        lines.append("- 系统在设定检索预算内未发现足够可信的公开结构化履历。")
        lines.append("- 根据合规协议，系统停止生成未经充分支持的断言。")
        return "\n".join(lines)

    if dossier.candidate_entity_id is None:
        lines.append("> **状态提示**: `[AMBIGUOUS_IDENTITY] 存在同名多实体且置信边际不足，未自动选择主实体`")
        lines.append(f"> **检测到的候选实体数量**: {len(dossier.ambiguous_candidates)}")
        lines.append("")
        lines.append("### 候选实体消歧并列简报 (Ambiguous Candidate Profiles)")
        if candidates:
            for idx, cand in enumerate(candidates, 1):
                c_claims = [c for c in claims if c.candidate_entity_id == cand.candidate_entity_id]
                lines.append(f"#### 候选人 {idx}: `{cand.candidate_entity_id}` (关联实体簇: `{cand.proposed_cluster_id}`)")
                lines.append(f"- 提及数 (Mentions): {len(cand.mention_ids)}")
                lines.append(f"- 关联断言数: {len(c_claims)}")
                for c in c_claims:
                    lines.append(f"  - `{c.predicate}`: {c.object_raw} (`[{c.claim_id}]`)")
                lines.append("")
        lines.append("---")
        if is_offline_replay:
            lines.append("*说明：本档案基于本地离线/合成重放语料生成，未开展在线实时网络抓取。机器仅提供候选聚类与存疑提示，不自动进行正式法律身份合并。*")
        else:
            lines.append("*说明：本档案基于公开可访问来源程序化抽取生成。机器仅提供候选聚类与存疑提示，不自动进行正式法律身份合并。*")
        return "\n".join(lines)

    lines.append(f"> **建议实体簇 (Proposed Cluster ID)**: `{dossier.proposed_cluster_id}`")
    # Filter claims strictly belonging to this dossier's candidate entity
    primary_claims = [c for c in claims if c.candidate_entity_id == dossier.candidate_entity_id]
    supported_claims = [c for c in primary_claims if c.adjudication_status == AdjudicationStatus.SUPPORTED]
    unresolved_claims = [c for c in primary_claims if c.adjudication_status == AdjudicationStatus.UNRESOLVED]
    contested_claims = [c for c in primary_claims if c.adjudication_status == AdjudicationStatus.CONTESTED]

    lines.append(f"> **抽取断言总数 (待裁决/Unresolved)**: {len(unresolved_claims)}")
    if supported_claims:
        lines.append(f"> **已裁决支持事实 (Supported)**: {len(supported_claims)}")
    if contested_claims:
        lines.append(f"> **争议断言 (Contested)**: {len(contested_claims)}")
    lines.append("")

    # Group statements by section
    sections: Dict[str, List[str]] = {}
    for stmt in dossier.statements:
        sec = stmt.section
        if sec not in sections:
            sections[sec] = []
        c_tags = " ".join([f"`[{c_id}]`" for c_id in stmt.backed_claim_ids])
        sections[sec].append(f"- {stmt.rendered_text} {c_tags}")

    for sec_name, stmt_list in sections.items():
        lines.append(f"### {sec_name}")
        for s in stmt_list:
            lines.append(s)
        lines.append("")

    # Add atomic claims table (only for primary candidate)
    lines.append("### 声明级事实溯源表 (Claim-Level Evidence Ledger)")
    lines.append("| 断言编号 (Claim ID) | 谓词 (Predicate) | 宾语/取值 (Object) | 极性 (Polarity) | 时态 (Temporal Status) | 裁决状态 (Adjudication) | 引用证据 (Evidence IDs) |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    for c in primary_claims:
        ev_str = ", ".join(c.evidence_ids) if c.evidence_ids else "N/A"
        lines.append(f"| `{c.claim_id}` | `{c.predicate}` | {c.object_raw} | `{c.polarity.value}` | `{c.temporal_status.value}` | `{c.adjudication_status.value}` | `{ev_str}` |")

    lines.append("")
    lines.append("---")
    if is_offline_replay:
        lines.append("*说明：本档案基于本地离线/合成重放语料生成，未开展在线实时网络抓取。机器仅提供候选聚类与存疑提示，不自动进行正式法律身份合并。*")
    else:
        lines.append("*说明：本档案基于公开可访问来源程序化抽取生成。机器仅提供候选聚类与存疑提示，不自动进行正式法律身份合并。*")

    return "\n".join(lines)
