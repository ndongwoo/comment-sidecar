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

MAILHOG_BASE_URL = os.environ.get(
    "MAILHOG_BASE_URL",
    "http://localhost:8025/api/",
)
MAILHOG_MESSAGES_URL = MAILHOG_BASE_URL + "v2/messages"

MYSQLDB_CONNECTION = {
    "host": "127.0.0.1",
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": "root",
    "passwd": "root",
    "db": "comment-sidecar",
}


@pytest.fixture(autouse=True)
def clean_state():
    db = connect(**MYSQLDB_CONNECTION)
    cur = db.cursor()
    cur.execute("SET FOREIGN_KEY_CHECKS=0")
    cur.execute("TRUNCATE TABLE comments")
    cur.execute("TRUNCATE TABLE ip_addresses")
    cur.execute("SET FOREIGN_KEY_CHECKS=1")
    db.commit()
    cur.close()
    db.close()

    response = requests.delete(MAILHOG_BASE_URL + "v1/messages")
    assert response.status_code == 200


def payload():
    return {
        "author": "Header Test",
        "email": "header@example.com",
        "content": "test",
        "site": "https://example.com",
        "path": "/header-test/",
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("author", "Header Test\r\nBcc: injected@example.com"),
        ("email", "a@b.co\r\nBcc:x@y.co"),
        ("path", "/article/\r\nBcc: injected@example.com"),
    ],
)
def test_post_rejects_mail_header_newlines(field, value):
    post = payload()
    post[field] = value

    response = requests.post(COMMENT_URL, json=post)

    assert response.status_code == 400
    assert response.json()["message"] == (
        f"{field} must not contain line breaks."
    )

    db = connect(**MYSQLDB_CONNECTION)
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) FROM comments")
    assert cur.fetchone()[0] == 0
    cur.close()
    db.close()

    messages = requests.get(MAILHOG_MESSAGES_URL).json()
    assert messages["total"] == 0


def test_legacy_unsafe_recipient_is_not_passed_to_mail():
    parent_response = requests.post(
        COMMENT_URL,
        json={
            "author": "Parent",
            "email": "parent@example.com",
            "content": "parent",
            "site": "https://example.com",
            "path": "/article/",
        },
    )
    assert parent_response.status_code == 201, parent_response.text
    parent_id = parent_response.json()["id"]

    db = connect(**MYSQLDB_CONNECTION)
    cur = db.cursor()
    cur.execute(
        "UPDATE comments "
        "SET email = %s, subscribed = TRUE "
        "WHERE id = %s",
        ("a@b.co\r\nBcc:x@y.co", parent_id),
    )
    # This test exercises mail-header safety, not rate limiting.
    # The parent POST has already recorded this test client's IP, so clear
    # that independent state before creating the reply.
    cur.execute("TRUNCATE TABLE ip_addresses")
    db.commit()
    cur.close()
    db.close()

    clear = requests.delete(MAILHOG_BASE_URL + "v1/messages")
    assert clear.status_code == 200

    reply_response = requests.post(
        COMMENT_URL,
        json={
            "author": "Reply Author",
            "email": "reply@example.com",
            "content": "reply",
            "replyTo": parent_id,
            "site": "https://example.com",
            "path": "/article/",
        },
    )
    assert reply_response.status_code == 201, reply_response.text

    messages = requests.get(MAILHOG_MESSAGES_URL).json()
    assert messages["total"] == 1
    assert messages["items"][0]["Content"]["Headers"]["To"][0] == (
        "test@localhost.de"
    )
