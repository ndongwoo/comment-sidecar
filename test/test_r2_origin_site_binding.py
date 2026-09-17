#!/usr/bin/env python3

import os

import pytest
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

ALLOWED_ORIGIN = "http://testdomain.com"


@pytest.fixture(autouse=True)
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


def payload(site=ALLOWED_ORIGIN):
    return {
        "author": "Origin Test",
        "email": "",
        "content": "test",
        "site": site,
        "path": "/origin-test/",
    }


def comment_count():
    db = connect(**MYSQLDB_CONNECTION)
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) FROM comments")
    count = cur.fetchone()[0]
    cur.close()
    db.close()
    return count


def test_matching_allowed_origin_can_post():
    response = requests.post(
        COMMENT_URL,
        json=payload(),
        headers={"Origin": ALLOWED_ORIGIN},
    )

    assert response.status_code == 201, response.text
    assert response.headers["Access-Control-Allow-Origin"] == ALLOWED_ORIGIN
    assert comment_count() == 1


def test_allowed_origin_cannot_write_another_site_namespace():
    response = requests.post(
        COMMENT_URL,
        json=payload(site="https://other.example"),
        headers={"Origin": ALLOWED_ORIGIN},
    )

    assert response.status_code == 403
    assert response.json()["message"] == (
        "Origin is not allowed to write to this site."
    )
    assert comment_count() == 0


def test_disallowed_origin_is_rejected_server_side():
    response = requests.post(
        COMMENT_URL,
        json=payload(site="http://invalid.com"),
        headers={"Origin": "http://invalid.com"},
    )

    assert response.status_code == 403
    assert response.json()["message"] == (
        "Origin is not allowed to write comments."
    )
    assert "Access-Control-Allow-Origin" not in response.headers
    assert comment_count() == 0


def test_request_without_origin_remains_supported_for_direct_clients():
    response = requests.post(
        COMMENT_URL,
        json=payload(site="https://direct-client.example"),
    )

    assert response.status_code == 201, response.text
    assert comment_count() == 1


def test_default_port_and_site_path_normalize_to_same_origin():
    response = requests.post(
        COMMENT_URL,
        json=payload(site="http://testdomain.com:80/blog"),
        headers={"Origin": ALLOWED_ORIGIN},
    )

    assert response.status_code == 201, response.text
    assert comment_count() == 1
