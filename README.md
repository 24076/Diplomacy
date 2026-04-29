# Diplomacy Local Desktop Guide

This project is a local desktop version of *Diplomacy* built with `pygame`.
It includes a playable map UI, a rules engine, AI-controlled powers, diplomacy chat,
battle report export, map point calibration tools, and automated tests.

It can be used in two ways:

- Local hotseat play with multiple human-controlled powers
- Mixed play where some powers are controlled by AI

## What Is In The Codebase

- `main.py`: application entry point
- `ui/app.py`: desktop UI, interaction flow, map rendering, side panel, diplomacy chat
- `engine/`: game state, orders, validation, phase flow, resolution, battle reports
- `engine/ai/`: AI diplomacy memory, model client, AI order selection, fallback logic
- `map/assets/`: map image assets
- `map/ui_layout.json`: unit marker coordinates and layout data
- `tools/`: helper scripts
- `tests/`: automated tests
- `reports/`: generated reports and verification artifacts

## Requirements

- Python 3.11+
- A desktop environment that can run `pygame`

Install dependencies:

```bash
pip install -r requirements.txt
```

## Start The Game

Run:

```bash
python main.py
```

The app starts in a setup screen first.

- Selected powers are human-controlled
- Unselected powers are AI-controlled
- Up to 6 powers can be assigned to humans
- Click `Start Match` to begin the game

## How To Play

### Turn Flow

The normal flow is:

1. Select the current power's unit on the map
2. Choose one order from the `Possible Orders` panel
3. Repeat until that power's orders are ready
4. Click `Submit`
5. After all required powers have submitted, click `Process`

The engine will automatically move between:

- `ORDERS`
- `RETREATS`
- `ADJUSTMENTS`

### Order Input

- Click one of your units to see legal orders
- Click an order in the right panel to add it to the draft
- Choosing another order for the same unit replaces the previous draft
- Units without an explicit order default to `Hold` during resolution

### Diplomacy Chat

If at least one AI power is active, the `Diplomacy` section is available.

- Select an AI recipient
- Type a short diplomatic message
- Click `Send`

The AI can reply and uses remembered trust, fear, promises, and prior messages
to influence later behavior.

## AI Configuration

Live AI uses the DeepSeek-compatible client in `engine/ai/client.py`.

Set the API key before running live AI tests or campaigns:

```bash
set DEEPSEEK_API_KEY=your_key
```

Optional environment variables:

```bash
set DEEPSEEK_BASE_URL=https://api.deepseek.com
set DEEPSEEK_MODEL=deepseek-v4-pro
set DEEPSEEK_TIMEOUT_SECONDS=180
set DEEPSEEK_MAX_RETRIES=3
set DEEPSEEK_RETRY_DELAY_SECONDS=4
```

If `DEEPSEEK_API_KEY` is not set:

- The desktop app still runs
- AI behavior falls back to local heuristic logic instead of live model calls

## Common Scripts

### Calibrate Map Points

Use this when unit markers need to be repositioned on the map:

```bash
python tools/calibrate_points.py
```

This tool:

- loads `map/ui_layout.json`
- lets you click the map to place coordinates
- auto-saves updated positions back to `map/ui_layout.json`

### Run Full Verification And Generate A Report

```bash
python tools/run_full_test_and_report.py
```

Optional arguments:

```bash
python tools/run_full_test_and_report.py --output-dir reports --stem nightly_run
```

This script:

- runs `pytest -q`
- generates a sample battle report if tests pass
- writes Markdown, JSON, and summary output files

### Live DeepSeek Smoke Test

```bash
python tools/smoke_test_deepseek_ai.py
```

This checks whether:

- the API client is available
- AI can reply to a message
- AI can choose orders for a live game state

### Long AI Campaign

```bash
python tools/run_long_ai_campaign.py
```

Fallback-only mode:

```bash
python tools/run_long_ai_campaign.py fallback
```

## Testing

Run all tests:

```bash
pytest -q
```

The test suite covers areas such as:

- map data
- order parsing and validation
- resolution and phase progression
- retreats and winter adjustments
- UI click flow
- AI diplomacy and long-play flow

## Generated Outputs

The `reports/` directory stores generated verification artifacts such as:

- `full_verification.md`
- `full_verification.json`
- `full_verification_summary.json`

The repository also includes:

- `rules_cn.pdf`: Chinese rules reference
- `rule_extract.txt`: extracted rules text for analysis or validation

## Current Architecture Summary

From the current implementation, the project is organized into three main layers:

- `ui/`: rendering, clicks, local interaction, drafting, diplomacy input
- `engine/`: rules, validation, state updates, phase transitions, reports
- `engine/ai/`: DeepSeek client integration, diplomacy memory, AI order selection

`main.py` currently launches `DiplomacyApp(start_in_setup=True)`, so the expected
entry flow is setup screen first, then the actual match UI.
