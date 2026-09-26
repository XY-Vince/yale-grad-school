# 🏛️ (Yale) Grad School Workspace Hub

Welcome to the **(Yale) Grad School Workspace Hub** — a consolidated platform for graduate school affairs, academic milestones, autonomous research agent workflows, and educational simulation.

---

## 🧭 Repository Structure & Subprojects

```
yale-grad-school/
├── README.md                      # This master hub overview
├── AGENTS.md                      # Root agent guide & confidentiality boundaries
├── plans/                         # Tracked project plans & implementation records
├── docs/                          # Subproject: GradQuest @ Yale (PhD Simulator)
│   ├── index.html                 # Game engine & UI (shipped client-side app)
│   ├── README.md                  # Game documentation
│   └── CONTRIBUTING.md            # Game development guidelines
├── .agents/                       # Autonomous Research & Engineering Agent Infrastructure
│   ├── rules/                     # Coding standards, engineering rigor, and compliance
│   ├── skills/                    # Research skills (e.g. verify-public-person-profile)
│   └── workflows/                 # Operational agent workflows
├── tests/                         # Test suites (browser integration, unit tests)
└── data/                          # Historical/experimental rulesets and auxiliary playtest data
```

### Core Components

1. **[GradQuest @ Yale](docs/)**:
   An interactive, browser-based PhD life simulator that models academic milestones (publications, qualifiers, thesis preparation, and committee defense gauntlet) while managing morale and stress.
   - Live URL: `https://xy-vince.github.io/yale-grad-school/`
   - Shipped source of truth: `docs/index.html`

2. **[Agent Workflows & Skills](.agents/)**:
   Tools and automated skills for academic research assistance, structured evidence extraction, dossier validation, and reproducible benchmarking.

3. **Academic Milestones & Tracking**:
   Workspace governance for doctoral milestones, committee coordination, and publication pipelines.

---

## 🔒 Confidentiality & Privacy Boundaries

To maintain institutional compliance and research integrity:

> [!IMPORTANT]
> **FERPA and Confidentiality Policy**:
> - **No Student Records**: Never commit student-identifiable educational records, course grading data, or confidential student correspondence to this repository (complying with FERPA).
> - **No Unreleased Data/Credentials**: Never commit private personal access tokens, API keys, unreleased lab data, or confidential advisor evaluations.
> - **Secure Storage**: Confidential records must be maintained in designated institutional storage or external private repositories, not solely in `.gitignore`.

---

## 🛠️ Quick Start

```bash
# Clone the workspace hub
git clone https://github.com/XY-Vince/yale-grad-school.git
cd yale-grad-school

# Launch the simulator locally
open docs/index.html

# Run browser & integration test suite
node --check tests/browser_tests.js
python3 run_tests.py
```

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
