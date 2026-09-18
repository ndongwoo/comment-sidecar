#!/usr/bin/env python3

import os
import re
from pathlib import Path

import pytest
import requests
from mysql.connector import connect


ROOT_DIR = Path(__file__).resolve().parents[1]
TRANSLATION_DIR = ROOT_DIR / "src" / "translations"

BASE_URL = os.environ.get(
    "COMMENT_SIDECAR_BASE_URL",
    "http://localhost",
).rstrip("/")
DELIVERY_URL = f"{BASE_URL}/comment-sidecar-js-delivery.php"
COMMENT_URL = f"{BASE_URL}/comment-sidecar.php"

MAILHOG_BASE_URL = os.environ.get(
    "MAILHOG_BASE_URL",
    "http://localhost:8025/api/",
)
MAILHOG_MESSAGES_URL = MAILHOG_BASE_URL + "v2/messages"
MAILHOG_DELETE_URL = MAILHOG_BASE_URL + "v1/messages"

MYSQLDB_CONNECTION = {
    "host": "127.0.0.1",
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": "root",
    "passwd": "root",
    "db": "comment-sidecar",
}

KEY_RE = re.compile(r"^\s*'([^']+)'\s*=>", re.MULTILINE)


def translation_keys(path):
    return set(KEY_RE.findall(path.read_text(encoding="utf-8")))


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


def clear_rate_limit():
    db = connect(**MYSQLDB_CONNECTION)
    cur = db.cursor()
    cur.execute("TRUNCATE TABLE ip_addresses")
    db.commit()
    cur.close()
    db.close()


def clear_mails():
    response = requests.delete(MAILHOG_DELETE_URL, timeout=10)
    assert response.status_code == 200


def decode_mailhog_utf8_body(value):
    try:
        return value.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


@pytest.fixture(autouse=True)
def isolated_state():
    clean_database()
    clear_mails()
    yield
    clean_database()
    clear_mails()


def base_payload():
    return {
        "author": "Multilingual Test",
        "email": "",
        "content": "test",
        "site": "https://example.com",
        "path": "/multilingual/",
        "url": "",
    }


def test_all_translation_files_have_the_same_keys():
    files = sorted(TRANSLATION_DIR.glob("*.php"))
    assert {path.stem for path in files} >= {"en", "de", "nl", "ko"}

    expected = translation_keys(TRANSLATION_DIR / "en.php")
    assert expected

    for path in files:
        assert translation_keys(path) == expected, path.name


def test_korean_widget_is_selected_per_embed():
    response = requests.get(
        DELIVERY_URL,
        params={"lang": "ko"},
        timeout=10,
    )

    assert response.status_code == 200
    assert response.headers["Content-Language"] == "ko"
    assert 'const LANGUAGE = "ko";' in response.text
    assert "댓글 작성..." in response.text
    assert "아직 댓글이 없습니다. 첫 댓글을 남겨보세요!" in response.text
    assert "language: LANGUAGE" in response.text


def test_locale_variant_falls_back_to_base_language():
    response = requests.get(
        DELIVERY_URL,
        params={"lang": "ko-KR"},
        timeout=10,
    )

    assert response.status_code == 200
    assert response.headers["Content-Language"] == "ko"
    assert "댓글 작성..." in response.text


def test_unavailable_language_falls_back_to_configured_default():
    response = requests.get(
        DELIVERY_URL,
        params={"lang": "fr"},
        timeout=10,
    )

    assert response.status_code == 200
    assert response.headers["Content-Language"] == "en"
    assert 'const LANGUAGE = "en";' in response.text
    assert "Write a Comment..." in response.text


def test_invalid_post_language_tag_is_rejected():
    payload = base_payload()
    payload["language"] = "../../ko"

    response = requests.post(
        COMMENT_URL,
        json=payload,
        timeout=10,
    )

    assert response.status_code == 400
    assert response.json()["message"] == (
        "language must be a valid language tag."
    )


def test_reply_notification_uses_korean_widget_language():
    parent = base_payload()
    parent["author"] = "Parent"
    parent["email"] = "parent@example.com"
    parent["content"] = "parent"

    parent_response = requests.post(
        COMMENT_URL,
        json=parent,
        timeout=10,
    )
    assert parent_response.status_code == 201, parent_response.text
    parent_id = parent_response.json()["id"]

    clear_rate_limit()
    clear_mails()

    reply = base_payload()
    reply["author"] = "Replier"
    reply["content"] = "reply"
    reply["replyTo"] = parent_id
    reply["language"] = "ko"

    response = requests.post(
        COMMENT_URL,
        json=reply,
        timeout=10,
    )
    assert response.status_code == 201, response.text

    messages = requests.get(
        MAILHOG_MESSAGES_URL,
        timeout=10,
    ).json()["items"]

    bodies = "\n".join(
        decode_mailhog_utf8_body(item["Content"]["Body"])
        for item in messages
    )

    assert "Parent님, 안녕하세요." in bodies
    assert "회원님의 댓글에 새 답글이 달렸습니다." in bodies
    assert "작성자: Replier" in bodies
    assert "이와 같은 이메일 알림을 더 이상 받지 않으려면" in bodies
