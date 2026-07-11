import json

import pytest

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
    responses["/cards"]["cards"].append({"grpId": 90001, "owned": 2})
    cli.main(["--card-db", str(card_db), "--daemon-url", url, "-o", str(tmp_path)])
    data = json.loads((tmp_path / "collection.json").read_text())
    assert all(c["rebalanced"] is False for c in data["cards"])
    assert data["meta"]["rebalanced_dropped"] == 2  # copies, not distinct grpIds


def test_cli_json_only_csv_only_mutually_exclusive(card_db, tmp_path):
    with pytest.raises(SystemExit) as e:
        cli.main([
            "--card-db", str(card_db), "-o", str(tmp_path),
            "--json-only", "--csv-only",
        ])
    assert e.value.code == 2


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


def test_cli_json_only(card_db, stub_daemon, tmp_path):
    url, _ = stub_daemon
    rc = cli.main([
        "--card-db", str(card_db), "--daemon-url", url,
        "-o", str(tmp_path), "--json-only",
    ])
    assert rc == 0
    assert (tmp_path / "collection.json").exists()
    assert not (tmp_path / "collection-moxfield.csv").exists()


def test_cli_csv_only(card_db, stub_daemon, tmp_path, capsys):
    url, _ = stub_daemon
    rc = cli.main([
        "--card-db", str(card_db), "--daemon-url", url,
        "-o", str(tmp_path), "--csv-only",
    ])
    assert rc == 0
    assert not (tmp_path / "collection.json").exists()
    assert (tmp_path / "collection-moxfield.csv").exists()
    # message must not claim digital-only cards were kept in a JSON we didn't write
    assert "kept in JSON" not in capsys.readouterr().out


def test_cli_corrupt_card_db(stub_daemon, tmp_path, capsys):
    url, _ = stub_daemon
    bad_db = tmp_path / "Raw_CardDatabase_bad.mtga"
    bad_db.write_bytes(b"this is not sqlite")
    rc = cli.main([
        "--card-db", str(bad_db), "--daemon-url", url, "-o", str(tmp_path),
    ])
    assert rc == 1
    assert "cannot read card database" in capsys.readouterr().err


def test_cli_unresolved_grpids_warn(card_db, stub_daemon, tmp_path, capsys):
    url, responses = stub_daemon
    responses["/cards"]["cards"].append({"grpId": 424242, "owned": 1})
    rc = cli.main(["--card-db", str(card_db), "--daemon-url", url, "-o", str(tmp_path)])
    assert rc == 0
    assert "WARNING" in capsys.readouterr().out
    data = json.loads((tmp_path / "collection.json").read_text())
    assert 424242 in data["meta"]["unresolved_grpids"]


def test_cli_zero_count_skipped(card_db, stub_daemon, tmp_path):
    url, responses = stub_daemon
    responses["/cards"]["cards"].append({"grpId": 82000, "owned": 0})
    cli.main(["--card-db", str(card_db), "--daemon-url", url, "-o", str(tmp_path)])
    data = json.loads((tmp_path / "collection.json").read_text())
    assert all(c["count"] > 0 for c in data["cards"])
    assert not any(c["grp_id"] == 82000 for c in data["cards"])


def test_cli_unwritable_output_dir(card_db, stub_daemon, tmp_path, capsys):
    url, _ = stub_daemon
    target = tmp_path / "not-a-dir"
    target.write_text("file in the way")
    rc = cli.main(["--card-db", str(card_db), "--daemon-url", url, "-o", str(target)])
    assert rc == 1
    assert "cannot write" in capsys.readouterr().err
