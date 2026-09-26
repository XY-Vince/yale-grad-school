# (Yale) Grad School Workspace Hub — Restructuring & Governance Plan

**Date**: 2026-09-25  
**Target Repository**: `yale-grad-school` (formerly `GradQuest`)  
**Branch**: `codex/rebrand-yale-grad-school` (isolated worktree)  
**Status**: Approved for Implementation  

---

## 1. Context & Two-Tier Architecture

The repository is expanding from a single-game repository into a comprehensive **(Yale) Grad School Workspace Hub** for all graduate school affairs, academic milestones, research agent tools, and simulation games.

```
yale-grad-school/                  <-- (Yale) Grad School Hub
├── README.md                      <-- Hub Overview: Yale PhD portal, subprojects, confidentiality rules
├── AGENTS.md                      <-- Root Guide: Hub routing, privacy boundaries, subproject authority
├── plans/                         <-- Tracked restructuring plans & implementation records
│   └── yale-grad-school-workspace-restructure.md
├── docs/                          <-- GradQuest @ Yale Subproject (PhD Simulator)
│   ├── index.html                 <-- Shipped game (UI display updated to 'GradQuest @ Yale')
│   ├── README.md                  <-- Synchronized to V2.59.2 reality (retired stale v2.46 & Python backend claims)
│   ├── CONTRIBUTING.md            <-- Clarified single-file client-side architecture
│   └── AGENTS.md                  <-- Game-specific engineering & playtest rules
├── .agents/                       <-- Academic & Research Agent Infrastructure
│   ├── rules/                     <-- Engineering rigor, terminology, and conduct rules
│   ├── skills/                    <-- Autonomous research skills (e.g. verify-public-person-profile)
│   └── workflows/                 <-- Game & research workflows
├── tests/                         <-- Integration & regression test suites (browser_tests.js, pytest)
└── data/                          <-- Historical/experimental rulesets and auxiliary playtest data
```

### Approved Naming Standards
- **Workspace & Repository Name**: `(Yale) Grad School`
- **Repository Slug & Directory**: `yale-grad-school`
- **Interactive Game Subproject**: `GradQuest @ Yale` (subtitle: `PhD Life Simulator`)
- **Internal Identifiers Preserved**:
  - `localStorage` key remains `gradquest_save` (avoiding key migration paths; verified by regression tests).
  - Python test classes (`GradQuestPlaytester`, etc.) remain unchanged.
  - Historical artifacts (`archive/`, `test reports/`, historical CHANGELOGs) remain unchanged as historical records.

---

## 2. Public / Confidentiality Boundary (FERPA & Research Privacy)

Because the repository is transitioning to encompass broader graduate school matters and may be publicly accessible via GitHub and GitHub Pages:

1. **Strict Prohibition on Sensitive Materials**:
   - Never commit student educational records, grading data, or student-identifiable communications (FERPA compliance).
   - Never commit private degree audits, advisor private correspondence, unreleased research data/manuscripts, or access credentials (API keys, personal tokens).
2. **Storage Location Rule**:
   - Truly confidential records must live in a separate, dedicated private repository or secure institutional storage outside this repository.
   - Confidentiality must not rely solely on `.gitignore`.

---

## 3. Subproject Authority & Source of Truth

- **Overarching Hub Authority**: Root `AGENTS.md` governs global repository routing, privacy boundaries, and subproject handoffs.
- **Game Authority**: `docs/index.html` is the sole source of truth for shipped gameplay logic and state. `data/` represents historical/experimental rulesets and auxiliary data, not the live runtime engine.
- **Skill Authority**: Individual research skills are governed by their respective `.agents/skills/*/SKILL.md` specifications.

---

## 4. Implementation Steps

### Phase 0: Security & Isolation (COMPLETED)
- [x] **Phase 0A**: Sanitized `git remote origin` by stripping the embedded GitHub PAT (`ghp_...`). Local remote is now `https://github.com/XY-Vince/GradQuest.git`.
- [x] **Phase 0B**: Created isolated worktree at `.worktrees/rebrand-yale-grad-school` on branch `codex/rebrand-yale-grad-school` directly from `main`. Preserved the 7 Blind V2 uncommitted files on `feat/v5-alpha-integration` untouched.

### Phase 1: Game UI & Storage Verification (`docs/`)
- [ ] Update `docs/index.html`:
  - Page `<title>`: `🎓 GradQuest @ Yale - PhD Life Simulator`
  - Header `<h1>`: `🎓 GradQuest @ Yale`
  - Welcome Modal: `Welcome to GradQuest @ Yale!`
  - How to Play Modal: `📖 How to Play GradQuest @ Yale`
  - **Storage Key**: Retain `gradquest_save` without modification.
- [ ] Add explicit browser regression test in `tests/browser_tests.js`:
  - Verify that the game initializes and saves/loads state targeting `localStorage['gradquest_save']`.
- [ ] Update `docs/README.md`:
  - Synchronize documentation to current baseline V2.59.2.
  - Remove stale references to nonexistent Python runtime backend or obsolete v2.46 routes.
- [ ] Update `docs/CONTRIBUTING.md`:
  - Clarify static single-file architecture.

### Phase 2: Hub Governance & Root Documentation
- [ ] Create root `README.md`:
  - Introduce **(Yale) Grad School Hub**.
  - Index subprojects: GradQuest @ Yale Simulator, Academic Agent Tools, Research Verification.
- [ ] Update root `AGENTS.md`:
  - Define Hub routing, confidentiality/FERPA rules, and subproject sources of truth.
  - Retain canonical state rules (`state.items.paper`, `state.confPaperCount`, `state.fundingMonths`, `teaching_load`, max stress 100).
- [ ] Update `docs/AGENTS.md`:
  - Align with root AGENTS.md as game-specific guidelines.

### Phase 3: Verification & Quality Gates
- [ ] Run test suite:
  ```bash
  node --check tests/browser_tests.js
  python3 -m pytest tests/test_js_integration.py
  git diff --check
  ```
- [ ] Verify save continuity: existing game save structures load and deserialize without schema distortion.

### Phase 4: Remote & Repository Renaming (Post-Merge)
- [ ] Merge `codex/rebrand-yale-grad-school` to `main`.
- [ ] Rename GitHub repository from `GradQuest` to `yale-grad-school`.
- [ ] Update local Git remote: `git remote set-url origin https://github.com/XY-Vince/yale-grad-school.git`.
- [ ] Note Pages URL transition: `https://xy-vince.github.io/yale-grad-school/` (external links to `GradQuest` will need updating).
- [ ] Convert this plan to past-tense Implementation Record upon completion.
