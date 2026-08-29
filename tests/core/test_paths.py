"""Testes do PathManager / resolução da raiz do projeto."""

from __future__ import annotations

from pathlib import Path

from radioskysims_core.paths import PathManager, get_project_root


def test_get_project_root_resolves_to_repo() -> None:
    root = get_project_root()
    assert (root / "pyproject.toml").exists() or (root / ".git").exists()


def test_path_manager_default_root() -> None:
    pm = PathManager()
    assert pm.root == get_project_root()
    assert pm.settings_file == pm.root / "settings.toml"
    assert pm.data_dir == pm.root / "data"


def test_path_manager_custom_root(tmp_path: Path) -> None:
    pm = PathManager(tmp_path)
    assert pm.root == tmp_path.resolve()
    assert pm.data_dir == tmp_path / "data"
    assert pm.src_dir == tmp_path / "src/radioskysims"


def test_path_manager_load_config(tmp_path: Path) -> None:
    settings = tmp_path / "settings.toml"
    settings.write_text('[demo]\nfoo = "bar"\n', encoding="utf-8")
    pm = PathManager(tmp_path)
    cfg = pm.load_config(settings)
    assert cfg["demo"]["foo"] == "bar"
