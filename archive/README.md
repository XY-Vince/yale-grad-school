# GradQuest Archive

This directory contains historical files, legacy implementations, and outdated documentation preserved for reference.

## Structure

### `/test-reports/` (38 files)
Historical playtest reports from versions V2.15 through V2.39.
- Contains both English and Chinese versions of reports
- Documents the evolution of game mechanics and balance
- Kept for historical reference and design archaeology

### `/phd-game-reference/` 
Original TypeScript/Webpack implementation imported from [research.wmz.ninja](https://research.wmz.ninja/projects/phd/index.html).
- Complete TypeScript source code
- YAML-based ruleset system
- Webpack build configuration
- **Status:** Not actively maintained, preserved as reference

### `/legacy-backend/`
Python-based game engine and CLI interface.
- Flask web interface
- Event-driven architecture with YAML configs
- VariableStore, ExpressionParser, GameEngine
- **Status:** Superseded by JavaScript implementation in `docs/`

### `/root-docs/`
Root-level documentation files that have been moved from repository root.
- `index-v2.56-legacy.html` - Old version of game (pre-v2.57)
- `IMPLEMENTATION_PLAN.md` - Historical implementation roadmap (172KB)
- `BBS_RECAP.md` - Chinese development log

## Current Active Code

The current live version is in:
- `/docs/index.html` - V2.57 (GitHub Pages deployment)
- `/docs/tests.html` - Test suite
- `/docs/AGENTS.md` - Architecture documentation

## When to Reference This Archive

1. **Design Decisions:** Understanding why certain mechanics were added/removed
2. **Balance History:** Seeing how difficulty evolved across versions
3. **Technical Reference:** The TypeScript/Python implementations for porting ideas
4. **Documentation:** Historical roadmaps and planning documents

---
*Archived: 2026-02-02*
