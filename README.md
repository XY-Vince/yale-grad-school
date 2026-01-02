# GradQuest

A Python port of the PhD Simulator game with modular architecture designed for future LLM API expansion.

## Quick Start

### Command Line
```bash
cd GradQuest
pip install -r requirements.txt
python -m gradquest.main
```

### Web Browser (New in V1.2!)
```bash
cd GradQuest
python run_web.py
```
Then open **http://localhost:5000** in your browser.

### Options
- `--seed 42` - Reproducible gameplay (CLI only)
- `--port 8080` - Custom port (Web UI)

## Project Structure

```
gradquest/           # Main package
├── core/            # Core engine (VariableStore, EventEngine, etc.)
├── effects/         # Effect system (Items, Status, Attributes)
├── events/          # Event handling and YAML loading
├── interface/       # CLI interface
└── extensions/      # LLM integration preparation

data/rulesets/       # Game data (YAML files)
```

## Version History

### V1.6 (Current)
- **Automated tests**: pytest suite with 11 passing tests
- **Save/Load**: Game state persists to browser localStorage
- **Load button**: Continue previous game from start screen

### V1.5
- **Equipment bug fixed**: Repair now handled in web app (guaranteed within 3 months)
- **Total months counter**: Shows elapsed time
- **Advisor happiness bar**: Visual indicator in stats
- **Status tooltips**: Hover to see effect description
- **Randomized qual prep**: 0-2 points per session (need ~2-4 sessions)

### V1.2
- **Fixed qual exam timing**: Triggers in September year 2 (one full year)
- **Thesis action**: Explicit "Work on Thesis" when you have 3+ papers
- **Graduation works**: Thesis defense properly ends the game

### V1.1
- **Status recovery**: Slacking cures exhaustion (35%) and advisor anger (25%)
- **Balanced gameplay**: Higher success rates
- **Renamed Hope→Morale**

### V1.0
- Core engine port from TypeScript PhD Simulator
- Full research pipeline, CLI interface, LLM preparation

## LLM Expansion

Configure via environment variables:
```bash
export GRADQUEST_LLM_PROVIDER=openai  # or anthropic, local
export GRADQUEST_LLM_API_KEY=your-key
export GRADQUEST_LLM_MODEL=gpt-4
```

## Requirements

- Python 3.8+
- PyYAML

## License

MIT License
