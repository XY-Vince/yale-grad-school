# 🎓 GradQuest

> *Can you survive the PhD? Publish 3 papers before your morale runs out!*

[![Play Now](https://img.shields.io/badge/▶_Play_Now-GitHub_Pages-blue?style=for-the-badge)](https://xy-vince.github.io/GradQuest/)
[![Version](https://img.shields.io/badge/Version-2.0-green?style=flat-square)](https://github.com/XY-Vince/GradQuest/releases)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

---

## 🎮 Play Now

**[▶ Play GradQuest](https://xy-vince.github.io/GradQuest/)** - No download required!

---

## 📖 About

GradQuest is a text-based PhD life simulator inspired by the classic [PhD Simulator](http://research.wmz.ninja/projects/phd). Navigate the challenging journey of graduate school: read papers, develop ideas, publish research, and manage your relationship with your advisor—all while keeping your morale above zero!

### The Research Pipeline

```
📚 Read Papers → 💡 Idea → 🔬 Initial Findings → 🎯 Key Discovery
                                                      ↓
                        🎓 Thesis ← 📝 Paper ← 📊 Document Findings (×3)
```

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Research Pipeline** | Realistic progression from ideas to publication |
| **Advisor Relationship** | Keep your advisor happy or face morale penalties |
| **Paper Submission** | Experience realistic review delays |
| **Qualifying Exams** | Prepare for quals in Year 2 |
| **Save/Load** | Continue your PhD journey anytime |
| **Shareable Seeds** | Share your timeline with `?seed=X` URLs |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                  GradQuest                          │
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

### Option 3: CLI Mode
```bash
python -m gradquest.main --seed 42
```

---

## 📁 Project Structure

```
GradQuest/
├── docs/               # Static web version (GitHub Pages)
│   └── index.html      # Complete game in one file
├── gradquest/          # Python backend
│   ├── core/           # Engine: VariableStore, GameEngine
│   ├── events/         # Event handling, YAML loading
│   └── web/            # Flask web interface
├── data/rulesets/      # Game data (YAML)
└── tests/              # pytest suite
```

---

## 📋 Version History

See [CHANGELOG.md](CHANGELOG.md) for full history.

| Version | Highlights |
|---------|------------|
| **v2.0** | Professional README, pipeline visualizer, CI/CD |
| v1.9 | Typewriter effect, load button, cleaner UI |
| v1.8 | Paper delays, diverse messages |
| v1.7 | Shareable seeds, help modal |

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
