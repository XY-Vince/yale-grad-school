import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from benchmarks.tools.blind_v2_runner import (
    INVESTIGATOR_ASSETS,
    build_pipeline_command,
    build_seatbelt_profile,
    ensure_new_workspace,
    stage_investigator_assets,
    write_bundle_seal,
    write_result_receipt,
)
from benchmarks.tools.evaluator_v2_4 import compute_bundle_tree_hash


def test_investigator_staging_contains_no_gold_or_capture_audit(tmp_path: Path):
    hidden = tmp_path / "hidden"
    staging = tmp_path / "staging"
    hidden.mkdir()
    for filename in (*INVESTIGATOR_ASSETS, "gold.json", "capture_manifest.jsonl"):
        (hidden / filename).write_text(filename, encoding="utf-8")

    hashes = stage_investigator_assets(hidden, staging)

    assert set(hashes) == set(INVESTIGATOR_ASSETS)
    assert {path.name for path in staging.iterdir()} == set(INVESTIGATOR_ASSETS)
    assert not (staging / "gold.json").exists()
    assert not (staging / "capture_manifest.jsonl").exists()


def test_seatbelt_profile_denies_entire_hidden_asset_tree(tmp_path: Path):
    hidden = tmp_path / 'hidden "assets"'
    profile = build_seatbelt_profile(hidden)

    assert "(allow default)" in profile
    assert "deny file-read*" in profile
    assert "deny file-write*" in profile
    assert str(hidden.resolve()).replace('"', '\\"') in profile


def test_g2_and_g3_commands_differ_only_by_target_prior_flag(tmp_path: Path):
    persona = SimpleNamespace(
        target_name="Alice Smith",
        hints=["Stanford"],
        aliases=["A. Smith"],
    )
    common = {
        "sandbox_exec": "/usr/bin/sandbox-exec",
        "seatbelt_profile": "(version 1)\n(allow default)",
        "persona": persona,
        "output_dir": tmp_path / "bundle",
        "corpus_path": tmp_path / "investigator_input" / "corpus.warc",
        "query_budget": 15,
    }
    g2 = build_pipeline_command(**common, enable_target_prior=False)
    g3 = build_pipeline_command(**common, enable_target_prior=True)

    assert "--enable-target-prior" not in g2
    assert g3 == [*g2, "--enable-target-prior"]
    joined = " ".join(g3)
    assert "gold.json" not in joined
    assert "capture_manifest" not in joined
    assert "--query-budget 15" in joined


def test_workspace_bundle_seal_and_result_receipt_are_fail_closed(tmp_path: Path):
    workspace = tmp_path / "workspace"
    ensure_new_workspace(workspace)
    with pytest.raises(FileExistsError):
        (workspace / "occupied").write_text("x", encoding="utf-8")
        ensure_new_workspace(workspace)

    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "manifest.json").write_text('{"run_outcome":"completed"}', encoding="utf-8")
    expected_hash = compute_bundle_tree_hash(bundle)
    seal = write_bundle_seal(bundle, "BLIND2-001", "g2")
    assert seal["bundle_tree_hash"] == expected_hash
    with pytest.raises(FileExistsError):
        write_bundle_seal(bundle, "BLIND2-001", "g2")

    evaluation = tmp_path / "evaluation.json"
    evaluation.write_text(
        json.dumps({"all_gates_passed": False, "evaluation_decision": "blocked"}),
        encoding="utf-8",
    )
    ledger = tmp_path / "ledger"
    receipt = write_result_receipt(
        ledger,
        "blind_release_v2",
        status="completed",
        evaluation_json=evaluation,
    )
    saved = json.loads(receipt.read_text(encoding="utf-8"))
    assert saved["all_gates_passed"] is False
    assert saved["evaluation_decision"] == "blocked"
    with pytest.raises(FileExistsError):
        write_result_receipt(
            ledger,
            "blind_release_v2",
            status="completed",
            evaluation_json=evaluation,
        )
