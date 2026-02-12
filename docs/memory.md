# GradQuest Project Memory

## 📦 Project Metadata
* **Name**: GradQuest
* **Type**: PhD Life Simulator / Resource Management Strategy
* **Current Version**: V2.59.2
* **Last Stable Build**: V2.59.2

## 🎯 Current Focus: V3.0 "Gold Release"
We are transitioning from V2.5x (Focused Mode & Balance) to V3.0 features.

| Phase | Feature | Status | Notes |
|-------|---------|--------|-------|
| **0.5** | **Architecture** | ✅ **Done** | EventResolver, State Ownership, Hidden Metrics Audit. |
| **1.0** | **Defense Gauntlet** | 🚧 **In Progress** | UI skeleton exists (V2.40). Logic is still one-shot rng (`attemptDefense`). Needs 3-turn interactive loop. |
| **2.0** | **Narrative Endings** | ✅ **Done** | `CAREER_ENDINGS` system active (V2.18). Supports PhD/MS paths & industry/academic outcomes. |
| **3.0** | **Soundscapes** | ❌ **Pending** | No Web Audio API implementation yet. |

## 📜 Recent Changelog
* **V2.59.1 (Balance)**: Fixed "Death Spiral" (morale < 35 recovery) and "Quals Wall" (AI bot logic fix).
* **V2.58 (Economy)**: Adjusted Quals wall and morale economy.
* **V2.55 (Architecture)**: Central EventResolver, explicit state ownership, modal discipline.
* **V2.46 (Focus)**: Conference streamline (2/year, one-choice).

## 🛣️ Strategic Roadmap
| Version | Theme | Key Features | Status |
| :--- | :--- | :--- | :--- |
| **V2.55** | Architecture | EventResolver, State Ownership | ✅ Done |
| **V2.59** | Balance | Playtest Verification, Economy Fixes | ✅ Done |
| **V3.0** | **Gold Release** | **Interactive Defense, Sound** | 📅 **Next** |

## 🧠 Key Logic/Rules Established
* **Defense**: Currently a probability check (`attemptDefense`). V3.0 will make this a 3-turn minigame.
* **Thesis**: Requires 1+ Papers + 100% Thesis Progress + Quals Passed.
* **Rivals**: Progress independently; countered by "Pre-Register" or "Coordinate".
* **Funding**: Hitting 0 triggers "Teaching Load" (-50% speed).
* **Specializations**:
    * 🔬 **Experimentalist**: Protocol Reuse (Faster Figures).
    * 📐 **Theoretician**: Auto-Idea (Once/Year).
    * 💻 **Computational**: Pipeline Optimization (+50% analysis/thesis speed).
