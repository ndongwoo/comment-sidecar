#!/usr/bin/env python3

import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import requests
from mysql.connector import connect

ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT_DIR / "src" / "config.php"
BASE_URL = os.environ.get("COMMENT_SIDECAR_BASE_URL", "http://localhost").rstrip("/")
COMMENT_URL = f"{BASE_URL}/comment-sidecar.php"
MYSQLDB_CONNECTION = {
    "host": "127.0.0.1",
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": "root",
    "passwd": "root",
    "db": "comment-sidecar",
}
RATE_LIMIT_RE = re.compile(r'const RATE_LIMIT_THRESHOLD_SECONDS = ".*?";')


def set_rate_limit_threshold(seconds):
    source = CONFIG_PATH.read_text(encoding="utf-8")
    updated = RATE_LIMIT_RE.sub(
        f'const RATE_LIMIT_THRESHOLD_SECONDS = "{seconds}";', source, count=1
    )
    assert updated != source
    CONFIG_PATH.write_text(updated, encoding="utf-8")


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


@pytest.fixture(autouse=True)
def isolated_rate_limit_window():
    original_config = CONFIG_PATH.read_text(encoding="utf-8")
    clean_database()
    set_rate_limit_threshold(60)
    try:
        yield
    finally:
        CONFIG_PATH.write_text(original_config, encoding="utf-8")
        clean_database()


def payload(content="rate-limit-test"):
    return {
        "author": "Rate Limit Test",
        "email": "",
        "content": content,
        "site": "https://example.com",
        "path": "/rate-limit-test/",
    }


def test_rate_limit_storage_is_pseudonymous():
    response = requests.post(COMMENT_URL, json=payload())
    assert response.status_code == 201, response.text
    db = connect(**MYSQLDB_CONNECTION)
    cur = db.cursor()
    cur.execute("SELECT ip_hash FROM ip_addresses")
    rows = cur.fetchall()
    cur.close()
    db.close()
    assert len(rows) == 1
    stored = rows[0][0]
    assert re.fullmatch(r"[0-9a-f]{64}", stored)
    assert stored != "127.0.0.1"


def test_concurrent_posts_reserve_rate_limit_atomically():
    barrier = threading.Barrier(2)
    def post_once(index):
        barrier.wait(timeout=5)
        return requests.post(
            COMMENT_URL,
            json=payload(content=f"concurrent-{index}"),
            timeout=10,
        )
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(post_once, [1, 2]))
    assert sorted(response.status_code for response in responses) == [201, 400]
    rejected = [response for response in responses if response.status_code == 400]
    assert rejected[0].json()["message"] == (
        "You have exceeded the maximal number of comments within a time frame."
    )
    db = connect(**MYSQLDB_CONNECTION)
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) FROM comments")
    assert cur.fetchone()[0] == 1
    cur.execute("SELECT COUNT(*) FROM ip_addresses")
    assert cur.fetchone()[0] == 1
    cur.close()
    db.close()
