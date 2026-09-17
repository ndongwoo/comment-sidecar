#!/usr/bin/env python3

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"


def test_phpinfo_endpoint_is_not_shipped():
    assert not (SRC_DIR / "phpinfo.php").exists()


def test_no_phpinfo_call_is_shipped_in_php_sources():
    for php_file in SRC_DIR.rglob("*.php"):
        source = php_file.read_text(encoding="utf-8")
        assert "phpinfo(" not in source, php_file
