# mtga-export

Export your MTG Arena collection on Linux (Steam/Proton) to:

- `collection-moxfield.csv` — import at moxfield.com → Collection → Import
- `collection.json` — full structured collection for scripting/LLM deckbuilding

## Install

Editable install only — the tool spawns the daemon vendored inside this repo,
so a regular `pip install .` would not find it:

    python -m venv .venv && .venv/bin/pip install -e .

## Usage

1. Launch MTG Arena (Steam) and wait for the home screen.
2. Run `mtga-export` (optionally `-o DIR`).

Arena-only cards (e.g. ANB) are kept in the JSON (`digital_only: true`) but
excluded from the Moxfield CSV. Rebalanced Alchemy "A-" copies are dropped.

## How it works

[mtga-tracker-daemon](https://github.com/frcaton/mtga-tracker-daemon)
(vendored, see `vendor/README.md`) reads the collection from the Arena
process; card names come from Arena's own local card database. Everything
stays on your machine.

## Development

`python -m pytest` — unit tests need nothing; `-m integration` needs Arena running.
