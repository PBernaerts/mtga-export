import pytest

from mtga_export.resolver import CardResolver, find_card_db


def test_resolves_basic_fields(card_db):
    r = CardResolver(card_db)
    c = r.resolve(67330)
    assert c.name == "Llanowar Elves"
    assert c.set_code == "DOM"          # DAR remapped to paper code
    assert c.collector_number == "168"
    assert c.rarity == "common"
    assert c.colors == ["G"]
    assert c.mana_cost == "{G}"
    assert c.digital_only is False
    assert c.rebalanced is False


def test_digital_only_flagged(card_db):
    c = CardResolver(card_db).resolve(75450)
    assert c.name == "Hallowed Priest"
    assert c.set_code == "ANB"
    assert c.digital_only is True


def test_rebalanced_flagged(card_db):
    c = CardResolver(card_db).resolve(90001)
    assert c.rebalanced is True


def test_multicolor_and_x_cost(card_db):
    c = CardResolver(card_db).resolve(80100)
    assert c.colors == ["U", "B"]
    assert c.mana_cost == "{X}{U}{B}"
    assert c.rarity == "mythic"


def test_colorless_artifact(card_db):
    c = CardResolver(card_db).resolve(81000)
    assert c.name == "Test Artifact"
    assert c.colors == []
    assert c.mana_cost == "{2}"


def test_close_removes_temp_copy(card_db):
    from pathlib import Path
    r = CardResolver(card_db)
    tmp_name = r._tmp.name
    assert Path(tmp_name).exists()
    r.close()
    assert not Path(tmp_name).exists()


def test_context_manager(card_db):
    from pathlib import Path
    with CardResolver(card_db) as r:
        tmp_name = r._tmp.name
        assert r.resolve(67330).name == "Llanowar Elves"
    assert not Path(tmp_name).exists()


def test_init_failure_leaves_no_temp_file(tmp_path, monkeypatch):
    import tempfile
    temp_dir = tmp_path / "tempdir"
    temp_dir.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temp_dir))
    with pytest.raises(OSError):
        CardResolver(tmp_path / "does_not_exist.mtga")
    assert list(temp_dir.iterdir()) == []


def test_unknown_grpid_returns_none(card_db):
    assert CardResolver(card_db).resolve(999999) is None


def test_find_card_db_missing_dir(tmp_path):
    with pytest.raises(FileNotFoundError):
        find_card_db(tmp_path / "nope")


def test_find_card_db_picks_newest(tmp_path):
    old = tmp_path / "Raw_CardDatabase_old.mtga"
    new = tmp_path / "Raw_CardDatabase_new.mtga"
    old.write_bytes(b"x")
    new.write_bytes(b"x")
    import os, time
    os.utime(old, (time.time() - 100, time.time() - 100))
    assert find_card_db(tmp_path) == new
