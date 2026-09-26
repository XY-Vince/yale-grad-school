# 🎓 GradQuest @ Yale: PhD Life Simulator

> *Navigate the PhD journey at Yale: Publish, survive, and defend—or strategically exit.*

[![Version](https://img.shields.io/badge/Version-2.59.2-green?style=flat-square)](CHANGELOG.md)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](../LICENSE)

---

## 🎮 Play Now

**[▶ Play GradQuest @ Yale](https://xy-vince.github.io/yale-grad-school/)** — Runs entirely in your browser, no download required!

*Note: GradQuest is maintained as the interactive simulation subproject of the **(Yale) Grad School** workspace hub.*

---

## 📖 About

**GradQuest @ Yale** is a strategic, client-side PhD life simulator modeling the academic journey. Manage research, publications, funding, and advisor relationships while balancing mental stamina and stress.

### Baseline: V2.59.2
- **Focused Core Progression**: Streamlined research pipeline (Read Papers → Idea → Discovery → Figures → Paper Submission → Thesis → Defense Gauntlet).
- **Conference Balance**: Strategic conference choices (Poster, Talk, Network) with persistent benefits.
- **Slog Check**: Every punishment unlocks a mechanical recovery path (Vacation, Therapy, Emergency Grant, Extension).
- **Defense Gauntlet**: 3-turn interactive oral defense with committee skepticism calculations.

---

## 🎯 Win Conditions

Per the authoritative `GRADUATION_CONTRACT`:

| Route | Requirements |
|---|---|
| **🎓 Standard PhD** | 3 journal papers (`state.items.paper ≥ 3`) + Quals passed + 100% thesis + Defense Gauntlet victory |
| **🔬 Hybrid PhD** | 2 journal papers + 2 conference papers (`state.items.paper ≥ 2 && state.confPaperCount ≥ 2`) + Quals passed + 100% thesis + Defense Gauntlet victory |
| **🚪 Master's Exit** | Strategic exit available in Year 2+ when burnout or funding constraints prevent PhD completion |

---

## 🔬 Core Progression Pipeline

| Phase | Action | Description |
|---|---|---|
| **Ideation** | 📚 Read Papers | Discover literature and generate viable research ideas |
| **Execution** | 💡 Work on Idea | Develop ideas into preliminary laboratory findings |
| **Execution** | 🔬 Develop Findings | Refine findings into a key scientific discovery |
| **Validation** | 📊 Validate Discovery | Produce peer-review ready figures (3 needed per manuscript) |
| **Dissemination** | 📋 Conference Paper | Rapid peer dissemination (shorter review cycle) |
| **Dissemination** | 📝 Journal Paper | Authoritative journal submission under rigorous review |
| **Writing** | 📖 Write Thesis | Synthesize published and unpublished work into dissertation |
| **Endgame** | 🎓 Defend Thesis | Face the 3-turn Committee Defense Gauntlet |

---

## 🛡️ Recovery & Health Mechanics

- **Morale**: Reaching 0 triggers academic dismissal or dropout. Take breaks, socialize, or take vacations to recover.
- **Stress**: Numeric stress is capped at `100`. High stress accelerates monthly decay and elevates committee skepticism during defense.
- **Funding**: Tracked in months (`state.fundingMonths`). Running out adds `teaching_load` status, reducing available research turns.

---

## 🚀 Local Development

The game runs as a zero-dependency static web application:

```bash
# Clone the repository
git clone https://github.com/XY-Vince/yale-grad-school.git
cd yale-grad-school

# Open docs/index.html directly in any browser
open docs/index.html

# Run browser verification tests
node --check tests/browser_tests.js
python3 run_tests.py
```

---

## 📄 License

MIT License — see [LICENSE](../LICENSE) for details.
