#!/usr/bin/env python3
"""Human-style strategy simulations for GradQuest.

This runner uses the shipped browser game as the source of truth. It drives the
game through public runtime methods in docs/index.html, but chooses actions with
profile-specific "human player" priorities rather than random clicking.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright


CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


@dataclass
class SimResult:
    profile: str
    run: int
    specialization: str
    seed: int
    outcome: str
    won: bool
    reason: str
    months: int
    turns: int
    papers: int
    conf_papers: int
    thesis: int
    morale: int
    lowest_morale: int
    stress: int
    max_stress: int
    funding_months: int
    quals_passed: bool
    exhaustion_months: int
    burnout_months: int
    breaks: int
    medical_leave: int
    vacation: int
    journal_submits: int
    conference_submits: int
    revisions: int
    conferences_taken: int
    defense_actions: int
    modal_count: int
    silent_count: int
    no_action_turns: int
    repeated_action_max: int
    action_counts: dict[str, int] = field(default_factory=dict)
    final_actions: list[str] = field(default_factory=list)
    recent_events: list[str] = field(default_factory=list)


PROFILE_CONFIGS: dict[str, dict[str, Any]] = {
    "balanced": {
        "morale_floor": 34,
        "stress_floor": 85,
        "quals_month": 6,
        "prefer_conference": True,
        "prefer_journal": True,
        "defense_after_hybrid": True,
    },
    "cautious": {
        "morale_floor": 48,
        "stress_floor": 70,
        "quals_month": 4,
        "prefer_conference": False,
        "prefer_journal": True,
        "defense_after_hybrid": False,
    },
    "aggressive": {
        "morale_floor": 18,
        "stress_floor": 95,
        "quals_month": 8,
        "prefer_conference": False,
        "prefer_journal": True,
        "defense_after_hybrid": True,
    },
    "conference_hybrid": {
        "morale_floor": 30,
        "stress_floor": 85,
        "quals_month": 6,
        "prefer_conference": True,
        "prefer_journal": False,
        "defense_after_hybrid": True,
    },
    "novice": {
        "morale_floor": 22,
        "stress_floor": 95,
        "quals_month": 8,
        "prefer_conference": True,
        "prefer_journal": False,
        "defense_after_hybrid": False,
        "novice": True,
    },
}


SIM_JS = r"""
({ profile, run, specialization, seed, maxTurns, config }) => {
    const actionCounts = {};
    const recentEvents = [];
    const actionHistory = [];
    let lowestMorale = 100;
    let maxStress = 0;
    let noActionTurns = 0;
    let exhaustionMonths = 0;
    let burnoutMonths = 0;
    let defenseActions = 0;

    const hasStatus = (id) => game.state && game.state.statuses && game.state.statuses.has(id);
    const countAction = (id) => { actionCounts[id] = (actionCounts[id] || 0) + 1; actionHistory.push(id); };
    const actions = () => game.getActions().filter(a => !a.disabled);
    const hasAction = (id) => actions().some(a => a.id === id);
    const chooseFirst = (ids) => ids.find(id => hasAction(id));
    const clearEventModal = () => {
        let guard = 0;
        while (game.waitingForAcknowledge && guard++ < 10) {
            game.acknowledgeEvent();
        }
    };
    const snapshot = () => {
        const s = game.state;
        return {
            month: s.totalMonths || 0,
            morale: s.morale || 0,
            stress: s.stress || 0,
            papers: s.items?.paper || 0,
            confPapers: s.confPaperCount || 0,
            thesis: s.thesisProgress || 0,
            quals: !!s.qualsPassed,
            qualsPrep: s.qualifyLevel || 0,
            monthsUntilQuals: game.getMonthsUntilQuals ? game.getMonthsUntilQuals(s) : 99,
            funding: s.fundingMonths || 0,
            ideas: s.items?.idea || 0,
            findings: s.items?.initial_findings || 0,
            discovery: s.items?.key_discovery || 0,
            figures: s.items?.figure || 0,
            pending: s.pendingPapers?.length || 0,
            revisions: s.items?.revision_required || 0,
            rejected: s.items?.rejected_paper || 0,
            activeConference: !!s.activeConference,
            waiting: game.waitingForAcknowledge,
            actions: actions().map(a => a.id),
        };
    };
    const pickDefenseAction = () => {
        const ds = game.defenseState;
        const available = game.getDefenseActions(ds.turn);
        const weakest = ["thesis_quality", "presentation_skill", "committee_support"]
            .sort((a, b) => ds[a] - ds[b])[0];
        const best = available
            .map(a => ({
                action: a,
                score: Object.entries(a.tracks).reduce((sum, [track, weight]) => {
                    const weakBonus = track === weakest ? 1.4 : 1;
                    return sum + a.gain * weight * weakBonus;
                }, 0)
            }))
            .sort((a, b) => b.score - a.score)[0].action;
        game.doDefenseAction(best);
        defenseActions++;
    };
    const chooseAction = (s) => {
        const cfg = config;
        const a = new Set(s.actions);

        if (cfg.novice) {
            if (s.morale < cfg.morale_floor) return chooseFirst(["break", "medical_leave", "vacation"]);
            if (!s.quals && s.monthsUntilQuals <= 12 && s.monthsUntilQuals >= 0 && s.qualsPrep < 3 && a.has("quals")) {
                return "quals";
            }
            const guided = s.actions.find(id => !["break", "medical_leave", "vacation", "advance"].includes(id));
            return guided || chooseFirst(["break", "advance"]) || s.actions[0];
        }

        if (s.activeConference) {
            return chooseFirst(profile === "conference_hybrid"
                ? ["conf_talk", "conf_network", "conf_poster"]
                : ["conf_network", "conf_talk", "conf_poster"]);
        }

        if (s.morale < cfg.morale_floor || s.stress >= cfg.stress_floor) {
            const recovery = chooseFirst(["medical_leave", "vacation", "break", "conf_recovery"]);
            if (recovery) return recovery;
        }

        if (!s.quals && s.month >= cfg.quals_month && s.month <= 24) {
            const quals = chooseFirst(["quals", "break"]);
            if (quals) return quals;
        }

        const review = chooseFirst([
            "pending",
            "review_polite_0", "review_polite_1", "review_polite_2",
            "revise_major", "resubmit"
        ]);
        if (review) return review;

        if (s.funding <= 0) {
            const grant = chooseFirst(["emergency_grant"]);
            if (grant) return grant;
        }

        if (s.confPapers >= 2 && s.papers < 2) {
            const convert = chooseFirst(["expand_conf_journal", "write_paper"]);
            if (convert) return convert;
        }

        const canHybrid = s.papers >= 2 && s.confPapers >= 2;
        const canGold = s.papers >= 3;
        if (s.thesis >= 100 && s.quals && (canGold || (cfg.defense_after_hybrid && canHybrid))) {
            const defense = chooseFirst(["prepare_defense", "thesis", "defend_thesis"]);
            if (defense) return defense;
        }

        if ((canGold || (cfg.defense_after_hybrid && canHybrid)) && s.thesis < 100) {
            const thesis = chooseFirst(["write_thesis", "write_dissertation"]);
            if (thesis) return thesis;
        }

        if (cfg.prefer_conference && s.papers >= 1 && s.confPapers < 2) {
            const seek = chooseFirst(["seek_conference"]);
            if (seek) return seek;
        }

        if (s.figures >= 3) {
            const publish = cfg.prefer_journal
                ? chooseFirst(["write_paper", "conf_paper"])
                : chooseFirst(["conf_paper", "write_paper"]);
            if (publish) return publish;
        }
        if (s.discovery >= 1) return chooseFirst(["work_figures", "work_figures_blocked", "maintenance", "break"]);
        if (s.findings >= 1) return chooseFirst(["work_findings", "break"]);
        if (s.ideas >= 1) return chooseFirst(["work_idea", "read"]);

        return chooseFirst(["read", "advance", "break"]) || s.actions[0];
    };

    game.selectSpecialization(specialization);
    const oldSearch = window.location.search;
    window.history.replaceState(null, "", `${window.location.pathname}?seed=${seed}`);
    game.start();
    window.history.replaceState(null, "", `${window.location.pathname}${oldSearch || ""}`);
    clearEventModal();

    for (let turn = 0; turn < maxTurns; turn++) {
        if (game.state.isEnded) break;
        clearEventModal();

        if (document.getElementById("thesis-modal")?.classList.contains("active")) {
            game.thesisDefend();
            continue;
        }
        if (document.getElementById("defense-modal")?.classList.contains("active")) {
            if (game.defenseState && !game.defenseState.complete) {
                pickDefenseAction();
                continue;
            }
            game.endDefense();
            clearEventModal();
            continue;
        }

        const before = snapshot();
        lowestMorale = Math.min(lowestMorale, before.morale);
        maxStress = Math.max(maxStress, before.stress);
        if (hasStatus("exhaustion")) exhaustionMonths++;
        if (hasStatus("burnout")) burnoutMonths++;

        const chosen = chooseAction(before);
        if (!chosen) {
            noActionTurns++;
            break;
        }
        countAction(chosen);
        game.doAction(chosen);
        clearEventModal();

        const lastEvent = game.state.eventLog?.[game.state.eventLog.length - 1];
        if (lastEvent) recentEvents.push(`${game.state.totalMonths}: ${lastEvent.text.slice(0, 120)}`);
        if (recentEvents.length > 12) recentEvents.shift();
    }

    clearEventModal();
    const s = game.state;
    const modalCount = s.eventLog?.filter(e => e.modal).length || 0;
    const silentCount = s.eventLog?.filter(e => !e.modal).length || 0;
    let repeatedActionMax = 0;
    let currentRun = 0;
    let previous = null;
    for (const action of actionHistory) {
        if (action === previous) currentRun++;
        else currentRun = 1;
        repeatedActionMax = Math.max(repeatedActionMax, currentRun);
        previous = action;
    }

    return {
        profile,
        run,
        specialization,
        seed,
        outcome: s.endState?.message || (s.isEnded ? "Ended" : "Timeout"),
        won: !!s.endState?.won,
        reason: s.endState?.reason || (s.isEnded ? "ended" : "timeout"),
        months: s.totalMonths || 0,
        turns: actionHistory.length,
        papers: s.items?.paper || 0,
        conf_papers: s.confPaperCount || 0,
        thesis: s.thesisProgress || 0,
        morale: s.morale || 0,
        lowest_morale: lowestMorale,
        stress: s.stress || 0,
        max_stress: maxStress,
        funding_months: s.fundingMonths || 0,
        quals_passed: !!s.qualsPassed,
        exhaustion_months: exhaustionMonths,
        burnout_months: burnoutMonths,
        breaks: actionCounts.break || 0,
        medical_leave: actionCounts.medical_leave || 0,
        vacation: actionCounts.vacation || 0,
        journal_submits: actionCounts.write_paper || 0,
        conference_submits: actionCounts.conf_paper || 0,
        revisions: (actionCounts.revise_major || 0) + (actionCounts.resubmit || 0)
            + Object.keys(actionCounts).filter(k => k.startsWith("review_")).reduce((sum, k) => sum + actionCounts[k], 0),
        conferences_taken: (actionCounts.conf_talk || 0) + (actionCounts.conf_network || 0) + (actionCounts.conf_poster || 0),
        defense_actions: defenseActions,
        modal_count: modalCount,
        silent_count: silentCount,
        no_action_turns: noActionTurns,
        repeated_action_max: repeatedActionMax,
        action_counts: actionCounts,
        final_actions: snapshot().actions,
        recent_events: recentEvents,
    };
}
"""


async def run_simulations(runs_per_profile: int, max_turns: int) -> list[SimResult]:
    specs = ["experimentalist", "theoretician", "computational"]
    url = (Path(__file__).resolve().parent / "docs" / "index.html").as_uri()
    results: list[SimResult] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path=CHROME)
        for profile, config in PROFILE_CONFIGS.items():
            for run in range(1, runs_per_profile + 1):
                page = await browser.new_page(viewport={"width": 1280, "height": 800})
                seed = 200000 + len(results) * 137 + run
                specialization = specs[(run - 1) % len(specs)]
                await page.goto(url, wait_until="networkidle")
                await page.wait_for_selector("#start-screen", timeout=10000)
                data = await page.evaluate(
                    SIM_JS,
                    {
                        "profile": profile,
                        "run": run,
                        "specialization": specialization,
                        "seed": seed,
                        "maxTurns": max_turns,
                        "config": config,
                    },
                )
                results.append(SimResult(**data))
                print(
                    f"{profile:18s} run {run:02d} {specialization:15s} "
                    f"{data['reason']:12s} {data['months']:3d}mo "
                    f"{data['papers']}J/{data['conf_papers']}C thesis={data['thesis']} "
                    f"morale={data['morale']} low={data['lowest_morale']}"
                )
                await page.close()
        await browser.close()

    return results


def summarize(results: list[SimResult]) -> dict[str, Any]:
    by_profile: dict[str, list[SimResult]] = {}
    for result in results:
        by_profile.setdefault(result.profile, []).append(result)

    summary: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "total_runs": len(results),
        "overall": {},
        "profiles": {},
    }
    wins = [r for r in results if r.won]
    timeouts = [r for r in results if r.reason == "timeout"]
    months = [r.months for r in results]
    summary["overall"] = {
        "win_rate": round(len(wins) / len(results), 3) if results else 0,
        "timeouts": len(timeouts),
        "median_months": statistics.median(months) if months else 0,
        "avg_months": round(statistics.mean(months), 1) if months else 0,
        "avg_journals": round(statistics.mean([r.papers for r in results]), 2) if results else 0,
        "avg_conf_papers": round(statistics.mean([r.conf_papers for r in results]), 2) if results else 0,
        "avg_lowest_morale": round(statistics.mean([r.lowest_morale for r in results]), 1) if results else 0,
        "avg_max_stress": round(statistics.mean([r.max_stress for r in results]), 1) if results else 0,
    }

    for profile, rows in by_profile.items():
        summary["profiles"][profile] = {
            "runs": len(rows),
            "wins": sum(1 for r in rows if r.won),
            "timeouts": sum(1 for r in rows if r.reason == "timeout"),
            "avg_months": round(statistics.mean([r.months for r in rows]), 1),
            "median_months": statistics.median([r.months for r in rows]),
            "avg_journals": round(statistics.mean([r.papers for r in rows]), 2),
            "avg_conf_papers": round(statistics.mean([r.conf_papers for r in rows]), 2),
            "avg_thesis": round(statistics.mean([r.thesis for r in rows]), 1),
            "avg_lowest_morale": round(statistics.mean([r.lowest_morale for r in rows]), 1),
            "avg_max_stress": round(statistics.mean([r.max_stress for r in rows]), 1),
            "avg_breaks": round(statistics.mean([r.breaks for r in rows]), 1),
            "avg_revisions": round(statistics.mean([r.revisions for r in rows]), 1),
            "avg_defense_actions": round(statistics.mean([r.defense_actions for r in rows]), 1),
            "reasons": {reason: sum(1 for r in rows if r.reason == reason) for reason in sorted({r.reason for r in rows})},
        }
    return summary


def write_outputs(results: list[SimResult], summary: dict[str, Any]) -> None:
    out_json = Path(__file__).resolve().parent / "human_playtest_results.json"
    out_md = Path(__file__).resolve().parent / "human_playtest_report.md"

    payload = {
        "summary": summary,
        "runs": [asdict(r) for r in results],
    }
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# GradQuest Human-Style Playtest Report",
        "",
        f"Generated: {summary['generated_at']}",
        f"Total runs: {summary['total_runs']}",
        "",
        "## Overall",
    ]
    for key, value in summary["overall"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Profiles")
    for profile, stats in summary["profiles"].items():
        lines.append(f"### {profile}")
        for key, value in stats.items():
            lines.append(f"- {key}: {value}")
        lines.append("")
    lines.append("## Runs")
    lines.append("| Profile | Run | Spec | Reason | Won | Months | J | C | Thesis | Low Morale | Max Stress | Defense Actions |")
    lines.append("|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in results:
        lines.append(
            f"| {r.profile} | {r.run} | {r.specialization} | {r.reason} | "
            f"{int(r.won)} | {r.months} | {r.papers} | {r.conf_papers} | "
            f"{r.thesis} | {r.lowest_morale} | {r.max_stress} | {r.defense_actions} |"
        )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Saved JSON: {out_json}")
    print(f"Saved Markdown: {out_md}")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-per-profile", type=int, default=5)
    parser.add_argument("--max-turns", type=int, default=220)
    args = parser.parse_args()

    results = await run_simulations(args.runs_per_profile, args.max_turns)
    summary = summarize(results)
    print(json.dumps(summary, indent=2))
    write_outputs(results, summary)


if __name__ == "__main__":
    asyncio.run(main())
