"""Writers: Moxfield collection CSV and deckbuilding JSON."""

import csv
import json
from dataclasses import asdict
from pathlib import Path

from .resolver import Card

MOXFIELD_HEADER = [
    "Count", "Tradelist Count", "Name", "Edition", "Condition", "Language",
    "Foil", "Tags", "Last Modified", "Collector Number", "Alter", "Proxy",
    "Purchase Price",
]


def write_moxfield_csv(cards: list[tuple[Card, int]], path: Path) -> int:
    """Write Moxfield import CSV. Digital-only cards are excluded (Moxfield
    has no printings for Arena-only sets). Returns rows written."""
    written = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(MOXFIELD_HEADER)
        for card, count in cards:
            if card.digital_only:
                continue
            w.writerow([
                count, "", card.name, card.set_code.lower(), "Near Mint",
                "English", "", "", "", card.collector_number, "", "", "",
            ])
            written += 1
    return written


def write_json(cards: list[tuple[Card, int]], meta: dict, path: Path) -> None:
    payload = {
        "meta": {
            **meta,
            "distinct_cards": len(cards),
            "total_cards": sum(count for _, count in cards),
        },
        "cards": [{**asdict(card), "count": count} for card, count in cards],
    }
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
