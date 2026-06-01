# ClaudeBlackJack

A Blackjack simulator with an interactive dashboard UI, built to learn Claude Code.

## Project Structure

```
ClaudeBlackJack/
├── app/          # Dashboard UI (framework TBD: Dash or Streamlit)
├── simulator/    # Core Blackjack game logic (pure Python)
├── tests/        # Unit tests
├── docs/         # Notes and documentation
└── .claude/      # Claude Code config
```

## Language & Runtime

- **Python 3.13**
- Dashboard framework: TBD (Dash or Streamlit — see docs/)

## Key Conventions

- Game logic lives in `simulator/` and must be pure Python with no UI dependencies
- Dashboard code lives in `app/` and imports from `simulator/`
- All tests go in `tests/` and use `pytest`

## Running the App

_To be filled in once framework is chosen._

## Running Tests

```
pytest tests/
```
