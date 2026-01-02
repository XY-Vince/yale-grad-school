# Contributing to GradQuest

Thank you for your interest in contributing! 🎓

## How to Contribute

### Reporting Bugs
1. Check existing [Issues](https://github.com/XY-Vince/GradQuest/issues)
2. Create a new issue with:
   - Clear title
   - Steps to reproduce
   - Expected vs actual behavior
   - Browser/OS info

### Feature Requests
Open an issue with the `enhancement` label describing:
- The feature
- Why it would be useful
- Potential implementation approach

### Code Contributions

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Make your changes
4. Test locally
5. Submit a Pull Request

### Commit Convention

Use [Conventional Commits](https://conventionalcommits.org/):

```
feat: add new action type
fix: resolve paper delay bug
docs: update README
style: format code
refactor: simplify game loop
test: add event tests
```

## Development Setup

```bash
git clone https://github.com/YOUR_USERNAME/GradQuest.git
cd GradQuest
pip install -r requirements.txt
python -m pytest tests/
```

## Project Structure

- `docs/index.html` - Static web game (edit for UI changes)
- `gradquest/` - Python backend
- `data/rulesets/` - Game data YAML files
- `tests/` - pytest suite

## Code Style

- JavaScript: Use `const`/`let`, arrow functions
- Python: Follow PEP 8
- Keep functions small and focused

---

Questions? Open an issue or reach out!
