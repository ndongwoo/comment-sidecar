#!/usr/bin/env python3

import os

import requests
from mysql.connector import connect


BASE_URL = os.environ.get(
    "COMMENT_SIDECAR_BASE_URL",
    "http://localhost",
).rstrip("/")

COMMENT_URL = f"{BASE_URL}/comment-sidecar.php"
UNSUBSCRIBE_URL = f"{BASE_URL}/unsubscribe.php"

MYSQLDB_CONNECTION = {
    "host": "127.0.0.1",
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": "root",
    "passwd": "root",
    "db": "comment-sidecar",
}

GENERIC_ERROR = {"message": "Internal server error."}
RENAMED_TABLE = "comments_r2_error_test"


def with_comments_table_temporarily_renamed(request_callable):
    db = connect(**MYSQLDB_CONNECTION)
    db.autocommit = True
    cur = db.cursor()

    try:
        cur.execute(f"DROP TABLE IF EXISTS `{RENAMED_TABLE}`")
        cur.execute(f"RENAME TABLE comments TO `{RENAMED_TABLE}`")
        return request_callable()
    finally:
        try:
            cur.execute(
                f"RENAME TABLE `{RENAMED_TABLE}` TO comments"
            )
        finally:
            cur.close()
            db.close()


def test_comment_endpoint_hides_internal_database_errors():
    response = with_comments_table_temporarily_renamed(
        lambda: requests.get(
            COMMENT_URL,
            params={
                "site": "https://example.com",
                "path": "/article/",
            },
        )
    )

    assert response.status_code == 500
    assert response.json() == GENERIC_ERROR


def test_unsubscribe_endpoint_hides_internal_database_errors():
    response = with_comments_table_temporarily_renamed(
        lambda: requests.get(
            UNSUBSCRIBE_URL,
            params={
                "commentId": "1",
                "unsubscribeToken": "not-a-real-token",
            },
        )
    )

    assert response.status_code == 500
    assert response.json() == GENERIC_ERROR
