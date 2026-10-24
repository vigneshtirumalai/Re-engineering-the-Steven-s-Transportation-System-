from pathlib import Path

import pytest
import yaml

CLIENTS_DIR = Path(__file__).resolve().parent.parent / "clients"
CONFIGS = sorted(CLIENTS_DIR.glob("*/config.yaml"))
ID_FIELDS = {"zomato": "zomato_res_id", "swiggy": "swiggy_id"}


def _known_id(value):
    return value not in (None, "TODO")


def test_configs_exist():
    assert {p.parent.name for p in CONFIGS} == {"tempt", "tbs", "ck"}


@pytest.mark.parametrize("path", CONFIGS, ids=lambda p: p.parent.name)
def test_config_loads(path):
    config = yaml.safe_load(path.read_text())
    assert config["client"] == path.parent.name
    assert "legal_entity" in config
    assert isinstance(config["outlets"], list)


@pytest.mark.parametrize("path", CONFIGS, ids=lambda p: p.parent.name)
def test_no_platform_id_used_twice(path):
    config = yaml.safe_load(path.read_text())
    for platform, field in ID_FIELDS.items():
        ids = [o.get(field) for o in config["outlets"] if _known_id(o.get(field))]
        assert len(ids) == len(set(ids)), f"{platform} ID assigned to more than one outlet"


@pytest.mark.parametrize("path", CONFIGS, ids=lambda p: p.parent.name)
def test_excluded_ids_not_assigned(path):
    config = yaml.safe_load(path.read_text())
    for platform, entries in (config.get("excluded_ids") or {}).items():
        field = ID_FIELDS[platform]
        assigned = {o.get(field) for o in config["outlets"]}
        for entry in entries:
            assert entry["id"] not in assigned


def test_inbox_path_override(monkeypatch, tmp_path):
    import importlib
    import sys

    sys.path.insert(0, str(CLIENTS_DIR.parent / "scripts"))
    import paths

    monkeypatch.setenv("SECRET_SAUCE_INBOX", str(tmp_path))
    paths = importlib.reload(paths)
    assert paths.inbox("tempt", "zomato") == tmp_path / "tempt" / "zomato"
    monkeypatch.delenv("SECRET_SAUCE_INBOX")
    paths = importlib.reload(paths)
    assert paths.INBOX_DIR == paths.REPO_ROOT / "inbox"
