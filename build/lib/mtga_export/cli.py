"""mtga-export: export your MTG Arena collection to Moxfield CSV and JSON."""

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .daemon import DEFAULT_URL, DaemonClient, DaemonError, daemon_session
from .export import write_json, write_moxfield_csv
from .resolver import CardResolver, find_card_db


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="mtga-export", description=__doc__)
    p.add_argument("-o", "--output-dir", type=Path, default=Path.cwd())
    p.add_argument("--card-db", type=Path, help="path to Raw_CardDatabase_*.mtga")
    p.add_argument("--daemon-url", default=DEFAULT_URL)
    p.add_argument("--no-spawn", action="store_true",
                   help="only use an already-running daemon")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--json-only", action="store_true")
    g.add_argument("--csv-only", action="store_true")
    p.add_argument("--version", action="version", version=__version__)
    args = p.parse_args(argv)

    try:
        db_path = args.card_db or find_card_db()
        if not db_path.is_file():
            raise FileNotFoundError(f"card database not found: {db_path}")
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    try:
        if args.no_spawn:
            client = DaemonClient(base_url=args.daemon_url)
            raw = client.get_cards()
            daemon_version = client.status().get("daemonVersion", "?")
        else:
            with daemon_session(base_url=args.daemon_url) as client:
                raw = client.get_cards()
                daemon_version = client.status().get("daemonVersion", "?")
    except DaemonError as e:
        print(f"error: daemon: {e}", file=sys.stderr)
        return 1

    cards, unresolved, rebalanced_dropped = [], [], 0
    try:
        with CardResolver(db_path) as resolver:
            for grp_id, count in sorted(raw.items()):
                if count <= 0:
                    continue
                card = resolver.resolve(grp_id)
                if card is None:
                    unresolved.append(grp_id)
                elif card.rebalanced:
                    rebalanced_dropped += count
                else:
                    cards.append((card, count))
    except sqlite3.Error as e:
        print(
            f"error: cannot read card database {db_path}: {e}\n"
            "If Arena recently updated, its DB schema may have changed — "
            "please report this at the project's issue tracker.",
            file=sys.stderr,
        )
        return 1
    cards.sort(key=lambda pair: pair[0].name)

    meta = {
        "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "card_db": db_path.name,
        "daemon_version": daemon_version,
        "unresolved_grpids": unresolved,
        "rebalanced_dropped": rebalanced_dropped,
    }
    csv_rows = 0
    try:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        if not args.csv_only:
            write_json(cards, meta, args.output_dir / "collection.json")
        if not args.json_only:
            csv_rows = write_moxfield_csv(
                cards, args.output_dir / "collection-moxfield.csv"
            )
    except OSError as e:
        print(f"error: cannot write to {args.output_dir}: {e}", file=sys.stderr)
        return 1

    digital = sum(1 for c, _ in cards if c.digital_only)
    digital_note = (
        f"digital-only excluded: {digital}" if args.csv_only
        else f"digital-only kept in JSON only: {digital}"
    )
    print(
        f"Exported {len(cards)} cards "
        f"({sum(n for _, n in cards)} total copies) to {args.output_dir}/\n"
        f"  Moxfield CSV rows: {csv_rows} ({digital_note})\n"
        f"  Rebalanced (Alchemy) copies dropped: {rebalanced_dropped}"
    )
    if unresolved:
        print(f"  WARNING: {len(unresolved)} grpIds not in card DB: "
              f"{unresolved[:10]}{'...' if len(unresolved) > 10 else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
