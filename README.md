# 🎓 GradQuest

> *Can you survive the PhD? Publish 3 papers before your morale runs out!*

[![Play Now](https://img.shields.io/badge/▶_Play_Now-GitHub_Pages-blue?style=for-the-badge)](https://xy-vince.github.io/GradQuest/)
[![Version](https://img.shields.io/badge/Version-2.3-green?style=flat-square)](https://github.com/XY-Vince/GradQuest/releases)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

---

## 🎮 Play Now

**[▶ Play GradQuest](https://xy-vince.github.io/GradQuest/)** - No download required!

---

## 📖 About

GradQuest is a strategic PhD life simulator that evolves from survival to **resilience management**. Navigate graduate school by developing research, managing your advisor relationship, building your peer network, and making strategic decisions—all while keeping your morale above zero!

---

## 🎯 Win Conditions

| Path | Requirements |
|------|--------------|
| **🎓 PhD** | Publish 3 journal papers + defend thesis |
| **🚪 Master's** | Strategic exit with 3 ending profiles |

---

## 📊 Core Mechanics

### Research Pipeline

```
📚 Read Papers → 💡 Idea → 🔬 Initial Findings → 🎯 Key Discovery
                                                      ↓
                        🎓 Thesis ← 📝 Paper ← 📊 Figures (×3)
```

### Stats You Need to Manage

| Stat | Description |
|------|-------------|
| **😊 Morale** | Falls to 0 = Game Over. Base decay 4/month. |
| **🧑‍🏫 Advisor** | Affects paper outcomes, morale penalties |
| **📰 Papers** | Need 3 for thesis defense |
| **🤝 Network** | Unlocks Study Group (≥50), affects MS-Out endings |

---

## 🧑‍🏫 Advisor System (V2.2 Pro)

Your advisor has **hidden traits** that affect your outcomes:

| Trait | High Value | Low Value |
|-------|-----------|-----------|
| **Risk Tolerance** | Likes bold ideas | Prefers safe methods |
| **Attention Span** | Fast feedback | Slow responses |
| **Strictness** | Harsh reviews | Encouraging feedback |

**💬 Pitch Session**: Use this action to learn your advisor's preferences. Look for signals like:
- *"I like bold ideas"* → High Risk Tolerance
- *"Every comma matters"* → High Strictness
- *"I'll get to it when I can"* → Low Attention Span

---

## 📋 Publication Tracks

| Track | Wait Time | Success Rate | Reward |
|-------|-----------|--------------|--------|
| **📝 Journal Paper** | 8-12 months | 50% accept, 25% major revision | Counts toward graduation |
| **📋 Conference Paper** | 4 months | 60% | +15 Network, +8 morale |

### Paper Outcomes
- **Accepted**: +1 paper, +10 morale
- **Major Revision** (Reviewer #2): Snarky message, can revise
- **Rejected**: Can revise and resubmit

---

## 📅 Key Milestones

| Event | Timing | Requirements |
|-------|--------|--------------|
| **📝 Qualifying Exam** | September Year 2 | Need 2 prep sessions (or 1 + Study Group) |
| **🆘 Last-Minute Cram** | August Year 2 only | Emergency option: -25 morale, +exhaustion |
| **🚪 MS-Out Offer** | Morale < 20, Year ≥ 2 | Strategic exit becomes available |

### Quals Survival Tips
- **⚠️ Urgency Warning**: 3 months before deadline, button shows warning
- **👥 Study Group**: Network ≥50 counts as +1 prep session
- **🆘 Cram**: Last resort option in August Y2

---

## 🎲 Random Events

| Event | Chance | Effect |
|-------|--------|--------|
| **😰 Imposter Syndrome** | ~8%/month | -3 to -7 morale |
| **📢 Getting Scooped** | ~3% if have ideas | Lose 1 idea, -5 to -10 morale |
| **🎄 December Break** | 50% in Dec | +5 morale |
| **☀️ Summer Focus** | 15% Jun-Aug | +3 morale |
| **📚 September Chaos** | 30% in Sep | -3 morale |
| **📝 Teaching Duty** | ~10% fall/spring | TA for 3-4 months, bonus on completion |
| **💡 Inspiration** | 3%/month | +15 morale, +1 idea |

---

## 🚪 MS-Out Strategic Exit (V2.2 Pro)

When morale drops below 20 after Year 2, your advisor offers the Master's exit:

| Ending Profile | Condition |
|----------------|-----------|
| **🏢 Industry R&D Lead** | Network > 60 |
| **📊 Data Scientist** | Papers ≥ 2 |
| **🏃 The Great Escape** | Low everything |

---

## 🛡️ Status Effects

| Status | Effect |
|--------|--------|
| **🥱 Exhaustion** | +6 morale decay/month |
| **😠 Unhappy Advisor** | +6 morale decay/month |
| **🔧 Broken Equipment** | Blocks "Document Findings" |
| **📝 TA Duty** | Shows in pipeline, bonus on completion |
| **🎓 First Year** | Removed at Year 2 start |

---

## 🎮 UI Features

| Feature | Location |
|---------|----------|
| **📜 History** | Footer button - view last 20 events |
| **🎲 Seed** | Footer button - get shareable URL |
| **📖 Help** | Footer button - game mechanics |
| **💾 Save/Load** | Right panel buttons |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                  GradQuest v2.3                     │
├─────────────────────┬───────────────────────────────┤
│   Static Web UI     │      Python Backend           │
│   (docs/index.html) │      (gradquest/)             │
├─────────────────────┼───────────────────────────────┤
│ • Pure JavaScript   │ • Core Engine (VariableStore) │
│ • GitHub Pages      │ • Event System (YAML-driven)  │
│ • localStorage      │ • CLI Interface               │
│ • Typewriter effect │ • LLM Integration Prep        │
└─────────────────────┴───────────────────────────────┘
```

---

## 🚀 Quick Start

### Option 1: Play Online (Recommended)
Visit **[xy-vince.github.io/GradQuest](https://xy-vince.github.io/GradQuest/)**

### Option 2: Run Locally
```bash
git clone https://github.com/XY-Vince/GradQuest.git
cd GradQuest
pip install -r requirements.txt
python run_web.py
```
Open **http://localhost:8080**

---

## 📋 Version History

See [CHANGELOG.md](CHANGELOG.md) for full history.

| Version | Highlights |
|---------|------------|
| **v2.3** | Quals urgency, Study Group, Cram, Figure counter |
| **v2.2** | Advisor profiling, Network stat, MS-Out endings |
| **v2.1** | Imposter syndrome, Scooped, Teaching, Reviewer #2 |
| v2.0 | Professional README, pipeline visualizer |
| v1.9 | Typewriter effect, load button |

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  <i>Made with ☕ and existential dread</i>
</p>
