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


@pytest.fixture(autouse=True)
def clean_database():
    db = connect(**MYSQLDB_CONNECTION)
    cur = db.cursor()
    cur.execute("SET FOREIGN_KEY_CHECKS=0;")
    cur.execute("TRUNCATE TABLE comments;")
    cur.execute("TRUNCATE TABLE ip_addresses;")
    cur.execute("SET FOREIGN_KEY_CHECKS=1;")
    db.commit()
    cur.close()
    db.close()


def payload(site="https://site-a.example",
            path="/articles/current-url/",
            page_id=None):
    value = {
        "author": "Peter",
        "email": "",
        "content": "page-id test comment",
        "site": site,
        "path": path,
        "url": "",
    }
    if page_id is not None:
        value["pageId"] = page_id
    return value


def clear_rate_limit():
    db = connect(**MYSQLDB_CONNECTION)
    cur = db.cursor()
    cur.execute("TRUNCATE TABLE ip_addresses;")
    cur.close()
    db.close()


def post_comment(value):
    # These tests exercise thread identity, not rate limiting. Clear the
    # rate-limit state so multiple posts can be made deterministically
    # within a single test.
    clear_rate_limit()
    response = requests.post(COMMENT_URL, json=value)
    assert response.status_code == 201, response.text
    return response


def get_by_page_id(site, page_id):
    return requests.get(
        COMMENT_URL,
        params={"site": site, "pageId": page_id},
    )


def test_explicit_page_id_survives_path_change():
    site = "https://site-a.example"
    page_id = "article-2026-001"

    post_comment(payload(site, "/old-url/", page_id))

    response = get_by_page_id(site, page_id)
    assert response.status_code == 200
    assert len(response.json()) == 1

    post_comment(payload(site, "/new-url/", page_id))

    response = get_by_page_id(site, page_id)
    assert response.status_code == 200
    comments = response.json()
    assert len(comments) == 2


def test_same_page_id_is_isolated_by_site():
    page_id = "shared-id"

    post_comment(payload("https://site-a.example", "/a/", page_id))
    post_comment(payload("https://site-b.example", "/b/", page_id))

    response_a = get_by_page_id("https://site-a.example", page_id)
    response_b = get_by_page_id("https://site-b.example", page_id)

    assert len(response_a.json()) == 1
    assert len(response_b.json()) == 1


def test_different_page_ids_are_isolated_on_same_site_and_path():
    site = "https://site-a.example"
    path = "/same-path/"

    post_comment(payload(site, path, "article-a"))
    post_comment(payload(site, path, "article-b"))

    assert len(get_by_page_id(site, "article-a").json()) == 1
    assert len(get_by_page_id(site, "article-b").json()) == 1


def test_legacy_site_and_path_lookup_still_works():
    site = "https://site-a.example"
    path = "/legacy-page/"

    post_comment(payload(site, path))

    response = requests.get(
        COMMENT_URL,
        params={"site": site, "path": path},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_page_id_length_is_validated():
    value = payload(page_id="x" * 171)

    response = requests.post(COMMENT_URL, json=value)

    assert response.status_code == 400
    assert response.json()["message"] == \
        "pageId value exceeds maximal length of 170"
