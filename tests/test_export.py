import csv
import json

from mtga_export.export import write_moxfield_csv, write_json
from mtga_export.resolver import Card


def _card(**kw):
    base = dict(
        grp_id=67330, name="Llanowar Elves", set_code="DOM",
        collector_number="168", rarity="common", colors=["G"],
        mana_cost="{G}", digital_only=False, rebalanced=False,
    )
    base.update(kw)
    return Card(**base)


MOXFIELD_HEADER = [
    "Count", "Tradelist Count", "Name", "Edition", "Condition", "Language",
    "Foil", "Tags", "Last Modified", "Collector Number", "Alter", "Proxy",
    "Purchase Price",
]


def test_moxfield_csv(tmp_path):
    out = tmp_path / "c.csv"
    n = write_moxfield_csv([(_card(), 4)], out)
    rows = list(csv.reader(out.open()))
    assert rows[0] == MOXFIELD_HEADER
    assert rows[1][0] == "4"
    assert rows[1][2] == "Llanowar Elves"
    assert rows[1][3] == "dom"
    assert rows[1][4] == "Near Mint"
    assert rows[1][5] == "English"
    assert rows[1][9] == "168"
    assert n == 1


def test_moxfield_csv_excludes_digital_only(tmp_path):
    out = tmp_path / "c.csv"
    n = write_moxfield_csv([(_card(digital_only=True), 2)], out)
    assert n == 0
    assert len(list(csv.reader(out.open()))) == 1  # header only


def test_json_export(tmp_path):
    out = tmp_path / "c.json"
    meta = {"exported_at": "2026-07-10T12:00:00", "daemon_version": "1.0.11.0"}
    write_json([(_card(), 4), (_card(grp_id=75450, digital_only=True), 1)], meta, out)
    data = json.loads(out.read_text())
    assert data["meta"]["daemon_version"] == "1.0.11.0"
    assert data["meta"]["distinct_cards"] == 2
    assert data["meta"]["total_cards"] == 5
    first = data["cards"][0]
    assert first["name"] == "Llanowar Elves"
    assert first["count"] == 4
    assert first["digital_only"] is False
