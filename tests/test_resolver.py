import pytest

from mtga_export.resolver import CardResolver, _mana_text, find_card_db


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


def test_hybrid_and_phyrexian_mana_costs():
    assert _mana_text("o2o(G/W)o(W/P)o(2/U)") == "{2}{G/W}{W/P}{2/U}"


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


def test_formatted1_only_name_resolved_and_stripped(card_db):
    # Most real cards have no Formatted=0 title row; the old query
    # (AND l.Formatted = 0) returned None for them, and without tag
    # stripping the name would keep the <nobr> markup.
    card = CardResolver(card_db).resolve(82000)
    assert card is not None
    assert card.name == "Half-Elf Monk"


def test_formatted0_preferred_when_both_exist(card_db):
    assert CardResolver(card_db).resolve(82001).name == "Plain Name"


def test_null_columns_resolve_without_crash(card_db):
    c = CardResolver(card_db).resolve(83000)
    assert c is not None
    assert c.name == "Null Heavy Card"
    assert c.set_code == ""
    assert c.collector_number == ""
    assert c.colors == []
    assert c.mana_cost == ""


def test_find_card_db_searches_steam_roots(tmp_path, monkeypatch):
    import mtga_export.resolver as resolver
    root = tmp_path / "steam-root"
    raw = root / resolver.RAW_SUBPATH
    raw.mkdir(parents=True)
    db = raw / "Raw_CardDatabase_abc.mtga"
    db.write_bytes(b"x")
    monkeypatch.setattr(resolver, "STEAM_ROOTS", [tmp_path / "missing", root])
    assert find_card_db() == db


def test_find_card_db_follows_libraryfolders_vdf(tmp_path, monkeypatch):
    import mtga_export.resolver as resolver
    root = tmp_path / "steam-root"
    (root / "steamapps").mkdir(parents=True)
    lib2 = tmp_path / "second-drive" / "SteamLibrary"
    raw = lib2 / resolver.RAW_SUBPATH
    raw.mkdir(parents=True)
    db = raw / "Raw_CardDatabase_abc.mtga"
    db.write_bytes(b"x")
    (root / "steamapps" / "libraryfolders.vdf").write_text(
        f'"libraryfolders"\n{{\n\t"1"\n\t{{\n\t\t"path"\t\t"{lib2}"\n\t}}\n}}\n'
    )
    monkeypatch.setattr(resolver, "STEAM_ROOTS", [root])
    assert find_card_db() == db


def test_find_card_db_error_lists_searched_paths(tmp_path, monkeypatch):
    import mtga_export.resolver as resolver
    monkeypatch.setattr(resolver, "STEAM_ROOTS", [tmp_path / "a", tmp_path / "b"])
    with pytest.raises(FileNotFoundError) as e:
        find_card_db()
    assert "--card-db" in str(e.value)
    assert str(tmp_path / "a") in str(e.value)
