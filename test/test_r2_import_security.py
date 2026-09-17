#!/usr/bin/env python3

import re
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
IMPORT_DIR = ROOT_DIR / "import"
sys.path.insert(0, str(IMPORT_DIR))

import import_disqus_comments as importer


class FakeCursor:
    def __init__(self):
        self.calls = []
        self.lastrowid = 1

    def execute(self, query, params):
        self.calls.append((query, params))


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()
        self.committed = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True


def test_import_escape_matches_php_ent_compat_storage_invariant():
    value = '<script>alert("x")</script> & O\'Neil'

    escaped = importer.escape_comment_html(value)

    assert escaped == (
        "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; "
        "&amp; O'Neil"
    )


def test_imported_comments_are_escaped_unsubscribed_and_securely_tokenized():
    connection = FakeConnection()
    comment = importer.DisqusComment(
        id="post-1",
        thread_id="thread-1",
        author='<img src=x onerror="alert(1)">',
        reply_to=None,
        creation_date="2020-01-01T00:00:00",
        creation_date_timestamp="1577836800",
        content='<script>alert("x")</script>',
    )

    importer.insert_into_db(
        connection,
        {
            "thread-1": "https://example.com/article/",
        },
        [comment],
        "https://example.com",
        "https://example.com",
    )

    assert connection.committed is True
    assert len(connection.cursor_instance.calls) == 1

    query, params = connection.cursor_instance.calls[0]

    assert "subscribed, unsubscribe_token" in query
    assert "FALSE" in query
    assert params[0] == (
        "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;"
    )
    assert params[1] == (
        "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;"
    )
    assert params[3] == "https://example.com"
    assert params[4] == "/article/"
    assert re.fullmatch(r"[0-9a-f]{64}", params[5])
    assert params[6] == "1577836800"


def test_importer_uses_utf8mb4_for_database_connection():
    source = (
        ROOT_DIR / "import" / "import_disqus_comments.py"
    ).read_text(encoding="utf-8")

    assert "charset='utf8mb4'" in source
    assert "charset='utf8'" not in source
