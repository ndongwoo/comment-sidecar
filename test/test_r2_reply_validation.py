#!/usr/bin/env python3

import os

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


def base_payload():
    return {
        "author": "Reply Validation",
        "email": "",
        "content": "test",
        "site": "https://example.com",
        "path": "/reply-validation/",
    }


def test_invalid_reply_to_values_are_rejected_before_database_lookup():
    clean_database()

    invalid_values = [
        0,
        -1,
        1.5,
        True,
        [],
        {"id": 1},
        "1 OR 1=1",
        "1abc",
    ]

    for value in invalid_values:
        payload = base_payload()
        payload["replyTo"] = value

        response = requests.post(COMMENT_URL, json=payload)

        assert response.status_code == 400
        assert response.json()["message"] == (
            "replyTo must be a positive integer."
        )
