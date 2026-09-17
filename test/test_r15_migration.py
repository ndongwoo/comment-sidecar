#!/usr/bin/env python3

import os
from pathlib import Path

from mysql.connector import connect


ROOT_DIR = Path(__file__).resolve().parents[1]
MIGRATION_FILES = [
    ROOT_DIR / "sql" / "migrations" / "001_add_page_id.sql",
    ROOT_DIR / "sql" / "migrations" / "002_widen_site.sql",
]

MYSQL_CONNECTION = {
    "host": "127.0.0.1",
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": "root",
    "passwd": "root",
}

TEST_DB = "comment_sidecar_r15_migration_test"


def test_page_id_migration_preserves_existing_comments():
    admin = connect(**MYSQL_CONNECTION)
    admin.autocommit = True
    admin_cursor = admin.cursor()

    try:
        admin_cursor.execute(f"DROP DATABASE IF EXISTS `{TEST_DB}`")
        admin_cursor.execute(
            f"CREATE DATABASE `{TEST_DB}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )

        db = connect(
            **MYSQL_CONNECTION,
            db=TEST_DB,
        )
        cursor = db.cursor()

        try:
            # Reproduce the comments table immediately before R1.5.
            cursor.execute(
                """
                CREATE TABLE comments (
                    `id` int(11) NOT NULL PRIMARY KEY AUTO_INCREMENT,
                    `author` varchar(40) NOT NULL,
                    `email` varchar(40) DEFAULT NULL,
                    `content` text NOT NULL,
                    `reply_to` int(11) DEFAULT NULL,
                    `site` varchar(40) NOT NULL,
                    `path` varchar(170) NOT NULL,
                    `subscribed` BOOL NOT NULL,
                    `unsubscribe_token` varchar(10) NOT NULL,
                    `creation_date` timestamp NOT NULL
                        DEFAULT CURRENT_TIMESTAMP()
                ) ENGINE=InnoDB
                  DEFAULT CHARSET=utf8mb4
                  COLLATE=utf8mb4_unicode_ci
                """
            )

            cursor.execute(
                """
                CREATE INDEX read_index
                    ON comments (`site`, `path`, `creation_date`)
                """
            )

            cursor.execute(
                """
                INSERT INTO comments
                    (author, email, content, reply_to, site, path,
                     subscribed, unsubscribe_token)
                VALUES
                    ('Existing Author', NULL, 'Existing comment', NULL,
                     'legacy-site', '/legacy-page/', FALSE, 'abcdefghij')
                """
            )
            db.commit()

            for migration_file in MIGRATION_FILES:
                migration_sql = migration_file.read_text(encoding="utf-8")
                statements = [
                    statement.strip()
                    for statement in migration_sql.split(";")
                    if statement.strip()
                ]

                for statement in statements:
                    cursor.execute(statement)

            db.commit()

            cursor.execute(
                "SHOW COLUMNS FROM comments LIKE 'page_id'"
            )
            column = cursor.fetchone()
            assert column is not None
            assert column[0] == "page_id"
            assert column[2] == "YES"

            cursor.execute(
                "SHOW COLUMNS FROM comments LIKE 'site'"
            )
            site_column = cursor.fetchone()
            assert site_column is not None
            assert site_column[1].lower() == "varchar(255)"


            cursor.execute(
                """
                SHOW INDEX FROM comments
                WHERE Key_name = 'explicit_thread_index'
                """
            )
            index_rows = cursor.fetchall()

            assert [row[4] for row in index_rows] == [
                "site",
                "page_id",
                "creation_date",
            ]

            cursor.execute(
                """
                SELECT author, content, site, path, page_id
                FROM comments
                WHERE id = 1
                """
            )
            row = cursor.fetchone()

            assert row == (
                "Existing Author",
                "Existing comment",
                "legacy-site",
                "/legacy-page/",
                None,
            )

        finally:
            cursor.close()
            db.close()

    finally:
        admin_cursor.execute(f"DROP DATABASE IF EXISTS `{TEST_DB}`")
        admin_cursor.close()
        admin.close()
