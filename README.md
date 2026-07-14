# mtga-export

Export your MTG Arena collection on Linux (Steam/Proton) to:

- `collection.json` — full structured collection (name, set, collector number,
  rarity, colors, mana cost, count) for scripting or LLM-assisted deckbuilding
- `collection-moxfield.csv` — import at moxfield.com → Collection → Import

Everything runs locally; nothing is uploaded anywhere.

## Requirements

- Linux x86-64 (glibc) — the bundled daemon is an x86-64 Linux binary
- Python 3.11+
- MTG Arena installed through Steam (Proton). Other installs (Lutris, custom
  Wine prefix) work too, but you must point `--card-db` at Arena's card
  database yourself.

## Install

```
git clone https://github.com/PBernaerts/mtga-export
cd mtga-export
scripts/fetch-daemon.sh
python -m venv .venv && .venv/bin/pip install -e .
```

`fetch-daemon.sh` downloads a pinned, checksum-verified release of
[mtga-tracker-daemon](https://github.com/frcaton/mtga-tracker-daemon).
The editable install (`-e`) is required: the tool spawns that daemon from
inside the repo, so a plain `pip install .` or pipx install will not work.

## Usage

1. Launch MTG Arena and wait for the home screen.
2. `.venv/bin/mtga-export` (optionally `-o DIR`; see `--help` for more).

Arena-only cards (e.g. ANB) are kept in the JSON (`digital_only: true`) but
excluded from the Moxfield CSV, which has no printings for them. Rebalanced
Alchemy "A-" copies are dropped entirely.

## How it works

mtga-tracker-daemon reads the collection (card IDs and counts) from the
running Arena process — the same technique every Arena tracker uses; the
collection has not been written to Player.log for years. Card names and
printings come from Arena's own local card database. `mtga-export` glues the
two together and writes the output files.

## Troubleshooting

- **"No Raw_CardDatabase found"** — Arena isn't in a searched Steam location.
  Find `Raw_CardDatabase_*.mtga` under
  `.../steamapps/common/MTGA/MTGA_Data/Downloads/Raw/` and pass it with
  `--card-db`.
- **"MTG Arena process not found"** — Arena must be running (fully loaded to
  the home screen) when you export.
- **Daemon starts but `/cards` fails or hangs** — reading another process's
  memory can be blocked by hardening: check
  `sysctl kernel.yama.ptrace_scope` (2 or 3 will block it), and note that
  flatpak-sandboxed Steam may block memory reads entirely.
- **"N grpIds not in card DB" warning** — Arena updated and your card DB is
  newer/older than the collection state, or the DB schema changed. Re-run
  after Arena finishes updating; if it persists, please open an issue.

## Development

`pytest` runs the unit suite. `pytest -m integration` additionally talks to
the real daemon and needs Arena running.

## Disclaimer

Unofficial fan project, not affiliated with or endorsed by Wizards of the
Coast. It reads Arena's process memory read-only, like other collection
trackers; use at your own risk. This Python project is MIT licensed; the
downloaded mtga-tracker-daemon is separately licensed under GPL-3.0.
