#!/usr/bin/env python3

import os
from pathlib import Path

from mysql.connector import connect


ROOT_DIR = Path(__file__).resolve().parents[1]
MIGRATION_FILE = (
    ROOT_DIR / "sql" / "migrations" / "003_widen_unsubscribe_token.sql"
)

MYSQL_CONNECTION = {
    "host": "127.0.0.1",
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": "root",
    "passwd": "root",
}

TEST_DB = "comment_sidecar_r2_token_migration_test"


def test_unsubscribe_token_migration_preserves_legacy_tokens():
    admin = connect(**MYSQL_CONNECTION)
    admin.autocommit = True
    admin_cursor = admin.cursor()

    try:
        admin_cursor.execute(f"DROP DATABASE IF EXISTS `{TEST_DB}`")
        admin_cursor.execute(
            f"CREATE DATABASE `{TEST_DB}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )

        db = connect(**MYSQL_CONNECTION, db=TEST_DB)
        cursor = db.cursor()

        try:
            cursor.execute(
                """
                CREATE TABLE comments (
                    `id` int(11) NOT NULL PRIMARY KEY AUTO_INCREMENT,
                    `unsubscribe_token` varchar(10) NOT NULL
                ) ENGINE=InnoDB
                  DEFAULT CHARSET=utf8mb4
                  COLLATE=utf8mb4_unicode_ci
                """
            )
            cursor.execute(
                """
                INSERT INTO comments (unsubscribe_token)
                VALUES ('abcdefghij')
                """
            )
            db.commit()

            migration_sql = MIGRATION_FILE.read_text(encoding="utf-8")
            statements = [
                statement.strip()
                for statement in migration_sql.split(";")
                if statement.strip()
            ]
            for statement in statements:
                cursor.execute(statement)
            db.commit()

            cursor.execute(
                "SHOW COLUMNS FROM comments LIKE 'unsubscribe_token'"
            )
            column = cursor.fetchone()
            assert column is not None
            assert column[1].lower() == "varchar(64)"

            cursor.execute(
                "SELECT unsubscribe_token FROM comments WHERE id = 1"
            )
            assert cursor.fetchone()[0] == "abcdefghij"
        finally:
            cursor.close()
            db.close()
    finally:
        admin_cursor.execute(f"DROP DATABASE IF EXISTS `{TEST_DB}`")
        admin_cursor.close()
        admin.close()
