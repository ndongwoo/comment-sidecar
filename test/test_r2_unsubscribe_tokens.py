#!/usr/bin/env python3

import os
import re

import requests
from mysql.connector import connect


BASE_URL = os.environ.get(
    "COMMENT_SIDECAR_BASE_URL",
    "http://localhost",
).rstrip("/")
COMMENT_URL = f"{BASE_URL}/comment-sidecar.php"

MYSQLDB_CONNECTION = {
    "host": "127.0.0.1",
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": "root",
    "passwd": "root",
    "db": "comment-sidecar",
}


def test_new_unsubscribe_token_is_256_bit_hex():
    db = connect(**MYSQLDB_CONNECTION)
    cur = db.cursor()
    cur.execute("TRUNCATE TABLE comments")
    cur.execute("TRUNCATE TABLE ip_addresses")
    db.commit()
    cur.close()
    db.close()

    response = requests.post(
        COMMENT_URL,
        json={
            "author": "Token Test",
            "email": "token@example.com",
            "content": "test",
            "site": "https://example.com",
            "path": "/token-test/",
        },
    )
    assert response.status_code == 201, response.text

    db = connect(**MYSQLDB_CONNECTION)
    cur = db.cursor()
    cur.execute(
        "SELECT unsubscribe_token FROM comments WHERE id = %s",
        (response.json()["id"],),
    )
    token = cur.fetchone()[0]
    cur.close()
    db.close()

    assert len(token) == 64
    assert re.fullmatch(r"[0-9a-f]{64}", token)
