#!/usr/bin/env python3

import json
import os
import re
from pathlib import Path

import pytest
import requests
from mysql.connector import connect


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT_DIR / "src" / "config.php"
PROBE_PATH = ROOT_DIR / "src" / "_r21_cidr_probe.php"
OPCACHE_RESET_PATH = ROOT_DIR / "src" / "_r21_opcache_reset.php"

BASE_URL = os.environ.get(
    "COMMENT_SIDECAR_BASE_URL",
    "http://localhost",
).rstrip("/")
COMMENT_URL = f"{BASE_URL}/comment-sidecar.php"
PROBE_URL = f"{BASE_URL}/_r21_cidr_probe.php"
OPCACHE_RESET_URL = f"{BASE_URL}/_r21_opcache_reset.php"

MYSQLDB_CONNECTION = {
    "host": "127.0.0.1",
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": "root",
    "passwd": "root",
    "db": "comment-sidecar",
}

BLOCKLIST_RE = re.compile(
    r"const BLOCKED_IP_CIDRS = \[[^\]]*\];",
    re.DOTALL,
)


def clean_database():
    db = connect(**MYSQLDB_CONNECTION)
    cur = db.cursor()
    cur.execute("SET FOREIGN_KEY_CHECKS=0")
    cur.execute("TRUNCATE TABLE comments")
    cur.execute("TRUNCATE TABLE ip_addresses")
    cur.execute("SET FOREIGN_KEY_CHECKS=1")
    db.commit()
    cur.close()
    db.close()


def database_counts():
    db = connect(**MYSQLDB_CONNECTION)
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) FROM comments")
    comments = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM ip_addresses")
    rate_limits = cur.fetchone()[0]
    cur.close()
    db.close()
    return comments, rate_limits


def set_blocklist(entries):
    source = CONFIG_PATH.read_text(encoding="utf-8")
    encoded = ", ".join(json.dumps(entry) for entry in entries)
    replacement = f"const BLOCKED_IP_CIDRS = [ {encoded} ];"
    updated, count = BLOCKLIST_RE.subn(replacement, source, count=1)
    assert count == 1
    CONFIG_PATH.write_text(updated, encoding="utf-8")
    response = requests.get(OPCACHE_RESET_URL, timeout=10)
    assert response.status_code == 200, response.text


@pytest.fixture(autouse=True)
def isolated_config_and_database():
    original_config = CONFIG_PATH.read_text(encoding="utf-8")
    OPCACHE_RESET_PATH.write_text(
        """<?php
header("Content-Type: application/json; charset=UTF-8");
$result = function_exists("opcache_reset") ? opcache_reset() : null;
echo json_encode(["opcache_reset" => $result]);
""",
        encoding="utf-8",
    )
    clean_database()
    try:
        yield
    finally:
        CONFIG_PATH.write_text(original_config, encoding="utf-8")
        try:
            requests.get(OPCACHE_RESET_URL, timeout=10)
        finally:
            if PROBE_PATH.exists():
                PROBE_PATH.unlink()
            if OPCACHE_RESET_PATH.exists():
                OPCACHE_RESET_PATH.unlink()
        clean_database()


def payload():
    return {
        "author": "CIDR Test",
        "email": "",
        "content": "test",
        "site": "https://example.com",
        "path": "/cidr-test/",
    }


def test_cidr_matcher_handles_requested_ipv4_ranges_and_ipv6():
    PROBE_PATH.write_text(
        """<?php
include_once __DIR__ . "/common.php";
header("Content-Type: application/json; charset=UTF-8");
echo json_encode([
    "match" => ipMatchesCidr(
        $_GET["ip"] ?? "",
        $_GET["cidr"] ?? ""
    )
]);
""",
        encoding="utf-8",
    )

    cases = [
        ("77.238.12.34", "77.238.0.0/16", True),
        ("77.239.12.34", "77.238.0.0/16", False),
        ("87.199.255.254", "87.199.0.0/16", True),
        ("89.110.0.1", "89.110.0.0/16", True),
        ("2001:db8::1234", "2001:db8::/32", True),
        ("2001:db9::1", "2001:db8::/32", False),
    ]

    for ip, cidr, expected in cases:
        response = requests.get(
            PROBE_URL,
            params={"ip": ip, "cidr": cidr},
            timeout=10,
        )
        assert response.status_code == 200, response.text
        assert response.json()["match"] is expected


def test_blocked_client_is_rejected_before_storage_or_rate_limit():
    set_blocklist(["0.0.0.0/0", "::/0"])

    response = requests.post(
        COMMENT_URL,
        json=payload(),
        timeout=10,
    )

    assert response.status_code == 403
    assert response.json()["message"] == (
        "Comment posting is not allowed from this network."
    )
    assert database_counts() == (0, 0)


def test_nonmatching_cidr_list_allows_comment():
    set_blocklist(["192.0.2.0/24", "2001:db8::/32"])

    response = requests.post(
        COMMENT_URL,
        json=payload(),
        timeout=10,
    )

    assert response.status_code == 201, response.text
    assert database_counts()[0] == 1
