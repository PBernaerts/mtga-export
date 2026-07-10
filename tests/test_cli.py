import json

from mtga_export import cli


def test_cli_end_to_end(card_db, stub_daemon, tmp_path, capsys):
    url, _ = stub_daemon
    rc = cli.main([
        "--card-db", str(card_db),
        "--daemon-url", url,
        "-o", str(tmp_path),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Exported 2 cards" in out  # 2 distinct from stub: 67330 + 75450
    data = json.loads((tmp_path / "collection.json").read_text())
    assert data["meta"]["total_cards"] == 5
    csv_text = (tmp_path / "collection-moxfield.csv").read_text()
    assert "Llanowar Elves" in csv_text
    assert "Hallowed Priest" not in csv_text  # digital-only excluded from CSV


def test_cli_rebalanced_dropped(card_db, stub_daemon, tmp_path):
    url, responses = stub_daemon
    responses["/cards"]["cards"].append({"grpId": 90001, "owned": 1})
    cli.main(["--card-db", str(card_db), "--daemon-url", url, "-o", str(tmp_path)])
    data = json.loads((tmp_path / "collection.json").read_text())
    assert all(c["rebalanced"] is False for c in data["cards"])


def test_cli_bad_card_db_path(tmp_path, capsys):
    rc = cli.main([
        "--card-db", "/nonexistent/db.mtga",
        "--daemon-url", "http://127.0.0.1:1",
        "-o", str(tmp_path),
    ])
    assert rc == 1
    err = capsys.readouterr().err
    assert "error:" in err
    # DB path must be validated before any daemon interaction
    assert "card database not found" in err


def test_cli_daemon_unreachable(card_db, tmp_path, capsys):
    rc = cli.main([
        "--card-db", str(card_db),
        "--daemon-url", "http://127.0.0.1:1",
        "-o", str(tmp_path), "--no-spawn",
    ])
    assert rc == 1
    assert "daemon" in capsys.readouterr().err.lower()
